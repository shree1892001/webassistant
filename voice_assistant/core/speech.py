import pyttsx3
from typing import Optional
from voice_assistant.core.config import SpeechConfig

class SpeechEngine:
    def __init__(self, config: Optional[SpeechConfig] = None):
        self.config = config or SpeechConfig()
        self.engine = pyttsx3.init()
        self._configure_engine()

    def _configure_engine(self):
        """Configure the speech engine with the provided settings"""
        self.engine.setProperty('rate', self.config.rate)
        self.engine.setProperty('volume', self.config.volume)

    def speak(self, text: str) -> None:
        """Speak the given text and print it to console"""
        print(f"ASSISTANT: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

    def update_config(self, config: SpeechConfig) -> None:
        """Update the speech configuration"""
        self.config = config
        self._configure_engine() 