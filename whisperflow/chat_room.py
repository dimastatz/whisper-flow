""" 
Implements conversation loop: capture 
audio -> speech to text -> custom action -> text to speech -> play audio 
"""

import asyncio


class ChatRoom:
    """
    A class enabling real-time communication with microphone input and speaker output.
    It supports speech-to-text (STT) and text-to-speech (TTS) 
    processing, with an optional handler for custom text analysis.
    """

    def __init__(self):
        self.chat_started = False

    async def start_chat(self):
        """start chat by listening to mic"""
        self.chat_started = True
        while self.chat_started:
            await asyncio.sleep(0.01)

    def stop_chat(self):
        """stop chat and relase resources"""
        self.chat_started = False
