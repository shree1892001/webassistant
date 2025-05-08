"""
Main entry point for the Voice Assistant.
"""

import os
import asyncio
import logging
from dotenv import load_dotenv

from webassist.core.config import AssistantConfig
from webassist.voice_assistant.core.assistant import VoiceAssistant

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    """Main entry point"""
    try:
        # Load environment variables if .env file exists
        if os.path.exists(".env"):
            load_dotenv()
            logger.info("Loaded environment variables from .env file")
        else:
            logger.info("No .env file found, using environment variables")

        logger.info("Initializing Voice Assistant...")
        logger.info("Loading configuration...")
        config = AssistantConfig.from_env()

        # Check if API key is available
        if not config.gemini_api_key:
            logger.warning("No Gemini API key found in environment variables or .env file.")
            logger.warning("Using default API key from constants.py")
            from webassist.Common.constants import DEFAULT_API_KEY
            config.gemini_api_key = DEFAULT_API_KEY

        logger.info(f"Configuration loaded successfully. Using API key: {config.gemini_api_key[:5]}...")

        # Create and initialize the assistant
        logger.info("Creating VoiceAssistant instance...")
        assistant = VoiceAssistant(config)
        logger.info("VoiceAssistant instance created successfully")

        logger.info("Initializing VoiceAssistant components...")
        await assistant.initialize()
        logger.info("VoiceAssistant initialization completed successfully")

        # Run the assistant's main loop
        logger.info("Starting VoiceAssistant main loop...")
        await assistant.run()

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt detected. Exiting...")
    except Exception as e:
        import traceback
        logger.error(f"Error: {e}")
        traceback.print_exc()
    finally:
        logger.info("Program ended. Browser will remain open.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        import traceback
        logger.error(f"Fatal error: {e}")
        traceback.print_exc()
