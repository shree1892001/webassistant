"""
Voice Direct File Input - A file-based version of the Voice Direct Web Assistant.

This script provides a file-based interface for the Voice Direct Web Assistant,
which avoids issues with command prompts in the terminal.
"""

import os
import re
import asyncio
import logging
import time
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

# File paths
COMMAND_FILE = "command.txt"
OUTPUT_FILE = "output.txt"
MODE_FILE = "mode.txt"

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
        print("Voice Direct File Input - Web Assistant")
        print("="*50 + "\n")

        # Create the command file if it doesn't exist
        with open(COMMAND_FILE, "w") as f:
            f.write("# Enter your commands here, one per line\n")
            f.write("# The assistant will process the last non-empty, non-comment line\n")
            f.write("# Type 'exit' or 'quit' to exit\n")
            f.write("# Type 'voice' or 'text' to switch modes\n")
        
        # Create the output file if it doesn't exist
        with open(OUTPUT_FILE, "w") as f:
            f.write("# Output will appear here\n")
        
        # Create the mode file if it doesn't exist
        with open(MODE_FILE, "w") as f:
            f.write("text")  # Default to text mode
        
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
            input_mode = "voice"
            with open(MODE_FILE, "w") as f:
                f.write("voice")
            print("🚀 Assistant initialized in voice mode")
        else:
            input_mode = "text"
            with open(MODE_FILE, "w") as f:
                f.write("text")
            print("🚀 Assistant initialized in text mode")
            
        # Set the input mode in the config
        config.input_mode = input_mode

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
        await assistant.speak("Voice Assistant is ready. Enter commands in the command file.")
        
        print(f"\n=== READY FOR COMMANDS ===")
        print(f"Enter commands in the file: {os.path.abspath(COMMAND_FILE)}")
        print(f"Output will appear in the file: {os.path.abspath(OUTPUT_FILE)}")
        print(f"Current mode is stored in: {os.path.abspath(MODE_FILE)}")
        
        # Write to output file
        with open(OUTPUT_FILE, "a") as f:
            f.write("\nASSISTANT: Voice Assistant is ready. Enter commands in the command file.\n")
            f.write("ASSISTANT: Type 'help' for available commands or 'exit' to quit.\n")
        
        # Track the last command processed
        last_command = ""
        
        # Main command loop
        while True:
            try:
                # Read the command file
                with open(COMMAND_FILE, "r") as f:
                    lines = f.readlines()
                
                # Process the last non-empty, non-comment line
                command = ""
                for line in reversed(lines):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        command = line
                        break
                
                # If the command is new, process it
                if command and command != last_command:
                    last_command = command
                    
                    # Write the command to the output file
                    with open(OUTPUT_FILE, "a") as f:
                        f.write(f"\nUSER: {command}\n")
                    
                    # Check for mode switching
                    if command.lower() in ["voice", "voice mode", "switch to voice", "switch to voice mode"]:
                        with open(MODE_FILE, "w") as f:
                            f.write("voice")
                        with open(OUTPUT_FILE, "a") as f:
                            f.write("ASSISTANT: Switched to voice mode.\n")
                        print("Switched to voice mode.")
                        continue
                        
                    if command.lower() in ["text", "text mode", "switch to text", "switch to text mode"]:
                        with open(MODE_FILE, "w") as f:
                            f.write("text")
                        with open(OUTPUT_FILE, "a") as f:
                            f.write("ASSISTANT: Switched to text mode.\n")
                        print("Switched to text mode.")
                        continue
                    
                    # Exit if the command is 'exit' or 'quit'
                    if command.lower() in ['exit', 'quit']:
                        with open(OUTPUT_FILE, "a") as f:
                            f.write("ASSISTANT: Goodbye!\n")
                        print("Exiting...")
                        break
                    
                    # Process the command
                    print(f"Processing command: {command}")
                    result = await assistant.process_command(command)
                    
                    if not result:  # If process_command returns False, exit
                        break
                
                # Sleep to avoid busy waiting
                await asyncio.sleep(0.5)
                
            except KeyboardInterrupt:
                print("\nKeyboard interrupt detected. Exiting...")
                with open(OUTPUT_FILE, "a") as f:
                    f.write("ASSISTANT: Keyboard interrupt detected. Exiting...\n")
                break
            except Exception as e:
                print(f"Error processing command: {e}")
                import traceback
                traceback.print_exc()
                with open(OUTPUT_FILE, "a") as f:
                    f.write(f"ERROR: {str(e)}\n")
                await assistant.speak(f"Error processing command: {str(e)}")
        
        # Close the assistant
        await assistant.close(keep_browser_open=True)
        
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
