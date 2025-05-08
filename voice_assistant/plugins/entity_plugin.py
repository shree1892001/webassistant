from typing import Dict, Any, Optional, List
from ..core.plugin import BasePlugin
from ..utils.constants import COMMAND_PATTERNS, ERROR_MESSAGES, SUCCESS_MESSAGES

class EntityPlugin(BasePlugin):
    """Plugin for handling entity type selection and related functionality"""
    
    def __init__(self, page, speech, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.page = page
        self.speech = speech

    def _get_command_patterns(self) -> Dict[str, str]:
        """Get command patterns for entity plugin"""
        return {
            'select_entity': r'select entity type (.*)',
            'ensure_entity_selected': r'ensure entity type selected'
        }

    async def handle_command(self, command: str) -> bool:
        """Handle entity-related commands"""
        command = command.lower().strip()
        
        # Handle entity type selection
        if self._matches_pattern(command, self.command_patterns['select_entity']):
            entity_type = self._extract_pattern(command, self.command_patterns['select_entity'])
            return await self._select_entity_type(entity_type)

        # Handle ensure entity type selected
        if self._matches_pattern(command, self.command_patterns['ensure_entity_selected']):
            return await self._ensure_entity_type_selected()

        return False

    async def _select_entity_type(self, entity_type: str) -> bool:
        """Select an entity type"""
        try:
            # Find and click the entity type option
            entity_option = await self.page.query_selector(f'.p-dropdown-item:text("{entity_type}")')
            if not entity_option:
                self.speech.speak(ERROR_MESSAGES['entity_type_not_found'])
                return False

            await entity_option.click()
            self.speech.speak(SUCCESS_MESSAGES['entity_type_selected'].format(type=entity_type))
            return True
        except Exception as e:
            self.speech.speak(f"Error selecting entity type: {str(e)}")
            return False

    async def _ensure_entity_type_selected(self) -> bool:
        """Ensure an entity type is selected"""
        try:
            # Check if entity type is already selected
            selected_entity = await self.page.query_selector('.p-dropdown-label')
            if selected_entity:
                current_text = await selected_entity.text_content()
                if current_text.strip():
                    return True

            # If not selected, try to select default
            default_entity = await self.page.query_selector('.p-dropdown-item')
            if not default_entity:
                self.speech.speak(ERROR_MESSAGES['no_entity_types_found'])
                return False

            await default_entity.click()
            self.speech.speak(SUCCESS_MESSAGES['entity_type_selected'].format(type="default"))
            return True
        except Exception as e:
            self.speech.speak(f"Error ensuring entity type selected: {str(e)}")
            return False

    def get_help_text(self) -> List[str]:
        """Get help text for entity commands"""
        return [
            "select entity type [name] - Select an entity type",
            "ensure entity type selected - Ensure an entity type is selected"
        ]

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for entity plugin"""
        return {
            'enabled': bool,
            'timeout': int,
            'max_retries': int,
            'default_entity_type': str
        } 