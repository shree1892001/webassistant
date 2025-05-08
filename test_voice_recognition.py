"""
Test Voice Recognition - A simple script to test if voice recognition is working.
"""

import sys
import time

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    print("Speech recognition not available. Install with: pip install SpeechRecognition")
    print("You'll also need PyAudio: pip install pyaudio")
    SPEECH_RECOGNITION_AVAILABLE = False
    sys.exit(1)

def test_microphone():
    """Test if the microphone is working"""
    print("Testing microphone...")
    try:
        # Create a recognizer and microphone instance
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        
        # Test microphone by adjusting for ambient noise
        with microphone as source:
            print("Microphone detected!")
            print("Adjusting for ambient noise...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print("Ambient noise adjustment complete")
        
        print("Microphone test successful!")
        return True
    except Exception as e:
        print(f"Microphone test failed: {e}")
        return False

def listen_for_command():
    """Listen for a voice command"""
    # Create a recognizer and microphone instance
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    try:
        with microphone as source:
            print("\n" + "=" * 60)
            print("🎤 LISTENING FOR VOICE COMMAND...")
            print("=" * 60)
            sys.stdout.flush()
            
            # Adjust for ambient noise
            print("Adjusting for ambient noise...")
            recognizer.adjust_for_ambient_noise(source, duration=1.0)
            
            # Set parameters for better recognition
            recognizer.energy_threshold = 300  # Lower threshold for better sensitivity
            recognizer.dynamic_energy_threshold = True
            
            print("Ready! Please speak your command now.")
            sys.stdout.flush()
            
            # Listen for audio
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)
            
            print("\n" + "-" * 50)
            print("🔍 RECOGNIZING SPEECH...")
            print("-" * 50)
            sys.stdout.flush()
            
            # Recognize speech using Google Speech Recognition
            text = recognizer.recognize_google(audio, language="en-US")
            
            print("\n" + "*" * 60)
            print("*" + " " * 58 + "*")
            print("*" + f"🎯 RECOGNIZED COMMAND: \"{text}\"".center(58) + "*")
            print("*" + " " * 58 + "*")
            print("*" * 60)
            
            return text.lower()
    except sr.UnknownValueError:
        print("\n" + "!" * 50)
        print("❌ SPEECH NOT RECOGNIZED. Please try again.")
        print("!" * 50)
        print("\nTips for better recognition:")
        print("- Speak clearly and directly into the microphone")
        print("- Reduce background noise if possible")
        print("- Try speaking at a moderate pace")
        print("- Make sure your microphone is working properly")
        return None
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        return None
    except Exception as e:
        print(f"Error in voice recognition: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main function"""
    print("\n" + "=" * 50)
    print("Voice Recognition Test")
    print("=" * 50)
    
    # Test microphone
    if not test_microphone():
        print("Microphone test failed. Exiting.")
        return
    
    print("\nVoice recognition is ready.")
    print("Say 'exit' or 'quit' to end the test.")
    
    # Main loop
    running = True
    while running:
        try:
            # Listen for command
            command = listen_for_command()
            
            if command:
                print(f"You said: {command}")
                
                # Check for exit command
                if command in ["exit", "quit", "stop", "end"]:
                    print("Exiting...")
                    running = False
            else:
                print("No command recognized. Please try again.")
                
            # Add a small delay
            time.sleep(1)
        except KeyboardInterrupt:
            print("\nKeyboard interrupt detected. Exiting...")
            running = False
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("Test complete. Goodbye!")

if __name__ == "__main__":
    main()
