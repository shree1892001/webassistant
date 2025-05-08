from typing import Dict, Any, List, Optional
from playwright.async_api import Page
from voice_assistant.core.speech import SpeechEngine
from voice_assistant.utils.constants import TIMEOUTS, ERROR_MESSAGES,SUCCESS_MESSAGES

class BaseHandler:
    """Base class for all handlers with common functionality"""
    
    def __init__(self, page: Page, speech: SpeechEngine):
        self.page = page
        self.speech = speech

    async def _try_selectors_for_click(self, selectors: List[str], purpose: str) -> bool:
        """Try multiple selectors for clicking"""
        for selector in selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=TIMEOUTS['selector'])
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
                element = await self.page.wait_for_selector(selector, timeout=TIMEOUTS['selector'])
                if element:
                    await element.type(text)
                    return True
            except Exception:
                continue
        return False

    async def _try_selectors_for_hover(self, selectors: List[str], purpose: str) -> bool:
        """Try multiple selectors for hovering"""
        for selector in selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=TIMEOUTS['selector'])
                if element:
                    await element.hover()
                    return True
            except Exception:
                continue
        return False

    async def _execute_actions(self, actions: List[Dict[str, Any]]) -> bool:
        """Execute a list of actions"""
        for action in actions:
            try:
                if action['type'] == 'click':
                    success = await self._try_selectors_for_click(action['selectors'], action['purpose'])
                elif action['type'] == 'type':
                    success = await self._try_selectors_for_type(
                        action['selectors'],
                        action['text'],
                        action['purpose']
                    )
                elif action['type'] == 'hover':
                    success = await self._try_selectors_for_hover(action['selectors'], action['purpose'])
                else:
                    self.speech.speak(f"Unknown action type: {action['type']}")
                    return False
                
                if not success:
                    self.speech.speak(f"Failed to execute action: {action['purpose']}")
                    return False
                
                await self.page.wait_for_timeout(TIMEOUTS['action_delay'])
            except Exception as e:
                self.speech.speak(f"Error executing action: {str(e)}")
                return False
        return True

    async def _wait_for_element(self, selector: str, timeout: Optional[int] = None) -> bool:
        """Wait for an element to be present"""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout or TIMEOUTS['selector'])
            return True
        except Exception:
            return False

    async def _evaluate_js(self, script: str) -> Any:
        """Evaluate JavaScript on the page"""
        try:
            return await self.page.evaluate(script)
        except Exception as e:
            self.speech.speak(ERROR_MESSAGES['js_evaluation_failed'].format(error=str(e)))
            return None

    def _format_error(self, error_type: str, **kwargs) -> str:
        """Format error message with parameters"""
        return ERROR_MESSAGES.get(error_type, "Unknown error").format(**kwargs)

    def _format_success(self, success_type: str, **kwargs) -> str:
        """Format success message with parameters"""
        return SUCCESS_MESSAGES.get(success_type, "Operation successful").format(**kwargs) 