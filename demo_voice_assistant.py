"""
Demo Voice Assistant

A simplified voice assistant that reliably recognizes and processes voice commands
for navigation, clicking, and form filling.
"""

import os
import sys
import time
import threading
import queue
import re
import speech_recognition as sr
from playwright.sync_api import sync_playwright

# Initialize global variables
running = True
command_queue = queue.Queue()

# Define command patterns
GOTO_PATTERN = re.compile(r'(?:goto|go to|navigate to|open|visit)\s+([\w\.-]+(?:\.\w+)+)', re.IGNORECASE)
CLICK_PATTERN = re.compile(r'click\s+(?:on\s+)?(?:the\s+)?([\w\s]+)', re.IGNORECASE)
EMAIL_PATTERN = re.compile(r'(?:enter|input|type|fill)\s+(?:email|e-mail)\s+([\w\.-]+@[\w\.-]+(?:\.\w+)+)', re.IGNORECASE)
PASSWORD_PATTERN = re.compile(r'(?:enter|input|type|fill)\s+(?:password)\s+(\S+)', re.IGNORECASE)

def display_banner():
    """Display a banner with instructions"""
    print("\n" + "=" * 80)
    print("VOICE ASSISTANT DEMO".center(80))
    print("=" * 80)
    print("Available commands:")
    print("- 'goto [website]' - Navigate to a website (e.g., 'goto redberyltest.in')")
    print("- 'click [element]' - Click on an element (e.g., 'click Sign in')")
    print("- 'enter email [email]' - Enter an email address")
    print("- 'enter password [password]' - Enter a password")
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

            if command.lower() in ["help"]:
                display_banner()
                continue

            # Process the command
            print(f"\nProcessing command: {command}")
            
            # Handle navigation commands
            goto_match = GOTO_PATTERN.search(command)
            if goto_match:
                url = goto_match.group(1).strip()
                
                # Special handling for redberyltest.in
                if "redberyl" in url.lower() or "red beryl" in url.lower():
                    url = "redberyltest.in"
                    print(f"Corrected URL to: {url}")
                
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                print(f"Navigating to: {url}")
                browser_page.goto(url)
                print(f"Loaded: {browser_page.title()}")
                continue
            
            # Handle click commands
            click_match = CLICK_PATTERN.search(command)
            if click_match:
                element_text = click_match.group(1).strip()
                print(f"Looking for element: {element_text}")
                try:
                    # Try various selectors
                    selectors = [
                        f'text="{element_text}"',
                        f'button:has-text("{element_text}")',
                        f'a:has-text("{element_text}")',
                        f'[role="button"]:has-text("{element_text}")',
                        f'input[value="{element_text}"]',
                        f'[aria-label*="{element_text}" i]',
                        f'[placeholder*="{element_text}" i]',
                        f'[title*="{element_text}" i]'
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
                        # Try clicking by JavaScript if selectors fail
                        js_click_script = f"""
                        (function() {{
                            const elements = Array.from(document.querySelectorAll('*'));
                            const element = elements.find(el => 
                                (el.textContent || '').toLowerCase().includes('{element_text.lower()}') && 
                                (el.tagName === 'BUTTON' || el.tagName === 'A' || 
                                 el.role === 'button' || el.getAttribute('role') === 'button')
                            );
                            if (element) {{
                                element.click();
                                return true;
                            }}
                            return false;
                        }})();
                        """
                        clicked = browser_page.evaluate(js_click_script)
                        if clicked:
                            print(f"Clicked element using JavaScript: {element_text}")
                        else:
                            print(f"Could not find element: {element_text}")
                except Exception as e:
                    print(f"Error clicking element: {e}")
                continue
            
            # Handle email commands
            email_match = EMAIL_PATTERN.search(command)
            if email_match:
                email = email_match.group(1).strip()
                print(f"Entering email: {email}")
                try:
                    # Try various selectors for email fields
                    email_selectors = [
                        'input[type="email"]',
                        'input[name="email"]',
                        'input[id*="email" i]',
                        'input[placeholder*="email" i]',
                        'input[aria-label*="email" i]',
                        '#floating_outlined3',  # Specific selector from your code
                        'input.p-inputtext'  # Generic class selector
                    ]
                    
                    for selector in email_selectors:
                        try:
                            if browser_page.query_selector(selector):
                                browser_page.fill(selector, email)
                                print(f"Entered email: {email}")
                                break
                        except:
                            continue
                    else:
                        # Try filling by JavaScript if selectors fail
                        js_fill_script = f"""
                        (function() {{
                            const emailInputs = Array.from(document.querySelectorAll('input')).filter(input => 
                                input.type === 'email' || 
                                input.name?.toLowerCase().includes('email') ||
                                input.id?.toLowerCase().includes('email') ||
                                input.placeholder?.toLowerCase().includes('email') ||
                                input.ariaLabel?.toLowerCase().includes('email')
                            );
                            if (emailInputs.length > 0) {{
                                emailInputs[0].value = '{email}';
                                emailInputs[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
                                emailInputs[0].dispatchEvent(new Event('change', {{ bubbles: true }}));
                                return true;
                            }}
                            return false;
                        }})();
                        """
                        filled = browser_page.evaluate(js_fill_script)
                        if filled:
                            print(f"Entered email using JavaScript: {email}")
                        else:
                            print(f"Could not find email field")
                except Exception as e:
                    print(f"Error entering email: {e}")
                continue
            
            # Handle password commands
            password_match = PASSWORD_PATTERN.search(command)
            if password_match:
                password = password_match.group(1).strip()
                print(f"Entering password: {'*' * len(password)}")
                try:
                    # Try various selectors for password fields
                    password_selectors = [
                        'input[type="password"]',
                        'input[name="password"]',
                        'input[id*="password" i]',
                        'input[placeholder*="password" i]',
                        'input[aria-label*="password" i]',
                        '#floating_outlined15',  # Specific selector from your code
                        'input.p-password'  # Generic class selector
                    ]
                    
                    for selector in password_selectors:
                        try:
                            if browser_page.query_selector(selector):
                                browser_page.fill(selector, password)
                                print(f"Entered password: {'*' * len(password)}")
                                break
                        except:
                            continue
                    else:
                        # Try filling by JavaScript if selectors fail
                        js_fill_script = f"""
                        (function() {{
                            const passwordInputs = Array.from(document.querySelectorAll('input')).filter(input => 
                                input.type === 'password' || 
                                input.name?.toLowerCase().includes('password') ||
                                input.id?.toLowerCase().includes('password') ||
                                input.placeholder?.toLowerCase().includes('password') ||
                                input.ariaLabel?.toLowerCase().includes('password')
                            );
                            if (passwordInputs.length > 0) {{
                                passwordInputs[0].value = '{password}';
                                passwordInputs[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
                                passwordInputs[0].dispatchEvent(new Event('change', {{ bubbles: true }}));
                                return true;
                            }}
                            return false;
                        }})();
                        """
                        filled = browser_page.evaluate(js_fill_script)
                        if filled:
                            print(f"Entered password using JavaScript: {'*' * len(password)}")
                        else:
                            print(f"Could not find password field")
                except Exception as e:
                    print(f"Error entering password: {e}")
                continue
            
            # Handle unknown commands
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
        print("\n==== Starting Voice Assistant Demo ====")
        
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
