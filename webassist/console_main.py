"""
Console main entry point for WebAssist with simplified input handling
"""

import os
import asyncio
import threading
import queue
from dotenv import load_dotenv

from webassist.core.config import AssistantConfig
from webassist.core.assistant import Assistant
from webassist.core.constants import DEFAULT_START_URL, EXIT_COMMANDS

# Use a default API key if not provided in environment
DEFAULT_API_KEY = "AIzaSyAvNz1x-OZl3kUDEm4-ZhwzJJy1Tqq6Flg"

# Global variables
command_queue = queue.Queue()
assistant = None
running = True


def input_thread_function():
    """Function to run in the input thread"""
    global running
    
    print("\nWelcome to WebAssist!")
    print("Type 'help' for available commands or 'exit' to quit.")
    
    while running:
        try:
            # Get user input directly
            command = input("\nCommand: ").strip()
            
            # Put the command in the queue
            command_queue.put(command)
            
            # Check for exit command
            if command.lower() in EXIT_COMMANDS:
                running = False
                break
                
        except (KeyboardInterrupt, EOFError):
            print("\nInput interrupted. Exiting...")
            running = False
            command_queue.put("exit")
            break
        except Exception as e:
            print(f"Input error: {e}")


async def process_commands():
    """Process commands from the queue"""
    global running
    
    while running:
        try:
            # Check if there's a command in the queue
            if not command_queue.empty():
                command = command_queue.get()
                
                # Handle empty command
                if not command:
                    print("Empty command. Please try again.")
                    continue
                
                # Handle exit command
                if command.lower() in EXIT_COMMANDS:
                    print("Exiting assistant...")
                    running = False
                    break
                
                # Process the command
                print(f"Processing command: '{command}'")
                try:
                    result = await assistant.process_command(command)
                    print(f"Command processed: {'success' if result else 'failed'}")
                except Exception as e:
                    import traceback
                    print(f"Error processing command: {e}")
                    traceback.print_exc()
            
            # Sleep a bit to avoid busy waiting
            await asyncio.sleep(0.1)
            
        except Exception as e:
            import traceback
            print(f"Error in command processing: {e}")
            traceback.print_exc()
            await asyncio.sleep(1)


async def main():
    """Main entry point with separate input thread"""
    global assistant, running
    
    # Load environment variables
    load_dotenv()

    # Get API key from environment variables or default
    gemini_api_key = os.environ.get("GEMINI_API_KEY", DEFAULT_API_KEY)

    if not gemini_api_key:
        print("❌ Error: GEMINI_API_KEY environment variable not set.")
        print("Please create a .env file with your API key or set it in your environment.")
        exit(1)

    try:
        print("Starting WebAssist...")
        # Create and initialize assistant
        config = AssistantConfig()
        config.gemini_api_key = gemini_api_key
        assistant = Assistant(config)
        
        print("Initializing browser and components...")
        await assistant.initialize()
        print("Initialization complete.")
        
        # Start with Google
        print("Opening browser to Google...")
        await assistant.navigator.browse_website(DEFAULT_START_URL)
        print("Browser opened. Ready for commands.")
        
        # Start the input thread
        input_thread = threading.Thread(target=input_thread_function)
        input_thread.daemon = True
        input_thread.start()
        
        # Process commands
        await process_commands()
        
        # Wait for the input thread to finish
        input_thread.join(timeout=1)
    
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
        running = False
    except Exception as e:
        import traceback
        print(f"❌ Error: {e}")
        traceback.print_exc()
    finally:
        running = False
        try:
            if assistant:
                print("Closing assistant...")
                await assistant.close()
                print("Assistant closed.")
        except Exception as e:
            print(f"Error closing assistant: {e}")


if __name__ == "__main__":
    asyncio.run(main())
