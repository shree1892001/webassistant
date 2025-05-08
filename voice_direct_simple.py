"""
Voice Direct Simple - A simplified version of the Voice Direct Web Assistant.

This script provides a simplified version of the Voice Direct Web Assistant
that focuses on reliable input handling for both voice and text modes.
"""

import os
import re
import asyncio
import logging
from dotenv import load_dotenv

from webassist.Common.constants import *
from webassist.core.config import AssistantConfig
from webassist.voice_assistant.core.assistant import VoiceAssistant
from webassist.voice_assistant.interactions.navigation import NavigationHandler
from webassist.voice_assistant.interactions.form_filling import FormFillingHandler
from webassist.voice_assistant.interactions.selection import SelectionHandler
from webassist.voice_assistant.interactions.specialized import SpecializedHandler
from webassist.voice_assistant.utils.browser_utils import BrowserUtils
from webassist.voice_assistant.utils.llm_utils import LLMUtils
from webassist.voice_assistant.speech.recognizer import create_recognizer
from webassist.voice_assistant.speech.synthesizer import create_synthesizer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SimpleVoiceAssistant:
    """A simplified voice assistant that handles both voice and text input"""
    
    def __init__(self):
        """Initialize the assistant"""
        self.assistant = None
        self.input_mode = "text"  # Default to text mode
        
    async def initialize(self):
        """Initialize the assistant"""
        # Load environment variables if .env file exists
        if os.path.exists(".env"):
            load_dotenv()
            logger.info("Loaded environment variables from .env file")
        else:
            logger.info("No .env file found, using environment variables")

        print("\n" + "="*50)
        print("Voice Direct Simple - Web Assistant")
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
        choice = input("Choice (1/2): ").strip()
        
        # Set the input mode based on user choice
        if choice == "1" or choice.lower() in ["voice", "v", "1."]:
            self.input_mode = "voice"
            print("🚀 Assistant initialized in voice mode")
        else:
            self.input_mode = "text"
            print("🚀 Assistant initialized in text mode")
            
        # Set the input mode in the config
        config.input_mode = self.input_mode

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
        
    async def run(self):
        """Run the assistant"""
        # Welcome message
        await self.assistant.speak("Voice Assistant is ready. Say or type 'help' for available commands or 'exit' to quit.")
        
        print("\n=== READY FOR COMMANDS ===")
        if self.input_mode == "text":
            print("Type your commands below. Type 'help' for available commands or 'exit' to quit.")
            print("Type 'voice' to switch to voice mode.")
        else:
            print("Say your commands. Say 'help' for available commands or 'exit' to quit.")
            print("Say 'text' to switch to text mode.")
            print("🎤 Listening...")
        
        # Main command loop
        while True:
            try:
                # Get command based on current mode
                if self.input_mode == "text":
                    # Text mode - get input directly
                    command = input("\n⌨️ Command: ").strip()
                    
                    # Check for mode switching
                    if command.lower() in ["voice", "voice mode", "switch to voice", "switch to voice mode"]:
                        self.input_mode = "voice"
                        print("Switched to voice mode. Say your commands.")
                        print("Say 'text' or 'switch to text mode' to switch back to text mode.")
                        print("🎤 Listening...")
                        continue
                else:
                    # Voice mode - use the recognizer
                    print("\n🎤 Listening...")
                    command = await self.assistant.recognizer.listen()
                    print(f"Recognized: {command}")
                    
                    # Check for mode switching
                    if command.lower() in ["text", "text mode", "switch to text", "switch to text mode"]:
                        self.input_mode = "text"
                        print("Switched to text mode. Type your commands.")
                        print("Type 'voice' or 'switch to voice mode' to switch back to voice mode.")
                        continue
                
                # Skip empty commands
                if not command:
                    continue
                    
                # Process the command
                print(f"USER: {command}")
                
                # Exit if the command is 'exit' or 'quit'
                if command.lower() in ['exit', 'quit']:
                    await self.assistant.speak("Goodbye!")
                    break
                    
                # Process the command
                result = await self.assistant.process_command(command)
                if not result:  # If process_command returns False, exit
                    break
                    
            except KeyboardInterrupt:
                print("\nKeyboard interrupt detected. Exiting...")
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
        # Create and initialize the assistant
        assistant = SimpleVoiceAssistant()
        await assistant.initialize()
        
        # Run the assistant
        await assistant.run()
        
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
