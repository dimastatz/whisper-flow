""" 
Implements conversation loop: capture 
audio -> speech to text -> custom action -> text to speech -> play audio 
"""

import queue
import asyncio
import pytest
import whisperflow.audio.microphone as mic


class ChatRoom:
    """
    A class enabling real-time communication with microphone input and speaker output.
    It supports speech-to-text (STT) and text-to-speech (TTS)
    processing, with an optional handler for custom text analysis.
    """

    def __init__(self, listener, speaker, processor):
        self.audio_chunks = queue.Queue()
        self.text_result = queue.Queue()
        self.listener = listener
        self.speaker = speaker
        self.processor = processor
        self.stop_chat_event = asyncio.Event()

    async def start_chat(self):
        """start chat by listening to mic"""
        self.stop_chat_event.clear()

        # start listener and processor
        await asyncio.gather(
            self.listener(self.audio_chunks, self.stop_chat_event),
            self.processor(self.audio_chunks, self.text_result, self.stop_chat_event),
            self.speaker(self.text_result, self.stop_chat_event),
        )

    def stop_chat(self):
        """stop chat and release resources"""
        self.stop_chat_event.set()
        assert self.stop_chat_event.is_set()


@pytest.mark.skip(reason="requires audio hardware")
def main():
    # Create a dummy processor
    async def dummy_proc(audio: queue.Queue, text: queue.Queue, stop: asyncio.Event):
        """dummy processor"""
        while not stop.is_set():
            if not audio.empty():
                data = audio.get()
                text.put(data)
            await asyncio.sleep(0.001)

    chat_room = ChatRoom(mic.capture_audio, mic.play_audio, dummy_proc)

    try:
        # Run the async main function
        chat_room.start_chat()
    except KeyboardInterrupt:
        chat_room.stop_chat()
        print("Chat stopped")


if __name__ == "__main__":
    main()
