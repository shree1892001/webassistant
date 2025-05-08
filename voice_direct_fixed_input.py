"""
Voice Direct Fixed Input - A version of the Voice Direct Web Assistant with fixed input handling.

This script provides a direct implementation of the Voice Direct Web Assistant with
special handling for command input to ensure it's always visible and working.
"""

import os
import asyncio
import logging
import sys
import time
from dotenv import load_dotenv

from webassist.Common.constants import *
from webassist.core.config import AssistantConfig
from webassist.voice_assistant.core.assistant import VoiceAssistant
from webassist.voice_assistant.interactions.specialized import SpecializedHandler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CommandLineInterface:
    """A simple command-line interface for the Voice Assistant"""
    
    def __init__(self):
        """Initialize the interface"""
        self.assistant = None
        self.running = True
        
    async def initialize(self):
        """Initialize the assistant"""
        # Load environment variables if .env file exists
        if os.path.exists(".env"):
            load_dotenv()
            logger.info("Loaded environment variables from .env file")
        else:
            logger.info("No .env file found, using environment variables")

        print("\n" + "="*50)
        print("Voice Direct Fixed Input - Web Assistant")
        print("="*50 + "\n")

        print("Initializing Voice Assistant...")
        # Create configuration
        config = AssistantConfig.from_env()

        # Check if API key is available
        if not config.gemini_api_key:
            print("WARNING: No Gemini API key found in environment variables or .env file.")
            print("Using default API key from constants.py")
            config.gemini_api_key = DEFAULT_API_KEY

        # Always use text mode for simplicity
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
        
    async def get_command(self):
        """Get a command from the user"""
        # Use a direct approach that should work reliably
        print("\n⌨️ Command: ", end='', flush=True)
        return input().strip()
        
    async def run(self):
        """Run the interface"""
        # Welcome message
        print("\n=== READY FOR COMMANDS ===")
        print("Type your commands below. Type 'help' for available commands or 'exit' to quit.")
        await self.assistant.speak("Voice Assistant is ready. Type 'help' for available commands or 'exit' to quit.")
        
        # Main command loop
        while self.running:
            try:
                # Get command from user
                command = await self.get_command()
                
                # Skip empty commands
                if not command:
                    continue
                    
                # Process the command
                print(f"USER: {command}")
                
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
                print("\nKeyboard interrupt detected. Exiting...")
                self.running = False
                break
            except Exception as e:
                print(f"Error processing command: {e}")
                import traceback
                traceback.print_exc()
                await self.assistant.speak(f"Error processing command: {str(e)}")
                
        # Close the assistant
        await self.assistant.close(keep_browser_open=True)


async def main():
    """Main entry point"""
    try:
        # Create and initialize the interface
        interface = CommandLineInterface()
        await interface.initialize()
        
        # Run the interface
        await interface.run()
        
    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected. Exiting...")
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
    finally:
        print("\nProgram ended. Browser will remain open for inspection.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        import traceback
        logger.error(f"Fatal error: {e}")
        traceback.print_exc()
