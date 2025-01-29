""" 
Implements conversation loop: capture 
audio -> speech to text -> custom action -> text to speech -> play audio 
"""

import queue
import asyncio


class ChatRoom:
    """
    A class enabling real-time communication with microphone input and speaker output.
    It supports speech-to-text (STT) and text-to-speech (TTS)
    processing, with an optional handler for custom text analysis.
    """

    def __init__(self, listener, speaker, processor):
        self.chat_started = False
        self.audio_chunks = queue.Queue()
        self.text_result = queue.Queue()
        self.listener = listener
        self.speaker = speaker
        self.processor = processor

    async def start_chat(self):
        """start chat by listening to mic"""

        async def start_control():
            while self.chat_started:
                await asyncio.sleep(0.01)

        self.chat_started = True

        # start listener and processor
        await asyncio.gather(
            start_control(),
            self.listener(self.audio_chunks),
            self.processor(self.audio_chunks, self.text_result),
            self.speaker(self.text_result),
        )

    def stop_chat(self):
        """stop chat and release resources"""
        self.chat_started = False
