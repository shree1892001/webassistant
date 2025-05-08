from typing import Dict, Any, List, Optional
from playwright.async_api import Page
from  voice_assistant.core.speech import SpeechEngine
from voice_assistant.utils.constants  import (
    DROPDOWN_FILTER_SELECTORS,
    ERROR_MESSAGES,
    SUCCESS_MESSAGES
)
from .base_handler import BaseHandler

class DropdownHandler(BaseHandler):
    """Handles all dropdown-related interactions"""
    
    def __init__(self, page: Page, speech: SpeechEngine, config: Optional[Dict[str, Any]] = None):
        super().__init__(page, speech)
        self.config = config or {}
        self._initialize_config()

    def _initialize_config(self):
        """Initialize configuration with defaults"""
        self.config.setdefault('filter_timeout', 5000)
        self.config.setdefault('max_retries', 3)
        self.config.setdefault('filter_selectors', DROPDOWN_FILTER_SELECTORS)
        self.config.setdefault('verify_text', True)
        self.config.setdefault('verify_clear', True)

    async def handle_filter(self, search_text: str, custom_selectors: Optional[List[str]] = None) -> bool:
        """Handle typing into a dropdown filter input
        
        Args:
            search_text: Text to enter into the filter
            custom_selectors: Optional custom selectors to use instead of defaults
        """
        try:
            # First, find the dropdown filter input
            filter_state = await self._get_filter_state(custom_selectors)
            if not await self._validate_filter_state(filter_state):
                return False

            # Generate and execute actions
            actions = self._generate_filter_actions(search_text, custom_selectors)
            if not await self._execute_actions(actions):
                return False

            # Verify the text was entered if configured to do so
            if self.config['verify_text'] and not await self._verify_filter_text(search_text, custom_selectors):
                return False

            self.speech.speak(self._format_success('filter_text_entered', text=search_text))
            return True

        except Exception as e:
            self.speech.speak(f"Failed to handle dropdown filter: {str(e)}")
            return False

    async def clear_filter(self, custom_selectors: Optional[List[str]] = None) -> bool:
        """Clear the dropdown filter input
        
        Args:
            custom_selectors: Optional custom selectors to use instead of defaults
        """
        try:
            # First, check if the filter exists and is visible
            filter_state = await self._get_filter_state(custom_selectors)
            if not await self._validate_filter_state(filter_state):
                return False

            # Generate and execute clear actions
            actions = self._generate_clear_actions(custom_selectors)
            if not await self._execute_actions(actions):
                return False

            # Verify the input was cleared if configured to do so
            if self.config['verify_clear'] and not await self._verify_filter_cleared(custom_selectors):
                return False

            self.speech.speak(self._format_success('filter_cleared'))
            return True

        except Exception as e:
            self.speech.speak(f"Failed to clear dropdown filter: {str(e)}")
            return False

    async def _get_filter_state(self, custom_selectors: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get the current state of the filter input"""
        selectors = custom_selectors or self.config['filter_selectors']['input']
        selector_str = ', '.join(f"'{s}'" for s in selectors)
        
        return await self._evaluate_js(f"""() => {{
            const selectors = [{selector_str}];
            let filterInput = null;
            
            for (const selector of selectors) {{
                filterInput = document.querySelector(selector);
                if (filterInput) break;
            }}
            
            if (!filterInput) return null;

            return {{
                is_visible: filterInput.offsetParent !== null,
                current_value: filterInput.value,
                is_enabled: !filterInput.disabled
            }};
        }}""")

    async def _validate_filter_state(self, state: Dict[str, Any]) -> bool:
        """Validate the filter state"""
        if not state:
            self.speech.speak(self._format_error('filter_not_found'))
            return False

        if not state['is_visible']:
            self.speech.speak(self._format_error('filter_not_visible'))
            return False

        if not state['is_enabled']:
            self.speech.speak(self._format_error('filter_disabled'))
            return False

        return True

    def _generate_filter_actions(self, search_text: str, custom_selectors: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Generate actions for filtering"""
        selectors = custom_selectors or self.config['filter_selectors']['input']
        return [
            {
                'type': 'click',
                'selectors': selectors,
                'purpose': 'Focus dropdown filter input'
            },
            {
                'type': 'type',
                'selectors': selectors,
                'text': search_text,
                'purpose': 'Type search text into filter'
            }
        ]

    def _generate_clear_actions(self, custom_selectors: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Generate actions for clearing the filter"""
        selectors = custom_selectors or self.config['filter_selectors']['input']
        return [
            {
                'type': 'click',
                'selectors': selectors,
                'purpose': 'Focus dropdown filter input'
            },
            {
                'type': 'type',
                'selectors': selectors,
                'text': '',
                'purpose': 'Clear filter input'
            }
        ]

    async def _execute_actions(self, actions: List[Dict[str, Any]]) -> bool:
        """Execute a list of actions"""
        for action in actions:
            if action['type'] == 'click':
                success = await self._try_selectors_for_click(action['selectors'], action['purpose'])
            elif action['type'] == 'type':
                success = await self._try_selectors_for_type(
                    action['selectors'],
                    action['text'],
                    action['purpose']
                )
            
            if not success:
                self.speech.speak(f"Failed to execute action: {action['purpose']}")
                return False
            
            await self.page.wait_for_timeout(500)
        return True

    async def _try_selectors_for_click(self, selectors: List[str], purpose: str) -> bool:
        """Try multiple selectors for clicking"""
        for selector in selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=5000)
                if element:
                    await element.click()
                    return True
            except Exception:
                continue
        return False

    async def _try_selectors_for_type(self, selectors: List[str], text: str, purpose: str) -> bool:
        """Try multiple selectors for typing"""
        for selector in selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=5000)
                if element:
                    await element.type(text)
                    return True
            except Exception:
                continue
        return False

    async def _verify_filter_text(self, expected_text: str, custom_selectors: Optional[List[str]] = None) -> bool:
        """Verify the filter text was entered correctly"""
        selectors = custom_selectors or self.config['filter_selectors']['input']
        selector_str = ', '.join(f"'{s}'" for s in selectors)
        
        final_state = await self._evaluate_js(f"""() => {{
            const selectors = [{selector_str}];
            let filterInput = null;
            
            for (const selector of selectors) {{
                filterInput = document.querySelector(selector);
                if (filterInput) break;
            }}
            
            return filterInput ? filterInput.value : null;
        }}""")

        if final_state != expected_text:
            self.speech.speak(self._format_error('filter_text_failed'))
            return False
        return True

    async def _verify_filter_cleared(self, custom_selectors: Optional[List[str]] = None) -> bool:
        """Verify the filter was cleared"""
        selectors = custom_selectors or self.config['filter_selectors']['input']
        selector_str = ', '.join(f"'{s}'" for s in selectors)
        
        final_state = await self._evaluate_js(f"""() => {{
            const selectors = [{selector_str}];
            let filterInput = null;
            
            for (const selector of selectors) {{
                filterInput = document.querySelector(selector);
                if (filterInput) break;
            }}
            
            return filterInput ? filterInput.value : null;
        }}""")

        if final_state != '':
            self.speech.speak(self._format_error('filter_clear_failed'))
            return False
        return True 