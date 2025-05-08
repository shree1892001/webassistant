from typing import Optional, Dict, Any
import logging
from voice_assistant.domain.entities.command import Command
from voice_assistant.domain.repositories.command_processor import CommandProcessor
from voice_assistant.application.services.action_executor import ActionExecutor

logger = logging.getLogger(__name__)

class VoiceAssistant:
    """Main voice assistant service that coordinates all components"""
    
    def __init__(
        self,
        config_manager,
        voice_engine,
        browser_manager,
        plugin_manager,
        command_processor: CommandProcessor,
        action_executor: ActionExecutor
    ):
        self.config_manager = config_manager
        self.voice_engine = voice_engine
        self.browser_manager = browser_manager
        self.plugin_manager = plugin_manager
        self.command_processor = command_processor
        self.action_executor = action_executor
        self.input_mode = self.config_manager.get('input_mode', 'text')
    
    async def process_command(self, command: str) -> bool:
        """Process a command using LLM-based detection"""
        try:
            # Use Gemini to detect command type and parameters
            command_analysis = await self.command_processor.detect_command(command)
            
            if command_analysis.confidence < 0.5:
                self.speak("I'm not sure what you want me to do. Please try again or say 'help' for available commands.")
                return False
            
            # Get action suggestion from Gemini
            action_suggestion = await self.command_processor.suggest_action(command_analysis)
            
            if action_suggestion["confidence"] < 0.5:
                self.speak("I'm not sure how to execute that command. Please try again or say 'help' for available commands.")
                return False
            
            action_type = action_suggestion["action"].lower()
            selector = action_suggestion["selector"]
            action_params = action_suggestion["parameters"]
            
            # Execute the suggested action
            success = False
            if action_type == "goto":
                url = action_params.get("url", "")
                if not url:
                    self.speak("Please specify a website to navigate to")
                    return False
                success = await self.action_executor.execute_goto(url)
                if success:
                    self.speak(f"Navigating to {url}")
                else:
                    self.speak("Sorry, I couldn't navigate to that website")
                    
            elif action_type == "click":
                success = await self.action_executor.execute_click(selector, command_analysis.target)
                if success:
                    self.speak(f"Clicked the {command_analysis.target} button")
                else:
                    self.speak(f"Could not find the {command_analysis.target} button")
                    
            elif action_type == "fill":
                text = action_params.get("text", "")
                if not text:
                    self.speak("Please specify what text to enter")
                    return False
                success = await self.action_executor.execute_fill(selector, text)
                if success:
                    self.speak(f"Entered {text}")
                else:
                    self.speak("Could not find the input field")
                    
            elif action_type == "switch_mode":
                mode = action_params.get("mode", "")
                success = await self.action_executor.execute_switch_mode(mode)
                if success:
                    self.speak(f"Switched to {mode} mode")
                else:
                    self.speak("Invalid mode specified")
                    
            else:
                self.speak("I don't know how to execute that action")
                return False
                
            return success
                
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            self.speak("Sorry, I couldn't process that command")
            return False
    
    def speak(self, text: str) -> None:
        """Speak text using voice engine"""
        self.voice_engine.speak(text)
    
    async def listen(self) -> str:
        """Listen for input based on current mode"""
        if self.input_mode == "voice":
            return await self.voice_engine.listen()
        else:
            return self._listen_text()
    
    def _listen_text(self) -> str:
        """Listen for text input"""
        try:
            text = input("\n⌨️ Command: ").strip()
            if text.lower() in ["voice", "voice mode"]:
                self.input_mode = 'voice'
                self.config_manager.set('input_mode', 'voice')
                print("Voice mode activated")
            return text
        except Exception as e:
            print(f"Input error: {e}")
            return ""
    
    def _show_help(self) -> None:
        """Show available commands"""
        help_text = [
            "I can help you with:",
            "1. Navigation:",
            "   - 'go to [website]' or 'open [website]'",
            "   - 'visit [website]' or 'navigate to [website]'",
            "2. Text Input:",
            "   - 'enter [text]' or 'type [text]'",
            "   - 'input [text]' or 'fill [text]'",
            "   - 'enter email [email]' or 'type username [username]'",
            "3. Button Actions:",
            "   - 'click [button]' or 'press [button]'",
            "   - 'select [button]' or 'tap [button]'",
            "4. Mode Switching:",
            "   - 'switch to voice' or 'voice mode'",
            "   - 'switch to text' or 'text mode'",
            "5. Other Commands:",
            "   - 'help' or 'what can you do'",
            "   - 'exit' or 'quit'"
        ]
        
        if self.input_mode == "voice":
            for line in help_text:
                self.speak(line)
        else:
            print("\n".join(help_text))
    
    async def close(self, keep_browser_open: bool = False) -> None:
        """Close all components"""
        self.voice_engine.close()
        await self.browser_manager.close(keep_browser_open) 