

import asyncio
import threading
import time
import sys
import os
import logging
from queue import Queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import the assistant
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from webassist.voice_assistant.core.assistant import VoiceAssistant

# Create queues for communication between threads
command_queue = Queue()
response_queue = Queue()

def input_thread():
    """Thread for handling user input"""
    print("\n=== Voice Direct CLI ===")
    print("Type your commands below. Type 'help' for available commands or 'exit' to quit.")
    
    while True:
        try:
            # Display prompt and get input
            command = input("\n⌨️ Command: ").strip()
            
            # Put the command in the queue
            command_queue.put(command)
            
            # Exit if the command is 'exit' or 'quit'
            if command.lower() in ['exit', 'quit']:
                break
                
            # Wait for a response
            print("Waiting for response...")
            response = response_queue.get()
            print(f"Response: {response}")
            
        except KeyboardInterrupt:
            print("\nKeyboard interrupt detected. Exiting...")
            command_queue.put("exit")
            break
        except Exception as e:
            print(f"Error in input thread: {e}")

async def process_commands(assistant):
    """Process commands from the queue"""
    while True:
        # Check if there's a command in the queue
        if not command_queue.empty():
            command = command_queue.get()
            
            # Exit if the command is 'exit' or 'quit'
            if command.lower() in ['exit', 'quit']:
                response_queue.put("Goodbye!")
                break
                
            # Process the command
            try:
                print(f"Processing command: {command}")
                result = await assistant.process_command(command)
                response_queue.put(f"Command processed: {result}")
            except Exception as e:
                print(f"Error processing command: {e}")
                response_queue.put(f"Error: {e}")
        
        # Sleep to avoid busy waiting
        await asyncio.sleep(0.1)

async def assistant_thread():
    """Thread for running the assistant"""
    try:
        # Create and initialize the assistant
        assistant = VoiceAssistant()
        await assistant.initialize()
        
        # Start processing commands
        await process_commands(assistant)
        
        # Close the assistant
        await assistant.close(keep_browser_open=True)
        
    except Exception as e:
        print(f"Error in assistant thread: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main entry point"""
    try:
        # Start the input thread
        input_thread_handle = threading.Thread(target=input_thread)
        input_thread_handle.daemon = True
        input_thread_handle.start()
        
        # Run the assistant thread
        asyncio.run(assistant_thread())
        
        # Wait for the input thread to finish
        input_thread_handle.join()
        
    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
