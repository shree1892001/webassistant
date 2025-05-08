from typing import Dict, Any, List
from playwright.async_api import Page
from  voice_assistant.core.speech import SpeechEngine
from voice_assistant.handlers.base_handler import BaseHandler

class EinHandler(BaseHandler):
    """Handles EIN service component interactions"""
    
    def __init__(self, page: Page, speech: SpeechEngine):
        super().__init__(page, speech)

    async def handle_ein_service(self) -> Dict[str, Any]:
        """Handle EIN service component actions"""
        try:
            # Get the EIN service element and its properties
            ein_info = await self._get_ein_state()
            if not ein_info:
                return {
                    'success': False,
                    'error': 'EIN service element not found'
                }

            # Generate actions based on the element state
            actions = self._generate_ein_actions(ein_info)
            if not await self._execute_actions(actions):
                return {
                    'success': False,
                    'error': 'Failed to execute EIN service actions'
                }

            # Return success with service information
            return {
                'success': True,
                'info': {
                    'name': 'EIN',
                    'price': ein_info['price'],
                    'description': ein_info['tooltip']['title'],
                    'is_selected': ein_info['checkbox'] and ein_info['checkbox']['checked']
                }
            }

        except Exception as e:
            self.speech.speak(f"Failed to handle EIN service: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def get_ein_status(self) -> Dict[str, Any]:
        """Get the current status of the EIN service"""
        try:
            status = await self._get_ein_state()
            if not status:
                return {
                    'success': False,
                    'error': 'EIN service element not found'
                }

            return {
                'success': True,
                'status': {
                    'is_selected': status['checkbox'] and status['checkbox']['checked'],
                    'price': status['price'],
                    'description': status['tooltip']['title']
                }
            }

        except Exception as e:
            self.speech.speak(f"Failed to get EIN service status: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _get_ein_state(self) -> Dict[str, Any]:
        """Get the current state of the EIN service component"""
        return await self._evaluate_js("""() => {
            const einElement = document.querySelector('.wizard-card-checkbox-text1');
            if (!einElement) return null;

            const checkbox = einElement.closest('.col-12').querySelector('input[type="checkbox"]');
            const priceElement = einElement.closest('.col-12').nextElementSibling;
            const tooltip = einElement.querySelector('[data-bs-toggle="tooltip"]');

            return {
                checkbox: checkbox ? {
                    selector: 'input[type="checkbox"]',
                    checked: checkbox.checked
                } : null,
                price: priceElement?.textContent?.trim() || '$45.00',
                tooltip: {
                    title: tooltip?.getAttribute('title') || 'Preparation & submission of required forms to obtain an EIN with the IRS.',
                    button: tooltip ? true : false,
                    icon: einElement.querySelector('.pi-info-circle') ? true : false
                }
            };
        }""")

    def _generate_ein_actions(self, ein_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate actions for the EIN service component"""
        actions = []

        # Action 1: Click the checkbox if not checked
        if ein_info['checkbox'] and not ein_info['checkbox']['checked']:
            actions.append({
                'type': 'click',
                'selectors': [
                    "//div[contains(@class, 'wizard-card-checkbox-text1')]//div[contains(text(), 'EIN')]/ancestor::div[contains(@class, 'col-12')]//input[@type='checkbox']",
                    "//div[contains(@class, 'wizard-card-checkbox-text1')]//div[contains(text(), 'EIN')]/ancestor::div[contains(@class, 'col-12')]//input"
                ],
                'purpose': 'Select EIN service checkbox'
            })

        # Action 2: Click the text area (fallback)
        actions.append({
            'type': 'click',
            'selectors': [
                "//div[contains(@class, 'wizard-card-checkbox-text1')]//div[contains(text(), 'EIN')]",
                "//div[contains(@class, 'wizard-card-checkbox-text1')]//div[contains(text(), 'EIN')]/ancestor::div[contains(@class, 'col-12')]"
            ],
            'purpose': 'Select EIN service by clicking text'
        })

        # Action 3: Hover over info button
        if ein_info['tooltip']['button']:
            actions.append({
                'type': 'hover',
                'selectors': [
                    "//button[@data-bs-toggle='tooltip']",
                    "//i[contains(@class, 'pi-info-circle')]"
                ],
                'purpose': 'Show EIN service description'
            })

        return actions 