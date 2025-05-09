"""
Enhanced speech recognition module for the Voice Assistant.

This module provides improved speech recognition with multiple recognition engines,
better error handling, and more robust recognition capabilities.
"""

import asyncio
import sys
import speech_recognition as sr
import logging

# Get logger
logger = logging.getLogger(__name__)

# Disable optional dependencies to avoid conflicts
WHISPER_AVAILABLE = False
PYDUB_AVAILABLE = False
logger.warning("Optional dependencies (Whisper, PyDub) are disabled to avoid conflicts")

from webassist.core.config import AssistantConfig


class EnhancedSpeechRecognizer:
    """Enhanced speech recognizer with multiple recognition engines and better error handling"""

    def __init__(self, config: AssistantConfig, speak_func=None):
        """Initialize the recognizer"""
        self.config = config
        self.speak = speak_func
        self.mode = "voice"
        self.recognizer = sr.Recognizer()

        # Configure recognizer settings for better recognition
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 300  # Lower threshold for better sensitivity
        self.recognizer.pause_threshold = 0.8   # Shorter pause threshold for faster recognition
        self.recognizer.phrase_threshold = 0.3  # Lower phrase threshold for better recognition

        # Initialize microphone
        try:
            logger.info("Initializing microphone for enhanced recognizer...")

            # List available microphones
            logger.info("Available microphones:")
            for index, name in enumerate(sr.Microphone.list_microphone_names()):
                logger.info(f"Microphone {index}: {name}")

            # Initialize microphone with default device
            self.microphone = sr.Microphone()

            # Test the microphone
            with self.microphone as source:
                logger.info("Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                logger.info("Microphone initialized successfully")

                # Try to listen for a short period to test the microphone
                try:
                    logger.info("Testing microphone...")
                    self.recognizer.listen(source, timeout=1, phrase_time_limit=1)
                    logger.info("Microphone test successful")
                except Exception as e:
                    logger.warning(f"Microphone test failed: {e}")
                    logger.warning("Continuing anyway, but voice recognition may not work properly")
        except Exception as e:
            logger.error(f"Error initializing microphone: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

        # Initialize Whisper model if available (disabled for now)
        self.whisper_model = None

        logger.info("Enhanced speech recognizer initialized successfully")

    async def listen(self) -> str:
        """Listen for speech and return the recognized text"""
        try:
            logger.info("Starting voice recognition with enhanced recognizer...")
            # Run the blocking speech recognition in a separate thread
            for attempt in range(3):  # Try up to 3 times
                try:
                    logger.info(f"Voice recognition attempt {attempt+1}/3")
                    result = await asyncio.to_thread(self._listen_sync)
                    if result and result != "retry_voice_recognition":
                        return result
                    logger.info(f"Retrying voice recognition (attempt {attempt+1} failed)")
                    # Add a small delay between attempts
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"Error in voice recognition attempt {attempt+1}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    # Add a small delay between attempts
                    await asyncio.sleep(0.5)

            # If we get here, all attempts failed
            logger.error("All voice recognition attempts failed")
            return "retry_voice_recognition"
        except Exception as e:
            logger.error(f"Audio error in listen(): {e}")
            import traceback
            logger.error(traceback.format_exc())
            return "retry_voice_recognition"

    def _listen_sync(self) -> str:
        """Synchronous voice listening method to run in a separate thread"""
        try:
            logger.info("Initializing microphone for listening...")
            with self.microphone as source:
                print("\n" + "=" * 80)
                print("=" * 80)
                print("🎤 LISTENING NOW... (Speak your command clearly)".center(80))
                print("=" * 80)
                print("=" * 80)
                sys.stdout.flush()

                # More aggressive noise adjustment for better recognition
                try:
                    # Adjust for ambient noise with shorter duration for faster response
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    logger.info(f"Adjusted for ambient noise. Energy threshold: {self.recognizer.energy_threshold}")

                    # Set more aggressive settings for better recognition
                    self.recognizer.energy_threshold = 300  # Lower threshold for better sensitivity
                    self.recognizer.dynamic_energy_threshold = True
                    self.recognizer.pause_threshold = 0.3  # Shorter pause threshold for faster recognition
                    self.recognizer.phrase_threshold = 0.1  # Lower phrase threshold for better recognition
                    self.recognizer.non_speaking_duration = 0.1  # Shorter non-speaking duration
                except Exception as noise_error:
                    logger.warning(f"Error adjusting for ambient noise: {noise_error}")
                    # Continue anyway with default settings

                try:
                    # Use a shorter timeout and phrase time limit for faster response
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    logger.info("Audio captured successfully")
                except sr.WaitTimeoutError:
                    print("\n❌ TIMEOUT: No speech detected within the listening period.")
                    print("\nTips:")
                    print("- Make sure your microphone is working")
                    print("- Speak clearly and directly into the microphone")
                    print("- Try again by saying 'retry' or just wait for the next listening prompt")
                    sys.stdout.flush()
                    return "retry_voice_recognition"
                except Exception as listen_error:
                    logger.error(f"Error capturing audio: {listen_error}")
                    print(f"\n⚠️ Error capturing audio: {listen_error}")
                    return "retry_voice_recognition"

                print("\n" + "-" * 80)
                print("🔍 RECOGNIZING SPEECH...".center(80))
                print("-" * 80)
                sys.stdout.flush()

                # Try multiple recognition engines in sequence
                return self._recognize_with_multiple_engines(audio)

        except sr.WaitTimeoutError:
            print("\n❌ TIMEOUT: No speech detected within the listening period.")
            print("\nTips:")
            print("- Make sure your microphone is working")
            print("- Speak clearly and directly into the microphone")
            print("- Try again by saying 'retry' or just wait for the next listening prompt")
            sys.stdout.flush()
            return "retry_voice_recognition"

        except Exception as e:
            logger.error(f"Error in voice recognition: {e}")
            import traceback
            logger.error(traceback.format_exc())
            print(f"\n⚠️ Error in voice recognition: {e}")
            return "retry_voice_recognition"

    def _recognize_with_multiple_engines(self, audio):
        """Try multiple recognition engines in sequence"""
        # First try Google's speech recognition service with higher sensitivity
        try:
            # Set the energy threshold lower to pick up quieter speech
            original_energy_threshold = self.recognizer.energy_threshold
            self.recognizer.energy_threshold = 300  # Lower threshold for better sensitivity

            # Try with language hint for better accuracy
            text = self.recognizer.recognize_google(
                audio,
                language="en-US",
                show_all=False
            ).lower()

            # Restore original energy threshold
            self.recognizer.energy_threshold = original_energy_threshold

            logger.info(f"Google recognition successful: {text}")
            self._display_recognized_text(text, "Google Speech Recognition")
            return text
        except sr.UnknownValueError:
            logger.warning("Google speech recognition could not understand audio")
            # Continue to next engine
        except sr.RequestError as e:
            logger.error(f"Google speech recognition service error: {e}")
            print(f"\n⚠️ Google speech recognition service error: {e}")
            # Continue to next engine

        # Try Google again with different settings
        try:
            logger.info("Trying Google recognition with different settings...")
            # Adjust settings for another attempt
            self.recognizer.energy_threshold = 4000  # Higher threshold
            self.recognizer.dynamic_energy_threshold = True

            text = self.recognizer.recognize_google(
                audio,
                language="en-US",
                show_all=False
            ).lower()

            logger.info(f"Google recognition (second attempt) successful: {text}")
            self._display_recognized_text(text, "Google Speech Recognition (Retry)")
            return text
        except Exception:
            logger.warning("Google speech recognition (second attempt) failed")
            # Continue to next engine

        # Try Sphinx as a last resort (offline recognition)
        try:
            logger.info("Trying Sphinx recognition...")
            text = self.recognizer.recognize_sphinx(audio).lower()
            logger.info(f"Sphinx recognition successful: {text}")
            self._display_recognized_text(text, "Sphinx (Offline)")
            return text
        except Exception as e:
            logger.error(f"Error with Sphinx recognition: {e}")

        # If all recognition engines fail
        self._display_recognition_failure()
        return "retry_voice_recognition"

    def _display_recognized_text(self, text, engine_name):
        """Display the recognized text with enhanced visibility"""
        print("\n" + "#" * 100)
        print("#" * 100)
        print(f"🎯 RECOGNIZED COMMAND ({engine_name}):".center(100))
        print(f"\"{text}\"".center(100))
        print("#" * 100)
        print("#" * 100)
        sys.stdout.flush()

    def _display_recognition_failure(self):
        """Display recognition failure message with helpful tips"""
        print("\n" + "=" * 80)
        print("=" * 80)
        print("❌ SPEECH NOT RECOGNIZED. Please try again.".center(80))
        print("=" * 80)
        print("=" * 80)
        print("\nTips for better recognition:")
        print("- Speak clearly and directly into the microphone")
        print("- Reduce background noise if possible")
        print("- Try speaking at a moderate pace")
        print("- Make sure you're speaking within 5 seconds of seeing 'LISTENING NOW...'")
        print("- For URLs, say 'dot' instead of '.' (e.g., 'redberyltest dot in')")
        print("- For 'redberyltest', say it slowly and clearly")

        print("\n🔄 Trying again with different settings...")
        print("Please speak your command again...")
        sys.stdout.flush()

    async def set_mode(self, mode: str) -> None:
        """Set the recognition mode"""
        self.mode = mode


class TextInputRecognizer:
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


def create_enhanced_recognizer(config: AssistantConfig, mode: str = "text", speak_func=None):
    """Create an enhanced speech recognizer based on configuration and mode"""
    if mode.lower() == "voice":
        try:
            # Try to create a voice recognizer
            return EnhancedSpeechRecognizer(config, speak_func)
        except Exception as e:
            # If PyAudio or other dependencies are missing, fall back to text mode
            logger.error(f"Error creating voice recognizer: {e}")
            print("⚠️ Voice recognition is not available. Falling back to text mode.")
            print("⚠️ To enable voice recognition, install PyAudio with: pip install pyaudio")
            print("⚠️ On Windows, you might need to install PyAudio from a wheel file.")

            # Return text recognizer as fallback
            return TextInputRecognizer(config, speak_func)
    else:
        return TextInputRecognizer(config, speak_func)
