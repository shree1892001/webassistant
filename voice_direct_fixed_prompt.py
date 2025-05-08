"""
Voice Direct Fixed Prompt - A version of the Voice Direct Modular Web Assistant with fixed prompt handling.

This script provides a direct implementation of the Voice Direct Web Assistant with
special handling for command prompts to ensure they're always visible.
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
result_queue = Queue()

def input_thread_func():
    """Thread function for handling user input"""
    while True:
        try:
            # Display the prompt in a way that's guaranteed to be visible
            sys.stdout.write("\n⌨️ Command: ")
            sys.stdout.flush()
            
            # Get input directly
            command = input().strip()
            
            # Put the command in the queue
            command_queue.put(command)
            
            # Exit if the command is 'exit' or 'quit'
            if command.lower() in ['exit', 'quit']:
                break
                
            # Wait for a result
            result = result_queue.get()
            if result == "EXIT":
                break
        except KeyboardInterrupt:
            print("\nKeyboard interrupt detected. Exiting...")
            command_queue.put("exit")
            break
        except Exception as e:
            print(f"Error in input thread: {e}")
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
                result_queue.put("EXIT")
                return False
                
            # Process the command
            try:
                print(f"USER: {command}")
                result = await assistant.process_command(command)
                result_queue.put(result)
                
                if not result:  # If process_command returns False, exit
                    return False
            except Exception as e:
                print(f"Error processing command: {e}")
                import traceback
                traceback.print_exc()
                result_queue.put(False)
        
        # Sleep to avoid busy waiting
        await asyncio.sleep(0.1)
        
    return True

async def main():
    """Main entry point"""
    try:
        print("\n==================================================")
        print("Voice Direct Fixed Prompt - Web Assistant")
        print("==================================================\n")
        
        # Create and initialize the assistant
        assistant = VoiceAssistant()
        
        # Initialize the assistant
        print("Initializing Voice Assistant...")
        await assistant.initialize()
        
        # Start the input thread
        input_thread = Thread(target=input_thread_func)
        input_thread.daemon = True
        input_thread.start()
        
        # Welcome message
        await assistant.speak("Voice Assistant is ready. Say or type 'help' for available commands or 'exit' to quit.")
        
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
