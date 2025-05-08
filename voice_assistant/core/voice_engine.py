import pyttsx3
import speech_recognition as sr
from typing import Optional

class VoiceEngine:
    """Handles all voice-related functionality"""
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.engine = None
        self.recognizer = None
        self.microphone = None
        self._initialize_components()

    def _initialize_components(self):
        """Initialize speech components"""
        # Initialize text-to-speech
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', self.config.get('speech_rate', 150))
        self.engine.setProperty('volume', self.config.get('speech_volume', 1.0))

        # Initialize speech recognition
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

    def speak(self, text: str) -> None:
        """Speak the given text"""
        print(f"ASSISTANT: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

    def listen(self) -> str:
        """Listen for voice input"""
        try:
            with self.microphone as source:
                print("Listening...")
                audio = self.recognizer.listen(source)
                text = self.recognizer.recognize_google(audio)
                print(f"USER: {text}")
                return text
        except sr.UnknownValueError:
            print("Could not understand audio")
            return ""
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
            return ""
        except Exception as e:
            print(f"Audio error: {e}")
            return ""

    def close(self) -> None:
        """Clean up resources"""
        if self.engine:
            self.engine.stop() 