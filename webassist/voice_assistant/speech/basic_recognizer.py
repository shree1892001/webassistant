"""
Basic speech recognition module for the Voice Assistant.

This module provides a simple, reliable speech recognition implementation
that works directly with the speech_recognition library without complex async operations.
"""

import sys
import time
import speech_recognition as sr
import logging

# Get logger
logger = logging.getLogger(__name__)

class BasicVoiceRecognizer:
    """Basic voice recognizer that works directly with speech_recognition"""

    def __init__(self, speak_func=None):
        """Initialize the recognizer"""
        self.speak = speak_func
        self.mode = "voice"
        
        # Initialize recognizer
        self.recognizer = sr.Recognizer()
        
        # Configure recognizer settings for better recognition
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 300  # Lower threshold for better sensitivity
        self.recognizer.pause_threshold = 0.3   # Shorter pause threshold for faster recognition
        self.recognizer.phrase_threshold = 0.1  # Lower phrase threshold for better recognition
        self.recognizer.non_speaking_duration = 0.1  # Shorter non-speaking duration
        
        # Initialize microphone
        try:
            logger.info("Initializing microphone...")
            
            # List available microphones
            logger.info("Available microphones:")
            for index, name in enumerate(sr.Microphone.list_microphone_names()):
                logger.info(f"Microphone {index}: {name}")
            
            # Initialize microphone with default device
            self.microphone = sr.Microphone()
            logger.info("Microphone initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing microphone: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def listen(self):
        """Listen for speech and return the recognized text"""
        try:
            logger.info("Starting voice recognition...")
            with self.microphone as source:
                print("\n" + "=" * 80)
                print("=" * 80)
                print("🎤 LISTENING NOW... (Speak your command clearly)".center(80))
                print("=" * 80)
                print("=" * 80)
                sys.stdout.flush()

                # Adjust for ambient noise
                try:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    logger.info(f"Adjusted for ambient noise. Energy threshold: {self.recognizer.energy_threshold}")
                except Exception as e:
                    logger.warning(f"Error adjusting for ambient noise: {e}")
                
                # Listen for audio
                try:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    logger.info("Audio captured successfully")
                except sr.WaitTimeoutError:
                    print("\n❌ TIMEOUT: No speech detected within the listening period.")
                    return None
                except Exception as e:
                    logger.error(f"Error capturing audio: {e}")
                    print(f"\n⚠️ Error capturing audio: {e}")
                    return None

                print("\n" + "-" * 80)
                print("🔍 RECOGNIZING SPEECH...".center(80))
                print("-" * 80)
                sys.stdout.flush()

                # Try to recognize the speech
                return self._recognize_speech(audio)
                
        except Exception as e:
            logger.error(f"Error in voice recognition: {e}")
            import traceback
            logger.error(traceback.format_exc())
            print(f"\n⚠️ Error in voice recognition: {e}")
            return None

    def _recognize_speech(self, audio):
        """Recognize speech using multiple engines"""
        # Try Google's speech recognition service
        try:
            text = self.recognizer.recognize_google(
                audio,
                language="en-US",
                show_all=False
            ).lower()
            
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
            original_energy = self.recognizer.energy_threshold
            self.recognizer.energy_threshold = 4000  # Higher threshold
            
            text = self.recognizer.recognize_google(
                audio,
                language="en-US",
                show_all=False
            ).lower()
            
            # Restore original settings
            self.recognizer.energy_threshold = original_energy
            
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
        return None
        
    def _display_recognized_text(self, text, engine_name):
        """Display the recognized text with enhanced visibility"""
        print("\n" + "#" * 80)
        print("#" * 80)
        print(f"🎯 RECOGNIZED COMMAND ({engine_name}):".center(80))
        print(f"\"{text}\"".center(80))
        print("#" * 80)
        print("#" * 80)
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
        sys.stdout.flush()


class BasicTextRecognizer:
    """Basic text input recognizer"""

    def __init__(self, speak_func=None):
        """Initialize the recognizer"""
        self.speak = speak_func
        self.mode = "text"

    def listen(self):
        """Get input from text"""
        try:
            # Display the command prompt
            sys.stdout.write("\n⌨️ Command: ")
            sys.stdout.flush()

            # Get input directly from stdin
            text = input().strip()
            print(f"Received text input: '{text}'")

            # Check for mode switching command
            if text.lower() in ["voice", "voice mode", "switch to voice", "switch to voice mode"]:
                print("🔄 Mode switch command detected: Switching to voice mode")
                return "switch_to_voice_mode"

            return text
        except Exception as e:
            print(f"Input error: {e}")
            import traceback
            traceback.print_exc()
            return None


def create_basic_recognizer(mode="text", speak_func=None):
    """Create a basic recognizer based on mode"""
    if mode.lower() == "voice":
        try:
            return BasicVoiceRecognizer(speak_func)
        except Exception as e:
            print(f"❌ Failed to initialize voice recognizer: {e}")
            print("⚠️ Falling back to text mode")
            return BasicTextRecognizer(speak_func)
    else:
        return BasicTextRecognizer(speak_func)
