"""
Simple Voice Assistant - A standalone voice recognition and web navigation tool.
This is a simplified version that focuses solely on voice recognition and basic web navigation.
"""

import os
import sys
import asyncio
import time
import re
from playwright.async_api import async_playwright

# Try to import speech recognition
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    print("Speech recognition not available. Install with: pip install SpeechRecognition")
    print("You'll also need PyAudio: pip install pyaudio")
    SPEECH_RECOGNITION_AVAILABLE = False

# Constants
VOICE_PROMPT = "🎤 READY FOR VOICE COMMAND... (Say 'help' for available commands or 'text' to switch to text mode)"
TEXT_PROMPT = "Type your commands below. Type 'help' for available commands or 'exit' to quit."
HELP_TEXT = """
Available commands:
- 'go to [website]' or 'navigate to [website]': Navigate to a website
- 'text' or 'switch to text mode': Switch to text input mode
- 'voice' or 'switch to voice mode': Switch to voice input mode
- 'help': Show this help message
- 'exit' or 'quit': Exit the program
"""

class SimpleAssistant:
    def __init__(self):
        self.page = None
        self.browser = None
        self.input_mode = "text"  # Default to text mode
        self.running = True
        
    async def initialize(self):
        """Initialize the assistant"""
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
        if command.lower() in ["exit", "quit"]:
            print("Goodbye!")
            self.running = False
            return False
            
        # Handle help command
        if command.lower() == "help":
            print(HELP_TEXT)
            return True
            
        # Handle mode switching commands
        if command.lower() in ["voice", "voice mode", "switch to voice", "switch to voice mode"]:
            if not SPEECH_RECOGNITION_AVAILABLE:
                print("Speech recognition is not available. Please install the required packages.")
                return True
                
            self.input_mode = "voice"
            print("Switched to voice mode. Say your commands.")
            return True
            
        if command.lower() in ["text", "text mode", "switch to text", "switch to text mode"]:
            self.input_mode = "text"
            print("Switched to text mode. Type your commands.")
            return True
            
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
        print("I'm not sure how to process that command. Type 'help' for available commands.")
        return True
        
    async def listen_voice(self):
        """Listen for voice input"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            print("Speech recognition is not available. Switching to text mode.")
            self.input_mode = "text"
            return ""
            
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        
        try:
            with microphone as source:
                print("\n" + "=" * 60)
                print(VOICE_PROMPT)
                print("=" * 60)
                sys.stdout.flush()
                
                print("Adjusting for ambient noise...")
                recognizer.adjust_for_ambient_noise(source, duration=1.0)
                
                print("Ready! Please speak your command now.")
                sys.stdout.flush()
                
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)
                
                print("Recognizing speech...")
                text = recognizer.recognize_google(audio).lower()
                
                print(f"Recognized: \"{text}\"")
                return text
        except sr.UnknownValueError:
            print("Speech not recognized. Please try again.")
            # Provide a fallback to text input
            print("Fallback to text input:")
            return input("Command: ").strip()
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            # Provide a fallback to text input
            print("Fallback to text input:")
            return input("Command: ").strip()
        except Exception as e:
            print(f"Error in voice recognition: {e}")
            # Provide a fallback to text input
            print("Fallback to text input:")
            return input("Command: ").strip()
            
    async def listen_text(self):
        """Listen for text input"""
        try:
            command = input("\nCommand: ").strip()
            return command
        except Exception as e:
            print(f"Error getting text input: {e}")
            return ""
            
    async def run(self):
        """Run the assistant"""
        print("\n" + "=" * 50)
        print("Simple Voice Assistant")
        print("=" * 50)
        
        if SPEECH_RECOGNITION_AVAILABLE:
            print("\nVoice recognition is available.")
            print("Would you like to use voice mode? (y/n): ", end="")
            choice = input().strip().lower()
            if choice in ["y", "yes"]:
                self.input_mode = "voice"
                print("Starting in voice mode.")
            else:
                print("Starting in text mode.")
        else:
            print("\nVoice recognition is not available. Starting in text mode.")
            
        print(HELP_TEXT)
        
        while self.running:
            try:
                # Get command based on current mode
                if self.input_mode == "voice":
                    command = await self.listen_voice()
                else:
                    command = await self.listen_text()
                    
                # Process the command
                result = await self.process_command(command)
                if not result:
                    break
            except KeyboardInterrupt:
                print("\nKeyboard interrupt detected. Exiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
                
        # Clean up
        if self.browser:
            print("Closing browser...")
            await self.browser.close()
            
        print("Goodbye!")
        
async def main():
    """Main entry point"""
    assistant = SimpleAssistant()
    success = await assistant.initialize()
    if success:
        await assistant.run()
    else:
        print("Failed to initialize assistant. Exiting.")
        
if __name__ == "__main__":
    asyncio.run(main())
