import os
import asyncio
import logging
from playwright.async_api import async_playwright

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from webassist.Common.constants import DEFAULT_START_URL, DEFAULT_API_KEY, EXIT_COMMANDS, HELP_COMMAND
from webassist.core.config import AssistantConfig
from webassist.llm.provider import LLMProviderFactory
from webassist.models.context import PageContext
from webassist.models.result import InteractionResult

from webassist.voice_assistant.interactions.navigation import NavigationHandler
from webassist.voice_assistant.interactions.form_filling import FormFillingHandler
from webassist.voice_assistant.interactions.selection import SelectionHandler
from webassist.voice_assistant.utils.browser_utils import BrowserUtils
from webassist.voice_assistant.utils.llm_utils import LLMUtils
from webassist.voice_assistant.speech.recognizer import create_recognizer
from webassist.voice_assistant.speech.synthesizer import create_synthesizer


class VoiceAssistant:
    """Main voice assistant class that coordinates all functionality"""

    def __init__(self, config=None):
        """Initialize the voice assistant with configuration"""
        self.synthesizer = None
        self.recognizer = None
        self.llm_provider = None
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.input_mode = "text"  # Default to text mode

        # Use provided config or create default
        self.config = config or AssistantConfig.from_env()

        # Initialize handlers
        self.navigation_handler = None
        self.form_filling_handler = None
        self.selection_handler = None
        self.browser_utils = None
        self.llm_utils = None

    async def initialize(self):
        """Initialize all components"""
        try:
            # Get initial input mode from user
            self.input_mode = self._get_initial_mode()
            print(f"🚀 Assistant initialized in {self.input_mode} mode")

            print("Initializing speech components...")
            # Initialize speech synthesis
            self.synthesizer = create_synthesizer(self.config)

            # Create a synchronous wrapper for the speak function
            def sync_speak(text):
                print(f"ASSISTANT: {text}")
                # Can't await in a synchronous function, so just print

            # Initialize speech recognition with the synchronous speak function
            self.recognizer = create_recognizer(self.config, self.input_mode, sync_speak)
            print("Speech components initialized successfully")

            print("Initializing LLM provider...")
            api_key = self.config.gemini_api_key or os.environ.get("GEMINI_API_KEY", DEFAULT_API_KEY)
            if not api_key:
                raise ValueError("No Gemini API key found. Please set GEMINI_API_KEY environment variable or in .env file.")
            self.llm_provider = LLMProviderFactory.create_provider("gemini", api_key, self.config.llm_model)
            print("LLM provider initialized successfully")

            print("Initializing browser...")
            try:
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(headless=self.config.browser_headless)
                self.context = await self.browser.new_context(
                    viewport={'width': self.config.browser_width, 'height': self.config.browser_height}
                )
                self.page = await self.context.new_page()
                print("Browser initialized successfully")
            except Exception as e:
                print(f"Error initializing browser: {e}")
                print("\nPlease run 'playwright install' to install the required browsers.")
                print("Then run the application again.")
                import sys
                sys.exit(1)

            print("Initializing utility handlers...")
            self.browser_utils = BrowserUtils(self.page, self.speak)
            self.llm_utils = LLMUtils(self.llm_provider, self.page, self.speak, self.browser_utils)
            print("Utility handlers initialized successfully")

            print("Initializing navigation handler...")
            self.navigation_handler = NavigationHandler(self.page, self.speak, self.llm_utils, self.browser_utils)
            print("Navigation handler initialized successfully")

            print("Setting up circular dependencies...")
            # Set navigation handler in llm_utils to resolve circular dependency
            self.llm_utils.navigation_handler = self.navigation_handler
            print("Circular dependencies resolved")

            print("Initializing remaining handlers...")
            self.form_filling_handler = FormFillingHandler(self.page, self.speak, self.llm_utils, self.browser_utils)
            self.selection_handler = SelectionHandler(self.page, self.speak, self.llm_utils, self.browser_utils)
            print("All handlers initialized successfully")

            print(f"Navigating to start URL: {DEFAULT_START_URL}")
            # Navigate to start URL
            await self.navigation_handler.browse_website(DEFAULT_START_URL)
            print("Navigation to start URL completed")
        except Exception as e:
            import traceback
            print(f"Error during initialization: {e}")
            traceback.print_exc()
            raise

    def _get_initial_mode(self):
        """Get the initial input mode from the user"""
        print("\n🔊 Select input mode:")
        print("1. Voice\n2. Text")
        while True:
            choice = input("Choice (1/2): ").strip()
            # Handle various input formats
            if choice == "1" or choice.lower() in ["voice", "v", "1."]:
                return "voice"
            elif choice == "2" or choice.lower() in ["text", "t", "2."]:
                return "text"
            # Extract the first digit if there's any in the input
            elif any(c.isdigit() for c in choice):
                digit = next((c for c in choice if c.isdigit()), None)
                if digit == "1":
                    return "voice"
                elif digit == "2":
                    return "text"
            # Default fallback
            print("Invalid choice. Please enter 1 for Voice or 2 for Text.")

    async def close(self, keep_browser_open=True):
        """Close components"""
        if not keep_browser_open:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            print("Browser closed")
        else:
            print("Browser kept open for inspection")

    async def speak(self, text):
        """Speak text"""
        print(f"ASSISTANT: {text}")
        if self.synthesizer:
            await self.synthesizer.speak(text)

    async def listen(self):
        """Listen for user input based on current mode"""
        import sys

        if self.input_mode == "text":
            # Display the command prompt for text mode
            sys.stdout.write("\n⌨️ Command: ")
            sys.stdout.flush()

            # Get input directly
            try:
                text = input().strip()
                print(f"Received text input: '{text}'")

                # Check for mode switching
                if text.lower() in ["voice", "voice mode", "switch to voice", "switch to voice mode"]:
                    self.input_mode = "voice"
                    if self.recognizer:
                        await self.recognizer.set_mode("voice")
                    print("Switched to voice mode. Say your commands.")
                    print("Listening...")
                    # Return empty string to trigger another listen cycle
                    return ""

                return text
            except Exception as e:
                print(f"Error getting text input: {e}")
                import traceback
                traceback.print_exc()
                return ""
        else:  # Voice mode
            print("Listening for voice command...")

            if not self.recognizer:
                # Fallback to text input if recognizer is not initialized
                print("Voice recognizer not initialized. Falling back to text input.")
                sys.stdout.write("⌨️ Command: ")
                sys.stdout.flush()
                return input().strip()

            # Use the voice recognizer
            try:
                text = await self.recognizer.listen()
                print(f"Recognized voice command: '{text}'")

                # Check for mode switching
                if text.lower() in ["text", "text mode", "switch to text", "switch to text mode"]:
                    self.input_mode = "text"
                    if self.recognizer:
                        await self.recognizer.set_mode("text")
                    print("Switched to text mode. Type your commands.")
                    # Return empty string to trigger another listen cycle
                    return ""

                return text
            except Exception as e:
                print(f"Error recognizing voice: {e}")
                import traceback
                traceback.print_exc()
                # Fallback to text input
                print("Voice recognition failed. Falling back to text input.")
                sys.stdout.write("⌨️ Command: ")
                sys.stdout.flush()
                return input().strip()

    async def process_command(self, command):
        """Process a command"""
        print(f"DEBUG: Processing command: '{command}'")

        # Handle mode switching commands
        if command.lower() in ["voice", "voice mode", "switch to voice", "switch to voice mode"]:
            if self.input_mode != "voice":
                self.input_mode = "voice"
                if self.recognizer:
                    await self.recognizer.set_mode("voice")
                await self.speak("Switched to voice mode")
            else:
                await self.speak("Already in voice mode")
            return True

        if command.lower() in ["text", "text mode", "switch to text", "switch to text mode"]:
            if self.input_mode != "text":
                self.input_mode = "text"
                if self.recognizer:
                    await self.recognizer.set_mode("text")
                await self.speak("Switched to text mode")
            else:
                await self.speak("Already in text mode")
            return True

        if command.lower() in EXIT_COMMANDS:
            await self.speak("Goodbye! Browser will remain open for inspection.")
            return False

        if command.lower() == HELP_COMMAND:
            await self.show_help()
            return True

        if command.lower().startswith(("go to ", "navigate to ", "open ")):
            # Extract URL
            parts = command.split(" ", 2)
            if len(parts) >= 3:
                url = parts[2]
                await self.navigation_handler.browse_website(url)
                return True

        # Try direct commands with specialized handlers
        if await self.navigation_handler.handle_command(command):
            return True

        if await self.form_filling_handler.handle_command(command):
            return True

        if await self.selection_handler.handle_command(command):
            return True

        # For other commands, use LLM to generate actions
        action_data = await self.llm_utils.get_actions(command)
        return await self.llm_utils.execute_actions(action_data)

    async def run(self):
        """Run the assistant"""
        await self.speak("Voice Assistant is ready. Say or type 'help' for available commands or 'exit' to quit.")

        if self.input_mode == "text":
            print("\nWaiting for your text commands. Type 'help' for available commands or 'exit' to quit.")
            print("Type 'voice' to switch to voice mode.")
            # Force the command prompt to display
            import sys
            sys.stdout.write("\n⌨️ Command: ")
            sys.stdout.flush()
        else:
            print("\nWaiting for your voice commands. Say 'help' for available commands or 'exit' to quit.")
            print("Say 'text' to switch to text mode.")
            print("Listening...")

        try:
            while True:
                try:
                    # Get user input using the appropriate mode (voice or text)
                    command = await self.listen()

                    # Handle empty command
                    if not command:
                        print("Empty command. Please try again.")
                        continue

                    print(f"USER: {command}")

                    # Process the command
                    continue_running = await self.process_command(command)
                    if not continue_running:
                        break
                except Exception as inner_e:
                    import traceback
                    print(f"Error processing command: {inner_e}")
                    traceback.print_exc()
                    await self.speak("Error processing command. Please try again.")
                    # Continue the loop to get the next command
                    continue
        except KeyboardInterrupt:
            await self.speak("Interrupted. Goodbye!")
        except Exception as e:
            import traceback
            print(f"Error during execution: {e}")
            traceback.print_exc()
            await self.speak("An error occurred. Please check the console for details.")

    async def show_help(self):
        """Show help information"""
        help_text = """
        🔍 Voice Web Assistant Help:

        Basic Navigation:
        - "Go to [website]" - Navigate to a website
        - "Navigate to [section]" - Go to a specific section on the current site
        - "Open [website]" - Open a website

        Login:
        - "Login with email [email] and password [password]" - Log in to a website
        - "Enter email [email] and password [password]" - Fill in login form without submitting
        - "Enter email [email]" - Fill in just the email field

        Search:
        - "Search for [query]" - Search on the current website

        Forms and Selections:
        - "Check product [product name]" - Check a product checkbox in a product list
        - "Check all products" - Check all available product checkboxes
        - "Select product [product name]" - Select a product from a list
        - "Check checkbox for [option]" - Check a checkbox for a specific option
        - "Click on [element]" - Click on a specific element
        - "Select [dropdown name] dropdown" - Open a dropdown menu
        - "Select [option] from [dropdown] dropdown" - Select an option from a dropdown

        Address Form:
        - "Enter [text] in address line 1" - Fill in the first address line
        - "Enter [text] in address line 2" - Fill in the second address line
        - "Enter [text] in city" - Fill in the city field
        - "Enter [text] in zip code" - Fill in the zip code field
        - "Select [state] from state dropdown" - Select a state from the dropdown

        Input Mode:
        - "Switch to voice mode" - Switch to voice input mode
        - "Switch to text mode" - Switch to text input mode

        General:
        - "Help" - Show this help message
        - "Exit" or "Quit" - Close the assistant
        """
        print(help_text)
        await self.speak("Here's the help information. You can see the full list on screen.")


async def main():
    """Main entry point for running the assistant directly"""
    try:
        # Load environment variables if .env file exists
        if os.path.exists(".env"):
            from dotenv import load_dotenv
            load_dotenv()

        print("Starting Voice Assistant...")
        # Create and initialize the assistant
        assistant = VoiceAssistant()
        await assistant.initialize()

        # Run the assistant's main loop
        await assistant.run()
    except Exception as e:
        import traceback
        logger.error(f"Fatal error: {e}")
        traceback.print_exc()
    finally:
        try:
            # Keep browser open for inspection
            await assistant.close(keep_browser_open=True)
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        import traceback
        logger.error(f"Fatal error in main: {e}")
        traceback.print_exc()