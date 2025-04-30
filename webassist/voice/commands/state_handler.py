import re
from typing import List, Dict, Any

class StateHandler:
    def __init__(self, assistant):
        self.assistant = assistant

    async def handle_state_selection(self, command: str) -> bool:
        """Handle state selection commands"""
        state_match = re.search(r'(?:select|choose|pick)\s+(?:state\s+)?(.+)', command, re.IGNORECASE)
        if state_match:
            state_name = state_match.group(1).strip()
            return await self._handle_state_selection(state_name)
        return False

    async def _handle_state_selection(self, state_name: str) -> bool:
        """Handle the actual state selection process"""
        self.assistant.speak(f"Selecting state: {state_name}")

        # First ensure we're on the right page
        if not await self._ensure_entity_type_selected():
            return False

        # Try to find and click the state dropdown
        if not await self._click_state_dropdown_direct():
            return False

        # Wait for the dropdown to appear
        await self.assistant.page.wait_for_timeout(2000)

        # Try to find and click the state option
        state_selectors = [
            f'text="{state_name}"',
            f'[role="option"]:has-text("{state_name}")',
            f'[role="listbox"] >> text="{state_name}"',
            f'[role="menu"] >> text="{state_name}"',
            f'[role="combobox"] >> text="{state_name}"'
        ]

        for selector in state_selectors:
            try:
                if await self.assistant.page.locator(selector).count() > 0:
                    await self.assistant.page.locator(selector).first.click()
                    self.assistant.speak(f"Selected state: {state_name}")
                    await self.assistant.page.wait_for_timeout(2000)
                    return True
            except Exception:
                continue

        self.assistant.speak(f"Could not find state option: {state_name}")
        return False

    async def _ensure_entity_type_selected(self) -> bool:
        """Ensure entity type is selected before state selection"""
        try:
            # Check if we're on the right page
            current_url = self.assistant.page.url
            if not ('entity' in current_url or 'registration' in current_url):
                self.assistant.speak("Navigating to entity registration page...")
                await self.assistant.page.goto("https://www.redberyltest.in/#/entity-registration", wait_until="networkidle", timeout=20000)
                await self.assistant.page.wait_for_timeout(2000)

            # Check if entity type is already selected
            entity_type_selectors = [
                '[role="combobox"]:has-text("Entity Type")',
                'select[name="entityType"]',
                '[name="entityType"]'
            ]

            for selector in entity_type_selectors:
                try:
                    if await self.assistant.page.locator(selector).count() > 0:
                        # Entity type dropdown exists, check if it's selected
                        selected_value = await self.assistant.page.evaluate(f"""() => {{
                            const element = document.querySelector('{selector}');
                            return element ? element.value : null;
                        }}""")
                        if not selected_value:
                            self.assistant.speak("Entity type not selected, selecting default...")
                            await self._select_entity_type("Company")
                            return True
                        return True
                except Exception:
                    continue

            return True
        except Exception as e:
            self.assistant.speak(f"Error ensuring entity type: {str(e)}")
            return False

    async def _select_entity_type(self, entity_type: str) -> bool:
        """Select entity type"""
        try:
            # Try to find and click the entity type dropdown
            entity_type_selectors = [
                '[role="combobox"]:has-text("Entity Type")',
                'select[name="entityType"]',
                '[name="entityType"]'
            ]

            for selector in entity_type_selectors:
                try:
                    if await self.assistant.page.locator(selector).count() > 0:
                        await self.assistant.page.locator(selector).first.click()
                        await self.assistant.page.wait_for_timeout(1000)

                        # Try to find and click the entity type option
                        entity_option_selectors = [
                            f'text="{entity_type}"',
                            f'[role="option"]:has-text("{entity_type}")',
                            f'[role="listbox"] >> text="{entity_type}"'
                        ]

                        for option_selector in entity_option_selectors:
                            try:
                                if await self.assistant.page.locator(option_selector).count() > 0:
                                    await self.assistant.page.locator(option_selector).first.click()
                                    self.assistant.speak(f"Selected entity type: {entity_type}")
                                    await self.assistant.page.wait_for_timeout(2000)
                                    return True
                            except Exception:
                                continue
                except Exception:
                    continue

            return False
        except Exception as e:
            self.assistant.speak(f"Error selecting entity type: {str(e)}")
            return False

    async def _click_state_dropdown_direct(self) -> bool:
        """Click the state dropdown directly"""
        try:
            state_dropdown_selectors = [
                '[role="combobox"]:has-text("State")',
                'select[name="state"]',
                '[name="state"]',
                '[role="combobox"]:has-text("Select State")',
                'select:has-text("State")'
            ]

            for selector in state_dropdown_selectors:
                try:
                    if await self.assistant.page.locator(selector).count() > 0:
                        await self.assistant.page.locator(selector).first.click()
                        self.assistant.speak("Found and clicked state dropdown")
                        return True
                except Exception:
                    continue

            self.assistant.speak("Could not find state dropdown")
            return False
        except Exception as e:
            self.assistant.speak(f"Error clicking state dropdown: {str(e)}")
            return False 