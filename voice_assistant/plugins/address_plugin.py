from typing import Dict, Any, Optional, List
from ..core.plugin import BasePlugin
from ..utils.constants import COMMAND_PATTERNS, ERROR_MESSAGES, SUCCESS_MESSAGES

class AddressPlugin(BasePlugin):
    """Plugin for handling address field functionality"""
    
    def __init__(self, page, speech, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.page = page
        self.speech = speech

    def _get_command_patterns(self) -> Dict[str, str]:
        """Get command patterns for address plugin"""
        return {
            'enter_address': r'enter (.*) (?:in|into) (.*) field',
            'click_address_dropdown': r'click (.*) dropdown'
        }

    async def handle_command(self, command: str) -> bool:
        """Handle address-related commands"""
        command = command.lower().strip()
        
        # Handle address field entry
        if self._matches_pattern(command, self.command_patterns['enter_address']):
            match = self._extract_pattern(command, self.command_patterns['enter_address'])
            text, field_type = match.split(' ', 1)
            return await self._enter_address_field(text, field_type)

        # Handle address dropdown click
        if self._matches_pattern(command, self.command_patterns['click_address_dropdown']):
            dropdown_name = self._extract_pattern(command, self.command_patterns['click_address_dropdown'])
            return await self._click_generic_dropdown(dropdown_name)

        return False

    async def _enter_address_field(self, text: str, field_type: str) -> bool:
        """Enter text into an address field"""
        try:
            # Find the input field
            field = await self.page.query_selector(f'input[placeholder*="{field_type}"]')
            if not field:
                self.speech.speak(ERROR_MESSAGES['field_not_found'])
                return False

            # Clear and type the text
            await field.fill('')
            await field.type(text)
            self.speech.speak(SUCCESS_MESSAGES['text_entered'].format(text=text, field=field_type))
            return True
        except Exception as e:
            self.speech.speak(f"Error entering text: {str(e)}")
            return False

    async def _click_generic_dropdown(self, dropdown_name: str) -> bool:
        """Click a generic dropdown"""
        try:
            # Find the dropdown trigger
            dropdown = await self.page.query_selector(f'.{dropdown_name}-dropdown .p-dropdown-trigger')
            if not dropdown:
                self.speech.speak(ERROR_MESSAGES['dropdown_not_found'])
                return False

            await dropdown.click()
            self.speech.speak(SUCCESS_MESSAGES['dropdown_clicked'].format(name=dropdown_name))
            return True
        except Exception as e:
            self.speech.speak(f"Error clicking dropdown: {str(e)}")
            return False

    def get_help_text(self) -> List[str]:
        """Get help text for address commands"""
        return [
            "enter [text] in [field] field - Enter text into an address field",
            "click [name] dropdown - Click an address-related dropdown"
        ]

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for address plugin"""
        return {
            'enabled': bool,
            'timeout': int,
            'max_retries': int
        } 