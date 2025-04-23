"""
Simple main entry point for WebAssist
"""

import os
import asyncio
from dotenv import load_dotenv

from webassist.core.config import AssistantConfig
from webassist.core.assistant import Assistant

# Use a default API key if not provided in environment
DEFAULT_API_KEY = "AIzaSyAvNz1x-OZl3kUDEm4-ZhwzJJy1Tqq6Flg"


async def process_command(assistant, command):
    """Process a command"""
    print(f"Processing command: '{command}'")
    try:
        result = await assistant.process_command(command)
        print(f"Command processed: {'success' if result else 'failed'}")
        return result
    except Exception as e:
        import traceback
        print(f"Error processing command: {e}")
        traceback.print_exc()
        return False


async def main():
    """Main entry point with simplified input handling"""
    # Load environment variables
    load_dotenv()

    # Get API key from environment variables or default
    gemini_api_key = os.environ.get("GEMINI_API_KEY", DEFAULT_API_KEY)

    if not gemini_api_key:
        print("❌ Error: GEMINI_API_KEY environment variable not set.")
        print("Please create a .env file with your API key or set it in your environment.")
        exit(1)

    # Create configuration
    config = AssistantConfig()
    config.gemini_api_key = gemini_api_key

    assistant = None
    try:
        print("Starting WebAssist...")
        # Create and initialize assistant
        assistant = Assistant(config)
        print("Initializing browser and components...")
        await assistant.initialize()
        print("Initialization complete.")
        
        # Start with Google
        print("Opening browser to Google...")
        await assistant.navigator.browse_website("https://www.google.com")
        print("Browser opened. Ready for commands.")
        
        # Print welcome message
        print("\nWelcome to WebAssist!")
        print("Type 'help' for available commands or 'exit' to quit.")
        
        # Main command loop with direct input handling
        while True:
            try:
                # Get user input directly
                command = input("\n⌨️ Command: ").strip()
                
                # Handle empty command
                if not command:
                    print("Empty command. Please try again.")
                    continue
                
                # Handle exit command
                if command.lower() in ["exit", "quit"]:
                    print("Exiting assistant...")
                    break
                
                # Process the command
                await process_command(assistant, command)
                
            except KeyboardInterrupt:
                print("\nKeyboard interrupt detected. Exiting...")
                break
            except Exception as e:
                import traceback
                print(f"Error in command loop: {e}")
                traceback.print_exc()
    
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        import traceback
        print(f"❌ Error: {e}")
        traceback.print_exc()
    finally:
        try:
            if assistant:
                print("Closing assistant...")
                await assistant.close()
                print("Assistant closed.")
        except Exception as e:
            print(f"Error closing assistant: {e}")


if __name__ == "__main__":
    asyncio.run(main())
