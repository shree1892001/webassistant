"""
Test Speech - A simple script to test speech synthesizer initialization.
"""

import os
import asyncio
import logging

from webassist.core.config import AssistantConfig
from webassist.Common.constants import DEFAULT_SPEECH_RATE, DEFAULT_SPEECH_VOLUME
from webassist.voice_assistant.speech.synthesizer import create_synthesizer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def main():
    """Main entry point"""
    try:
        print("Testing speech synthesizer initialization...")
        
        # Create a proper AssistantConfig object for the speech components
        speech_config = AssistantConfig()
        speech_config.speech_rate = int(os.environ.get("TTS_RATE", DEFAULT_SPEECH_RATE))
        speech_config.speech_volume = float(os.environ.get("TTS_VOLUME", DEFAULT_SPEECH_VOLUME))
        speech_config.speech_voice_id = int(os.environ.get("TTS_VOICE_ID", "1"))
        
        # Initialize the synthesizer
        synthesizer = create_synthesizer(config=speech_config)
        print("Speech synthesizer initialized successfully")
        
        # Test speaking
        print("Testing speech...")
        await synthesizer.speak("This is a test of the speech synthesizer.")
        print("Speech test completed")
        
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        import traceback
        logger.error(f"Fatal error: {e}")
        traceback.print_exc()
