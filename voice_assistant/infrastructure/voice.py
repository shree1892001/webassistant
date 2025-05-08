import speech_recognition as sr
import pyttsx3
from typing import Dict, Any

class VoiceEngine:
    """Handles voice input and output"""
    
    def __init__(self, config: Dict[str, Any]):
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()
        
        # Configure voice engine
        if 'rate' in config:
            self.engine.setProperty('rate', config['rate'])
        if 'volume' in config:
            self.engine.setProperty('volume', config['volume'])
        if 'voice' in config:
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if config['voice'] in voice.name:
                    self.engine.setProperty('voice', voice.id)
                    break
    
    def speak(self, text: str) -> None:
        """Speak the given text"""
        self.engine.say(text)
        self.engine.runAndWait()
    
    async def listen(self) -> str:
        """Listen for voice input"""
        with sr.Microphone() as source:
            print("Listening...")
            audio = self.recognizer.listen(source)
            
            try:
                text = self.recognizer.recognize_google(audio)
                return text
            except sr.UnknownValueError:
                return ""
            except sr.RequestError as e:
                print(f"Could not request results; {e}")
                return ""
    
    def close(self) -> None:
        """Clean up resources"""
        self.engine.stop() 