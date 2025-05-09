"""
Simple Voice Assistant Demo

This is a simplified version of the voice assistant that focuses on reliable
voice recognition for demo purposes.
"""

import os
import sys
import time
import threading
import queue
import speech_recognition as sr
from playwright.sync_api import sync_playwright

# Initialize global variables
running = True
command_queue = queue.Queue()

def display_banner():
    """Display a banner with instructions"""
    print("\n" + "=" * 80)
    print("VOICE ASSISTANT DEMO".center(80))
    print("=" * 80)
    print("Available commands:")
    print("- 'goto [website]' - Navigate to a website")
    print("- 'click [element]' - Click on an element")
    print("- 'help' - Show this help message")
    print("- 'exit' or 'quit' - End the demo")
    print("=" * 80)
    sys.stdout.flush()

def process_commands(browser_page):
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
            
            # Handle navigation commands
            if command.lower().startswith("goto "):
                url = command[5:].strip()
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                print(f"Navigating to: {url}")
                browser_page.goto(url)
                print(f"Loaded: {browser_page.title()}")
            
            # Handle click commands
            elif command.lower().startswith("click "):
                element_text = command[6:].strip()
                print(f"Looking for element: {element_text}")
                try:
                    # Try various selectors
                    selectors = [
                        f'text="{element_text}"',
                        f'button:has-text("{element_text}")',
                        f'a:has-text("{element_text}")',
                        f'[role="button"]:has-text("{element_text}")',
                        f'input[value="{element_text}"]'
                    ]
                    
                    for selector in selectors:
                        try:
                            if browser_page.query_selector(selector):
                                browser_page.click(selector)
                                print(f"Clicked element: {element_text}")
                                break
                        except:
                            continue
                    else:
                        print(f"Could not find element: {element_text}")
                except Exception as e:
                    print(f"Error clicking element: {e}")
            
            # Handle help command
            elif command.lower() == "help":
                display_banner()
            
            # Handle unknown commands
            else:
                print(f"Unknown command: {command}")
            
            # Display the banner again
            print("\n🎤 Ready for next command...")

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
                    
                    # Process common command patterns
                    text = process_command_text(text)
                    
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

def process_command_text(text):
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

def main():
    """Main entry point"""
    global running
    
    try:
        print("\n==== Starting Simple Voice Assistant Demo ====")
        
        # Initialize browser
        print("\nInitializing browser...")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=False)
            page = browser.new_page()
            page.goto("https://www.google.com")
            print(f"Browser initialized and loaded: {page.title()}")
            
            # Start the voice recognition thread
            voice_thread = threading.Thread(target=voice_recognition_thread)
            voice_thread.daemon = True
            voice_thread.start()
            
            # Start the command processing thread
            process_thread = threading.Thread(target=process_commands, args=(page,))
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
        print("\nExiting voice assistant demo...")

if __name__ == "__main__":
    main()
