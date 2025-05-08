from typing import Dict, Any, Optional, List
from ..core.plugin import BasePlugin
from ..utils.constants import COMMAND_PATTERNS, ERROR_MESSAGES, SUCCESS_MESSAGES

class StatePlugin(BasePlugin):
    """Plugin for handling state selection and related functionality"""
    
    def __init__(self, page, speech, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.page = page
        self.speech = speech

    def _get_command_patterns(self) -> Dict[str, str]:
        """Get command patterns for state plugin"""
        return {
            'select_state': r'select state (.*)',
            'click_state_dropdown': r'click state dropdown',
            'click_address_state_dropdown': r'click address state dropdown'
        }

    async def handle_command(self, command: str) -> bool:
        """Handle state-related commands"""
        command = command.lower().strip()
        
        # Handle state selection
        if self._matches_pattern(command, self.command_patterns['select_state']):
            state_name = self._extract_pattern(command, self.command_patterns['select_state'])
            return await self._handle_state_selection(state_name)

        # Handle state dropdown click
        if self._matches_pattern(command, self.command_patterns['click_state_dropdown']):
            return await self._click_state_dropdown_direct()

        # Handle address state dropdown click
        if self._matches_pattern(command, self.command_patterns['click_address_state_dropdown']):
            return await self._click_address_state_dropdown()

        return False

    async def _handle_state_selection(self, state_name: str) -> bool:
        """Handle state selection"""
        try:
            # Find and click the state option
            state_option = await self.page.query_selector(f'.p-dropdown-item:text("{state_name}")')
            if not state_option:
                self.speech.speak(ERROR_MESSAGES['state_not_found'])
                return False

            await state_option.click()
            self.speech.speak(SUCCESS_MESSAGES['state_selected'].format(state=state_name))
            return True
        except Exception as e:
            self.speech.speak(f"Error selecting state: {str(e)}")
            return False

    async def _click_state_dropdown_direct(self) -> bool:
        """Click the state dropdown"""
        try:
            state_dropdown = await self.page.query_selector('.p-dropdown-trigger')
            if not state_dropdown:
                self.speech.speak(ERROR_MESSAGES['state_dropdown_not_found'])
                return False

            await state_dropdown.click()
            self.speech.speak(SUCCESS_MESSAGES['state_dropdown_clicked'])
            return True
        except Exception as e:
            self.speech.speak(f"Error clicking state dropdown: {str(e)}")
            return False

    async def _click_address_state_dropdown(self) -> bool:
        """Click the address state dropdown"""
        try:
            address_state_dropdown = await self.page.query_selector('.address-state-dropdown .p-dropdown-trigger')
            if not address_state_dropdown:
                self.speech.speak(ERROR_MESSAGES['address_state_dropdown_not_found'])
                return False

            await address_state_dropdown.click()
            self.speech.speak(SUCCESS_MESSAGES['address_state_dropdown_clicked'])
            return True
        except Exception as e:
            self.speech.speak(f"Error clicking address state dropdown: {str(e)}")
            return False

    def get_help_text(self) -> List[str]:
        """Get help text for state commands"""
        return [
            "select state [name] - Select a state from dropdown",
            "click state dropdown - Open state selection dropdown",
            "click address state dropdown - Open address state dropdown"
        ]

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for state plugin"""
        return {
            'enabled': bool,
            'timeout': int,
            'max_retries': int
        } 