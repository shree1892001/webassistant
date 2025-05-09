"""
Simple Voice Recognition Test

This script provides a basic test of voice recognition functionality.
It uses the speech_recognition library directly without any complex async operations.
"""

import sys
import time
import speech_recognition as sr
import threading
import queue

# Create a queue for commands
command_queue = queue.Queue()

# Flag to control running state
running = True

def display_banner():
    """Display a banner with instructions"""
    print("\n" + "=" * 80)
    print("SIMPLE VOICE RECOGNITION TEST".center(80))
    print("=" * 80)
    print("Say something to test voice recognition.")
    print("Say 'exit' or 'quit' to end the test.")
    print("=" * 80)
    sys.stdout.flush()

def process_commands():
    """Process commands from the queue"""
    while running:
        try:
            # Get command from queue with timeout
            try:
                command = command_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if command.lower() in ["exit", "quit"]:
                print("\nExiting...")
                global running
                running = False
                break

            # Process the command
            print(f"\nProcessing command: {command}")
            print("Command processed successfully!")
            
            # Display the banner again
            display_banner()

        except Exception as e:
            print(f"Error processing command: {e}")
            import traceback
            traceback.print_exc()

def voice_recognition_thread():
    """Thread for continuous voice recognition"""
    global running
    
    # Initialize recognizer
    recognizer = sr.Recognizer()
    
    # Configure recognizer settings for better recognition
    recognizer.dynamic_energy_threshold = True
    recognizer.energy_threshold = 300  # Lower threshold for better sensitivity
    recognizer.pause_threshold = 0.3   # Shorter pause threshold for faster recognition
    recognizer.phrase_threshold = 0.1  # Lower phrase threshold for better recognition
    recognizer.non_speaking_duration = 0.1  # Shorter non-speaking duration
    
    # Initialize microphone
    try:
        print("\n🎤 Initializing microphone...")
        
        # List available microphones
        print("\nAvailable microphones:")
        for index, name in enumerate(sr.Microphone.list_microphone_names()):
            print(f"Microphone {index}: {name}")
        
        # Initialize microphone with default device
        microphone = sr.Microphone()
        
        # Test microphone access and adjust for ambient noise
        with microphone as source:
            print("\nTesting microphone access...")
            print("Please remain quiet for 2 seconds while we calibrate the microphone...")
            # Adjust for ambient noise with longer duration
            recognizer.adjust_for_ambient_noise(source, duration=2)
            print("✅ Microphone calibrated successfully")
            
            # Test if microphone is picking up sound
            print("\nTesting microphone input...")
            print("Please speak something to test the microphone...")
            try:
                test_audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                print("✅ Microphone is picking up sound")
                
                # Try to recognize the test audio
                try:
                    test_text = recognizer.recognize_google(test_audio)
                    print(f"✅ Test recognition successful: \"{test_text}\"")
                except Exception as e:
                    print(f"⚠️ Test recognition failed: {e}")
                    print("Continuing anyway as microphone is working")
                
            except sr.WaitTimeoutError:
                print("❌ Microphone timeout - no sound detected")
                print("Please check if your microphone is properly connected and not muted")
                return
            except Exception as e:
                print(f"❌ Error testing microphone: {e}")
                return
    except Exception as e:
        print(f"❌ Failed to initialize microphone: {e}")
        return
    
    # Main voice recognition loop
    while running:
        try:
            # Listen for speech
            with microphone as source:
                print("\n" + "=" * 80)
                print("🎤 LISTENING NOW... (Speak your command clearly)".center(80))
                print("=" * 80)
                sys.stdout.flush()
                
                # Adjust for ambient noise
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                # Listen for audio
                try:
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    print("\n🔍 RECOGNIZING SPEECH...")
                except sr.WaitTimeoutError:
                    print("\n❌ TIMEOUT: No speech detected.")
                    continue
                except Exception as e:
                    print(f"\n⚠️ Error capturing audio: {e}")
                    continue
                
                # Try to recognize the speech
                try:
                    text = recognizer.recognize_google(audio).lower()
                    
                    # Display the recognized text
                    print("\n" + "#" * 80)
                    print("#" * 80)
                    print(f"🎯 RECOGNIZED COMMAND:".center(80))
                    print(f"\"{text}\"".center(80))
                    print("#" * 80)
                    print("#" * 80)
                    sys.stdout.flush()
                    
                    # Add command to queue for processing
                    command_queue.put(text)
                    print(f"📥 Added to command queue: \"{text}\"")
                    print(f"⏱️ Command will be processed momentarily...")
                    sys.stdout.flush()
                    
                except sr.UnknownValueError:
                    print("\n❌ SPEECH NOT RECOGNIZED. Please try again.")
                    print("\nTips for better recognition:")
                    print("- Speak clearly and directly into the microphone")
                    print("- Reduce background noise if possible")
                    print("- Try speaking at a moderate pace")
                    sys.stdout.flush()
                except sr.RequestError as e:
                    print(f"\n❌ SPEECH RECOGNITION SERVICE ERROR: {e}")
                    print("This could be due to network issues or problems with the Google Speech API.")
                    sys.stdout.flush()
                except Exception as e:
                    print(f"\n⚠️ Error in voice recognition: {e}")
                    import traceback
                    traceback.print_exc()
                    sys.stdout.flush()
        
        except Exception as e:
            print(f"Error in voice recognition thread: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(1)  # Delay before retrying

def main():
    """Main entry point"""
    global running
    
    try:
        print("\n==== Starting Simple Voice Recognition Test ====")
        
        # Start the voice recognition thread
        voice_thread = threading.Thread(target=voice_recognition_thread)
        voice_thread.daemon = True
        voice_thread.start()
        
        # Start the command processing thread
        process_thread = threading.Thread(target=process_commands)
        process_thread.daemon = True
        process_thread.start()
        
        # Display the banner
        display_banner()
        
        # Keep the main thread alive
        while running:
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected. Exiting...")
        running = False
    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
    finally:
        running = False
        print("\nExiting voice recognition test...")

if __name__ == "__main__":
    main()
