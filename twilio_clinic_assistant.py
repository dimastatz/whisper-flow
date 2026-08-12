#!/usr/bin/env python3
"""Twilio Voice webhook for a Czech clinic appointment assistant."""

from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Query
from fastapi.responses import PlainTextResponse


APP = FastAPI(title="Clinic Phone Assistant")
BASE_DIR = Path(__file__).resolve().parent
APPOINTMENTS_DB_PATH = BASE_DIR / "clinic_appointments.db"
LOW_CONFIDENCE_THRESHOLD = 0.65
COMMON_SPEECH_HINTS = (
    "praktický lékař,kontrola,preventivní prohlídka,odběry krve,recept,"
    "neschopenka,bolest,teplota,kašel,rýma,moč,pálení při močení,tlak,"
    "cukrovka,cholesterol,pondělí,úterý,středa,čtvrtek,pátek,dopoledne,"
    "odpoledne,ráno,zítra,příští týden"
)
STEP_SPEECH_HINTS = {
    "name": "jméno,příjmení,Novák,Nováková,Svoboda,Svobodová,Dvořák,Dvořáková",
    "reason": COMMON_SPEECH_HINTS,
    "time": (
        "dnes,zítra,pozítří,pondělí,úterý,středa,čtvrtek,pátek,"
        "ráno,dopoledne,poledne,odpoledne,večer,příští týden"
    ),
    "confirm": "ano,jo,správně,souhlas,ne,nesouhlas,špatně,jedna,dva",
}
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
CALL_STATE: dict[str, dict[str, str]] = {}


def xml_response(body: str) -> PlainTextResponse:
    return PlainTextResponse(
        '<?xml version="1.0" encoding="UTF-8"?>\n' + body,
        media_type="application/xml",
    )


def say(text: str) -> str:
    return f'<Say language="cs-CZ">{escape(text)}</Say>'


def gather(prompt: str, action: str, step: str) -> str:
    hints = STEP_SPEECH_HINTS.get(step, COMMON_SPEECH_HINTS)
    return (
        f'<Gather input="speech dtmf" language="cs-CZ" speechTimeout="auto" '
        f'timeout="8" action="{escape(action)}" method="POST" '
        f'hints="{escape(hints)}" profanityFilter="false">'
        f"{say(prompt)}"
        "</Gather>"
    )


def redirect(path: str) -> str:
    return f'<Redirect method="POST">{escape(path)}</Redirect>'


def normalize_input(speech_result: str | None, digits: str | None) -> str:
    if speech_result and speech_result.strip():
        return speech_result.strip()
    if digits and digits.strip():
        return digits.strip()
    return ""


def normalize_phone(phone: str) -> str:
    """Normalize phone numbers from form-encoded Twilio callbacks."""
    clean = phone.strip()
    if phone.startswith(" ") and clean.startswith("420"):
        return f"+{clean}"
    return clean


