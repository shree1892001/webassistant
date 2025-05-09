"""
Direct speech recognition module for the Voice Assistant.

This module provides a simple, reliable speech recognition implementation
that works directly with the speech_recognition library without complex async operations.
"""

import sys
import time
import speech_recognition as sr
import logging
import threading

# Get logger
logger = logging.getLogger(__name__)

class DirectVoiceRecognizer:
    """Direct voice recognizer that works reliably with all commands"""

    def __init__(self, speak_func=None):
        """Initialize the recognizer"""
        self.speak = speak_func
        self.mode = "voice"
        self.is_listening = False
        self.command_callback = None
        
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
            
            # Test the microphone
            with self.microphone as source:
                logger.info("Testing microphone...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                logger.info(f"Microphone test successful. Energy threshold: {self.recognizer.energy_threshold}")
        except Exception as e:
            logger.error(f"Error initializing microphone: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def start_listening(self, command_callback):
        """Start listening for commands in a separate thread
        
        Args:
            command_callback: Function to call when a command is recognized
        """
        if self.is_listening:
            logger.warning("Already listening")
            return
            
        self.is_listening = True
        self.command_callback = command_callback
        
        # Start listening thread
        self.listen_thread = threading.Thread(target=self._listen_loop)
        self.listen_thread.daemon = True
        self.listen_thread.start()
        
        logger.info("Started listening thread")
        
    def stop_listening(self):
        """Stop listening for commands"""
        self.is_listening = False
        logger.info("Stopped listening")
        
    def _listen_loop(self):
        """Main listening loop that runs in a separate thread"""
        logger.info("Listening loop started")
        
        while self.is_listening:
            try:
                # Listen for speech
                text = self._listen_once()
                
                # Process the recognized text
                if text:
                    # Check for mode switching command
                    if text.lower() in ["text", "switch to text", "switch to text mode"]:
                        logger.info("Mode switch command detected")
                        if self.command_callback:
                            self.command_callback("switch_to_text_mode")
                        continue
                        
                    # Call the command callback with the recognized text
                    if self.command_callback:
                        self.command_callback(text)
                
                # Small delay to prevent CPU hogging
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in listening loop: {e}")
                import traceback
                logger.error(traceback.format_exc())
                time.sleep(1)  # Delay before retrying
                
    def _listen_once(self):
        """Listen for speech once and return the recognized text"""
        try:
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
                except Exception as e:
                    logger.warning(f"Error adjusting for ambient noise: {e}")
                
                # Listen for audio
                try:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    logger.info("Audio captured successfully")
                except sr.WaitTimeoutError:
                    print("\n❌ TIMEOUT: No speech detected.")
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
            
            # Process common command patterns
            processed_text = self._process_command(text)
            return processed_text
            
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
            
            # Process common command patterns
            processed_text = self._process_command(text)
            return processed_text
            
        except Exception:
            logger.warning("Google speech recognition (second attempt) failed")
            # Continue to next engine

        # Try Sphinx as a last resort (offline recognition)
        try:
            logger.info("Trying Sphinx recognition...")
            text = self.recognizer.recognize_sphinx(audio).lower()
            logger.info(f"Sphinx recognition successful: {text}")
            self._display_recognized_text(text, "Sphinx (Offline)")
            
            # Process common command patterns
            processed_text = self._process_command(text)
            return processed_text
            
        except Exception as e:
            logger.error(f"Error with Sphinx recognition: {e}")
            
        # If all recognition engines fail
        self._display_recognition_failure()
        return None
    
    def _process_command(self, text):
        """Process common command patterns and normalize the text"""
        # Handle common URL recognition issues
        text = text.replace("dot com", ".com")
        text = text.replace("dot in", ".in")
        text = text.replace("dot org", ".org")
        text = text.replace("dot net", ".net")
        text = text.replace("dot co", ".co")
        text = text.replace("dot", ".")
        
        # Handle common command variations with proper spacing
        if "go to" in text:
            text = text.replace("go to", "goto ")
        if "navigate to" in text:
            text = text.replace("navigate to", "goto ")
        if "open" in text:
            text = text.replace("open", "goto ")
        if "visit" in text:
            text = text.replace("visit", "goto ")
            
        # Handle domain name corrections
        domain_corrections = {
            "redberyl": "redberyltest",
            "red beryl": "redberyltest",
            "redberyl test": "redberyltest",
            "red beryl test": "redberyltest"
        }
        
        for wrong, correct in domain_corrections.items():
            if wrong in text:
                text = text.replace(wrong, correct)
                print(f"\nℹ️ Corrected domain name from '{wrong}' to '{correct}'")
                
        # Ensure proper spacing in URLs
        if "goto" in text:
            # Split the command and URL
            parts = text.split("goto")
            if len(parts) == 2:
                command = parts[0].strip()
                url = parts[1].strip()
                # Ensure there's a space after goto
                text = f"{command}goto {url}"
                
        return text
        
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


class DirectTextRecognizer:
    """Direct text input recognizer"""

    def __init__(self, speak_func=None):
        """Initialize the recognizer"""
        self.speak = speak_func
        self.mode = "text"
        self.is_listening = False
        self.command_callback = None

    def start_listening(self, command_callback):
        """Start listening for commands in a separate thread
        
        Args:
            command_callback: Function to call when a command is recognized
        """
        if self.is_listening:
            logger.warning("Already listening")
            return
            
        self.is_listening = True
        self.command_callback = command_callback
        
        # Start listening thread
        self.listen_thread = threading.Thread(target=self._listen_loop)
        self.listen_thread.daemon = True
        self.listen_thread.start()
        
        logger.info("Started text input thread")
        
    def stop_listening(self):
        """Stop listening for commands"""
        self.is_listening = False
        logger.info("Stopped text input")
        
    def _listen_loop(self):
        """Main listening loop that runs in a separate thread"""
        logger.info("Text input loop started")
        
        while self.is_listening:
            try:
                # Get text input
                text = self._get_text_input()
                
                # Process the input text
                if text:
                    # Check for mode switching command
                    if text.lower() in ["voice", "switch to voice", "switch to voice mode"]:
                        logger.info("Mode switch command detected")
                        if self.command_callback:
                            self.command_callback("switch_to_voice_mode")
                        continue
                        
                    # Call the command callback with the input text
                    if self.command_callback:
                        self.command_callback(text)
                
                # Small delay to prevent CPU hogging
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in text input loop: {e}")
                import traceback
                logger.error(traceback.format_exc())
                time.sleep(1)  # Delay before retrying
                
    def _get_text_input(self):
        """Get input from text"""
        try:
            # Display the command prompt
            sys.stdout.write("\n⌨️ Command: ")
            sys.stdout.flush()

            # Get input directly from stdin
            text = input().strip()
            print(f"Received text input: '{text}'")
            return text
            
        except Exception as e:
            print(f"Input error: {e}")
            import traceback
            traceback.print_exc()
            return None


def create_direct_recognizer(mode="text", speak_func=None):
    """Create a direct recognizer based on mode"""
    if mode.lower() == "voice":
        try:
            return DirectVoiceRecognizer(speak_func)
        except Exception as e:
            print(f"❌ Failed to initialize voice recognizer: {e}")
            print("⚠️ Falling back to text mode")
            return DirectTextRecognizer(speak_func)
    else:
        return DirectTextRecognizer(speak_func)
