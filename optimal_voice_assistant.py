"""
Optimal Voice Assistant - A streamlined solution for voice recognition and web navigation.
"""

import asyncio
import sys
import re
from playwright.async_api import async_playwright

# Try to import speech recognition
try:
    import speech_recognition as sr
    SPEECH_AVAILABLE = True
except ImportError:
    print("Speech recognition not available. Install with: pip install SpeechRecognition pyaudio")
    SPEECH_AVAILABLE = False

class OptimalAssistant:
    def __init__(self):
        self.browser = None
        self.page = None
        self.running = True
        
    async def initialize(self):
        """Initialize the browser"""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=False)
            self.page = await self.browser.new_page()
            print("Browser initialized successfully")
            await self.navigate_to("https://www.google.com")
            return True
        except Exception as e:
            print(f"Error initializing browser: {e}")
            return False
    
    async def navigate_to(self, url):
        """Navigate to a URL with special handling for redberyltest.in"""
        try:
            # Format URL properly
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            
            # Special handling for redberyltest.in
            if "redberyltest.in" in url.lower():
                url = "https://www.redberyltest.in"
                print(f"Using specific URL for redberyltest.in: {url}")
            
            print(f"Navigating to: {url}")
            await self.page.goto(url)
            title = await self.page.title()
            print(f"Loaded: {title}")
            return True
        except Exception as e:
            print(f"Error navigating to {url}: {e}")
            return False
    
    def recognize_speech(self):
        """Recognize speech using direct microphone access"""
        if not SPEECH_AVAILABLE:
            print("Speech recognition not available")
            return None
        
        # Create fresh instances each time
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        
        try:
            with microphone as source:
                print("\n" + "=" * 60)
                print("🎤 LISTENING... (Speak your command)")
                print("=" * 60)
                sys.stdout.flush()
                
                # Adjust for ambient noise
                recognizer.adjust_for_ambient_noise(source, duration=1.0)
                
                # Set parameters for better recognition
                recognizer.energy_threshold = 300  # Lower threshold for better sensitivity
                recognizer.dynamic_energy_threshold = True
                
                # Listen for audio
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)
                
                print("🔍 Recognizing speech...")
                sys.stdout.flush()
                
                # Recognize speech using Google Speech Recognition
                text = recognizer.recognize_google(audio, language="en-US")
                print(f"🎯 Recognized: \"{text}\"")
                return text.lower()
        except sr.UnknownValueError:
            print("❌ Speech not recognized. Please try again or type your command.")
            return input("Command: ").strip()
        except Exception as e:
            print(f"Error in speech recognition: {e}")
            return input("Command: ").strip()
    
    async def process_command(self, command):
        """Process a user command"""
        if not command:
            return True
        
        print(f"Processing: {command}")
        
        # Handle exit commands
        if command.lower() in ["exit", "quit", "stop"]:
            self.running = False
            return False
        
        # Handle navigation commands
        if command.lower().startswith(("go to ", "navigate to ")):
            url = command.split(" ", 2)[-1].strip()
            await self.navigate_to(url)
            return True
        
        # If it looks like a URL, navigate to it
        if "." in command and " " not in command:
            await self.navigate_to(command)
            return True
        
        print("Command not recognized. Try 'go to website.com' or 'exit'")
        return True
    
    async def run(self):
        """Run the assistant"""
        print("\n" + "=" * 50)
        print("Optimal Voice Assistant")
        print("=" * 50)
        
        print("\nCommands:")
        print("- 'go to [website]' - Navigate to a website")
        print("- 'exit' or 'quit' - Exit the program")
        
        while self.running:
            try:
                # Get command using speech recognition
                command = self.recognize_speech()
                
                # Process the command
                if command:
                    await self.process_command(command)
                
                await asyncio.sleep(0.1)
            except KeyboardInterrupt:
                print("\nExiting...")
                self.running = False
            except Exception as e:
                print(f"Error: {e}")
        
        # Clean up
        if self.browser:
            await self.browser.close()
        
        print("Goodbye!")

async def main():
    assistant = OptimalAssistant()
    if await assistant.initialize():
        await assistant.run()
    else:
        print("Failed to initialize. Exiting.")

if __name__ == "__main__":
    asyncio.run(main())
