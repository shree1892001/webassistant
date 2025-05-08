"""
Voice Navigation - A simple script to test voice recognition with web navigation.
"""

import sys
import time
import re
import asyncio
from playwright.async_api import async_playwright

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    print("Speech recognition not available. Install with: pip install SpeechRecognition")
    print("You'll also need PyAudio: pip install pyaudio")
    SPEECH_RECOGNITION_AVAILABLE = False
    sys.exit(1)

class VoiceNavigation:
    def __init__(self):
        self.page = None
        self.browser = None
        self.running = True
        
    async def initialize(self):
        """Initialize the browser"""
        print("\nInitializing browser...")
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=False)
            self.page = await self.browser.new_page()
            print("Browser initialized successfully")
            
            # Navigate to a start URL
            await self.navigate_to("https://www.google.com")
            return True
        except Exception as e:
            print(f"Error initializing browser: {e}")
            return False
            
    async def navigate_to(self, url):
        """Navigate to a URL"""
        print(f"Navigating to: {url}")
        try:
            # Ensure the URL is properly formatted
            if not url.startswith("http"):
                url = "https://" + url
                
            # Special handling for redberyltest.in
            if "redberyltest.in" in url.lower():
                url = "https://www.redberyltest.in"
                print(f"Using specific URL for redberyltest.in: {url}")
                
            await self.page.goto(url)
            title = await self.page.title()
            print(f"Loaded: {title}")
            return True
        except Exception as e:
            print(f"Error navigating to {url}: {e}")
            return False
            
    async def process_command(self, command):
        """Process a user command"""
        if not command:
            return True
            
        print(f"Processing command: {command}")
        
        # Handle exit commands
        if command.lower() in ["exit", "quit", "stop", "end"]:
            print("Goodbye!")
            self.running = False
            return False
            
        # Process navigation commands
        if command.lower().startswith("go to ") or command.lower().startswith("navigate to "):
            url = command.split(" ", 2)[-1].strip()
            await self.navigate_to(url)
            return True
            
        # If it looks like a URL, try to navigate to it
        if "." in command and " " not in command:
            await self.navigate_to(command)
            return True
            
        # If nothing else worked, let the user know
        print("I'm not sure how to process that command.")
        print("Try saying 'go to [website]' or 'navigate to [website]'.")
        return True
        
    def listen_for_command(self):
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
            
            # Fallback to text input
            print("\nFallback to text input:")
            return input("Command: ").strip()
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            
            # Fallback to text input
            print("\nFallback to text input:")
            return input("Command: ").strip()
        except Exception as e:
            print(f"Error in voice recognition: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback to text input
            print("\nFallback to text input:")
            return input("Command: ").strip()
            
    async def run(self):
        """Run the voice navigation"""
        print("\n" + "=" * 50)
        print("Voice Navigation")
        print("=" * 50)
        
        print("\nVoice navigation is ready.")
        print("Say 'go to [website]' or 'navigate to [website]' to navigate.")
        print("Say 'exit' or 'quit' to end the program.")
        
        # Main loop
        while self.running:
            try:
                # Listen for command
                command = self.listen_for_command()
                
                # Process the command
                if command:
                    result = await self.process_command(command)
                    if not result:
                        break
                else:
                    print("No command recognized. Please try again.")
                    
                # Add a small delay
                await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nKeyboard interrupt detected. Exiting...")
                self.running = False
                break
            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()
        
        # Clean up
        if self.browser:
            print("Closing browser...")
            await self.browser.close()
            
        print("Goodbye!")
        
async def main():
    """Main function"""
    navigator = VoiceNavigation()
    success = await navigator.initialize()
    if success:
        await navigator.run()
    else:
        print("Failed to initialize navigator. Exiting.")
        
if __name__ == "__main__":
    asyncio.run(main())
