"""
Advanced Voice Assistant - A comprehensive solution with advanced web interaction capabilities.
"""

import asyncio
import sys
import re
import json
import time
from playwright.async_api import async_playwright, TimeoutError

# Try to import speech recognition
try:
    import speech_recognition as sr
    SPEECH_AVAILABLE = True
except ImportError:
    print("Speech recognition not available. Install with: pip install SpeechRecognition pyaudio")
    SPEECH_AVAILABLE = False

class AdvancedVoiceAssistant:
    def __init__(self):
        self.browser = None
        self.page = None
        self.running = True
        self.command_history = []
        
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
        """Navigate to a URL with special handling for specific sites"""
        try:
            # Format URL properly
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            
            # Special handling for specific sites
            if "redberyltest.in" in url.lower():
                url = "https://www.redberyltest.in"
                print(f"Using specific URL for redberyltest.in: {url}")
            
            print(f"Navigating to: {url}")
            await self.page.goto(url, timeout=30000)
            title = await self.page.title()
            print(f"Loaded: {title}")
            return True
        except Exception as e:
            print(f"Error navigating to {url}: {e}")
            return False
    
    async def fill_form(self, field_type, value):
        """Fill a form field based on type"""
        try:
            if field_type.lower() in ["email", "mail"]:
                # Try multiple selectors for email fields
                selectors = [
                    'input[type="email"]',
                    'input[name="email"]',
                    'input[id*="email"]',
                    'input[placeholder*="email"]',
                    '#floating_outlined3'  # Specific for redberyltest.in
                ]
                
                for selector in selectors:
                    try:
                        count = await self.page.locator(selector).count()
                        if count > 0:
                            await self.page.fill(selector, value)
                            print(f"Filled {field_type} field with: {value}")
                            return True
                    except:
                        continue
                
                print(f"Could not find {field_type} field")
                return False
                
            elif field_type.lower() in ["password", "pass", "pwd"]:
                # Try multiple selectors for password fields
                selectors = [
                    'input[type="password"]',
                    'input[name="password"]',
                    'input[id*="password"]',
                    '#floating_outlined15'  # Specific for redberyltest.in
                ]
                
                for selector in selectors:
                    try:
                        count = await self.page.locator(selector).count()
                        if count > 0:
                            await self.page.fill(selector, value)
                            print(f"Filled {field_type} field with: {'*' * len(value)}")
                            return True
                    except:
                        continue
                
                print(f"Could not find {field_type} field")
                return False
            
            else:
                # Generic field filling
                selectors = [
                    f'input[name*="{field_type}"]',
                    f'input[id*="{field_type}"]',
                    f'input[placeholder*="{field_type}"]',
                    f'textarea[name*="{field_type}"]',
                    f'textarea[id*="{field_type}"]',
                    f'textarea[placeholder*="{field_type}"]'
                ]
                
                for selector in selectors:
                    try:
                        count = await self.page.locator(selector).count()
                        if count > 0:
                            await self.page.fill(selector, value)
                            print(f"Filled {field_type} field with: {value}")
                            return True
                    except:
                        continue
                
                print(f"Could not find {field_type} field")
                return False
        except Exception as e:
            print(f"Error filling {field_type} field: {e}")
            return False
    
    async def click_element(self, element_name):
        """Click an element based on its name or description"""
        try:
            # Try multiple selectors based on element name
            selectors = [
                f'button:has-text("{element_name}")',
                f'a:has-text("{element_name}")',
                f'[role="button"]:has-text("{element_name}")',
                f'input[value="{element_name}"]',
                f'[aria-label*="{element_name}"]',
                f'[title*="{element_name}"]'
            ]
            
            # Special case for login button
            if element_name.lower() in ["login", "sign in", "signin"]:
                selectors.extend([
                    '#signInButton',  # Specific for redberyltest.in
                    'button[type="submit"]',
                    'input[type="submit"]'
                ])
            
            for selector in selectors:
                try:
                    count = await self.page.locator(selector).count()
                    if count > 0:
                        await self.page.click(selector)
                        print(f"Clicked {element_name}")
                        return True
                except:
                    continue
            
            print(f"Could not find {element_name} to click")
            return False
        except Exception as e:
            print(f"Error clicking {element_name}: {e}")
            return False
    
    def recognize_speech(self):
        """Recognize speech using direct microphone access"""
        if not SPEECH_AVAILABLE:
            print("Speech recognition not available")
            return input("Command: ").strip()
        
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
                
                # Add to command history
                self.command_history.append(text.lower())
                if len(self.command_history) > 10:
                    self.command_history.pop(0)
                
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
        
        # Handle help command
        if command.lower() in ["help", "commands", "what can you do"]:
            self.show_help()
            return True
        
        # Handle navigation commands
        if command.lower().startswith(("go to ", "navigate to ", "open ")):
            url = command.split(" ", 2)[-1].strip()
            await self.navigate_to(url)
            return True
        
        # If it looks like a URL, navigate to it
        if "." in command and " " not in command:
            await self.navigate_to(command)
            return True
        
        # Handle login commands
        login_match = re.search(r'(?:login|sign in)(?:\s+with)?\s+(?:email|username)?\s+(\S+@\S+)(?:\s+(?:and|with)?\s+(?:password|pass)\s+(\S+))?', command, re.IGNORECASE)
        if login_match:
            email = login_match.group(1)
            password = login_match.group(2) if login_match.group(2) else ""
            
            # Fill email field
            await self.fill_form("email", email)
            
            # Fill password field if provided
            if password:
                await self.fill_form("password", password)
            
            # Click login button
            await self.click_element("login")
            return True
        
        # Handle email/password commands separately
        email_match = re.search(r'(?:enter|input|type|fill)\s+(?:email|e-mail)\s+(\S+@\S+)', command, re.IGNORECASE)
        if email_match:
            email = email_match.group(1)
            await self.fill_form("email", email)
            return True
        
        password_match = re.search(r'(?:enter|input|type|fill)\s+(?:password|pass)\s+(\S+)', command, re.IGNORECASE)
        if password_match:
            password = password_match.group(1)
            await self.fill_form("password", password)
            return True
        
        # Handle click commands
        click_match = re.search(r'(?:click|press|select)\s+(?:on\s+)?(?:the\s+)?(.+)', command, re.IGNORECASE)
        if click_match:
            element_name = click_match.group(1).strip()
            await self.click_element(element_name)
            return True
        
        # Handle form filling commands
        form_match = re.search(r'(?:enter|input|type|fill)\s+(\S+)\s+(?:as|in|into|for)\s+(\S+)(?:\s+field)?', command, re.IGNORECASE)
        if form_match:
            value = form_match.group(1)
            field_type = form_match.group(2)
            await self.fill_form(field_type, value)
            return True
        
        print("Command not recognized. Try 'help' for available commands.")
        return True
    
    def show_help(self):
        """Show available commands"""
        print("\n" + "=" * 60)
        print("AVAILABLE COMMANDS")
        print("=" * 60)
        print("Navigation:")
        print("  - 'go to [website]' - Navigate to a website")
        print("  - 'navigate to [website]' - Navigate to a website")
        print("  - 'open [website]' - Open a website")
        print("\nForm Filling:")
        print("  - 'enter email [email]' - Fill an email field")
        print("  - 'enter password [password]' - Fill a password field")
        print("  - 'enter [value] as [field]' - Fill a specific field")
        print("  - 'login with email [email] and password [password]' - Login with credentials")
        print("\nInteraction:")
        print("  - 'click [element]' - Click on an element")
        print("  - 'press [button]' - Press a button")
        print("  - 'select [option]' - Select an option")
        print("\nSystem:")
        print("  - 'help' - Show this help message")
        print("  - 'exit' or 'quit' - Exit the program")
        print("=" * 60)
    
    async def run(self):
        """Run the assistant"""
        print("\n" + "=" * 50)
        print("Advanced Voice Assistant")
        print("=" * 50)
        
        self.show_help()
        
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
    assistant = AdvancedVoiceAssistant()
    if await assistant.initialize():
        await assistant.run()
    else:
        print("Failed to initialize. Exiting.")

if __name__ == "__main__":
    asyncio.run(main())
