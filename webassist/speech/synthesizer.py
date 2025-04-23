"""
Speech synthesis module for WebAssist
"""

from abc import ABC, abstractmethod
import asyncio
import pyttsx3
from webassist.core.config import AssistantConfig


class SpeechSynthesizer(ABC):
    """Abstract base class for speech synthesizers"""

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

    @abstractmethod
    async def set_voice(self, voice_id) -> None:
        """Set the voice"""
        pass


class PyttsxSynthesizer(SpeechSynthesizer):
    """Speech synthesizer using pyttsx3"""

    def __init__(self, config: AssistantConfig):
        """Initialize the synthesizer"""
        self.engine = pyttsx3.init()
        self.config = config

        # Configure the engine
        voices = self.engine.getProperty('voices')
        voice_id = voices[config.speech_voice_id].id if config.speech_voice_id < len(voices) else voices[0].id

        self.engine.setProperty('voice', voice_id)
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

    async def set_voice(self, voice_id) -> None:
        """Set the voice"""
        voices = self.engine.getProperty('voices')
        if voice_id < len(voices):
            self.engine.setProperty('voice', voices[voice_id].id)


# Factory function
def create_synthesizer(config: AssistantConfig) -> SpeechSynthesizer:
    """Create a speech synthesizer based on configuration"""
    # Currently only supports pyttsx3
    return PyttsxSynthesizer(config)
