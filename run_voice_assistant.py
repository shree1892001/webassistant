import asyncio
from webassist.voice.voice_assistant import VoiceAssistant

async def main():
    # Create and initialize the voice assistant
    assistant = VoiceAssistant()

    await assistant.initialize()
    
    try:
        while True:

            command = input("Enter command (or 'exit' to quit): ")

            if not await assistant.process_command(command):
                break
                
    finally:
        await assistant.close(keep_browser_open=True)

if __name__ == "__main__":
    asyncio.run(main()) 