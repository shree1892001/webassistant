"""
Voice Direct File - A file-based version of the Voice Direct Web Assistant.

This script provides a file-based interface for the Voice Direct Web Assistant,
which avoids issues with command prompts in the terminal.
"""

import asyncio
import os
import sys
import logging
import time
from threading import Thread
from queue import Queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import the assistant
from webassist.voice_assistant.core.assistant import VoiceAssistant

# Create queues for communication between threads
command_queue = Queue()
output_queue = Queue()

# File paths
COMMAND_FILE = "command.txt"
OUTPUT_FILE = "output.txt"

def input_thread_func():
    """Thread function for handling file-based input"""
    # Create the command file if it doesn't exist
    if not os.path.exists(COMMAND_FILE):
        with open(COMMAND_FILE, "w") as f:
            f.write("# Enter your commands here, one per line\n")
    
    # Create the output file if it doesn't exist
    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "w") as f:
            f.write("# Output will appear here\n")
    
    # Track the last command processed
    last_command = ""
    
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
                
                # Put the command in the queue
                command_queue.put(command)
                
                # Exit if the command is 'exit' or 'quit'
                if command.lower() in ['exit', 'quit']:
                    break
            
            # Sleep to avoid busy waiting
            time.sleep(0.5)
            
        except KeyboardInterrupt:
            print("\nKeyboard interrupt detected. Exiting...")
            command_queue.put("exit")
            break
        except Exception as e:
            print(f"Error in input thread: {e}")
            import traceback
            traceback.print_exc()

def output_thread_func():
    """Thread function for handling file-based output"""
    while True:
        try:
            # Check if there's output in the queue
            if not output_queue.empty():
                output = output_queue.get()
                
                # Append the output to the output file
                with open(OUTPUT_FILE, "a") as f:
                    f.write(f"{output}\n")
                
                # Also print to console
                print(output)
            
            # Sleep to avoid busy waiting
            time.sleep(0.1)
            
        except KeyboardInterrupt:
            print("\nKeyboard interrupt detected. Exiting...")
            break
        except Exception as e:
            print(f"Error in output thread: {e}")
            import traceback
            traceback.print_exc()

async def process_commands(assistant):
    """Process commands from the queue"""
    while True:
        # Check if there's a command in the queue
        if not command_queue.empty():
            command = command_queue.get()
            
            # Exit if the command is 'exit' or 'quit'
            if command.lower() in ['exit', 'quit']:
                output_queue.put("ASSISTANT: Goodbye!")
                return False
                
            # Process the command
            try:
                output_queue.put(f"USER: {command}")
                result = await assistant.process_command(command)
                if not result:  # If process_command returns False, exit
                    return False
            except Exception as e:
                print(f"Error processing command: {e}")
                import traceback
                traceback.print_exc()
                output_queue.put(f"ERROR: {e}")
        
        # Sleep to avoid busy waiting
        await asyncio.sleep(0.1)
        
    return True

async def main():
    """Main entry point"""
    try:
        print("\n==================================================")
        print("Voice Direct File - Web Assistant")
        print("==================================================\n")
        print(f"Enter commands in the file: {os.path.abspath(COMMAND_FILE)}")
        print(f"Output will appear in the file: {os.path.abspath(OUTPUT_FILE)}")
        
        # Start the input thread
        input_thread = Thread(target=input_thread_func)
        input_thread.daemon = True
        input_thread.start()
        
        # Start the output thread
        output_thread = Thread(target=output_thread_func)
        output_thread.daemon = True
        output_thread.start()
        
        # Create and initialize the assistant
        assistant = VoiceAssistant()
        
        # Initialize the assistant
        output_queue.put("Initializing Voice Assistant...")
        await assistant.initialize()
        
        # Welcome message
        output_queue.put("ASSISTANT: Voice Assistant is ready. Enter commands in the command file.")
        output_queue.put("ASSISTANT: Type 'help' for available commands or 'exit' to quit.")
        
        # Process commands until exit
        continue_running = True
        while continue_running:
            continue_running = await process_commands(assistant)
            
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
