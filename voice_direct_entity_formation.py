import os
import re
import asyncio
import pyttsx3
from playwright.async_api import async_playwright
from webassist.Common.constants import *
from webassist.llm.provider import LLMProviderFactory
from webassist.core.config import AssistantConfig
from webassist.models.context import PageContext, InteractionContext
from webassist.models.result import InteractionResult

class VoiceAssistantEntityFormation:
    def __init__(self, config=None):
        self.engine = None
        self.llm_provider = None
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        # Use provided config or create default
        self.config = config or AssistantConfig.from_env()

        # Entity formation specific state
        self.current_entity_type = None
        self.current_state = None
        self.current_step = None
        self.entity_name = None
        self.formation_steps = {
            "CORP": [
                "entity_type_selection",
                "state_selection",
                "entity_name",
                "principal_address",
                "registered_agent",
                "purpose",
                "incorporator",
                "shares",
                "director",
                "officer",
                "president",
                "treasurer",
                "secretary",
                "naics_code",
                "billing_shipping",
                "submit",
                "payment"
            ],
            "LLC": [
                "entity_type_selection",
                "state_selection",
                "entity_name",
                "principal_address",
                "registered_agent",
                "purpose",
                "organizer",
                "member_manager",
                "naics_code",
                "billing_shipping",
                "submit",
                "payment"
            ]
        }

    async def initialize(self):
        """Initialize components"""
        # Initialize text-to-speech
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', self.config.speech_rate)
        self.engine.setProperty('volume', self.config.speech_volume)

        # Initialize LLM provider
        api_key = self.config.gemini_api_key or os.environ.get("GEMINI_API_KEY", DEFAULT_API_KEY)
        self.llm_provider = LLMProviderFactory.create_provider("gemini", api_key, self.config.llm_model)

        # Initialize browser
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.config.browser_headless)
        self.context = await self.browser.new_context(
            viewport={'width': self.config.browser_width, 'height': self.config.browser_height}
        )
        self.page = await self.context.new_page()

        # Navigate to start URL
        await self.browse_website(DEFAULT_START_URL)

    async def close(self, keep_browser_open=True):
        """Close components"""
        if not keep_browser_open:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            print("Browser closed")
        else:
            print("Browser kept open for inspection")

    def speak(self, text):
        """Speak text"""
        print(f"ASSISTANT: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

    async def browse_website(self, url):
        """Navigate to URL"""
        try:
            # Clean up the URL
            url = url.strip()

            # Check if it's a valid URL format
            if not url.startswith(('http://', 'https://')):
                # Special handling for signin URLs
                if url.startswith('#/signin') or url.startswith('/#/signin') or 'signin' in url:
                    self.speak("Trying alternative approach for signin page...")
                    try:
                        # Try the known working URL
                        await self.page.goto("https://www.redberyltest.in/#/signin", wait_until="networkidle", timeout=40000)
                        self.speak("Successfully navigated to signin page")
                        return True
                    except Exception as alt_err:
                        self.speak(f"Alternative navigation also failed: {str(alt_err)}")

                        # As a last resort, try to find and click login button
                        self.speak("Trying to find login option...")
                        login_selectors = await self._get_llm_selectors("find login or sign in link or button",
                                                                  await self._get_page_context())
                        for selector in login_selectors:
                            try:
                                if await self.page.locator(selector).count() > 0:
                                    await self.page.locator(selector).first.click()
                                    await self.page.wait_for_timeout(10000)
                                    self.speak("Found and clicked login option")
                                    return True
                            except Exception:
                                continue
                    return False

                # Add https:// prefix for regular domains
                url = f"https://{url}"

            # Ensure there's a domain name
            domain_part = url.split('//')[1].split('/')[0]
            if not domain_part or domain_part == '':
                self.speak("Invalid URL: Missing domain name")
                return False

            print(f"Navigating to: {url}")
            await self.page.goto(url, wait_until="networkidle", timeout=20000)
            self.speak(f"Loaded: {await self.page.title()}")
            return True
        except Exception as e:
            self.speak(f"Navigation failed: {str(e)}")

            # Handle special case for login URLs
            if url.startswith('#/signin') or url.startswith('/#/signin') or 'signin' in url:
                self.speak("Trying alternative approach for signin page...")
                try:
                    # Try the known working URL
                    await self.page.goto("https://www.redberyltest.in/#/signin", wait_until="networkidle", timeout=30000)
                    self.speak("Successfully navigated to signin page")
                    return True
                except Exception as alt_err:
                    self.speak(f"Alternative navigation also failed: {str(alt_err)}")

                    # As a last resort, try to find and click login button
                    self.speak("Trying to find login option...")
                    login_selectors = await self._get_llm_selectors("find login or sign in link or button",
                                                              await self._get_page_context())
                    for selector in login_selectors:
                        try:
                            if await self.page.locator(selector).count() > 0:
                                await self.page.locator(selector).first.click()
                                await self.page.wait_for_timeout(10000)
                                self.speak("Found and clicked login option")
                                return True
                        except Exception:
                            continue
            return False

    async def process_command(self, command):
        """Process a command"""
        print(f"DEBUG: Processing command: '{command}'")

        if command.lower() in EXIT_COMMANDS:
            self.speak("Goodbye! Browser will remain open for inspection.")
            return False

        if command.lower() == HELP_COMMAND:
            self.show_help()
            return True

        if command.lower().startswith(("go to ", "navigate to ", "open ")):
            # Extract URL
            parts = command.split(" ", 2)
            if len(parts) >= 3:
                url = parts[2]
                await self.browse_website(url)
                return True

        # Try direct commands first
        if await self._handle_direct_commands(command):
            return True

        # For other commands, use LLM to generate actions
        action_data = await self._get_actions(command)
        return await self._execute_actions(action_data)

    async def _handle_direct_commands(self, command):
        """Handle common commands directly, using LLM for complex selector generation"""
        # Handle entity formation command
        entity_formation_match = re.search(r'(?:start|begin|create|form)(?:\s+an?)?\s+entity\s+formation(?:\s+for)?\s+([a-zA-Z]+)(?:\s+in)?\s+([a-zA-Z\s]+)', command, re.IGNORECASE)
        if entity_formation_match:
            entity_type = entity_formation_match.group(1).strip()
            state = entity_formation_match.group(2).strip()
            self.speak(f"Starting entity formation for {entity_type} in {state}...")
            return await self._start_entity_formation(entity_type, state)

        # Handle entity name command
        entity_name_match = re.search(r'(?:enter|input|type|fill)(?:\s+in)?\s+(.+?)(?:\s+as)?\s+(?:entity\s+name|company\s+name)', command, re.IGNORECASE)
        if entity_name_match:
            name_text = entity_name_match.group(1).strip()
            self.speak(f"Entering '{name_text}' as entity name...")
            self.entity_name = name_text
            return await self._enter_entity_name(name_text)

        # Handle purpose command
        purpose_match = re.search(r'(?:enter|input|type|fill)(?:\s+in)?\s+(.+?)(?:\s+as)?\s+(?:purpose|business\s+purpose)', command, re.IGNORECASE)
        if purpose_match:
            purpose_text = purpose_match.group(1).strip()
            self.speak(f"Entering '{purpose_text}' as purpose...")
            return await self._enter_field_value(purpose_text, "purpose")

        # Handle shares command
        shares_match = re.search(r'(?:enter|input|type|fill)(?:\s+in)?\s+(\d+)(?:\s+(?:as|for))?\s+(?:shares|number\s+of\s+shares)', command, re.IGNORECASE)
        if shares_match:
            shares_text = shares_match.group(1).strip()
            self.speak(f"Entering '{shares_text}' for shares...")
            return await self._enter_field_value(shares_text, "shares")

        # Handle NAICS code command
        naics_match = re.search(r'(?:enter|input|type|fill)(?:\s+in)?\s+(\d+)(?:\s+(?:as|for))?\s+(?:naics|naics\s+code)', command, re.IGNORECASE)
        if naics_match:
            naics_text = naics_match.group(1).strip()
            self.speak(f"Entering '{naics_text}' for NAICS code...")
            return await self._enter_field_value(naics_text, "naics_code")

        # Handle click next button command
        next_button_match = re.search(r'(?:click|press|hit)(?:\s+(?:the|on))?\s+(?:next|next\s+button)', command, re.IGNORECASE)
        if next_button_match:
            self.speak("Clicking next button...")
            return await self._click_next_button()

        # Handle continue to next step command
        continue_match = re.search(r'(?:continue|proceed|go|move)(?:\s+(?:to|with))?\s+(?:next|next\s+step)', command, re.IGNORECASE)
        if continue_match:
            self.speak("Proceeding to next step...")
            return await self._proceed_to_next_step()

        # Handle address form input commands
        address_line1_match = re.search(r'(?:enter|input|type|fill)(?:\s+in)?\s+(.+?)(?:\s+in(?:to)?)?\s+(?:address\s+line\s*1|first\s+address\s+line)', command, re.IGNORECASE)
        if address_line1_match:
            address_text = address_line1_match.group(1).strip()
            self.speak(f"Entering '{address_text}' in address line 1...")
            return await self._enter_field_value(address_text, "address_line1")

        address_line2_match = re.search(r'(?:enter|input|type|fill)(?:\s+in)?\s+(.+?)(?:\s+in(?:to)?)?\s+(?:address\s+line\s*2|second\s+address\s+line)', command, re.IGNORECASE)
        if address_line2_match:
            address_text = address_line2_match.group(1).strip()
            self.speak(f"Entering '{address_text}' in address line 2...")
            return await self._enter_field_value(address_text, "address_line2")

        city_match = re.search(r'(?:enter|input|type|fill)(?:\s+in)?\s+(.+?)(?:\s+in(?:to)?)?\s+(?:city|city\s+field)', command, re.IGNORECASE)
        if city_match:
            city_text = city_match.group(1).strip()
            self.speak(f"Entering '{city_text}' in city field...")
            return await self._enter_field_value(city_text, "city")

        zip_match = re.search(r'(?:enter|input|type|fill)(?:\s+in)?\s+(.+?)(?:\s+in(?:to)?)?\s+(?:zip|zip\s+code|postal\s+code)', command, re.IGNORECASE)
        if zip_match:
            zip_text = zip_match.group(1).strip()
            self.speak(f"Entering '{zip_text}' in zip code field...")
            return await self._enter_field_value(zip_text, "zip")

        # Handle state selection commands
        state_match = re.search(r'(?:select|choose|pick)(?:\s+the)?\s+(?:state|province)(?:\s+of\s+\w+)?\s+["\']?([^"\']+)["\']?', command, re.IGNORECASE)
        if state_match:
            state_name = state_match.group(1).strip()
            self.current_state = state_name
            self.speak(f"Selecting state: {state_name}...")
            return await self._select_state(state_name)

        # Handle entity type selection commands
        entity_type_match = re.search(r'(?:select|choose|pick)(?:\s+the)?\s+(?:entity|entity\s+type)\s+["\']?([^"\']+)["\']?', command, re.IGNORECASE)
        if entity_type_match:
            entity_type = entity_type_match.group(1).strip()
            self.current_entity_type = entity_type.upper()
            self.speak(f"Selecting entity type: {entity_type}...")
            return await self._select_entity_type(entity_type)

        # Handle click dropdown commands
        dropdown_match = re.search(r'(?:click|select|open)(?:\s+(?:on|the))?\s+(.+?)(?:\s+dropdown)', command, re.IGNORECASE)
        if dropdown_match:
            dropdown_name = dropdown_match.group(1).strip()
            self.speak(f"Clicking on {dropdown_name} dropdown...")
            return await self._click_dropdown(dropdown_name)

        # Handle click element commands
        click_match = re.search(r'(?:click|select|press)(?:\s+(?:on|the))?\s+(.+)', command, re.IGNORECASE)
        if click_match:
            element_name = click_match.group(1).strip()
            self.speak(f"Clicking on {element_name}...")
            return await self._click_element(element_name)

        # Handle select person commands
        person_match = re.search(r'(?:select|choose|pick)(?:\s+the)?\s+(?:person|contact)(?:\s+for)?\s+(.+)', command, re.IGNORECASE)
        if person_match:
            role = person_match.group(1).strip()
            self.speak(f"Selecting person for {role}...")
            return await self._select_person_for_role(role)

        # Handle submit form commands
        submit_match = re.search(r'(?:submit|send|complete)(?:\s+(?:the|this))?\s+(?:form|order|application)', command, re.IGNORECASE)
        if submit_match:
            self.speak("Submitting form...")
            return await self._submit_form()

        # Handle confirm commands
        confirm_match = re.search(r'(?:confirm|verify|approve)(?:\s+(?:the|this))?\s+(?:order|submission|application)', command, re.IGNORECASE)
        if confirm_match:
            self.speak("Confirming order...")
            return await self._confirm_order()

        # Handle payment commands
        payment_match = re.search(r'(?:enter|input|fill)(?:\s+(?:in|out))?\s+(?:payment|credit\s+card|card)(?:\s+(?:info|information|details))?', command, re.IGNORECASE)
        if payment_match:
            self.speak("Entering payment information...")
            return await self._enter_payment_info()

        # If no direct command matched, return False
        return False

    async def _get_page_context(self):
        """Get the current page context for LLM"""
        try:
            # Get page title
            title = await self.page.title()

            # Get page content
            content = await self.page.content()

            # Create a context object
            context = PageContext(
                url=self.page.url,
                title=title,
                content=content
            )

            return context
        except Exception as e:
            print(f"Error getting page context: {e}")
            return PageContext(
                url=self.page.url,
                title="Unknown",
                content=""
            )

    async def _get_actions(self, command):
        """Get actions from LLM for a command"""
        try:
            # Get page context
            context = await self._get_page_context()

            # Get actions from LLM
            actions = await self.llm_provider.get_actions(command, context)

            print(f"🔍 Raw LLM response: {actions}")
            return actions
        except Exception as e:
            print(f"Error getting actions from LLM: {e}")
            return {"actions": []}

    async def _execute_actions(self, action_data):
        """Execute actions from LLM"""
        try:
            if 'actions' not in action_data or not action_data['actions']:
                self.speak("No actions to execute")
                return False

            for action in action_data['actions']:
                action_type = action.get('action')
                selector = action.get('selector')

                if not action_type or not selector:
                    continue

                if action_type == 'click':
                    await self._retry_click(selector, action.get('purpose', 'element'))
                elif action_type == 'type':
                    await self._retry_type(selector, action.get('text', ''), action.get('purpose', 'field'))

            return True
        except Exception as e:
            print(f"Error executing actions: {e}")
            return False

    async def _get_llm_selectors(self, task, context):
        """Get selectors from LLM for a specific task"""
        try:
            # Create a specific command for the LLM
            command = f"Find selectors for: {task}"

            # Get actions from LLM
            action_data = await self.llm_provider.get_actions(command, context)

            # Extract selectors from actions
            selectors = []
            if 'actions' in action_data:
                for action in action_data['actions']:
                    if 'selector' in action:
                        selectors.append(action['selector'])
                    if 'fallback_selectors' in action:
                        selectors.extend(action['fallback_selectors'])

            return selectors
        except Exception as e:
            print(f"Error getting selectors from LLM: {e}")
            return []

    async def _retry_click(self, selector, element_name, max_retries=3, timeout=10000):
        """Retry clicking an element multiple times"""
        for attempt in range(max_retries):
            try:
                await self.page.locator(selector).first.click(timeout=timeout)
                return True
            except Exception as e:
                print(f"Click attempt {attempt+1} failed for {element_name}: {e}")
                if attempt == max_retries - 1:
                    print(f"All {max_retries} click attempts failed for {element_name}")
                    raise
                await self.page.wait_for_timeout(1000)  # Wait before retrying

    async def _retry_type(self, selector, text, field_name, max_retries=3, timeout=10000):
        """Retry typing into an element multiple times"""
        for attempt in range(max_retries):
            try:
                await self.page.locator(selector).first.fill(text, timeout=timeout)
                return True
            except Exception as e:
                print(f"Type attempt {attempt+1} failed for {field_name}: {e}")
                if attempt == max_retries - 1:
                    print(f"All {max_retries} type attempts failed for {field_name}")
                    raise
                await self.page.wait_for_timeout(1000)  # Wait before retrying

    async def _start_entity_formation(self, entity_type, state):
        """Start the entity formation process"""
        try:
            # Set current entity type and state
            self.current_entity_type = entity_type.upper()
            self.current_state = state
            self.current_step = "entity_type_selection"

            # Click on Entity Formation
            await self._click_element("Entity Formation")
            await self.page.wait_for_timeout(5000)

            # Click on Create Order
            await self._click_element("Create Order")
            await self.page.wait_for_timeout(2000)

            # Select entity type
            await self._click_dropdown("Entity Type")
            await self._select_entity_type(entity_type)
            await self.page.wait_for_timeout(2000)

            # Select state
            await self._click_dropdown("State")
            await self._select_state(state)
            await self.page.wait_for_timeout(2000)

            # Handle county selection if needed
            await self._handle_county_selection_if_needed()

            # Click Next
            await self._click_next_button()

            # Update current step
            self.current_step = "entity_name"

            self.speak(f"Started entity formation for {entity_type} in {state}. Please enter entity name.")
            return True
        except Exception as e:
            print(f"Error starting entity formation: {e}")
            self.speak(f"Error starting entity formation: {str(e)}")
            return False

    async def _proceed_to_next_step(self):
        """Proceed to the next step in the entity formation process"""
        try:
            if not self.current_entity_type or not self.current_state or not self.current_step:
                self.speak("Entity formation process not started. Please start entity formation first.")
                return False

            # Get the steps for the current entity type
            steps = self.formation_steps.get(self.current_entity_type, [])

            # Find the current step index
            try:
                current_index = steps.index(self.current_step)
            except ValueError:
                self.speak(f"Unknown current step: {self.current_step}")
                return False

            # Get the next step
            if current_index + 1 < len(steps):
                next_step = steps[current_index + 1]
            else:
                self.speak("Entity formation process is complete.")
                return True

            # Execute the next step
            self.speak(f"Proceeding to {next_step.replace('_', ' ')} step...")

            # Click Next button to proceed
            await self._click_next_button()

            # Update current step
            self.current_step = next_step

            # Provide guidance for the next step
            if next_step == "entity_name":
                self.speak("Please enter entity name.")
            elif next_step == "principal_address":
                self.speak("Please select principal address.")
            elif next_step == "registered_agent":
                self.speak("Please select registered agent.")
            elif next_step == "purpose":
                self.speak("Please enter business purpose.")
            elif next_step == "incorporator" or next_step == "organizer":
                self.speak(f"Please select {next_step}.")
            elif next_step == "shares":
                self.speak("Please enter number of shares.")
            elif next_step == "member_manager":
                self.speak("Please select member or manager.")
            elif next_step == "naics_code":
                self.speak("Please enter NAICS code.")
            elif next_step == "billing_shipping":
                self.speak("Please select billing and shipping address.")
            elif next_step == "submit":
                self.speak("Please submit the form.")
            elif next_step == "payment":
                self.speak("Please enter payment information.")

            return True
        except Exception as e:
            print(f"Error proceeding to next step: {e}")
            self.speak(f"Error proceeding to next step: {str(e)}")
            return False

    async def _click_element(self, element_name):
        """Click an element by name"""
        try:
            # First try using JavaScript to find and click the element
            clicked = await self.page.evaluate("""(elementName) => {
                // Function to find elements containing text
                const findElementsByText = (searchText) => {
                    const elements = [];

                    // Standard HTML elements
                    const allElements = document.querySelectorAll('a, button, div, span, li, td, th');
                    for (const el of allElements) {
                        if (el.textContent.toLowerCase().includes(searchText.toLowerCase())) {
                            elements.push(el);
                        }
                    }

                    // PrimeNG/PrimeReact specific elements
                    const primeElements = document.querySelectorAll(
                        '.p-button, .p-button-label, .p-menuitem, .p-menuitem-text, .p-menuitem-link'
                    );

                    for (const el of primeElements) {
                        if (el.textContent.toLowerCase().includes(searchText.toLowerCase())) {
                            // For elements with text but that might not be clickable themselves,
                            // try to find the closest clickable parent
                            if (el.classList.contains('p-button-label') ||
                                el.classList.contains('p-menuitem-text')) {

                                const clickableParent = el.closest('.p-button, .p-menuitem, .p-menuitem-link');
                                if (clickableParent) {
                                    elements.push(clickableParent);
                                    continue;
                                }
                            }

                            elements.push(el);
                        }
                    }

                    return elements;
                };

                // Find elements containing the text
                const elements = findElementsByText(elementName);
                console.log(`Found ${elements.length} elements containing "${elementName}"`);

                // Click the first one found
                if (elements.length > 0) {
                    console.log(`Clicking element with text: ${elements[0].textContent}`);
                    elements[0].click();
                    return true;
                }

                return false;
            }""", element_name)

            if clicked:
                self.speak(f"Clicked on {element_name}")
                await self.page.wait_for_timeout(2000)
                return True

            # If JavaScript didn't work, try with selectors
            context = await self._get_page_context()
            element_selectors = await self._get_llm_selectors(f"find {element_name}", context)

            for selector in element_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_click(selector, element_name)
                        self.speak(f"Clicked on {element_name}")
                        await self.page.wait_for_timeout(2000)
                        return True
                except Exception as e:
                    print(f"Error with selector {selector} for {element_name}: {e}")
                    continue

            self.speak(f"Could not find {element_name}")
            return False
        except Exception as e:
            print(f"Error clicking element {element_name}: {e}")
            self.speak(f"Error clicking {element_name}")
            return False

    async def _click_dropdown(self, dropdown_name):
        """Click a dropdown by name"""
        try:
            # Map common dropdown names to more specific identifiers
            dropdown_mapping = {
                "entity type": "Entity Type",
                "state": "State of Formation",
                "state of formation": "State of Formation",
                "principal address": "Principal Address",
                "registered agent": "Registered Agent",
                "billing": "Billing Address",
                "shipping": "Shipping Address"
            }

            # Normalize the dropdown name
            normalized_name = dropdown_name.lower()
            specific_name = dropdown_mapping.get(normalized_name, dropdown_name)

            # Try to find and click the dropdown using JavaScript
            clicked = await self.page.evaluate("""(dropdownName) => {
                console.log(`Looking for dropdown: ${dropdownName}`);

                // Function to find dropdown elements
                const findDropdowns = () => {
                    const dropdowns = [];

                    // Find PrimeNG/PrimeReact dropdowns
                    const primeDropdowns = document.querySelectorAll('.p-dropdown');
                    console.log(`Found ${primeDropdowns.length} PrimeNG/PrimeReact dropdowns`);

                    // Find dropdown labels
                    const labels = document.querySelectorAll('label');
                    console.log(`Found ${labels.length} labels`);

                    // Check each label to see if it contains the dropdown name
                    for (const label of labels) {
                        if (label.textContent.toLowerCase().includes(dropdownName.toLowerCase())) {
                            console.log(`Found label with text: ${label.textContent}`);

                            // Try to find the dropdown associated with this label
                            const forAttr = label.getAttribute('for');
                            if (forAttr) {
                                const dropdown = document.getElementById(forAttr);
                                if (dropdown) {
                                    dropdowns.push(dropdown);
                                    continue;
                                }
                            }

                            // Try to find a dropdown in the parent element
                            const parent = label.parentElement;
                            if (parent) {
                                const parentDropdowns = parent.querySelectorAll('.p-dropdown');
                                if (parentDropdowns.length > 0) {
                                    dropdowns.push(parentDropdowns[0]);
                                    continue;
                                }
                            }

                            // Try to find a dropdown in the siblings
                            const siblings = Array.from(label.parentElement?.children || []);
                            for (const sibling of siblings) {
                                if (sibling !== label) {
                                    const siblingDropdowns = sibling.querySelectorAll('.p-dropdown');
                                    if (siblingDropdowns.length > 0) {
                                        dropdowns.push(siblingDropdowns[0]);
                                        break;
                                    }
                                }
                            }
                        }
                    }

                    // If no dropdowns found by label, try to find by placeholder text
                    if (dropdowns.length === 0) {
                        for (const dropdown of primeDropdowns) {
                            const placeholder = dropdown.querySelector('.p-dropdown-label');
                            if (placeholder && placeholder.textContent.toLowerCase().includes(dropdownName.toLowerCase())) {
                                dropdowns.push(dropdown);
                            }
                        }
                    }

                    // If still no dropdowns found, return all dropdowns
                    if (dropdowns.length === 0) {
                        return Array.from(primeDropdowns);
                    }

                    return dropdowns;
                };

                // Find dropdowns
                const dropdowns = findDropdowns();
                console.log(`Found ${dropdowns.length} potential dropdowns for ${dropdownName}`);

                // Special case for "State" dropdown - it's usually the second dropdown
                if (dropdownName.toLowerCase().includes('state') && dropdowns.length > 1) {
                    console.log(`Clicking the second dropdown for State`);
                    dropdowns[1].click();
                    return true;
                }

                // Click the first dropdown found
                if (dropdowns.length > 0) {
                    console.log(`Clicking dropdown: ${dropdownName}`);
                    dropdowns[0].click();
                    return true;
                }

                return false;
            }""", specific_name)

            if clicked:
                self.speak(f"Clicked on {dropdown_name} dropdown")
                await self.page.wait_for_timeout(2000)
                return True

            # If JavaScript didn't work, try with selectors
            context = await self._get_page_context()
            dropdown_selectors = await self._get_llm_selectors(f"find {specific_name} dropdown", context)

            # Add fallback selectors
            fallback_selectors = [
                f"//label[contains(text(), '{specific_name}')]/following-sibling::span//div[contains(@class, 'p-dropdown')]",
                f"//div[contains(@class, 'p-dropdown-label') and contains(text(), '{specific_name}')]",
                f"//div[contains(@class, 'p-dropdown') and .//span[contains(text(), '{specific_name}')]]",
                ".p-dropdown"
            ]

            # Special case for State dropdown - it's usually the second dropdown
            if normalized_name in ["state", "state of formation"]:
                try:
                    # Try to click the second dropdown
                    dropdowns = await self.page.locator(".p-dropdown").all()
                    if len(dropdowns) > 1:
                        await dropdowns[1].click()
                        self.speak(f"Clicked on {dropdown_name} dropdown (second dropdown)")
                        await self.page.wait_for_timeout(2000)
                        return True
                except Exception as e:
                    print(f"Error clicking second dropdown for State: {e}")

            for selector in dropdown_selectors + fallback_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_click(selector, f"{dropdown_name} dropdown")
                        self.speak(f"Clicked on {dropdown_name} dropdown")
                        await self.page.wait_for_timeout(2000)
                        return True
                except Exception as e:
                    print(f"Error with selector {selector} for {dropdown_name} dropdown: {e}")
                    continue

            self.speak(f"Could not find {dropdown_name} dropdown")
            return False
        except Exception as e:
            print(f"Error clicking dropdown {dropdown_name}: {e}")
            self.speak(f"Error clicking {dropdown_name} dropdown")
            return False

    async def _select_entity_type(self, entity_type):
        """Select an entity type from the dropdown"""
        try:
            # Normalize entity type
            entity_type = entity_type.upper()

            # Map common entity type names
            entity_type_mapping = {
                "LLC": "LLC",
                "CORP": "CORP",
                "CORPORATION": "CORP",
                "INC": "CORP",
                "INCORPORATED": "CORP",
                "LIMITED LIABILITY COMPANY": "LLC"
            }

            # Get the normalized entity type
            normalized_type = entity_type_mapping.get(entity_type, entity_type)

            # Try to select the entity type using JavaScript
            selected = await self.page.evaluate("""(entityType) => {
                console.log(`Selecting entity type: ${entityType}`);

                // Find dropdown items
                const items = document.querySelectorAll('.p-dropdown-item');
                console.log(`Found ${items.length} dropdown items`);

                // Find the item with the matching text
                for (const item of items) {
                    if (item.textContent.toUpperCase().includes(entityType)) {
                        console.log(`Found entity type: ${item.textContent}`);
                        item.click();
                        return true;
                    }
                }

                return false;
            }""", normalized_type)

            if selected:
                self.current_entity_type = normalized_type
                self.speak(f"Selected entity type: {normalized_type}")
                await self.page.wait_for_timeout(2000)
                return True

            # If JavaScript didn't work, try with selectors
            entity_type_selector = f"//li[contains(@class, 'p-dropdown-item') and contains(text(), '{normalized_type}')]"

            try:
                if await self.page.locator(entity_type_selector).count() > 0:
                    await self._retry_click(entity_type_selector, f"entity type {normalized_type}")
                    self.current_entity_type = normalized_type
                    self.speak(f"Selected entity type: {normalized_type}")
                    await self.page.wait_for_timeout(2000)
                    return True
            except Exception as e:
                print(f"Error with selector for entity type {normalized_type}: {e}")

            self.speak(f"Could not find entity type: {normalized_type}")
            return False
        except Exception as e:
            print(f"Error selecting entity type {entity_type}: {e}")
            self.speak(f"Error selecting entity type: {entity_type}")
            return False

    async def _select_state(self, state):
        """Select a state from the dropdown"""
        try:
            # Normalize state name
            state = state.strip()

            # Try to select the state using JavaScript
            selected = await self.page.evaluate("""(stateName) => {
                console.log(`Selecting state: ${stateName}`);

                // Find dropdown items
                const items = document.querySelectorAll('.p-dropdown-item');
                console.log(`Found ${items.length} dropdown items`);

                // Find the item with the matching text
                for (const item of items) {
                    if (item.textContent.toLowerCase().includes(stateName.toLowerCase())) {
                        console.log(`Found state: ${item.textContent}`);
                        item.click();
                        return true;
                    }
                }

                return false;
            }""", state)

            if selected:
                self.current_state = state
                self.speak(f"Selected state: {state}")
                await self.page.wait_for_timeout(2000)
                return True

            # If JavaScript didn't work, try with selectors
            state_selector = f"//li[contains(@class, 'p-dropdown-item') and contains(text(), '{state}')]"

            try:
                if await self.page.locator(state_selector).count() > 0:
                    await self._retry_click(state_selector, f"state {state}")
                    self.current_state = state
                    self.speak(f"Selected state: {state}")
                    await self.page.wait_for_timeout(2000)
                    return True
            except Exception as e:
                print(f"Error with selector for state {state}: {e}")

            self.speak(f"Could not find state: {state}")
            return False
        except Exception as e:
            print(f"Error selecting state {state}: {e}")
            self.speak(f"Error selecting state: {state}")
            return False

    async def _handle_county_selection_if_needed(self):
        """Handle county selection if needed"""
        try:
            # Check if county dropdown is visible
            county_dropdown = "//label[contains(text(), 'County')]/following-sibling::span//div[contains(@class, 'p-dropdown')]"

            if await self.page.locator(county_dropdown).count() > 0:
                await self._retry_click(county_dropdown, "County dropdown")
                await self.page.wait_for_timeout(1000)

                # Select the first county option
                option_selector = ".p-dropdown-item:first-child"
                if await self.page.locator(option_selector).count() > 0:
                    await self._retry_click(option_selector, "first county option")
                    self.speak("Selected county")
                    return True
                else:
                    self.speak("Could not find county option")
                    return False
            else:
                # No county dropdown found, which is fine
                return True

        except Exception as e:
            print(f"Error handling county selection: {e}")
            return False

    async def _click_next_button(self):
        """Click the Next button"""
        try:
            # Try to find and click the Next button
            next_selectors = [
                "button:has-text('Next')",
                ".p-button:has-text('Next')",
                "button.next-button",
                "button[type='submit']:has-text('Next')"
            ]

            for selector in next_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_click(selector, "Next button")
                        self.speak("Clicked Next button")
                        await self.page.wait_for_timeout(2000)
                        return True
                except Exception as e:
                    print(f"Error with Next button selector {selector}: {e}")
                    continue

            # If selectors didn't work, try JavaScript
            clicked = await self.page.evaluate("""() => {
                // Try to find the Next button
                const nextButtons = Array.from(document.querySelectorAll('button'))
                    .filter(button => button.textContent.toLowerCase().includes('next'));

                if (nextButtons.length > 0) {
                    nextButtons[0].click();
                    return true;
                }

                return false;
            }""")

            if clicked:
                self.speak("Clicked Next button using JavaScript")
                await self.page.wait_for_timeout(2000)
                return True
            else:
                self.speak("Could not find Next button")
                return False

        except Exception as e:
            print(f"Error clicking Next button: {e}")
            return False

    async def _enter_entity_name(self, name):
        """Enter the entity name"""
        try:
            # Try to find and fill the entity name field
            entity_name_selectors = [
                "input[placeholder*='Entity Name']",
                "input[aria-label*='Entity Name']",
                "input[name*='entityName']",
                "input.entity-name",
                "#entity_name",
                "input[type='text']"
            ]

            for selector in entity_name_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_type(selector, name, "entity name")
                        self.entity_name = name
                        self.speak(f"Entered entity name: {name}")
                        return True
                except Exception as e:
                    print(f"Error with entity name selector {selector}: {e}")
                    continue

            # If selectors didn't work, try JavaScript
            filled = await self.page.evaluate("""(entityName) => {
                console.log(`Entering entity name: ${entityName}`);

                // Find input fields
                const inputs = document.querySelectorAll('input[type="text"]');
                console.log(`Found ${inputs.length} text input fields`);

                // Try to find the entity name field
                for (const input of inputs) {
                    // Check if this might be the entity name field
                    const placeholder = input.getAttribute('placeholder') || '';
                    const label = input.getAttribute('aria-label') || '';
                    const name = input.getAttribute('name') || '';

                    if (placeholder.toLowerCase().includes('entity') ||
                        label.toLowerCase().includes('entity') ||
                        name.toLowerCase().includes('entity') ||
                        placeholder.toLowerCase().includes('name') ||
                        label.toLowerCase().includes('name') ||
                        name.toLowerCase().includes('name')) {

                        console.log(`Found entity name field: ${placeholder || label || name}`);
                        input.value = entityName;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }
                }

                // If no specific field found, try the first input field
                if (inputs.length > 0) {
                    console.log(`Using first input field as entity name field`);
                    inputs[0].value = entityName;
                    inputs[0].dispatchEvent(new Event('input', { bubbles: true }));
                    inputs[0].dispatchEvent(new Event('change', { bubbles: true }));
                    return true;
                }

                return false;
            }""", name)

            if filled:
                self.entity_name = name
                self.speak(f"Entered entity name: {name}")
                return True
            else:
                self.speak("Could not find entity name field")
                return False

        except Exception as e:
            print(f"Error entering entity name: {e}")
            self.speak(f"Error entering entity name: {str(e)}")
            return False

    async def _enter_field_value(self, value, field_type):
        """Enter a value into a field"""
        try:
            # Define selectors for different field types
            field_selectors = {
                "address_line1": {
                    "selectors": [
                        "#floating_outlined2100",
                        "input[name='cityName1']",
                        "input[aria-label='Address Line 1']",
                        "input[placeholder*='Address Line 1']"
                    ],
                    "label": "Address Line 1"
                },
                "address_line2": {
                    "selectors": [
                        "#floating_outlined22",
                        "input[name='cityName2']",
                        "input[aria-label='Address Line 2']",
                        "input[placeholder*='Address Line 2']"
                    ],
                    "label": "Address Line 2"
                },
                "city": {
                    "selectors": [
                        "#floating_outlined2401",
                        "input[name='city']",
                        "input[aria-label='City']",
                        "input[placeholder*='City']"
                    ],
                    "label": "City"
                },
                "zip": {
                    "selectors": [
                        "#floating_outlined2601",
                        "input[name='zipCode']",
                        "input[aria-label='Zip Code']",
                        "input[placeholder*='Zip']",
                        "input[maxlength='5']"
                    ],
                    "label": "Zip Code"
                },
                "purpose": {
                    "selectors": [
                        "textarea[name='purpose']",
                        "textarea[aria-label='Purpose']",
                        "textarea[placeholder*='Purpose']",
                        "input[name='purpose']",
                        "input[aria-label='Purpose']",
                        "input[placeholder*='Purpose']"
                    ],
                    "label": "Purpose"
                },
                "shares": {
                    "selectors": [
                        "input[name='shares']",
                        "input[id*='Share']",
                        "input[aria-label*='Share']",
                        "input[placeholder*='Share']"
                    ],
                    "label": "Number of Shares"
                },
                "shares_par_value": {
                    "selectors": [
                        "input[name='shareParValue']",
                        "input[id*='Par']",
                        "input[aria-label*='Par Value']",
                        "input[placeholder*='Par Value']"
                    ],
                    "label": "Shares Par Value"
                },
                "naics_code": {
                    "selectors": [
                        "input[name='naicsCode']",
                        "input[aria-label='NAICS Code']",
                        "input[placeholder*='NAICS Code']",
                        "input[id*='naics']",
                        "input[id*='NAICS']"
                    ],
                    "label": "NAICS Code"
                }
            }

            # Get the selectors for the specified field type
            field_info = field_selectors.get(field_type)
            if not field_info:
                self.speak(f"Unknown field type: {field_type}")
                return False

            # Try each selector
            for selector in field_info["selectors"]:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_type(selector, value, field_info["label"])
                        self.speak(f"Entered {value} in {field_info['label']} field")
                        return True
                except Exception as e:
                    print(f"Error with selector {selector} for {field_info['label']}: {e}")
                    continue

            # If selectors didn't work, try JavaScript
            filled = await self.page.evaluate("""(fieldType, value, fieldLabel) => {
                console.log(`Entering ${value} in ${fieldLabel} field`);

                // Find input and textarea fields
                const inputs = document.querySelectorAll('input, textarea');
                console.log(`Found ${inputs.length} input/textarea fields`);

                // Try to find the field by label
                const labels = document.querySelectorAll('label');
                for (const label of labels) {
                    if (label.textContent.toLowerCase().includes(fieldLabel.toLowerCase())) {
                        console.log(`Found label: ${label.textContent}`);

                        // Try to find the input associated with this label
                        const forAttr = label.getAttribute('for');
                        if (forAttr) {
                            const input = document.getElementById(forAttr);
                            if (input) {
                                input.value = value;
                                input.dispatchEvent(new Event('input', { bubbles: true }));
                                input.dispatchEvent(new Event('change', { bubbles: true }));
                                return true;
                            }
                        }

                        // Try to find an input in the parent element
                        const parent = label.parentElement;
                        if (parent) {
                            const parentInputs = parent.querySelectorAll('input, textarea');
                            if (parentInputs.length > 0) {
                                parentInputs[0].value = value;
                                parentInputs[0].dispatchEvent(new Event('input', { bubbles: true }));
                                parentInputs[0].dispatchEvent(new Event('change', { bubbles: true }));
                                return true;
                            }
                        }

                        // Try to find an input in the siblings
                        const siblings = Array.from(label.parentElement?.children || []);
                        for (const sibling of siblings) {
                            if (sibling !== label) {
                                const siblingInputs = sibling.querySelectorAll('input, textarea');
                                if (siblingInputs.length > 0) {
                                    siblingInputs[0].value = value;
                                    siblingInputs[0].dispatchEvent(new Event('input', { bubbles: true }));
                                    siblingInputs[0].dispatchEvent(new Event('change', { bubbles: true }));
                                    return true;
                                }
                            }
                        }
                    }
                }

                return false;
            }""", field_type, value, field_info["label"])

            if filled:
                self.speak(f"Entered {value} in {field_info['label']} field")
                return True
            else:
                self.speak(f"Could not find {field_info['label']} field")
                return False

        except Exception as e:
            print(f"Error entering field value: {e}")
            self.speak(f"Error entering value in {field_type} field: {str(e)}")
            return False

    async def _select_person_for_role(self, role):
        """Select a person for a specific role"""
        try:
            # Click the dropdown for the role
            role_dropdown = f"//label[contains(text(), '{role}')]/following-sibling::span//div[contains(@class, 'p-dropdown')]"

            if await self.page.locator(role_dropdown).count() > 0:
                await self._retry_click(role_dropdown, f"{role} dropdown")
                await self.page.wait_for_timeout(1000)

                # Select the first option
                option_selector = ".p-dropdown-item:first-child"
                if await self.page.locator(option_selector).count() > 0:
                    await self._retry_click(option_selector, "first person option")
                    self.speak(f"Selected person for {role}")
                    return True
                else:
                    self.speak(f"Could not find person option for {role}")
                    return False
            else:
                # Try JavaScript
                clicked = await self.page.evaluate("""(roleName) => {
                    console.log(`Looking for dropdown for role: ${roleName}`);

                    // Find labels containing the role name
                    const labels = Array.from(document.querySelectorAll('label'));
                    const roleLabel = labels.find(label =>
                        label.textContent.toLowerCase().includes(roleName.toLowerCase()));

                    if (roleLabel) {
                        console.log(`Found label for role: ${roleLabel.textContent}`);

                        // Try to find the dropdown in the parent element
                        const parent = roleLabel.parentElement;
                        if (parent) {
                            const dropdowns = parent.querySelectorAll('.p-dropdown');
                            if (dropdowns.length > 0) {
                                console.log(`Found dropdown for role: ${roleName}`);
                                dropdowns[0].click();

                                // Wait a bit for the dropdown to open
                                setTimeout(() => {
                                    // Select the first option
                                    const options = document.querySelectorAll('.p-dropdown-item');
                                    if (options.length > 0) {
                                        options[0].click();
                                        console.log(`Selected first option for role: ${roleName}`);
                                    }
                                }, 500);

                                return true;
                            }
                        }
                    }

                    return false;
                }""", role)

                if clicked:
                    self.speak(f"Selected person for {role}")
                    await self.page.wait_for_timeout(2000)
                    return True
                else:
                    self.speak(f"Could not find dropdown for {role}")
                    return False

        except Exception as e:
            print(f"Error selecting person for {role}: {e}")
            self.speak(f"Error selecting person for {role}: {str(e)}")
            return False

    async def _submit_form(self):
        """Submit the form"""
        try:
            # Try to find and click the Submit button
            submit_selectors = [
                "button:has-text('Submit')",
                ".p-button:has-text('Submit')",
                "button[type='submit']"
            ]

            for selector in submit_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_click(selector, "Submit button")
                        self.speak("Submitted form")
                        await self.page.wait_for_timeout(2000)
                        return True
                except Exception as e:
                    print(f"Error with Submit button selector {selector}: {e}")
                    continue

            # If selectors didn't work, try JavaScript
            clicked = await self.page.evaluate("""() => {
                // Try to find the Submit button
                const submitButtons = Array.from(document.querySelectorAll('button'))
                    .filter(button => button.textContent.toLowerCase().includes('submit'));

                if (submitButtons.length > 0) {
                    submitButtons[0].click();
                    return true;
                }

                return false;
            }""")

            if clicked:
                self.speak("Submitted form using JavaScript")
                await self.page.wait_for_timeout(2000)
                return True
            else:
                self.speak("Could not find Submit button")
                return False

        except Exception as e:
            print(f"Error submitting form: {e}")
            self.speak(f"Error submitting form: {str(e)}")
            return False

    async def _confirm_order(self):
        """Confirm the order"""
        try:
            # Try to find and click the Confirm button
            confirm_selectors = [
                "button:has-text('Confirm')",
                ".p-button:has-text('Confirm')",
                "button:has-text('Proceed')",
                "button:has-text('Continue')"
            ]

            for selector in confirm_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_click(selector, "Confirm button")
                        self.speak("Confirmed order")
                        await self.page.wait_for_timeout(7000)
                        return True
                except Exception as e:
                    print(f"Error with Confirm button selector {selector}: {e}")
                    continue

            # If selectors didn't work, try JavaScript
            clicked = await self.page.evaluate("""() => {
                // Try to find the Confirm button
                const confirmButtons = Array.from(document.querySelectorAll('button'))
                    .filter(button =>
                        button.textContent.toLowerCase().includes('confirm') ||
                        button.textContent.toLowerCase().includes('proceed') ||
                        button.textContent.toLowerCase().includes('continue'));

                if (confirmButtons.length > 0) {
                    confirmButtons[0].click();
                    return true;
                }

                return false;
            }""")

            if clicked:
                self.speak("Confirmed order using JavaScript")
                await self.page.wait_for_timeout(7000)
                return True
            else:
                self.speak("Could not find Confirm button")
                return False

        except Exception as e:
            print(f"Error confirming order: {e}")
            self.speak(f"Error confirming order: {str(e)}")
            return False

    async def _enter_payment_info(self):
        """Enter payment information"""
        try:
            # Enter card number
            card_number_selector = "input[name='cardNumber'], input[placeholder*='Card'], input[aria-label*='Card']"
            if await self.page.locator(card_number_selector).count() > 0:
                await self._retry_type(card_number_selector, "4111111111111111", "card number")
                self.speak("Entered card number")

            # Enter card holder name
            await self._enter_field_value("John Doe", "name")

            # Enter CVV
            cvv_selector = "input[name='cvv'], input[placeholder*='CVV'], input[aria-label*='CVV']"
            if await self.page.locator(cvv_selector).count() > 0:
                await self._retry_type(cvv_selector, "123", "CVV")
                self.speak("Entered CVV")

            # Enter expiry date
            expiry_selector = "input[name='expiry'], input[placeholder*='Expiry'], input[aria-label*='Expiry']"
            if await self.page.locator(expiry_selector).count() > 0:
                await self._retry_type(expiry_selector, "12/25", "expiry date")
                self.speak("Entered expiry date")

            # Click Pay button
            pay_selectors = [
                "button:has-text('Pay')",
                ".p-button:has-text('Pay')",
                "button[type='submit']"
            ]

            for selector in pay_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_click(selector, "Pay button")
                        self.speak("Clicked Pay button")
                        await self.page.wait_for_timeout(2000)
                        return True
                except Exception as e:
                    print(f"Error with Pay button selector {selector}: {e}")
                    continue

            # If selectors didn't work, try JavaScript
            clicked = await self.page.evaluate("""() => {
                // Try to find the Pay button
                const payButtons = Array.from(document.querySelectorAll('button'))
                    .filter(button =>
                        button.textContent.toLowerCase().includes('pay') ||
                        button.textContent.toLowerCase().includes('submit') ||
                        button.textContent.toLowerCase().includes('process'));

                if (payButtons.length > 0) {
                    payButtons[0].click();
                    return true;
                }

                return false;
            }""")

            if clicked:
                self.speak("Processed payment using JavaScript")
                await self.page.wait_for_timeout(2000)
                return True
            else:
                self.speak("Could not find Pay button")
                return False

        except Exception as e:
            print(f"Error entering payment info: {e}")
            self.speak(f"Error entering payment information: {str(e)}")
            return False

    def show_help(self):
        """Show help information"""
        help_text = """
        🔍 Voice Entity Formation Assistant Help:

        Entity Formation Commands:
        - "Start entity formation for [entity type] in [state]" - Begin entity formation process
        - "Select entity type [LLC/CORP]" - Select the entity type
        - "Select state [state name]" - Select the state of formation
        - "Enter [text] as entity name" - Fill in the entity name field
        - "Enter [text] as purpose" - Fill in the purpose field
        - "Enter [number] for shares" - Fill in the number of shares
        - "Enter [number] for NAICS code" - Fill in the NAICS code
        - "Click next" - Click the next button to proceed
        - "Continue to next step" - Proceed to the next step in the formation process
        - "Select person for [role]" - Select a person for a specific role
        - "Submit form" - Submit the entity formation form
        - "Confirm order" - Confirm the entity formation order
        - "Enter payment information" - Fill in payment details

        Address Form Commands:
        - "Enter [text] in address line 1" - Fill in the first address line
        - "Enter [text] in address line 2" - Fill in the second address line
        - "Enter [text] in city" - Fill in the city field
        - "Enter [text] in zip code" - Fill in the zip code field

        Navigation Commands:
        - "Go to [website]" - Navigate to a website
        - "Click on [element]" - Click on a specific element
        - "Click [dropdown] dropdown" - Open a dropdown menu

        General Commands:
        - "Help" - Show this help message
        - "Exit" or "Quit" - Close the assistant
        """
        print(help_text)
        self.speak("Here's the help information. You can see the full list on screen.")

async def main():
    """Main entry point"""
    assistant = VoiceAssistantEntityFormation()
    await assistant.initialize()

    try:
        # Main loop
        running = True
        while running:
            # Get command from user
            command = input("USER: ")
            print(f"DEBUG: Processing command: '{command}'")

            # Process command
            running = await assistant.process_command(command)
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close assistant
        await assistant.close(keep_browser_open=True)

if __name__ == "__main__":
    asyncio.run(main())