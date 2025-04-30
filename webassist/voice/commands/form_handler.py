import re
from typing import List, Dict, Any

class FormHandler:
    def __init__(self, assistant):
        self.assistant = assistant

    async def handle_form_command(self, command: str) -> bool:
        """Handle form-related commands"""
        # Check for email input
        email_match = re.search(r'(?:enter|input|type|fill)\s+(?:email|emaol|e-mail|email\s+address|email\s+adddress)\s+([^\s]+@[^\s]+(?:\.[^\s]+)+)', command, re.IGNORECASE)
        if email_match:
            email = email_match.group(1)
            return await self._handle_email_input(email)

        # Check for dropdown selection
        dropdown_match = re.search(r'select\s+(.+?)(?:\s+from|\s+in)?\s+(.+?)(?:\s+dropdown)?', command, re.IGNORECASE)
        if dropdown_match:
            option, dropdown_name = dropdown_match.groups()
            return await self._handle_dropdown_selection(option.strip(), dropdown_name.strip())

        # Check for checkbox commands
        checkbox_match = re.search(r'(check|uncheck|toggle)(?:\s+the)?\s+(.+)', command, re.IGNORECASE)
        if checkbox_match:
            action, checkbox_name = checkbox_match.groups()
            return await self._handle_checkbox_action(action.strip().lower(), checkbox_name.strip())

        return False

    async def _handle_email_input(self, email: str) -> bool:
        """Handle email input"""
        self.assistant.speak(f"Entering email: {email}")

        # Try to find the email input field
        email_selectors = [
            'input[type="email"]',
            'input[name="email"]',
            'input[autocomplete="email"]',
            'input[placeholder*="email" i]',
            'input[placeholder*="Email" i]',
            'label:has-text("Email") + input',
            'label:has-text("Email") ~ input',
            'input:has-text("Email")',
            'input:has-text("email")'
        ]

        for selector in email_selectors:
            try:
                if await self.assistant.page.locator(selector).count() > 0:
                    # Clear the field first
                    await self.assistant.page.locator(selector).first.fill('')
                    # Type the email
                    await self.assistant.page.locator(selector).first.type(email, delay=100)
                    # Trigger input event
                    await self.assistant.page.evaluate(f"""
                        (selector) => {{
                            const input = document.querySelector(selector);
                            if (input) {{
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                        }}
                    """, selector)
                    self.assistant.speak("Email entered successfully")
                    return True
            except Exception as e:
                print(f"Error with selector {selector}: {e}")
                continue

        # If no specific email field found, try the first input field
        try:
            input_count = await self.assistant.page.locator('input').count()
            if input_count > 0:
                first_input = self.assistant.page.locator('input').first
                await first_input.fill('')
                await first_input.type(email, delay=100)
                await self.assistant.page.evaluate("""
                    (input) => {
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                """, first_input)
                self.assistant.speak("Email entered using first input field")
                return True
        except Exception as e:
            print(f"Error using first input field: {e}")

        self.assistant.speak("Could not find element to enter email address")
        return False

    async def _handle_dropdown_selection(self, option: str, dropdown_name: str) -> bool:
        """Handle dropdown selection"""
        self.assistant.speak(f"Selecting {option} from {dropdown_name} dropdown")

        # Try to find and click the dropdown
        if not await self._click_generic_dropdown(dropdown_name):
            return False

        # Wait for the dropdown to appear
        await self.assistant.page.wait_for_timeout(2000)

        # Try to find and click the option
        option_selectors = [
            f'text="{option}"',
            f'[role="option"]:has-text("{option}")',
            f'[role="listbox"] >> text="{option}"',
            f'[role="menu"] >> text="{option}"',
            f'[role="combobox"] >> text="{option}"'
        ]

        for selector in option_selectors:
            try:
                if await self.assistant.page.locator(selector).count() > 0:
                    await self.assistant.page.locator(selector).first.click()
                    self.assistant.speak(f"Selected {option} from {dropdown_name}")
                    await self.assistant.page.wait_for_timeout(2000)
                    return True
            except Exception:
                continue

        self.assistant.speak(f"Could not find option {option} in {dropdown_name} dropdown")
        return False

    async def _click_generic_dropdown(self, dropdown_name: str) -> bool:
        """Click a generic dropdown"""
        try:
            dropdown_selectors = [
                f'[role="combobox"]:has-text("{dropdown_name}")',
                f'select[name="{dropdown_name.lower()}"]',
                f'[name="{dropdown_name.lower()}"]',
                f'[role="combobox"]:has-text("Select {dropdown_name}")',
                f'select:has-text("{dropdown_name}")'
            ]

            for selector in dropdown_selectors:
                try:
                    if await self.assistant.page.locator(selector).count() > 0:
                        await self.assistant.page.locator(selector).first.click()
                        self.assistant.speak(f"Found and clicked {dropdown_name} dropdown")
                        return True
                except Exception:
                    continue

            self.assistant.speak(f"Could not find {dropdown_name} dropdown")
            return False
        except Exception as e:
            self.assistant.speak(f"Error clicking {dropdown_name} dropdown: {str(e)}")
            return False

    async def _handle_checkbox_action(self, action: str, checkbox_name: str) -> bool:
        """Handle checkbox actions (check/uncheck/toggle)"""
        self.assistant.speak(f"{action.capitalize()}ing checkbox: {checkbox_name}")

        # Try to find the checkbox
        checkbox_selectors = [
            f'input[type="checkbox"]:has-text("{checkbox_name}")',
            f'input[type="checkbox"][name="{checkbox_name.lower()}"]',
            f'input[type="checkbox"][id="{checkbox_name.lower()}"]',
            f'label:has-text("{checkbox_name}") >> input[type="checkbox"]'
        ]

        for selector in checkbox_selectors:
            try:
                if await self.assistant.page.locator(selector).count() > 0:
                    checkbox = self.assistant.page.locator(selector).first
                    
                    if action == "check":
                        await checkbox.check()
                    elif action == "uncheck":
                        await checkbox.uncheck()
                    else:  # toggle
                        is_checked = await checkbox.is_checked()
                        if is_checked:
                            await checkbox.uncheck()
                        else:
                            await checkbox.check()

                    self.assistant.speak(f"Successfully {action}ed checkbox: {checkbox_name}")
                    await self.assistant.page.wait_for_timeout(1000)
                    return True
            except Exception:
                continue

        self.assistant.speak(f"Could not find checkbox: {checkbox_name}")
        return False

    async def enter_address_field(self, text: str, field_type: str) -> bool:
        """Enter text into an address field"""
        try:
            self.assistant.speak(f"Entering {field_type} in address field")

            # Define selectors for different address field types
            field_selectors = {
                "address": [
                    'input[name="address"]',
                    'input[placeholder*="address" i]',
                    'textarea[name="address"]',
                    'textarea[placeholder*="address" i]'
                ],
                "city": [
                    'input[name="city"]',
                    'input[placeholder*="city" i]'
                ],
                "zip": [
                    'input[name="zip"]',
                    'input[placeholder*="zip" i]',
                    'input[name="postalCode"]',
                    'input[placeholder*="postal" i]'
                ]
            }

            # Get the appropriate selectors for the field type
            selectors = field_selectors.get(field_type.lower(), [])
            if not selectors:
                self.assistant.speak(f"Unknown address field type: {field_type}")
                return False

            # Try each selector
            for selector in selectors:
                try:
                    if await self.assistant.page.locator(selector).count() > 0:
                        await self.assistant.page.locator(selector).first.fill(text)
                        self.assistant.speak(f"Entered {field_type}: {text}")
                        await self.assistant.page.wait_for_timeout(1000)
                        return True
                except Exception:
                    continue

            self.assistant.speak(f"Could not find {field_type} field")
            return False
        except Exception as e:
            self.assistant.speak(f"Error entering {field_type}: {str(e)}")
            return False 