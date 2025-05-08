from typing import Dict, Any, Optional, List
from ..core.plugin import BasePlugin
from ..utils.constants import COMMAND_PATTERNS, ERROR_MESSAGES, SUCCESS_MESSAGES

class DropdownPlugin(BasePlugin):
    """Plugin for handling dropdown interactions"""
    
    def __init__(self, page, speech, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.page = page
        self.speech = speech

    def _get_command_patterns(self) -> Dict[str, str]:
        """Get command patterns for dropdown plugin"""
        return {
            'filter_dropdown': COMMAND_PATTERNS['filter_dropdown'],
            'clear_filter': COMMAND_PATTERNS['clear_filter'],
            'select_option': COMMAND_PATTERNS['select_option']
        }

    async def handle_command(self, command: str) -> bool:
        """Handle dropdown-related commands"""
        command = command.lower().strip()
        
        # Handle filter dropdown command
        if self._matches_pattern(command, self.command_patterns['filter_dropdown']):
            search_text = self._extract_pattern(command, self.command_patterns['filter_dropdown'])
            return await self._handle_filter_dropdown(search_text)

        # Handle clear filter command
        if self._matches_pattern(command, self.command_patterns['clear_filter']):
            return await self._handle_clear_filter()

        # Handle select option command
        if self._matches_pattern(command, self.command_patterns['select_option']):
            option_text = self._extract_pattern(command, self.command_patterns['select_option'])
            return await self._handle_select_option(option_text)

        return False

    async def _handle_filter_dropdown(self, search_text: str) -> bool:
        """Handle filtering a dropdown"""
        try:
            # Find and focus the dropdown filter input
            filter_input = await self.page.query_selector('input.p-dropdown-filter')
            if not filter_input:
                self.speech.speak(ERROR_MESSAGES['filter_not_found'])
                return False

            # Type the search text
            await filter_input.type(search_text)
            self.speech.speak(SUCCESS_MESSAGES['filter_text_entered'].format(text=search_text))
            return True
        except Exception as e:
            self.speech.speak(f"Error filtering dropdown: {str(e)}")
            return False

    async def _handle_clear_filter(self) -> bool:
        """Handle clearing a dropdown filter"""
        try:
            # Find and focus the dropdown filter input
            filter_input = await self.page.query_selector('input.p-dropdown-filter')
            if not filter_input:
                self.speech.speak(ERROR_MESSAGES['filter_not_found'])
                return False

            # Clear the input
            await filter_input.fill('')
            self.speech.speak(SUCCESS_MESSAGES['filter_cleared'])
            return True
        except Exception as e:
            self.speech.speak(f"Error clearing filter: {str(e)}")
            return False

    async def _handle_select_option(self, option_text: str) -> bool:
        """Handle selecting an option from dropdown"""
        try:
            # Find and click the option
            option = await self.page.query_selector(f'.p-dropdown-item:text("{option_text}")')
            if not option:
                self.speech.speak(ERROR_MESSAGES['option_not_found'])
                return False

            await option.click()
            self.speech.speak(SUCCESS_MESSAGES['option_selected'].format(option=option_text))
            return True
        except Exception as e:
            self.speech.speak(f"Error selecting option: {str(e)}")
            return False

    def get_help_text(self) -> List[str]:
        """Get help text for dropdown commands"""
        return [
            "filter dropdown [text] - Filter dropdown with text",
            "clear filter - Clear dropdown filter",
            "select option [text] - Select an option from dropdown"
        ]

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for dropdown plugin"""
        return {
            'enabled': bool,
            'timeout': int,
            'max_retries': int
        } 