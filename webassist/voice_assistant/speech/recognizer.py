"""
Speech recognition module for the Voice Assistant.
"""

import asyncio
import speech_recognition as sr
from abc import ABC, abstractmethod

from webassist.core.config import AssistantConfig


class SpeechRecognizer(ABC):
    """Abstract base class for speech recognition"""

    @abstractmethod
    async def listen(self) -> str:
        """Listen for speech and return the recognized text"""
        pass

    @abstractmethod
    async def set_mode(self, mode: str) -> None:
        """Set the recognition mode"""
        pass


class SRRecognizer(SpeechRecognizer):
    """Speech recognizer using speech_recognition"""

    def __init__(self, config: AssistantConfig, speak_func=None):
        """Initialize the recognizer"""
        try:
            print("Initializing speech recognizer...")
            self.recognizer = sr.Recognizer()
            print("Testing microphone availability...")
            try:
                self.microphone = sr.Microphone()
                with self.microphone as source:
                    print("Microphone initialized successfully")
                    # Adjust for ambient noise
                    print("Adjusting for ambient noise...")
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                    print("Ambient noise adjustment complete")
            except Exception as e:
                print(f"Error initializing microphone: {e}")
                raise
                self.config = config
                self.speak = speak_func
                self.mode = "voice"
                print("Speech recognizer initialized successfully")
        except Exception as e:
            print(f"Error in speech recognizer initialization: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def listen(self) -> str:
        """Listen for speech and return the recognized text"""
        try:
            print("Starting voice recognition...")
            # Run the blocking speech recognition in a separate thread
            return await asyncio.to_thread(self._listen_sync)
        except Exception as e:
            print(f"Audio error in listen(): {e}")
            import traceback
            traceback.print_exc()
            return ""

    def _listen_sync(self) -> str:
        """Synchronous voice listening method to run in a separate thread"""
        try:
            print("Initializing microphone for listening...")
            with self.microphone as source:
                print("\n" + "=" * 50)
                print("🎤 LISTENING FOR VOICE COMMAND...")
                print("=" * 50)

                # More aggressive noise adjustment for better recognition
                print("Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1.0)

                # Increase timeout and phrase_time_limit for better recognition
                print("Ready! Please speak your command now.")

                # Use a longer timeout and phrase time limit to ensure we capture the full command
                audio = self.recognizer.listen(source, timeout=15, phrase_time_limit=20)

                print("\n" + "-" * 50)
                print("🔍 RECOGNIZING SPEECH...")
                print("-" * 50)

                # Try Google's speech recognition service with increased sensitivity
                # Set the energy threshold lower to pick up quieter speech
                original_energy_threshold = self.recognizer.energy_threshold
                self.recognizer.energy_threshold = 300  # Lower threshold for better sensitivity

                # Try with language hint for better accuracy
                text = self.recognizer.recognize_google(
                    audio,
                    language="en-US",
                    show_all=False  # Set to True for debugging
                ).lower()

                # Restore original energy threshold
                self.recognizer.energy_threshold = original_energy_threshold

                # Display the recognized text prominently with enhanced visual feedback
                print("\n" + "*" * 60)
                print("*" + " " * 58 + "*")
                print("*" + f"🎯 RECOGNIZED COMMAND: \"{text}\"".center(58) + "*")
                print("*" + " " * 58 + "*")
                print("*" * 60)

                # Provide feedback on command type detection
                command_type = self._detect_command_type(text.lower())
                if command_type:
                    print(f"📋 Command type detected: {command_type}")
                    print(f"⚙️ Will execute as: {command_type} command")
                else:
                    print("⚠️ Unknown command type - will try to process anyway")

                # Check for mode switching command with more flexible matching
                text_mode_commands = ["text", "text mode", "switch to text", "switch to text mode",
                                     "text input", "type mode", "typing mode", "keyboard", "keyboard mode"]

                # Check if any of the text mode commands are in the recognized text
                if any(cmd in text.lower() for cmd in text_mode_commands) or "text" == text.lower():
                    self.mode = "text"
                    if self.speak:
                        # Can't use await in a synchronous function, so we'll handle this differently
                        print("ASSISTANT: Switched to text mode")
                    print("🔄 Mode switch command detected: Switching to text mode")
                    return "switch_to_text_mode"  # Special return value for mode switching

                # Log the recognized text to help with debugging
                print(f"DEBUG: Returning recognized text: '{text}'")
                return text
        except sr.UnknownValueError:
            print("\n" + "!" * 50)
            print("❌ SPEECH NOT RECOGNIZED. Please try again.")
            print("!" * 50)
            print("\nTips for better recognition:")
            print("- Speak clearly and directly into the microphone")
            print("- Reduce background noise if possible")
            print("- Try speaking at a moderate pace")
            print("- Make sure your microphone is working properly")
            print("\n🔄 Listening again automatically in 2 seconds...")
            import time
            time.sleep(2)  # Short pause before trying again
            return "retry_voice_recognition"  # Special return value to trigger retry
        except sr.RequestError as e:
            print("\n" + "!" * 50)
            print(f"❌ SPEECH RECOGNITION SERVICE ERROR: {e}")
            print("!" * 50)
            print("\nTrying alternative recognition method...")

            try:
                # Try with a different recognition service as backup
                print("🔄 Using alternative speech recognition service...")
                # Try Sphinx as a fallback (offline recognition)
                text = self.recognizer.recognize_sphinx(audio)
                print(f"🎯 Recognized with alternative service: \"{text}\"")
                return text.lower()
            except:
                # If that also fails, fall back to text input
                print("\nAll speech recognition methods failed. Falling back to text input...")
                return input("\n⌨️ Command: ").strip()
        except Exception as e:
            print("\n" + "!" * 50)
            print(f"❌ AUDIO ERROR: {e}")
            print("!" * 50)
            import traceback
            traceback.print_exc()

            # Try one more time with different settings
            try:
                print("\n🔄 Trying again with different settings...")
                # Adjust settings for another attempt
                self.recognizer.energy_threshold = 4000  # Higher threshold
                self.recognizer.dynamic_energy_threshold = True

                with self.microphone as source:
                    print("Please speak your command again...")
                    audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=10)
                    text = self.recognizer.recognize_google(audio).lower()
                    print(f"🎯 Successfully recognized on retry: \"{text}\"")
                    return text
            except:
                # If retry fails, fall back to text input
                print("\nRetry failed. Falling back to text input...")
                return input("\n⌨️ Command: ").strip()

    def _detect_command_type(self, text: str) -> str:
        """Detect the type of command from the text"""
        # Navigation commands
        if any(nav in text for nav in ["go to", "navigate to", "open", "visit"]):
            return "Navigation"

        # Form filling commands
        if any(form in text for form in ["enter", "input", "type", "fill", "write"]):
            if "email" in text or "@" in text:
                return "Email Input"
            elif "password" in text:
                return "Password Input"
            else:
                return "Form Filling"

        # Click commands
        if any(click in text for click in ["click", "press", "select", "choose"]):
            if "button" in text:
                return "Button Click"
            elif "tab" in text:
                return "Tab Selection"
            elif "login" in text or "sign in" in text:
                return "Login Action"
            else:
                return "Element Click"

        # Help and system commands
        if any(help_cmd in text for help_cmd in ["help", "what can you do", "commands"]):
            return "Help Request"
        if any(exit_cmd in text for exit_cmd in ["exit", "quit", "goodbye", "bye", "stop"]):
            return "Exit Command"
        if any(history_cmd in text for history_cmd in ["history", "previous commands"]):
            return "History Request"
        if any(repeat_cmd in text for repeat_cmd in ["repeat", "again", "redo"]):
            return "Repeat Command"

        # Mode switching
        if "voice mode" in text or "switch to voice" in text:
            return "Mode Switch - Voice"
        if "text mode" in text or "switch to text" in text:
            return "Mode Switch - Text"

        # Confirmation commands
        if any(confirm in text for confirm in ["confirm", "yes", "proceed", "continue"]):
            return "Confirmation"
        if any(cancel in text for cancel in ["cancel", "abort", "no", "don't"]):
            return "Cancellation"

        # Unknown command type
        return None

    async def set_mode(self, mode: str) -> None:
        """Set the recognition mode"""
        self.mode = mode


class TextInputRecognizer(SpeechRecognizer):
    """Text input recognizer"""

    def __init__(self, config: AssistantConfig, speak_func=None):
        """Initialize the recognizer"""
        self.config = config
        self.speak = speak_func
        self.mode = "text"

    async def listen(self) -> str:
        """Get input from text"""
        try:
            # Display the command prompt
            import sys
            sys.stdout.write("\n⌨️ Command: ")
            sys.stdout.flush()

            # Get input directly from stdin
            text = input().strip()
            print(f"Received text input: '{text}'")

            # Check for mode switching command with more flexible matching
            voice_mode_commands = ["voice", "voice mode", "switch to voice", "switch to voice mode",
                                  "voice input", "speak mode", "speaking mode", "microphone", "mic mode"]

            # Check if any of the voice mode commands are in the input text
            if any(cmd in text.lower() for cmd in voice_mode_commands) or "voice" == text.lower():
                self.mode = "voice"
                if self.speak:
                    # Use synchronous print since we can't await in a sync context
                    print("ASSISTANT: Switched to voice mode")
                print("🔄 Mode switch command detected: Switching to voice mode")
                # Return special value to trigger mode switch
                return "switch_to_voice_mode"

            return text
        except Exception as e:
            print(f"Input error: {e}")
            import traceback
            traceback.print_exc()
            return ""

    async def set_mode(self, mode: str) -> None:
        """Set the recognition mode"""
        self.mode = mode


def create_recognizer(config: AssistantConfig, mode: str = "text", speak_func=None) -> SpeechRecognizer:
    """Create a speech recognizer based on configuration and mode"""
    if mode.lower() == "voice":
        try:
            # Try to create a voice recognizer
            return SRRecognizer(config, speak_func)
        except Exception as e:
            # If PyAudio or other dependencies are missing, fall back to text mode
            print(f"⚠️ Error creating voice recognizer: {e}")
            print("⚠️ Voice recognition is not available. Falling back to text mode.")
            print("⚠️ To enable voice recognition, install PyAudio with: pip install pyaudio")
            print("⚠️ On Windows, you might need to install PyAudio from a wheel file.")

            # Return text recognizer as fallback
            return TextInputRecognizer(config, speak_func)
    else:
        return TextInputRecognizer(config, speak_func)
