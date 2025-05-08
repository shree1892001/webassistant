"""
Speech synthesis module for the Voice Assistant.
"""

import asyncio
import pyttsx3
from abc import ABC, abstractmethod

from webassist.core.config import AssistantConfig


class SpeechSynthesizer(ABC):
    """Abstract base class for speech synthesis"""

    @abstractmethod
    async def speak(self, text: str) -> None:
        """Speak the given text"""
        pass

    @abstractmethod
    async def set_rate(self, rate: int) -> None:
        """Set the speech rate"""
        pass

    @abstractmethod
    async def set_volume(self, volume: float) -> None:
        """Set the speech volume"""
        pass


class PyttsxSynthesizer(SpeechSynthesizer):
    """Speech synthesizer using pyttsx3"""

    def __init__(self, config: AssistantConfig):
        """Initialize the synthesizer"""
        self.engine = pyttsx3.init()
        self.config = config

        # Configure the engine
        self.engine.setProperty('rate', config.speech_rate)
        self.engine.setProperty('volume', config.speech_volume)

    async def speak(self, text: str) -> None:
        """Speak the given text"""
        # Always print the text to ensure it's visible even if speech fails
        print(f"ASSISTANT: {text}")
        try:
            # Run in a separate thread to avoid blocking
            await asyncio.to_thread(self._speak_sync, text)
        except Exception as e:
            print(f"Speech error (continuing anyway): {e}")

    def _speak_sync(self, text: str) -> None:
        """Synchronous speak method to run in a separate thread"""
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"Speech engine error: {e}")

    async def set_rate(self, rate: int) -> None:
        """Set the speech rate"""
        self.engine.setProperty('rate', rate)

    async def set_volume(self, volume: float) -> None:
        """Set the speech volume"""
        self.engine.setProperty('volume', volume)


def create_synthesizer(config: AssistantConfig) -> SpeechSynthesizer:
    """Create a speech synthesizer based on configuration"""
    return PyttsxSynthesizer(config)
