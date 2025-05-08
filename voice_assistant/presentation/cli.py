import asyncio
import logging
from voice_assistant.application.services.voice_assistant import VoiceAssistant

logger = logging.getLogger(__name__)

async def main():
    """Main entry point for the CLI application"""
    assistant = None
    try:
        logger.info("Starting Voice Assistant...")
        
        # Initialize components
        from voice_assistant.infrastructure.config import ConfigManager
        from voice_assistant.infrastructure.voice import VoiceEngine
        from voice_assistant.infrastructure.browser import BrowserManager
        from voice_assistant.infrastructure.plugins import PluginManager
        from voice_assistant.domain.repositories.command_processor import GeminiCommandProcessor
        from voice_assistant.application.services.action_executor import ActionExecutor
        
        # Initialize configuration
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        # Initialize components
        voice_engine = VoiceEngine(config['voice'])
        browser_manager = BrowserManager(config['browser'])
        plugin_manager = PluginManager(config['plugins'])
        
        # Initialize browser
        await browser_manager.initialize()
        
        # Initialize command processor
        command_processor = GeminiCommandProcessor(config['gemini_model'])
        
        # Initialize action executor
        action_executor = ActionExecutor(
            browser_manager.page,
            browser_manager,
            config_manager
        )
        
        # Initialize voice assistant
        assistant = VoiceAssistant(
            config_manager=config_manager,
            voice_engine=voice_engine,
            browser_manager=browser_manager,
            plugin_manager=plugin_manager,
            command_processor=command_processor,
            action_executor=action_executor
        )
        
        print("Welcome to the Voice Assistant!")
        print("Choose your input mode:")
        print("1. Voice Mode")
        print("2. Text Mode")
        
        while True:
            try:
                mode_choice = input("Enter your choice (1 or 2): ").strip()
                if mode_choice == "1":
                    assistant.input_mode = "voice"
                    print("Voice mode activated. Speak your commands.")
                    break
                elif mode_choice == "2":
                    assistant.input_mode = "text"
                    print("Text mode activated. Type your commands.")
                    break
                else:
                    print("Invalid choice. Please enter 1 or 2.")
            except KeyboardInterrupt:
                print("\nGoodbye!")
                return
            except Exception as e:
                logger.error(f"Error selecting mode: {e}")
                print("Error selecting mode. Please try again.")
        
        while True:
            try:
                if assistant.input_mode == "voice":
                    print("\nListening... (Press Ctrl+C to stop)")
                    command = await assistant.listen()
                    print(f"You said: {command}")
                else:
                    command = input("\nEnter command: ").strip()
                
                if not command:
                    continue
                
                if command.lower() in ["exit", "quit", "bye"]:
                    print("Goodbye!")
                    break
                
                if command.lower() in ["help", "what can you do"]:
                    assistant._show_help()
                    continue
                
                if command.lower() in ["voice", "voice mode"]:
                    assistant.input_mode = "voice"
                    print("Switched to voice mode")
                    continue
                
                if command.lower() in ["text", "text mode"]:
                    assistant.input_mode = "text"
                    print("Switched to text mode")
                    continue
                
                if not await assistant.process_command(command):
                    print("Command processing failed. Type 'help' for available commands.")
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                logger.error(f"Error processing command: {e}")
                print("An error occurred. Please try again.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        if assistant:
            try:
                await assistant.close()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal error in main: {e}") 