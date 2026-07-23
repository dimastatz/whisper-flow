#!/usr/bin/env python3
"""Local real-time Czech voice assistant client for WhisperFlow."""

from __future__ import annotations

import argparse
import asyncio
import csv
import datetime as dt
import json
import queue
import re
import signal
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pyaudio
import torch
import whisper
import websockets
from omnivoice import OmniVoice


SAMPLE_RATE = 16000
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
SILENCE_THRESHOLD = 500
MIN_SPEECH_CHUNKS = 8
SILENCE_CHUNKS_TO_CLOSE = 12
TTS_SAMPLE_RATE = 24000
APPOINTMENT_COLUMNS = (
    "id",
    "created_at",
    "call_sid",
    "name",
    "caller_phone",
    "name_confidence",
    "reason",
    "reason_confidence",
    "requested_time",
    "requested_time_confidence",
    "status",
    "raw_transcript_json",
    "recording_sid",
    "recording_url",
    "recording_status",
    "recording_duration",
    "recording_channels",
    "recording_track",
    "recording_start_time",
)


@dataclass
class ClinicDialog:
    """Small deterministic appointment intake dialog."""

    db_path: Path
    step: str = "name"
    name: str = ""
    caller_phone: str = ""
    reason: str = ""
    requested_time: str = ""
    appointments: list[dict[str, str]] = field(default_factory=list)

    def greeting(self) -> str:
        """Return the first prompt for the caller."""
        return (
            "Dobrý den, dovolali jste se do ordinace praktického lékaře. "
            "Jsem hlasový asistent pro objednávání termínů. "
            "Nejprve mi prosím řekněte své celé jméno."
        )

    def handle(self, text: str) -> str:
        """Advance the intake dialog and return the next spoken response."""
        clean_text = clean_transcript(text)
        lower = clean_text.lower()

        if any(word in lower for word in ("konec", "ukončit", "nashledanou")):
            self.step = "done"
            return "Dobře, končím hovor. Na shledanou."

        if self.step == "name":
            self.name = clean_text
            self.step = "reason"
            return f"Děkuji. S čím k nám prosím jdete, {self.name}?"

        if self.step == "reason":
            self.reason = clean_text
            self.step = "time"
            return (
                "Rozumím. Kdy by se vám termín hodil? "
                "Řekněte prosím den a přibližný čas, například zítra dopoledne, "
                "nebo příští úterý v deset."
            )

        if self.step == "time":
            self.requested_time = clean_text
            appointment_id = save_appointment(
                self.db_path,
                self.name,
                self.reason,
                self.requested_time,
                self.caller_phone,
            )
            self.appointments.append(
                {
                    "id": str(appointment_id),
                    "name": self.name,
                    "caller_phone": self.caller_phone,
                    "reason": self.reason,
                    "requested_time": self.requested_time,
                }
            )
            self.step = "done"
            preparation = preparation_instructions(self.reason)
            return (
                "Děkuji, žádost o objednání jsem uložil. "
                f"Jméno: {self.name}. "
                f"Termín: {self.requested_time}. "
                f"Důvod návštěvy: {self.reason}. "
                f"{preparation} "
                "Ordinace vám termín ještě potvrdí. Děkujeme za zavolání. Na shledanou."
            )

        return "Hovor už je ukončený. Pro nový termín spusťte asistenta znovu."


def clean_transcript(text: str, max_len: int = 160) -> str:
    """Normalize and limit STT output before it reaches dialog/TTS."""
    clean = re.sub(r"\s+", " ", text).strip(" .,!?:;")
    parts = [part.strip() for part in re.split(r"[,.;]", clean) if part.strip()]
    deduped = []
    for part in parts:
        if not deduped or part.lower() != deduped[-1].lower():
            deduped.append(part)
    clean = ", ".join(deduped) if deduped else clean
    if len(clean) > max_len:
        clean = clean[:max_len].rsplit(" ", 1)[0]
    return clean or "neuvedeno"


