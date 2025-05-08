"""
Voice Direct Simple Input - A very simple version of the Voice Direct Web Assistant
that focuses solely on reliable input handling.
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


async def main():
    """Main entry point"""
    try:
        # Load environment variables if .env file exists
        if os.path.exists(".env"):
            load_dotenv()
            logger.info("Loaded environment variables from .env file")
        else:
            logger.info("No .env file found, using environment variables")

        print("\n" + "="*50)
        print("Voice Direct Simple Input - Web Assistant")
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
        assistant = VoiceAssistant(config)
        await assistant.initialize()

        # Add the specialized handler
        print("Adding specialized handler for state selection, login, etc...")
        assistant.specialized_handler = SpecializedHandler(
            assistant.page, 
            assistant.speak, 
            assistant.llm_utils, 
            assistant.browser_utils
        )
        
        # Patch the process_command method
        original_process_command = assistant.process_command
        
        async def patched_process_command(command):
            # Try specialized handler first
            if hasattr(assistant, 'specialized_handler'):
                if await assistant.specialized_handler.handle_command(command):
                    return True
                    
            # If specialized handler didn't handle it, use the original method
            return await original_process_command(command)
            
        # Replace the process_command method
        assistant.process_command = patched_process_command
        
        # Welcome message
        print("\n=== READY FOR COMMANDS ===")
        print("Type your commands below. Type 'help' for available commands or 'exit' to quit.")
        await assistant.speak("Voice Assistant is ready. Type 'help' for available commands or 'exit' to quit.")
        
        # Main command loop
        while True:
            try:
                # Use a very direct approach to get input
                sys.stdout.write("\n⌨️ Command: ")
                sys.stdout.flush()
                command = sys.stdin.readline().strip()
                
                # Skip empty commands
                if not command:
                    continue
                    
                # Process the command
                print(f"USER: {command}")
                sys.stdout.flush()
                
                # Exit if the command is 'exit' or 'quit'
                if command.lower() in ['exit', 'quit']:
                    await assistant.speak("Goodbye!")
                    break
                    
                # Process the command
                result = await assistant.process_command(command)
                if not result:  # If process_command returns False, exit
                    break
                    
            except KeyboardInterrupt:
                print("\nKeyboard interrupt detected. Exiting...")
                break
            except Exception as e:
                print(f"Error processing command: {e}")
                import traceback
                traceback.print_exc()
                await assistant.speak(f"Error processing command: {str(e)}")
                
        # Close the assistant
        await assistant.close(keep_browser_open=True)
        
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
