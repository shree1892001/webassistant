"""
Voice Direct Dual Mode - A version of the Voice Direct Web Assistant with reliable handling
for both voice and text input modes.

This script provides a direct implementation of the Voice Direct Web Assistant with
special handling for both voice and text input to ensure it's always visible and working.
"""

import os
import asyncio
import logging
import sys
import time
import threading
from dotenv import load_dotenv

from webassist.Common.constants import *
from webassist.core.config import AssistantConfig
from webassist.voice_assistant.core.assistant import VoiceAssistant
from webassist.voice_assistant.interactions.specialized import SpecializedHandler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DualModeInterface:
    """A dual-mode interface for the Voice Assistant supporting both voice and text input"""

    def __init__(self):
        """Initialize the interface"""
        self.assistant = None
        self.running = True
        self.current_mode = "text"  # Default to text mode
        self.voice_thread = None
        self.voice_command = None
        self.voice_command_ready = threading.Event()

    async def initialize(self):
        """Initialize the assistant"""
        # Load environment variables if .env file exists
        if os.path.exists(".env"):
            load_dotenv()
            logger.info("Loaded environment variables from .env file")
        else:
            logger.info("No .env file found, using environment variables")

        print("\n" + "="*50)
        print("Voice Direct Dual Mode - Web Assistant")
        print("="*50 + "\n")

        print("Initializing Voice Assistant...")
        # Create configuration
        config = AssistantConfig.from_env()

        # Check if API key is available
        if not config.gemini_api_key:
            print("WARNING: No Gemini API key found in environment variables or .env file.")
            print("Using default API key from constants.py")
            config.gemini_api_key = DEFAULT_API_KEY

        # Get input mode from user
        print("\n🔊 Select input mode:")
        print("1. Voice\n2. Text")
        print("Choice (1/2): ", end='', flush=True)
        choice = input().strip()

        # Set the input mode based on user choice
        if choice == "1" or choice.lower() in ["voice", "v", "1."]:
            self.current_mode = "voice"
            config.input_mode = "voice"
            print("🚀 Assistant initialized in voice mode")
        else:
            self.current_mode = "text"
            config.input_mode = "text"
            print("🚀 Assistant initialized in text mode")

        # Initialize the assistant
        self.assistant = VoiceAssistant(config)
        await self.assistant.initialize()

        # Add the specialized handler
        print("Adding specialized handler for state selection, login, etc...")
        self.assistant.specialized_handler = SpecializedHandler(
            self.assistant.page,
            self.assistant.speak,
            self.assistant.llm_utils,
            self.assistant.browser_utils
        )

        # Ensure all handlers are properly initialized
        if not hasattr(self.assistant, 'selection_handler') or self.assistant.selection_handler is None:
            print("Initializing selection handler...")
            self.assistant.selection_handler = SelectionHandler(
                self.assistant.page,
                self.assistant.speak,
                self.assistant.llm_utils,
                self.assistant.browser_utils
            )

        if not hasattr(self.assistant, 'form_filling_handler') or self.assistant.form_filling_handler is None:
            print("Initializing form filling handler...")
            self.assistant.form_filling_handler = FormFillingHandler(
                self.assistant.page,
                self.assistant.speak,
                self.assistant.llm_utils,
                self.assistant.browser_utils
            )

        if not hasattr(self.assistant, 'navigation_handler') or self.assistant.navigation_handler is None:
            print("Initializing navigation handler...")
            self.assistant.navigation_handler = NavigationHandler(
                self.assistant.page,
                self.assistant.speak,
                self.assistant.llm_utils,
                self.assistant.browser_utils
            )

        # Patch the process_command method
        original_process_command = self.assistant.process_command

        async def patched_process_command(command):
            # Try specialized handler first
            if hasattr(self.assistant, 'specialized_handler'):
                if await self.assistant.specialized_handler.handle_command(command):
                    return True

            # If specialized handler didn't handle it, use the original method
            return await original_process_command(command)

        # Replace the process_command method
        self.assistant.process_command = patched_process_command

    def voice_input_thread(self):
        """Thread function for handling voice input"""
        while self.running and self.current_mode == "voice":
            try:
                print("\n🎤 Listening...", flush=True)

                # Use the voice recognizer directly
                if hasattr(self.assistant, 'recognizer'):
                    # This is a blocking call, but it's in its own thread
                    text = asyncio.run(self.assistant.recognizer.listen())

                    if text:
                        print(f"Recognized: {text}", flush=True)

                        # Check for mode switching
                        if text.lower() in ["text", "text mode", "switch to text", "switch to text mode"]:
                            self.current_mode = "text"
                            print("Switched to text mode. Type your commands.", flush=True)
                            continue

                        # Store the command and signal that it's ready
                        self.voice_command = text
                        self.voice_command_ready.set()

                        # Wait for the command to be processed
                        time.sleep(1)

                        # Reset the event for the next command
                        self.voice_command_ready.clear()
                else:
                    print("Voice recognizer not available. Switching to text mode.", flush=True)
                    self.current_mode = "text"
                    break
            except Exception as e:
                print(f"Error in voice recognition: {e}", flush=True)
                import traceback
                traceback.print_exc()
                # If there's an error, switch to text mode
                self.current_mode = "text"
                print("Error in voice recognition. Switched to text mode.", flush=True)
                break

    async def get_command(self):
        """Get a command from the user based on current mode"""
        if self.current_mode == "text":
            # Text mode - get input directly
            print("\n⌨️ Command: ", end='', flush=True)
            command = input().strip()

            # Check for mode switching
            if command.lower() in ["voice", "voice mode", "switch to voice", "switch to voice mode"]:
                self.current_mode = "voice"
                print("Switched to voice mode. Say your commands.", flush=True)
                print("Say 'text' or 'switch to text mode' to switch back to text mode.", flush=True)

                # Start the voice input thread
                self.voice_thread = threading.Thread(target=self.voice_input_thread)
                self.voice_thread.daemon = True
                self.voice_thread.start()

                # Return empty string to trigger another get_command call
                return ""

            return command
        else:
            # Voice mode - wait for a command from the voice thread
            if not self.voice_thread or not self.voice_thread.is_alive():
                # Start the voice input thread if it's not running
                self.voice_thread = threading.Thread(target=self.voice_input_thread)
                self.voice_thread.daemon = True
                self.voice_thread.start()

            # Wait for a voice command
            self.voice_command_ready.wait()
            command = self.voice_command

            return command

    async def run(self):
        """Run the interface"""
        # Welcome message
        print("\n=== READY FOR COMMANDS ===", flush=True)
        if self.current_mode == "text":
            print("Type your commands below. Type 'help' for available commands or 'exit' to quit.", flush=True)
            print("Type 'voice' to switch to voice mode.", flush=True)
        else:
            print("Say your commands. Say 'help' for available commands or 'exit' to quit.", flush=True)
            print("Say 'text' to switch to text mode.", flush=True)

            # Start the voice input thread
            self.voice_thread = threading.Thread(target=self.voice_input_thread)
            self.voice_thread.daemon = True
            self.voice_thread.start()

        await self.assistant.speak("Voice Assistant is ready. Say or type 'help' for available commands or 'exit' to quit.")

        # Main command loop
        while self.running:
            try:
                # Get command based on current mode
                command = await self.get_command()

                # Skip empty commands
                if not command:
                    continue

                # Process the command
                print(f"USER: {command}", flush=True)

                # Exit if the command is 'exit' or 'quit'
                if command.lower() in ['exit', 'quit']:
                    await self.assistant.speak("Goodbye!")
                    self.running = False
                    break

                # Process the command
                result = await self.assistant.process_command(command)
                if not result:  # If process_command returns False, exit
                    self.running = False
                    break

            except KeyboardInterrupt:
                print("\nKeyboard interrupt detected. Exiting...", flush=True)
                self.running = False
                break
            except Exception as e:
                print(f"Error processing command: {e}", flush=True)
                import traceback
                traceback.print_exc()
                await self.assistant.speak(f"Error processing command: {str(e)}")

        # Close the assistant
        await self.assistant.close(keep_browser_open=True)


async def main():
    """Main entry point"""
    try:
        # Create and initialize the interface
        interface = DualModeInterface()
        await interface.initialize()

        # Run the interface
        await interface.run()

    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected. Exiting...", flush=True)
    except Exception as e:
        import traceback
        print(f"Error: {e}", flush=True)
        traceback.print_exc()
    finally:
        print("\nProgram ended. Browser will remain open for inspection.", flush=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        import traceback
        logger.error(f"Fatal error: {e}")
        traceback.print_exc()