def init_database(db_path: Path) -> None:
    """Create the appointment table if needed."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                call_sid TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL DEFAULT '',
                caller_phone TEXT NOT NULL DEFAULT '',
                name_confidence TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL,
                reason_confidence TEXT NOT NULL DEFAULT '',
                requested_time TEXT NOT NULL,
                requested_time_confidence TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                raw_transcript_json TEXT NOT NULL DEFAULT '',
                recording_sid TEXT NOT NULL DEFAULT '',
                recording_url TEXT NOT NULL DEFAULT '',
                recording_status TEXT NOT NULL DEFAULT '',
                recording_duration TEXT NOT NULL DEFAULT '',
                recording_channels TEXT NOT NULL DEFAULT '',
                recording_track TEXT NOT NULL DEFAULT '',
                recording_start_time TEXT NOT NULL DEFAULT ''
            )
            """
        )
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(appointments)").fetchall()
        }
        if "name" not in columns:
            conn.execute(
                "ALTER TABLE appointments ADD COLUMN name TEXT NOT NULL DEFAULT ''"
            )
        if "caller_phone" not in columns:
            conn.execute(
                "ALTER TABLE appointments ADD COLUMN caller_phone TEXT NOT NULL DEFAULT ''"
            )
        for column in (
            "call_sid",
            "name_confidence",
            "reason_confidence",
            "requested_time_confidence",
            "raw_transcript_json",
            "recording_sid",
            "recording_url",
            "recording_status",
            "recording_duration",
            "recording_channels",
            "recording_track",
            "recording_start_time",
        ):
            if column not in columns:
                conn.execute(
                    f"ALTER TABLE appointments ADD COLUMN {column} TEXT NOT NULL DEFAULT ''"
                )
    export_appointments(db_path)


def appointment_export_paths(db_path: Path) -> tuple[Path, Path]:
    """Return human-readable export paths next to the SQLite database."""
    return db_path.with_suffix(".json"), db_path.with_suffix(".csv")


