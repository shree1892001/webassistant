import re
from typing import Optional, Dict, Any, Callable, Awaitable, List
from voice_assistant.core.navigator import WebNavigator
from voice_assistant.core.speech import SpeechEngine
from voice_assistant.handlers.base_handler import BaseHandler
from voice_assistant.handlers.dropdown_handler import DropdownHandler
from voice_assistant.utils.constants import COMMAND_PATTERNS

class CommandProcessor:
    """Processes and executes commands"""
    
    def __init__(self, page, speech, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.page = page
        self.speech = speech
        self.handlers = self._initialize_handlers()

    def _initialize_handlers(self) -> Dict[str, BaseHandler]:
        """Initialize command handlers"""
        return {
            'dropdown': DropdownHandler(self.page, self.speech, self.config)
            # Add more handlers here as needed
        }

    async def process_command(self, command: str) -> bool:
        """Process and execute a command"""
        command = command.lower().strip()
        
        # Check for mode switching commands
        if command in ["voice", "voice mode", "switch to voice", "switch to voice mode"]:
            self.speech.speak("Switching to voice mode")
            return True

        if command in ["text", "text mode", "switch to text", "switch to text mode"]:
            self.speech.speak("Switching to text mode")
            return True

        # Process dropdown filter commands
        if self._matches_pattern(command, COMMAND_PATTERNS['filter_dropdown']):
            search_text = self._extract_pattern(command, COMMAND_PATTERNS['filter_dropdown'])
            return await self.handlers['dropdown'].handle_filter(search_text)

        # Process clear filter commands
        if self._matches_pattern(command, COMMAND_PATTERNS['clear_filter']):
            return await self.handlers['dropdown'].clear_filter()

        # Add more command processing here

        return False

    def _matches_pattern(self, command: str, pattern: str) -> bool:
        """Check if command matches a pattern"""
        return bool(re.search(pattern, command, re.IGNORECASE))

    def _extract_pattern(self, command: str, pattern: str) -> str:
        """Extract value from command using pattern"""
        match = re.search(pattern, command, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def get_available_commands(self) -> List[str]:
        """Get list of available commands"""
        return [
            "voice/voice mode - Switch to voice input",
            "text/text mode - Switch to text input",
            "filter dropdown [text] - Filter dropdown with text",
            "clear filter - Clear dropdown filter",
            # Add more commands here
        ]

    async def process(self, command: str) -> bool:
        """Process a command and return whether to continue"""
        command = command.lower().strip()
        
        # Check for direct matches first
        if command in ['exit', 'quit']:
            return await self._handle_exit()
        if command == 'help':
            return await self._handle_help()

        # Try to match command patterns
        for handler_name, handler in self.handlers.items():
            if await handler.handle_command(command):
                return True

        # If no direct handler matches, use LLM
        return await self._handle_complex_command(command)

    async def _handle_exit(self) -> bool:
        """Handle exit command"""
        self.speech.speak("Goodbye! Browser will remain open for inspection.")
        return False

    async def _handle_help(self) -> bool:
        """Handle help command"""
        help_text = """
        Available commands:
        - 'go to [url]' or 'navigate to [url]' - Navigate to a website
        - 'login with email [email] and password [password]' - Login to the current site
        - 'select state [state name]' - Select a state from dropdown
        - 'help' - Show this help message
        - 'exit' or 'quit' - Exit the assistant
        """
        self.speech.speak(help_text)
        return True

    async def _handle_complex_command(self, command: str) -> bool:
        """Handle complex commands using LLM"""
        # TODO: Implement LLM-based command handling
        self.speech.speak("I'm not sure how to handle that command yet.")
        return True 