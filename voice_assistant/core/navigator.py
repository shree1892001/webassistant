from typing import Optional, List, Dict, Any
from playwright.async_api import Page, Locator
from voice_assistant.core.speech import SpeechEngine
from voice_assistant.core.config import BrowserConfig

class WebNavigator:
    def __init__(self, page: Page, speech_engine: SpeechEngine, config: Optional[BrowserConfig] = None):
        self.page = page
        self.speech = speech_engine
        self.config = config or BrowserConfig()

    async def navigate_to(self, url: str) -> bool:
        """Navigate to the specified URL"""
        try:
            url = url.strip()
            if not url.startswith(('http://', 'https://')):
                if self._is_signin_url(url):
                    return await self._handle_signin_navigation()
                url = f"https://{url}"

            domain_part = url.split('//')[1].split('/')[0]
            if not domain_part:
                self.speech.speak("Invalid URL: Missing domain name")
                return False

            print(f"Navigating to: {url}")
            await self.page.goto(url, wait_until="networkidle", timeout=self.config.timeout)
            self.speech.speak(f"Loaded: {await self.page.title()}")
            return True
        except Exception as e:
            self.speech.speak(f"Navigation failed: {str(e)}")
            return False

    def _is_signin_url(self, url: str) -> bool:
        """Check if the URL is a signin/login URL"""
        return any(pattern in url.lower() for pattern in ['signin', 'login'])

    async def _handle_signin_navigation(self) -> bool:
        """Handle navigation to signin pages"""
        try:
            await self.page.goto("https://www.redberyltest.in/#/signin", 
                               wait_until="networkidle", 
                               timeout=self.config.timeout)
            self.speech.speak("Successfully navigated to signin page")
            return True
        except Exception as e:
            self.speech.speak(f"Signin navigation failed: {str(e)}")
            return await self._try_login_button_click()

    async def _try_login_button_click(self) -> bool:
        """Try to find and click login buttons"""
        login_selectors = self._get_login_selectors()
        for selector in login_selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    await self.page.locator(selector).first.click()
                    await self.page.wait_for_timeout(10000)
                    self.speech.speak("Found and clicked login option")
                    return True
            except Exception:
                continue
        return False

    def _get_login_selectors(self) -> List[str]:
        """Get list of selectors for login buttons"""
        return [
            "button:has-text('Login')",
            "button:has-text('Sign In')",
            "a:has-text('Login')",
            "a:has-text('Sign In')"
        ]

    async def wait_for_element(self, selector: str, timeout: Optional[int] = None) -> bool:
        """Wait for an element to be present on the page"""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout or self.config.timeout)
            return True
        except Exception:
            return False

    async def click_element(self, selector: str) -> bool:
        """Click an element if it exists"""
        try:
            if await self.page.locator(selector).count() > 0:
                await self.page.locator(selector).first.click()
                return True
            return False
        except Exception:
            return False

    async def type_text(self, selector: str, text: str) -> bool:
        """Type text into an input field"""
        try:
            if await self.page.locator(selector).count() > 0:
                await self.page.locator(selector).first.fill(text)
                return True
            return False
        except Exception:
            return False

    async def click_state_dropdown(self) -> bool:
        """Click the state dropdown using various methods"""
        try:
            # Try to find and click the state dropdown using label and placeholder
            clicked = await self.page.evaluate("""() => {
                // Try to find the dropdown by label 'State' and placeholder 'Select a State'
                const stateLabels = Array.from(document.querySelectorAll('.p-dropdown-label'))
                    .filter(el => el.textContent.trim() === 'Select a State');
                if (stateLabels.length > 0) {
                    const dropdownContainer = stateLabels[0].closest('.p-dropdown');
                    if (dropdownContainer) {
                        dropdownContainer.click();
                        return true;
                    }
                }
                // Fallback: try by label text
                const labels = Array.from(document.querySelectorAll('label, span, div'))
                    .filter(el => el.textContent.trim().toLowerCase().includes('state'));
                for (const label of labels) {
                    let current = label;
                    while (current.nextElementSibling) {
                        current = current.nextElementSibling;
                        if (current.classList.contains('p-dropdown')) {
                            current.click();
                            return true;
                        }
                    }
                }
                // Fallback: try by position (second dropdown in address form)
                const dropdowns = document.querySelectorAll('.p-dropdown');
                if (dropdowns.length >= 2) {
                    dropdowns[1].click();
                    return true;
                }
                return false;
            }""")
            
            if clicked:
                self.speech.speak("Clicked the State dropdown.")
                await self.page.wait_for_timeout(1000)
                return True
            else:
                self.speech.speak("Could not find the State dropdown.")
                return False
        except Exception as e:
            self.speech.speak(f"Failed to click state dropdown: {str(e)}")
            return False

    async def click_generic_dropdown(self, dropdown_name: str) -> bool:
        """Click a generic dropdown by name"""
        try:
            # Try different selector patterns
            selectors = [
                f"label:has-text('{dropdown_name}') + .p-dropdown",
                f".p-dropdown-label:has-text('{dropdown_name}')",
                f"//label[contains(text(), '{dropdown_name}')]/following-sibling::div[contains(@class, 'p-dropdown')]",
                f"//div[contains(@class, 'p-dropdown')]//span[contains(text(), '{dropdown_name}')]"
            ]

            for selector in selectors:
                if await self.page.locator(selector).count() > 0:
                    await self.page.locator(selector).first.click()
                    await self.page.wait_for_timeout(1000)
                    return True

            return False
        except Exception as e:
            self.speech.speak(f"Failed to click dropdown {dropdown_name}: {str(e)}")
            return False

    async def select_state(self, state_name: str) -> bool:
        """Select a state from the state dropdown"""
        try:
            # First try to find and click the state dropdown
            if not await self.click_state_dropdown():
                return False

            # Wait for state options to appear
            await self.page.wait_for_timeout(1000)

            # Try to find and click the state option
            state_selectors = [
                f"li:has-text('{state_name}')",
                f"//li[contains(text(), '{state_name}')]",
                f".p-dropdown-item:has-text('{state_name}')",
                f"//span[contains(text(), '{state_name}')]"
            ]

            for selector in state_selectors:
                if await self.page.locator(selector).count() > 0:
                    await self.page.locator(selector).first.click()
                    self.speech.speak(f"Selected state: {state_name}")
                    return True

            self.speech.speak(f"Could not find state: {state_name}")
            return False
        except Exception as e:
            self.speech.speak(f"Failed to select state: {str(e)}")
            return False

    async def click_principal_address_dropdown(self) -> bool:
        """Click the principal address dropdown"""
        try:
            # Try to find the principal address dropdown
            selectors = [
                "//label[contains(text(), 'Principal Address')]/following-sibling::div[contains(@class, 'p-dropdown')]",
                "//div[contains(@class, 'p-dropdown')]//span[contains(text(), 'Principal Address')]",
                ".p-dropdown-label:has-text('Principal Address')"
            ]

            for selector in selectors:
                if await self.page.locator(selector).count() > 0:
                    await self.page.locator(selector).first.click()
                    await self.page.wait_for_timeout(1000)
                    return True

            return False
        except Exception as e:
            self.speech.speak(f"Failed to click principal address dropdown: {str(e)}")
            return False

    async def enter_address_field(self, text: str, field_type: str) -> bool:
        """Enter text into an address field"""
        try:
            field_mappings = {
                'address': ['Address', 'Street Address', 'Street'],
                'city': ['City', 'Town'],
                'zip': ['Zip', 'Postal Code', 'ZIP Code'],
                'country': ['Country']
            }

            if field_type not in field_mappings:
                self.speech.speak(f"Unknown field type: {field_type}")
                return False

            for label in field_mappings[field_type]:
                selectors = [
                    f"label:has-text('{label}') + input",
                    f"//label[contains(text(), '{label}')]/following-sibling::input",
                    f"input[placeholder*='{label}']",
                    f"//input[@placeholder[contains(., '{label}')]]"
                ]

                for selector in selectors:
                    if await self.page.locator(selector).count() > 0:
                        await self.page.locator(selector).first.fill(text)
                        return True

            return False
        except Exception as e:
            self.speech.speak(f"Failed to enter {field_type}: {str(e)}")
            return False

    async def check_product_checkbox(self, product_name: str) -> bool:
        """Check a product checkbox"""
        try:
            selectors = [
                f"//label[contains(text(), '{product_name}')]//input[@type='checkbox']",
                f"//input[@type='checkbox'][@name='{product_name}']",
                f"//input[@type='checkbox'][@value='{product_name}']"
            ]

            for selector in selectors:
                if await self.page.locator(selector).count() > 0:
                    checkbox = self.page.locator(selector).first
                    if not await checkbox.is_checked():
                        await checkbox.click()
                    return True

            return False
        except Exception as e:
            self.speech.speak(f"Failed to check product {product_name}: {str(e)}")
            return False

    async def check_all_products(self) -> bool:
        """Check all product checkboxes"""
        try:
            # Try to find a "Select All" checkbox or button
            select_all_selectors = [
                "//label[contains(text(), 'Select All')]//input[@type='checkbox']",
                "//button[contains(text(), 'Select All')]",
                "//input[@type='checkbox'][@name='selectAll']"
            ]

            for selector in select_all_selectors:
                if await self.page.locator(selector).count() > 0:
                    element = self.page.locator(selector).first
                    if await element.is_visible():
                        await element.click()
                        return True

            # If no "Select All" option, try to find and check all product checkboxes
            product_checkboxes = await self.page.query_selector_all("//input[@type='checkbox'][@name='product']")
            if product_checkboxes:
                for checkbox in product_checkboxes:
                    if not await checkbox.is_checked():
                        await checkbox.click()
                return True

            return False
        except Exception as e:
            self.speech.speak(f"Failed to check all products: {str(e)}")
            return False

    async def get_page_context(self) -> Dict[str, Any]:
        """Get the current page's context and structure"""
        try:
            context = await self.page.evaluate("""() => {
                const getElementInfo = (el) => {
                    const rect = el.getBoundingClientRect();
                    return {
                        tag: el.tagName.toLowerCase(),
                        id: el.id,
                        class: el.className,
                        type: el.type,
                        name: el.name,
                        value: el.value,
                        text: el.textContent?.trim(),
                        placeholder: el.placeholder,
                        visible: rect.width > 0 && rect.height > 0,
                        position: {
                            x: rect.x,
                            y: rect.y,
                            width: rect.width,
                            height: rect.height
                        }
                    };
                };

                return {
                    title: document.title,
                    url: window.location.href,
                    forms: Array.from(document.forms).map(form => ({
                        id: form.id,
                        action: form.action,
                        method: form.method,
                        inputs: Array.from(form.elements).map(getElementInfo)
                    })),
                    buttons: Array.from(document.querySelectorAll('button')).map(getElementInfo),
                    inputs: Array.from(document.querySelectorAll('input')).map(getElementInfo),
                    dropdowns: Array.from(document.querySelectorAll('.p-dropdown')).map(getElementInfo),
                    checkboxes: Array.from(document.querySelectorAll('input[type="checkbox"]')).map(getElementInfo)
                };
            }""")

            return context
        except Exception as e:
            self.speech.speak(f"Failed to get page context: {str(e)}")
            return {}

    async def enter_address(self, address_data: Dict[str, str]) -> bool:
        """Enter address information into form fields"""
        try:
            field_mappings = {
                'address': ['Address', 'Street Address', 'Street'],
                'city': ['City', 'Town'],
                'state': ['State'],
                'zip': ['Zip', 'Postal Code', 'ZIP Code'],
                'country': ['Country']
            }

            for field_type, possible_labels in field_mappings.items():
                if field_type in address_data:
                    value = address_data[field_type]
                    if field_type == 'state':
                        success = await self.select_state(value)
                    else:
                        success = await self._enter_text_field(possible_labels, value)
                    
                    if not success:
                        self.speech.speak(f"Failed to enter {field_type}")
                        return False

            return True
        except Exception as e:
            self.speech.speak(f"Failed to enter address: {str(e)}")
            return False

    async def _enter_text_field(self, possible_labels: List[str], value: str) -> bool:
        """Enter text into a field identified by possible labels"""
        try:
            for label in possible_labels:
                # Try different selector patterns
                selectors = [
                    f"label:has-text('{label}') + input",
                    f"//label[contains(text(), '{label}')]/following-sibling::input",
                    f"input[placeholder*='{label}']",
                    f"//input[@placeholder[contains(., '{label}')]]"
                ]

                for selector in selectors:
                    if await self.page.locator(selector).count() > 0:
                        await self.page.locator(selector).first.fill(value)
                        return True

            return False
        except Exception:
            return False

    async def check_checkbox(self, checkbox_name: str) -> bool:
        """Check a checkbox by name"""
        try:
            selectors = [
                f"label:has-text('{checkbox_name}') input[type='checkbox']",
                f"//label[contains(text(), '{checkbox_name}')]//input[@type='checkbox']",
                f"input[type='checkbox'][name*='{checkbox_name}']"
            ]

            for selector in selectors:
                if await self.page.locator(selector).count() > 0:
                    checkbox = self.page.locator(selector).first
                    if not await checkbox.is_checked():
                        await checkbox.click()
                    return True

            return False
        except Exception as e:
            self.speech.speak(f"Failed to check checkbox {checkbox_name}: {str(e)}")
            return False

    async def get_page_content(self) -> Dict[str, Any]:
        """Get the current page's content and context"""
        try:
            # Get visible text content
            content = await self.page.evaluate("""() => {
                return {
                    title: document.title,
                    url: window.location.href,
                    text: document.body.innerText,
                    forms: Array.from(document.forms).map(form => ({
                        id: form.id,
                        action: form.action,
                        method: form.method,
                        inputs: Array.from(form.elements).map(el => ({
                            type: el.type,
                            name: el.name,
                            value: el.value,
                            placeholder: el.placeholder
                        }))
                    })),
                    buttons: Array.from(document.querySelectorAll('button')).map(btn => ({
                        text: btn.innerText,
                        type: btn.type
                    }))
                };
            }""")

            return content
        except Exception as e:
            self.speech.speak(f"Failed to get page content: {str(e)}")
            return {}

    async def retry_operation(self, operation: callable, max_retries: int = 3, delay: int = 1000) -> bool:
        """Retry an operation multiple times with delay"""
        for attempt in range(max_retries):
            try:
                if await operation():
                    return True
            except Exception:
                if attempt < max_retries - 1:
                    await self.page.wait_for_timeout(delay)
                continue
        return False

    async def fill_ra_billing_form(self, form_data: Dict[str, str]) -> bool:
        """Fill the RA Billing form with provided data"""
        try:
            # Map form fields to their selectors
            field_mappings = {
                'name': ['input[name="name"]', 'input[placeholder*="Name"]'],
                'email': ['input[name="email"]', 'input[type="email"]'],
                'phone': ['input[name="phone"]', 'input[placeholder*="Phone"]'],
                'address': ['input[name="address"]', 'textarea[name="address"]'],
                'city': ['input[name="city"]', 'input[placeholder*="City"]'],
                'zip': ['input[name="zip"]', 'input[placeholder*="ZIP"]'],
                'state': ['select[name="state"]', '.state-dropdown']
            }

            for field, value in form_data.items():
                if field in field_mappings:
                    selectors = field_mappings[field]
                    for selector in selectors:
                        if await self.page.locator(selector).count() > 0:
                            if field == 'state':
                                await self.select_state(value)
                            else:
                                await self.page.locator(selector).first.fill(value)
                            break

            self.speech.speak("Filled RA Billing form successfully.")
            return True
        except Exception as e:
            self.speech.speak(f"Failed to fill RA Billing form: {str(e)}")
            return False

    async def _try_selectors_for_click(self, selectors: List[str], purpose: str) -> bool:
        """Try multiple selectors for clicking an element"""
        for selector in selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=5000)
                if element:
                    await element.click()
                    self.speech.speak(f"Successfully executed: {purpose}")
                    return True
            except Exception as e:
                continue
        return False

    async def _try_selectors_for_type(self, selectors: List[str], text: str, purpose: str, max_retries: int = 3, timeout: int = 30000) -> bool:
        """Try multiple selectors for typing text into an element"""
        for selector in selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    await self.page.locator(selector).first.fill(text)
                    self.speech.speak(f"Successfully typed text for {purpose}")
                    return True
            except Exception:
                continue
        self.speech.speak(f"Failed to type text for {purpose}")
        return False

    async def _try_selectors_for_hover(self, selectors: List[str], purpose: str) -> bool:
        """Try multiple selectors for hovering over an element"""
        for selector in selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=5000)
                if element:
                    await element.hover()
                    self.speech.speak(f"Successfully executed: {purpose}")
                    return True
            except Exception as e:
                continue
        return False

    async def _try_selectors_for_check(self, selectors: List[str], purpose: str) -> bool:
        """Try multiple selectors for checking a checkbox"""
        for selector in selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    checkbox = self.page.locator(selector).first
                    if not await checkbox.is_checked():
                        await checkbox.click()
                    self.speech.speak(f"Successfully checked element for {purpose}")
                    return True
            except Exception:
                continue
        self.speech.speak(f"Failed to check element for {purpose}")
        return False

    async def _retry_click(self, selector: str, purpose: str) -> bool:
        """Retry clicking an element multiple times"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if await self.page.locator(selector).count() > 0:
                    await self.page.locator(selector).first.click()
                    self.speech.speak(f"Successfully clicked element for {purpose}")
                    return True
            except Exception:
                if attempt < max_retries - 1:
                    await self.page.wait_for_timeout(1000)
                continue
        self.speech.speak(f"Failed to click element for {purpose} after {max_retries} attempts")
        return False

    async def _retry_type(self, selector: str, text: str, purpose: str, max_retries: int = 3, timeout: int = 30000) -> bool:
        """Retry typing text into an element multiple times"""
        for attempt in range(max_retries):
            try:
                if await self.page.locator(selector).count() > 0:
                    await self.page.locator(selector).first.fill(text)
                    self.speech.speak(f"Successfully typed text for {purpose}")
                    return True
            except Exception:
                if attempt < max_retries - 1:
                    await self.page.wait_for_timeout(1000)
                continue
        self.speech.speak(f"Failed to type text for {purpose} after {max_retries} attempts")
        return False

    async def _check_for_input_fields(self) -> List[Dict[str, Any]]:
        """Check for input fields on the page"""
        try:
            input_fields = await self.page.evaluate("""() => {
                return Array.from(document.querySelectorAll('input, select, textarea')).map(el => ({
                    type: el.type || el.tagName.toLowerCase(),
                    name: el.name,
                    id: el.id,
                    placeholder: el.placeholder,
                    value: el.value,
                    required: el.required,
                    disabled: el.disabled,
                    visible: el.offsetParent !== null
                }));
            }""")
            return input_fields
        except Exception as e:
            self.speech.speak(f"Failed to check for input fields: {str(e)}")
            return []

    async def _filter_html(self, html: str) -> str:
        """Filter HTML content to remove unnecessary elements"""
        try:
            filtered_html = await self.page.evaluate("""(html) => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                
                // Remove script and style elements
                const scripts = doc.querySelectorAll('script, style');
                scripts.forEach(el => el.remove());
                
                // Remove hidden elements
                const hidden = doc.querySelectorAll('[style*="display: none"], [style*="visibility: hidden"]');
                hidden.forEach(el => el.remove());
                
                // Remove empty elements
                const empty = doc.querySelectorAll('*:empty');
                empty.forEach(el => el.remove());
                
                return doc.body.innerHTML;
            }""", html)
            return filtered_html
        except Exception as e:
            self.speech.speak(f"Failed to filter HTML: {str(e)}")
            return html

    async def _get_actions(self, command: str) -> Dict[str, Any]:
        """Get actions to perform based on the command"""
        try:
            # Get page context
            context = await self.get_page_context()
            
            # Filter HTML for better context
            filtered_html = await self._filter_html(await self.page.content())
            
            # Get input fields
            input_fields = await self._check_for_input_fields()
            
            # Format the context for LLM
            formatted_context = {
                'url': self.page.url,
                'title': await self.page.title(),
                'forms': context.get('forms', []),
                'buttons': context.get('buttons', []),
                'inputs': input_fields,
                'html': filtered_html
            }
            
            # TODO: Use LLM to generate actions based on command and context
            return {
                'command': command,
                'context': formatted_context,
                'actions': []
            }
        except Exception as e:
            self.speech.speak(f"Failed to get actions: {str(e)}")
            return {}

    async def _execute_actions(self, action_data: Dict[str, Any]) -> bool:
        """Execute a list of actions"""
        try:
            actions = action_data.get('actions', [])
            for action in actions:
                action_type = action.get('type')
                if action_type == 'click':
                    await self._try_selectors_for_click(action['selectors'], action['purpose'])
                elif action_type == 'type':
                    await self._try_selectors_for_type(action['selectors'], action['text'], action['purpose'])
                elif action_type == 'hover':
                    await self._try_selectors_for_hover(action['selectors'], action['purpose'])
                elif action_type == 'check':
                    await self._try_selectors_for_check(action['selectors'], action['purpose'])
                await self.page.wait_for_timeout(1000)
            return True
        except Exception as e:
            self.speech.speak(f"Failed to execute actions: {str(e)}")
            return False

    async def _perform_action(self, action: Dict[str, Any]) -> bool:
        """Perform a single action"""
        try:
            action_type = action.get('type')
            if action_type == 'click':
                return await self._try_selectors_for_click(action['selectors'], action['purpose'])
            elif action_type == 'type':
                return await self._try_selectors_for_type(action['selectors'], action['text'], action['purpose'])
            elif action_type == 'hover':
                return await self._try_selectors_for_hover(action['selectors'], action['purpose'])
            elif action_type == 'check':
                return await self._try_selectors_for_check(action['selectors'], action['purpose'])
            return False
        except Exception as e:
            self.speech.speak(f"Failed to perform action: {str(e)}")
            return False

    async def check_ein_service(self) -> bool:
        """Check the EIN service checkbox"""
        try:
            # Try different selector patterns for the EIN checkbox
            selectors = [
                "//div[contains(@class, 'wizard-card-checkbox-text1')]//div[contains(text(), 'EIN')]/ancestor::div[contains(@class, 'col-12')]//input[@type='checkbox']",
                "//div[contains(@class, 'wizard-card-checkbox-text1')]//div[contains(text(), 'EIN')]/ancestor::div[contains(@class, 'col-12')]//input",
                "//div[contains(@class, 'wizard-card-checkbox-text1')]//div[contains(text(), 'EIN')]/ancestor::div[contains(@class, 'col-12')]/following-sibling::div[contains(@class, 'wizard-card-checkbox-text2')]/preceding-sibling::div//input"
            ]

            for selector in selectors:
                if await self.page.locator(selector).count() > 0:
                    checkbox = self.page.locator(selector).first
                    if not await checkbox.is_checked():
                        await checkbox.click()
                        self.speech.speak("Selected EIN service for $45.00")
                        return True

            # If checkbox not found, try clicking the text area
            text_selectors = [
                "//div[contains(@class, 'wizard-card-checkbox-text1')]//div[contains(text(), 'EIN')]",
                "//div[contains(@class, 'wizard-card-checkbox-text1')]//div[contains(text(), 'EIN')]/ancestor::div[contains(@class, 'col-12')]"
            ]

            for selector in text_selectors:
                if await self.page.locator(selector).count() > 0:
                    await self.page.locator(selector).first.click()
                    self.speech.speak("Selected EIN service for $45.00")
                    return True

            self.speech.speak("Could not find EIN service checkbox")
            return False
        except Exception as e:
            self.speech.speak(f"Failed to select EIN service: {str(e)}")
            return False

    async def get_ein_service_info(self) -> Dict[str, Any]:
        """Get information about the EIN service"""
        try:
            info = await self.page.evaluate("""() => {
                const einElement = Array.from(document.querySelectorAll('.wizard-card-checkbox-text1'))
                    .find(el => el.textContent.includes('EIN'));
                
                if (!einElement) return null;

                const priceElement = einElement.closest('.col-12').nextElementSibling;
                const tooltip = einElement.querySelector('[data-bs-toggle="tooltip"]');
                
                return {
                    name: 'EIN',
                    price: priceElement?.textContent?.trim() || '$45.00',
                    description: tooltip?.getAttribute('title') || 'Preparation & submission of required forms to obtain an EIN with the IRS.',
                    is_checked: einElement.closest('.col-12').querySelector('input[type="checkbox"]')?.checked || false
                };
            }""")

            if info:
                self.speech.speak(f"EIN service information: {info['description']}. Price: {info['price']}")
                return info
            else:
                self.speech.speak("Could not find EIN service information")
                return {}
        except Exception as e:
            self.speech.speak(f"Failed to get EIN service information: {str(e)}")
            return {}

    async def generate_ein_service_actions(self) -> List[Dict[str, Any]]:
        """Generate actions for EIN service based on HTML structure"""
        try:
            actions = []

            # Action 1: Click the checkbox
            actions.append({
                'type': 'click',
                'selectors': [
                    "//div[contains(@class, 'wizard-card-checkbox-text1')]//div[contains(text(), 'EIN')]/ancestor::div[contains(@class, 'col-12')]//input[@type='checkbox']",
                    "//div[contains(@class, 'wizard-card-checkbox-text1')]//div[contains(text(), 'EIN')]/ancestor::div[contains(@class, 'col-12')]//input"
                ],
                'purpose': 'Select EIN service checkbox',
                'wait_time': 1000
            })

            # Action 2: Click the text area (fallback)
            actions.append({
                'type': 'click',
                'selectors': [
                    "//div[contains(@class, 'wizard-card-checkbox-text1')]//div[contains(text(), 'EIN')]",
                    "//div[contains(@class, 'wizard-card-checkbox-text1')]//div[contains(text(), 'EIN')]/ancestor::div[contains(@class, 'col-12')]"
                ],
                'purpose': 'Select EIN service by clicking text',
                'wait_time': 1000
            })

            # Action 3: Hover over info button
            actions.append({
                'type': 'hover',
                'selectors': [
                    "//button[@data-bs-toggle='tooltip']",
                    "//i[contains(@class, 'pi-info-circle')]"
                ],
                'purpose': 'Show EIN service description',
                'wait_time': 500
            })

            return actions
        except Exception as e:
            self.speech.speak(f"Failed to generate EIN service actions: {str(e)}")
            return []

    async def execute_ein_service_actions(self) -> bool:
        """Execute the generated EIN service actions"""
        try:
            actions = await self.generate_ein_service_actions()
            
            for action in actions:
                action_type = action.get('type')
                wait_time = action.get('wait_time', 0)
                
                if action_type == 'click':
                    success = await self._try_selectors_for_click(action['selectors'], action['purpose'])
                elif action_type == 'hover':
                    success = await self._try_selectors_for_hover(action['selectors'], action['purpose'])
                else:
                    success = False
                
                if not success:
                    self.speech.speak(f"Failed to execute action: {action['purpose']}")
                    return False
                
                if wait_time > 0:
                    await self.page.wait_for_timeout(wait_time)
            
            return True
        except Exception as e:
            self.speech.speak(f"Failed to execute EIN service actions: {str(e)}")
            return False

    async def handle_ein_service(self) -> Dict[str, Any]:
        """Handle EIN service actions based on HTML structure"""
        try:
            # Get the EIN service element and its properties
            ein_info = await self.page.evaluate("""() => {
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
                    description: tooltip?.getAttribute('title') || 'Preparation & submission of required forms to obtain an EIN with the IRS.'
                };
            }""")

            if not ein_info:
                return {
                    'success': False,
                    'error': 'EIN service element not found'
                }

            # Generate actions based on the element state
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
            actions.append({
                'type': 'hover',
                'selectors': [
                    "//button[@data-bs-toggle='tooltip']",
                    "//i[contains(@class, 'pi-info-circle')]"
                ],
                'purpose': 'Show EIN service description'
            })

            # Execute actions
            for action in actions:
                if action['type'] == 'click':
                    success = await self._try_selectors_for_click(action['selectors'], action['purpose'])
                elif action['type'] == 'hover':
                    success = await self._try_selectors_for_hover(action['selectors'], action['purpose'])
                
                if not success:
                    self.speech.speak(f"Failed to execute action: {action['purpose']}")
                    return {
                        'success': False,
                        'error': f"Failed to execute action: {action['purpose']}"
                    }
                
                await self.page.wait_for_timeout(1000)

            # Return success with service information
            return {
                'success': True,
                'info': {
                    'name': 'EIN',
                    'price': ein_info['price'],
                    'description': ein_info['description']
                }
            }

        except Exception as e:
            self.speech.speak(f"Failed to handle EIN service: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def get_ein_service_status(self) -> Dict[str, Any]:
        """Get the current status of the EIN service"""
        try:
            status = await self.page.evaluate("""() => {
                const einElement = document.querySelector('.wizard-card-checkbox-text1');
                if (!einElement) return null;

                const checkbox = einElement.closest('.col-12').querySelector('input[type="checkbox"]');
                const priceElement = einElement.closest('.col-12').nextElementSibling;
                const tooltip = einElement.querySelector('[data-bs-toggle="tooltip"]');

                return {
                    is_selected: checkbox ? checkbox.checked : false,
                    price: priceElement?.textContent?.trim() || '$45.00',
                    description: tooltip?.getAttribute('title') || 'Preparation & submission of required forms to obtain an EIN with the IRS.'
                };
            }""")

            if not status:
                return {
                    'success': False,
                    'error': 'EIN service element not found'
                }

            return {
                'success': True,
                'status': status
            }

        except Exception as e:
            self.speech.speak(f"Failed to get EIN service status: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def handle_ein_service_component(self) -> Dict[str, Any]:
        """Handle the EIN service component with specific actions"""
        try:
            # First, get the component's current state
            component_state = await self.page.evaluate("""() => {
                const einContainer = document.querySelector('.wizard-card-checkbox-text1');
                if (!einContainer) return null;

                const checkbox = einContainer.closest('.col-12').querySelector('input[type="checkbox"]');
                const priceElement = einContainer.closest('.col-12').nextElementSibling;
                const tooltipButton = einContainer.querySelector('button[data-bs-toggle="tooltip"]');
                const infoIcon = einContainer.querySelector('.pi-info-circle');

                return {
                    checkbox: checkbox ? {
                        checked: checkbox.checked,
                        selector: 'input[type="checkbox"]'
                    } : null,
                    price: priceElement?.textContent?.trim() || '$45.00',
                    tooltip: {
                        title: tooltipButton?.getAttribute('title') || 'Preparation & submission of required forms to obtain an EIN with the IRS.',
                        button: tooltipButton ? true : false,
                        icon: infoIcon ? true : false
                    }
                };
            }""")

            if not component_state:
                return {
                    'success': False,
                    'error': 'EIN service component not found'
                }

            # Generate actions based on the component state
            actions = []

            # Action 1: Click the checkbox if not checked
            if component_state['checkbox'] and not component_state['checkbox']['checked']:
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
            if component_state['tooltip']['button']:
                actions.append({
                    'type': 'hover',
                    'selectors': [
                        "//button[@data-bs-toggle='tooltip']",
                        "//i[contains(@class, 'pi-info-circle')]"
                    ],
                    'purpose': 'Show EIN service description'
                })

            # Execute actions
            for action in actions:
                if action['type'] == 'click':
                    success = await self._try_selectors_for_click(action['selectors'], action['purpose'])
                elif action['type'] == 'hover':
                    success = await self._try_selectors_for_hover(action['selectors'], action['purpose'])
                
                if not success:
                    self.speech.speak(f"Failed to execute action: {action['purpose']}")
                    return {
                        'success': False,
                        'error': f"Failed to execute action: {action['purpose']}"
                    }
                
                await self.page.wait_for_timeout(1000)

            # Return success with component information
            return {
                'success': True,
                'component_info': {
                    'name': 'EIN',
                    'price': component_state['price'],
                    'description': component_state['tooltip']['title'],
                    'is_selected': component_state['checkbox'] and component_state['checkbox']['checked']
                }
            }

        except Exception as e:
            self.speech.speak(f"Failed to handle EIN service component: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def get_ein_component_status(self) -> Dict[str, Any]:
        """Get the current status of the EIN service component"""
        try:
            status = await self.page.evaluate("""() => {
                const einContainer = document.querySelector('.wizard-card-checkbox-text1');
                if (!einContainer) return null;

                const checkbox = einContainer.closest('.col-12').querySelector('input[type="checkbox"]');
                const priceElement = einContainer.closest('.col-12').nextElementSibling;
                const tooltipButton = einContainer.querySelector('button[data-bs-toggle="tooltip"]');

                return {
                    is_selected: checkbox ? checkbox.checked : false,
                    price: priceElement?.textContent?.trim() || '$45.00',
                    description: tooltipButton?.getAttribute('title') || 'Preparation & submission of required forms to obtain an EIN with the IRS.'
                };
            }""")

            if not status:
                return {
                    'success': False,
                    'error': 'EIN service component not found'
                }

            return {
                'success': True,
                'status': status
            }

        except Exception as e:
            self.speech.speak(f"Failed to get EIN component status: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def handle_dropdown_filter(self, search_text: str) -> Dict[str, Any]:
        """Handle typing into a PrimeNG dropdown filter input"""
        try:
            # First, find the dropdown filter input
            filter_state = await self.page.evaluate("""() => {
                const filterInput = document.querySelector('input.p-dropdown-filter');
                if (!filterInput) return null;

                return {
                    is_visible: filterInput.offsetParent !== null,
                    current_value: filterInput.value,
                    is_enabled: !filterInput.disabled
                };
            }""")

            if not filter_state:
                return {
                    'success': False,
                    'error': 'Dropdown filter input not found'
                }

            if not filter_state['is_visible']:
                return {
                    'success': False,
                    'error': 'Dropdown filter input is not visible'
                }

            if not filter_state['is_enabled']:
                return {
                    'success': False,
                    'error': 'Dropdown filter input is disabled'
                }

            # Generate actions for the filter input
            actions = []

            # Action 1: Click the input to focus
            actions.append({
                'type': 'click',
                'selectors': [
                    "//input[contains(@class, 'p-dropdown-filter')]",
                    "//input[@type='text'][contains(@class, 'p-dropdown-filter')]"
                ],
                'purpose': 'Focus dropdown filter input'
            })

            # Action 2: Type the search text
            actions.append({
                'type': 'type',
                'selectors': [
                    "//input[contains(@class, 'p-dropdown-filter')]",
                    "//input[@type='text'][contains(@class, 'p-dropdown-filter')]"
                ],
                'text': search_text,
                'purpose': 'Type search text into filter'
            })

            # Execute actions
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
                    return {
                        'success': False,
                        'error': f"Failed to execute action: {action['purpose']}"
                    }
                
                await self.page.wait_for_timeout(500)

            # Verify the text was entered
            final_state = await self.page.evaluate("""() => {
                const filterInput = document.querySelector('input.p-dropdown-filter');
                return filterInput ? filterInput.value : null;
            }""")

            if final_state != search_text:
                return {
                    'success': False,
                    'error': 'Failed to enter search text correctly'
                }

            return {
                'success': True,
                'info': {
                    'search_text': search_text,
                    'final_value': final_state
                }
            }

        except Exception as e:
            self.speech.speak(f"Failed to handle dropdown filter: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def clear_dropdown_filter(self) -> Dict[str, Any]:
        """Clear the PrimeNG dropdown filter input"""
        try:
            # First, check if the filter exists and is visible
            filter_state = await self.page.evaluate("""() => {
                const filterInput = document.querySelector('input.p-dropdown-filter');
                if (!filterInput) return null;

                return {
                    is_visible: filterInput.offsetParent !== null,
                    current_value: filterInput.value,
                    is_enabled: !filterInput.disabled
                };
            }""")

            if not filter_state:
                return {
                    'success': False,
                    'error': 'Dropdown filter input not found'
                }

            if not filter_state['is_visible']:
                return {
                    'success': False,
                    'error': 'Dropdown filter input is not visible'
                }

            if not filter_state['is_enabled']:
                return {
                    'success': False,
                    'error': 'Dropdown filter input is disabled'
                }

            # Generate actions to clear the filter
            actions = []

            # Action 1: Click the input to focus
            actions.append({
                'type': 'click',
                'selectors': [
                    "//input[contains(@class, 'p-dropdown-filter')]",
                    "//input[@type='text'][contains(@class, 'p-dropdown-filter')]"
                ],
                'purpose': 'Focus dropdown filter input'
            })

            # Action 2: Clear the input
            actions.append({
                'type': 'type',
                'selectors': [
                    "//input[contains(@class, 'p-dropdown-filter')]",
                    "//input[@type='text'][contains(@class, 'p-dropdown-filter')]"
                ],
                'text': '',
                'purpose': 'Clear filter input'
            })

            # Execute actions
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
                    return {
                        'success': False,
                        'error': f"Failed to execute action: {action['purpose']}"
                    }
                
                await self.page.wait_for_timeout(500)

            # Verify the input was cleared
            final_state = await self.page.evaluate("""() => {
                const filterInput = document.querySelector('input.p-dropdown-filter');
                return filterInput ? filterInput.value : null;
            }""")

            if final_state != '':
                return {
                    'success': False,
                    'error': 'Failed to clear filter input'
                }

            return {
                'success': True,
                'info': {
                    'final_value': final_state
                }
            }

        except Exception as e:
            self.speech.speak(f"Failed to clear dropdown filter: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            } 