def load_saved_appointments(db_path: Path) -> list[dict[str, str]]:
    """Read saved appointments from SQLite in a stable column order."""
    if not db_path.exists():
        return []

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                id, created_at, call_sid, name, caller_phone, name_confidence,
                reason, reason_confidence, requested_time,
                requested_time_confidence, status, raw_transcript_json,
                recording_sid, recording_url, recording_status, recording_duration,
                recording_channels, recording_track, recording_start_time
            FROM appointments
            ORDER BY id
            """
        ).fetchall()

    return [
        {column: str(row[column]) for column in APPOINTMENT_COLUMNS} for row in rows
    ]


def export_appointments(db_path: Path) -> None:
    """Export SQLite appointments to JSON and CSV files readable in VS Code."""
    appointments = load_saved_appointments(db_path)
    json_path, csv_path = appointment_export_paths(db_path)

    json_path.write_text(
        json.dumps(appointments, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=APPOINTMENT_COLUMNS)
        writer.writeheader()
        writer.writerows(appointments)


def save_appointment(
    db_path: Path,
    name: str,
    reason: str,
    requested_time: str,
    caller_phone: str = "",
) -> int:
    """Persist an appointment request and return its id."""
    init_database(db_path)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO appointments (
                created_at, call_sid, name, caller_phone, name_confidence,
                reason, reason_confidence, requested_time,
                requested_time_confidence, status, raw_transcript_json,
                recording_sid, recording_url, recording_status, recording_duration,
                recording_channels, recording_track, recording_start_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dt.datetime.now().isoformat(timespec="seconds"),
                "",
                name,
                caller_phone,
                "",
                reason,
                "",
                requested_time,
                "",
                "requested",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ),
        )
        appointment_id = int(cursor.lastrowid)
    export_appointments(db_path)
    return appointment_id


def preparation_instructions(reason: str) -> str:
    """Return short pre-visit instructions based on the appointment reason."""
    lower = reason.lower()
    base = "Vezměte si prosím kartičku pojišťovny, občanský průkaz a seznam léků."
    urine_keywords = ("moč", "močí", "močový", "pálení", "ledvin", "urolog", "cukr")
    blood_keywords = ("krev", "odběr", "preventiv", "kontrola", "cukrov")

    if any(keyword in lower for keyword in urine_keywords):
        return (
            base + " Pokud jdete kvůli moči nebo pálení při močení, "
            "přineste prosím ranní vzorek moči v čisté nádobce."
        )
    if any(keyword in lower for keyword in blood_keywords):
        return base + " Pokud půjdete na odběry krve, přijďte prosím nalačno."
    return base


def choose_input_device(audio: pyaudio.PyAudio, preferred: str | None) -> int | None:
    """Choose an input device by substring, otherwise first available input."""
    fallback = None
    for index in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(index)
        if info.get("maxInputChannels", 0) <= 0:
            continue
        if fallback is None:
            fallback = index
        if preferred and preferred.lower() in str(info.get("name", "")).lower():
            return index
    return fallback


def choose_output_device(audio: pyaudio.PyAudio, preferred: str | None) -> int | None:
    """Choose an output device by substring, otherwise first available output."""
    fallback = None
    for index in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(index)
        if info.get("maxOutputChannels", 0) <= 0:
            continue
        if fallback is None:
            fallback = index
        if preferred and preferred.lower() in str(info.get("name", "")).lower():
            return index
    return fallback


def pick_omnivoice_device() -> str:
    """Select the best local device supported by OmniVoice/PyTorch."""
    if torch.cuda.is_available():
        return "cuda:0"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def pick_omnivoice_dtype(device: str) -> torch.dtype:
    """Use float16 only where the backend reliably supports it."""
    return torch.float16 if device.startswith("cuda") else torch.float32


class OmniVoiceSpeaker:
    """Generate assistant responses with OmniVoice and play them locally."""

    def __init__(self, instruct: str | None, output_device: str | None):
        self.instruct = instruct
        self.audio = pyaudio.PyAudio()
        self.output_device_index = choose_output_device(self.audio, output_device)
        if self.output_device_index is None:
            self.audio.terminate()
            raise RuntimeError("PortAudio nevidí žádné výstupní audio zařízení.")

        device = self.audio.get_device_info_by_index(self.output_device_index)
        print(f"REPRODUKTOR: {device.get('name')}")

        ov_device = pick_omnivoice_device()
        print(f"Načítám OmniVoice na {ov_device}...")
        self.model = OmniVoice.from_pretrained(
            "k2-fsa/OmniVoice",
            device_map=ov_device,
            dtype=pick_omnivoice_dtype(ov_device),
            load_asr=False,
        )

    def speak(self, text: str) -> None:
        """Generate Czech speech with OmniVoice and play it via PyAudio."""
        print(f"ASISTENT: {text}")
        kwargs = {"text": text, "language": "Czech"}
        if self.instruct:
            kwargs["instruct"] = self.instruct
        audio = self.model.generate(**kwargs)
        samples = np.asarray(audio[0], dtype=np.float32).reshape(-1)
        pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16).tobytes()

        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=TTS_SAMPLE_RATE,
            output=True,
            output_device_index=self.output_device_index,
        )
        try:
            stream.write(pcm)
        finally:
            stream.stop_stream()
            stream.close()

    def close(self) -> None:
        """Release PortAudio resources."""
        self.audio.terminate()


def start_microphone(
    chunks: queue.Queue[bytes],
    stop_event: threading.Event,
    capture_enabled: threading.Event,
    preferred_device: str | None,
) -> tuple[pyaudio.PyAudio, pyaudio.Stream]:
    """Start a blocking PyAudio input stream in the current process."""
    audio = pyaudio.PyAudio()
    device_index = choose_input_device(audio, preferred_device)
    if device_index is None:
        audio.terminate()
        raise RuntimeError("PortAudio nevidí žádné vstupní audio zařízení.")

    device = audio.get_device_info_by_index(device_index)
    print(f"MIKROFON: {device.get('name')}")
    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=CHUNK_SIZE,
    )

    def read_loop() -> None:
        while not stop_event.is_set():
            try:
                data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                if capture_enabled.is_set():
                    chunks.put(data)
            except OSError as error:
                print(f"Chyba mikrofonu: {error}")
                stop_event.set()

    threading.Thread(target=read_loop, daemon=True).start()
    return audio, stream


def drain_queue(chunks: queue.Queue[bytes]) -> None:
    """Drop queued microphone audio."""
    while True:
        try:
            chunks.get_nowait()
        except queue.Empty:
            return


def speak_without_feedback(
    speaker: OmniVoiceSpeaker,
    text: str,
    chunks: queue.Queue[bytes],
    capture_enabled: threading.Event,
) -> None:
    """Speak while microphone capture is paused, then clear echo residue."""
    capture_enabled.clear()
    drain_queue(chunks)
    speaker.speak(text)
    time.sleep(0.25)
    drain_queue(chunks)
    capture_enabled.set()


async def send_audio(
    websocket, chunks: queue.Queue[bytes], stop_event: threading.Event
):
    """Send queued microphone chunks to WhisperFlow."""
    while not stop_event.is_set():
        try:
            chunk = chunks.get(timeout=0.1)
        except queue.Empty:
            await asyncio.sleep(0.01)
            continue
        await websocket.send(chunk)


async def receive_transcripts(
    websocket, dialog: ClinicDialog, speaker: OmniVoiceSpeaker
):
    """Handle final transcript segments and speak dialog responses."""
    async for message in websocket:
        event = json.loads(message)
        text = event.get("data", {}).get("text", "").strip()
        if not text:
            continue
        marker = "..." if event.get("is_partial") else ""
        print(f"VY{marker}: {text}")
        if not event.get("is_partial"):
            response = dialog.handle(text)
            speaker.speak(response)
            if dialog.step == "done":
                return


async def run(args: argparse.Namespace) -> None:
    """Run the local voice assistant."""
    chunks: queue.Queue[bytes] = queue.Queue()
    stop_event = threading.Event()
    capture_enabled = threading.Event()
    audio = None
    stream = None
    speaker = None
    dialog = ClinicDialog(Path(args.database), caller_phone=args.caller_phone or "")

    def handle_signal(_signum, _frame):
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        speaker = OmniVoiceSpeaker(args.tts_instruct, args.output_device)
        audio, stream = start_microphone(
            chunks, stop_event, capture_enabled, args.device
        )
        speak_without_feedback(speaker, dialog.greeting(), chunks, capture_enabled)

        async with websockets.connect(args.ws_url) as websocket:
            sender = asyncio.create_task(send_audio(websocket, chunks, stop_event))
            receiver = asyncio.create_task(
                receive_transcripts(websocket, dialog, speaker)
            )
            done, pending = await asyncio.wait(
                {sender, receiver}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            for task in done:
                task.result()
    finally:
        stop_event.set()
        if stream:
            stream.stop_stream()
            stream.close()
        if audio:
            audio.terminate()
        if speaker:
            speaker.close()


def transcribe_audio(model, chunks: list[bytes]) -> str:
    """Transcribe int16 PCM chunks using local Whisper."""
    samples = (
        np.frombuffer(b"".join(chunks), dtype=np.int16).astype(np.float32) / 32768.0
    )
    result = model.transcribe(samples, language="cs", fp16=False, temperature=0.0)
    return result.get("text", "").strip()


# pylint: disable-next=too-many-locals,too-many-statements
def run_direct(
    args: argparse.Namespace,
) -> None:
    """Run without WebSocket: mic -> local Whisper -> local TTS."""
    chunks: queue.Queue[bytes] = queue.Queue()
    stop_event = threading.Event()
    capture_enabled = threading.Event()
    audio = None
    stream = None
    speaker = None
    dialog = ClinicDialog(Path(args.database), caller_phone=args.caller_phone or "")
    speech_chunks: list[bytes] = []
    silent_chunks = 0
    has_speech = False

    def handle_signal(_signum, _frame):
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    print(f"Načítám Whisper model {args.stt_model}...")
    model = whisper.load_model(f"whisperflow/models/{args.stt_model}")

    try:
        speaker = OmniVoiceSpeaker(args.tts_instruct, args.output_device)
        audio, stream = start_microphone(
            chunks, stop_event, capture_enabled, args.device
        )
        speak_without_feedback(speaker, dialog.greeting(), chunks, capture_enabled)
        print("Poslouchám. Mluvte česky, po větě udělejte krátkou pauzu.")

        while not stop_event.is_set() and dialog.step != "done":
            try:
                chunk = chunks.get(timeout=0.1)
            except queue.Empty:
                continue

            level = int(np.max(np.abs(np.frombuffer(chunk, dtype=np.int16))))
            if level > args.silence_threshold:
                has_speech = True
                silent_chunks = 0
                speech_chunks.append(chunk)
                continue

            if has_speech:
                silent_chunks += 1
                speech_chunks.append(chunk)

            if (
                has_speech
                and silent_chunks >= args.silence_chunks
                and len(speech_chunks) >= args.min_speech_chunks
            ):
                utterance = speech_chunks[:]
                speech_chunks = []
                silent_chunks = 0
                has_speech = False

                text = transcribe_audio(model, utterance)
                if not text:
                    continue
                print(f"VY: {text}")
                response = dialog.handle(text)
                speak_without_feedback(speaker, response, chunks, capture_enabled)

        if dialog.appointments:
            print(f"ULOŽENO: {dialog.appointments[-1]}")
    finally:
        stop_event.set()
        if stream:
            stream.stop_stream()
            stream.close()
        if audio:
            audio.terminate()
        if speaker:
            speaker.close()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the clinic assistant."""
    parser = argparse.ArgumentParser(description="Talk to the clinic assistant.")
    parser.add_argument("--ws-url", default="ws://127.0.0.1:8181/ws")
    parser.add_argument("--device", help="Substring of input device name")
    parser.add_argument("--output-device", help="Substring of output device name")
    parser.add_argument(
        "--stt-model",
        default="base.pt",
        help="Whisper model file from whisperflow/models, e.g. tiny.pt or base.pt.",
    )
    parser.add_argument(
        "--tts-instruct",
        default="female, moderate pitch",
        help="OmniVoice instruction. Use supported items only.",
    )
    parser.add_argument(
        "--database",
        default="clinic_appointments.db",
        help="SQLite database for saved appointment requests.",
    )
    parser.add_argument(
        "--caller-phone",
        default="",
        help="Phone number to save with the appointment when known.",
    )
    parser.add_argument("--websocket", action="store_true", help="Use WhisperFlow /ws")
    parser.add_argument("--silence-threshold", type=int, default=SILENCE_THRESHOLD)
    parser.add_argument("--min-speech-chunks", type=int, default=MIN_SPEECH_CHUNKS)
    parser.add_argument("--silence-chunks", type=int, default=SILENCE_CHUNKS_TO_CLOSE)
    return parser.parse_args()


if __name__ == "__main__":
    parsed_args = parse_args()
    if parsed_args.websocket:
        asyncio.run(run(parsed_args))
    else:
        run_direct(parsed_args)