def parse_confidence(value: str | None) -> float | None:
    """Parse Twilio's optional Confidence value."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def should_repeat(
    step: str, confidence: float | None, call_state: dict[str, str]
) -> bool:
    """Repeat once when Twilio reports a low-confidence speech result."""
    if confidence is None or confidence >= LOW_CONFIDENCE_THRESHOLD:
        return False
    retry_key = f"{step}_retry"
    if call_state.get(retry_key) == "1":
        return False
    call_state[retry_key] = "1"
    return True


def store_answer(
    call_state: dict[str, str],
    field_name: str,
    answer: str,
    confidence: float | None,
) -> None:
    """Store the recognized text plus confidence for later review."""
    call_state[field_name] = answer
    if confidence is not None:
        call_state[f"{field_name}_confidence"] = f"{confidence:.3f}"


def raw_transcript(call_state: dict[str, str]) -> str:
    """Return per-field transcript details as JSON."""
    payload = {}
    for field_name in ("name", "reason", "requested_time"):
        payload[field_name] = {
            "text": call_state.get(field_name, ""),
            "confidence": call_state.get(f"{field_name}_confidence", ""),
        }
    return json.dumps(payload, ensure_ascii=False)


def init_database(db_path: Path | None = None) -> None:
    """Create or migrate the shared appointment database."""
    db_path = db_path or APPOINTMENTS_DB_PATH
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS call_recordings (
                call_sid TEXT PRIMARY KEY,
                recording_sid TEXT NOT NULL DEFAULT '',
                recording_url TEXT NOT NULL DEFAULT '',
                recording_status TEXT NOT NULL DEFAULT '',
                recording_duration TEXT NOT NULL DEFAULT '',
                recording_channels TEXT NOT NULL DEFAULT '',
                recording_track TEXT NOT NULL DEFAULT '',
                recording_start_time TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            )
            """
        )
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(appointments)").fetchall()
        }
        for column in (
            "call_sid",
            "name",
            "caller_phone",
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


def appointment_export_paths(db_path: Path | None = None) -> tuple[Path, Path]:
    """Return human-readable export paths next to the SQLite database."""
    db_path = db_path or APPOINTMENTS_DB_PATH
    return db_path.with_suffix(".json"), db_path.with_suffix(".csv")


def load_appointments() -> list[dict[str, Any]]:
    init_database()
    with sqlite3.connect(APPOINTMENTS_DB_PATH) as conn:
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
    return [{column: row[column] for column in APPOINTMENT_COLUMNS} for row in rows]


def export_appointments() -> None:
    """Export saved appointments to files that VS Code can display directly."""
    appointments = load_appointments()
    json_path, csv_path = appointment_export_paths()

    json_path.write_text(
        json.dumps(appointments, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=APPOINTMENT_COLUMNS)
        writer.writeheader()
        writer.writerows(appointments)


def save_appointment(appointment: dict[str, Any]) -> None:
    init_database()
    with sqlite3.connect(APPOINTMENTS_DB_PATH) as conn:
        conn.execute(
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
                appointment["created_at"],
                appointment.get("call_sid", ""),
                appointment.get("name", ""),
                appointment.get("caller_phone", ""),
                appointment.get("name_confidence", ""),
                appointment.get("reason", ""),
                appointment.get("reason_confidence", ""),
                appointment.get("requested_time", ""),
                appointment.get("requested_time_confidence", ""),
                appointment.get("status", "requested"),
                appointment.get("raw_transcript_json", ""),
                appointment.get("recording_sid", ""),
                appointment.get("recording_url", ""),
                appointment.get("recording_status", ""),
                appointment.get("recording_duration", ""),
                appointment.get("recording_channels", ""),
                appointment.get("recording_track", ""),
                appointment.get("recording_start_time", ""),
            ),
        )
    export_appointments()


def save_recording_metadata(recording: dict[str, str]) -> None:
    """Store Twilio call recording metadata and attach it to the appointment."""
    init_database()
    updated_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(APPOINTMENTS_DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO call_recordings (
                call_sid, recording_sid, recording_url, recording_status,
                recording_duration, recording_channels, recording_track,
                recording_start_time, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(call_sid) DO UPDATE SET
                recording_sid = excluded.recording_sid,
                recording_url = excluded.recording_url,
                recording_status = excluded.recording_status,
                recording_duration = excluded.recording_duration,
                recording_channels = excluded.recording_channels,
                recording_track = excluded.recording_track,
                recording_start_time = excluded.recording_start_time,
                updated_at = excluded.updated_at
            """,
            (
                recording.get("call_sid", ""),
                recording.get("recording_sid", ""),
                recording.get("recording_url", ""),
                recording.get("recording_status", ""),
                recording.get("recording_duration", ""),
                recording.get("recording_channels", ""),
                recording.get("recording_track", ""),
                recording.get("recording_start_time", ""),
                updated_at,
            ),
        )
        conn.execute(
            """
            UPDATE appointments
            SET recording_sid = ?,
                recording_url = ?,
                recording_status = ?,
                recording_duration = ?,
                recording_channels = ?,
                recording_track = ?,
                recording_start_time = ?
            WHERE call_sid = ?
            """,
            (
                recording.get("recording_sid", ""),
                recording.get("recording_url", ""),
                recording.get("recording_status", ""),
                recording.get("recording_duration", ""),
                recording.get("recording_channels", ""),
                recording.get("recording_track", ""),
                recording.get("recording_start_time", ""),
                recording.get("call_sid", ""),
            ),
        )
    export_appointments()


def state_for(call_sid: str) -> dict[str, str]:
    return CALL_STATE.setdefault(call_sid, {})


@APP.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@APP.api_route("/voice", methods=["GET", "POST"])
async def voice() -> PlainTextResponse:
    response = (
        "<Response>"
        + say(
            "Upozornění: pro přesné vyřízení bude tento hovor nahráván. "
            "Pokračováním s tím souhlasíte."
        )
        + gather(
            "Dobrý den, dovolali jste se do ordinace praktického lékaře. "
            "U telefonu je automatická sestra ordinace. "
            "Pomohu vám předat žádost o objednání. "
            "Mluvte prosím pomalu a krátce. "
            "Nejprve prosím řekněte své celé jméno.",
            "/voice/collect?step=name",
            "name",
        )
        + say("Neslyšel jsem odpověď. Zkusíme to ještě jednou.")
        + redirect("/voice")
        + "</Response>"
    )
    return xml_response(response)


@APP.post("/voice/collect")
async def collect(
    step: str = Query(...),
    CallSid: str = Form("unknown"),
    From: str = Form(""),
    SpeechResult: str | None = Form(None),
    Confidence: str | None = Form(None),
    Digits: str | None = Form(None),
) -> PlainTextResponse:
    answer = normalize_input(SpeechResult, Digits)
    confidence = parse_confidence(Confidence)
    call_state = state_for(CallSid)

    if not answer:
        return xml_response(
            "<Response>"
            + gather(
                "Neslyšel jsem vás dobře. Zopakujte to prosím.",
                f"/voice/collect?step={step}",
                step,
            )
            + say(
                "Omlouvám se, odpověď se nepodařilo rozpoznat. Zavolejte prosím později."
            )
            + "<Hangup/>"
            + "</Response>"
        )

    if should_repeat(step, confidence, call_state):
        return xml_response(
            "<Response>"
            + gather(
                "Nejsem si jistý, že jsem správně rozuměl. "
                "Řekněte to prosím ještě jednou, pomalu a krátce.",
                f"/voice/collect?step={step}",
                step,
            )
            + say("Omlouvám se, odpověď se nepodařilo rozpoznat.")
            + "<Hangup/>"
            + "</Response>"
        )

    if step == "name":
        store_answer(call_state, "name", answer, confidence)
        next_prompt = (
            f"Děkuji. Mám jméno {answer}. "
            "Teď mi prosím jednou krátkou větou řekněte důvod návštěvy."
        )
        return xml_response(
            "<Response>"
            + gather(next_prompt, "/voice/collect?step=reason", "reason")
            + say("Neslyšel jsem důvod návštěvy.")
            + redirect("/voice/collect?step=reason")
            + "</Response>"
        )

    if step == "reason":
        store_answer(call_state, "reason", answer, confidence)
        return xml_response(
            "<Response>"
            + gather(
                "Rozumím. Teď prosím řekněte, kdy by se vám termín hodil. "
                "Například zítra dopoledne, nebo příští úterý v deset.",
                "/voice/collect?step=time",
                "time",
            )
            + say("Neslyšel jsem požadovaný termín.")
            + redirect("/voice/collect?step=time")
            + "</Response>"
        )

    if step == "time":
        store_answer(call_state, "requested_time", answer, confidence)
        summary = (
            f"Rekapitulace. Jméno: {call_state.get('name', 'neuvedeno')}. "
            f"Důvod návštěvy: {call_state.get('reason', 'neuvedeno')}. "
            f"Požadovaný termín: {answer}. "
            "Pokud je to správně, řekněte ano nebo stiskněte jedničku. "
            "Pokud ne, řekněte ne nebo stiskněte dvojku."
        )
        return xml_response(
            "<Response>"
            + gather(summary, "/voice/collect?step=confirm", "confirm")
            + say("Potvrzení jsem neslyšel.")
            + redirect("/voice/collect?step=confirm")
            + "</Response>"
        )

    if step == "confirm":
        lowered = answer.lower()
        if any(word in lowered for word in ("ano", "jo", "správně", "souhlas", "1")):
            appointment = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "call_sid": CallSid,
                "caller_phone": normalize_phone(From),
                "name": call_state.get("name", ""),
                "name_confidence": call_state.get("name_confidence", ""),
                "reason": call_state.get("reason", ""),
                "reason_confidence": call_state.get("reason_confidence", ""),
                "requested_time": call_state.get("requested_time", ""),
                "requested_time_confidence": call_state.get(
                    "requested_time_confidence", ""
                ),
                "status": "requested",
                "raw_transcript_json": raw_transcript(call_state),
            }
            save_appointment(appointment)
            CALL_STATE.pop(CallSid, None)
            return xml_response(
                "<Response>"
                + say(
                    "Děkuji, žádost o objednání jsem uložil. "
                    "Pan doktor nebo sestřička vás bude kontaktovat s potvrzením "
                    "přesného termínu. Na shledanou."
                )
                + "<Hangup/>"
                + "</Response>"
            )

        CALL_STATE.pop(CallSid, None)
        return xml_response(
            "<Response>"
            + say("Dobře, začneme znovu.")
            + redirect("/voice")
            + "</Response>"
        )

    return xml_response(
        "<Response>"
        + say("Omlouvám se, nastala chyba v hovoru. Zavolejte prosím znovu.")
        + "<Hangup/>"
        + "</Response>"
    )


@APP.get("/appointments")
async def appointments() -> list[dict[str, Any]]:
    return load_appointments()


@APP.post("/recording-status")
async def recording_status(
    CallSid: str = Form(""),
    RecordingSid: str = Form(""),
    RecordingUrl: str = Form(""),
    RecordingStatus: str = Form(""),
    RecordingDuration: str = Form(""),
    RecordingChannels: str = Form(""),
    RecordingTrack: str = Form(""),
    RecordingStartTime: str = Form(""),
) -> dict[str, str]:
    """Receive Twilio recording status callbacks for whole-call recordings."""
    save_recording_metadata(
        {
            "call_sid": CallSid,
            "recording_sid": RecordingSid,
            "recording_url": RecordingUrl,
            "recording_status": RecordingStatus,
            "recording_duration": RecordingDuration,
            "recording_channels": RecordingChannels,
            "recording_track": RecordingTrack,
            "recording_start_time": RecordingStartTime,
        }
    )
    return {"status": "ok"}
