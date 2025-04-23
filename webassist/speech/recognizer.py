"""
Speech recognition module for WebAssist
"""

from abc import ABC, abstractmethod
import asyncio
import speech_recognition as sr
from webassist.core.config import AssistantConfig


class SpeechRecognizer(ABC):
    """Abstract base class for speech recognizers"""

    @abstractmethod
    async def listen(self) -> str:
        """Listen for speech and return the recognized text"""

        pass


class SRRecognizer(SpeechRecognizer):
    """Speech recognizer using speech_recognition"""

    def __init__(self, config: AssistantConfig):
        """Initialize the recognizer"""
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.config = config

    async def listen(self) -> str:
        """Listen for speech and return the recognized text"""
        try:
            # Run the blocking speech recognition in a separate thread
            return await asyncio.to_thread(self._listen_sync)
        except Exception as e:
            print(f"Audio error: {e}")
            return ""

    def _listen_sync(self) -> str:
        """Synchronous listen method to run in a separate thread"""
        try:
            with self.microphone as source:
                print("\n🎤 Listening...")
                self.recognizer.adjust_for_ambient_noise(source)
                audio = self.recognizer.listen(
                    source,
                    timeout=5,
                    phrase_time_limit=10
                )
                return self.recognizer.recognize_google(audio).lower()
        except sr.UnknownValueError:
            return ""
        except Exception as e:
            print(f"Audio error: {e}")
            return ""


class TextInputRecognizer(SpeechRecognizer):
    """Text input as a fallback for speech recognition"""

    def __init__(self, config: AssistantConfig):
        """Initialize the recognizer"""
        self.config = config

    async def listen(self) -> str:
        """Get input from the user"""
        try:
            # Use a simpler approach with direct print and input
            print("\n⌨️ Command: ", end="", flush=True)
            # Run the blocking input in a separate thread
            user_input = await asyncio.to_thread(input)
            return user_input.strip()
        except Exception as e:
            print(f"Input error: {e}")
            return ""


# Factory function
def create_recognizer(config: AssistantConfig, mode: str = "voice") -> SpeechRecognizer:
    """Create a speech recognizer based on configuration and mode"""
    if mode.lower() == "voice":
        return SRRecognizer(config)
    else:
        return TextInputRecognizer(config)
