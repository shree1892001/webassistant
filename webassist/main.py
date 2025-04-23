"""
Main entry point for WebAssist
"""

import os
import asyncio
from dotenv import load_dotenv

from webassist.core.config import AssistantConfig
from webassist.core.assistant import Assistant
# Use a default API key if not provided in environment
DEFAULT_API_KEY = "AIzaSyAvNz1x-OZl3kUDEm4-ZhwzJJy1Tqq6Flg"


async def main():
    """Main entry point"""
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
        print("Initialization complete. Starting assistant...")
        await assistant.run()
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
