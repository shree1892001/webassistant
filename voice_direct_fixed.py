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

class VoiceAssistant:
    def __init__(self, config=None):
        self.engine = None
        self.llm_provider = None
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        # Use provided config or create default
        self.config = config or AssistantConfig.from_env()

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
        # Simple login pattern - similar to original Voice.py
        login_match = re.search(r'login with email\s+(\S+)\s+and password\s+(\S+)', command, re.IGNORECASE)

        # More flexible login patterns if the simple one doesn't match
        if not login_match:
            # Try more flexible patterns for login
            login_patterns = [
                r'log[a-z]* w[a-z]* (?:email|email address)?\s+(\S+)\s+[a-z]* (?:password|pass|p[a-z]*)\s+(\S+)',
                r'login\s+(?:with|using|w[a-z]*)\s+(?:email|email address)?\s*(\S+)\s+(?:and|with|[a-z]*)\s+(?:password|pass|p[a-z]*)\s*(\S+)',
                r'(?:login|sign in|signin)\s+(?:with|using|w[a-z]*)?\s*(?:email|username)?\s*(\S+)\s+(?:and|with|[a-z]*)\s*(?:password|pass|p[a-z]*)?\s*(\S+)',
                r'log[a-z]*.*?(\S+@\S+).*?(\S+)'
            ]

            for pattern in login_patterns:
                login_match = re.search(pattern, command, re.IGNORECASE)
                if login_match:
                    break

        if login_match:
            email, password = login_match.groups()
            self.speak("Logging in with email and password...")

            url = self.page.url
            if not ('signin' in url or 'login' in url):
                self.speak("Navigating to signin page first...")
                # Navigate to the correct signin URL
                try:
                    await self.page.goto("https://www.redberyltest.in/#/signin", wait_until="networkidle", timeout=20000)
                    self.speak("Navigated to signin page")
                    # Wait for the page to load
                    await self.page.wait_for_timeout(5000)
                except Exception as e:
                    self.speak(f"Failed to navigate to signin page: {str(e)}")
                    return False

            # Now we should be on the login page
            self.speak("Found login page. Looking for login form...")
            # Try to find and click login button if needed
            login_selectors = await self._get_llm_selectors("find login or sign in link or button", await self._get_page_context())
            fallback_login_selectors = [
                'a:has-text("Login")',
                'a:has-text("Sign in")',
                'button:has-text("Login")',
                'button:has-text("Sign in")',
                '.login-button',
                '.signin-button',
                'button.blue-btnnn:has-text("Login/Register")',
                'a:has-text("Login/Register")'
            ]

            for selector in login_selectors + fallback_login_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self.page.locator(selector).first.click()
                        self.speak("Found and clicked login option. Waiting for form to appear...")
                        await self.page.wait_for_timeout(5000)  # Wait for form to appear
                        break
                except Exception:
                    continue

            # Perform DOM inspection to find form elements
            form_elements = await self._check_for_input_fields()
            print(f"DOM inspection results: {form_elements}")

            # Get page context after potential navigation
            context = await self._get_page_context()

            # Define specific selectors for known form elements
            specific_email_selector = '#floating_outlined3'
            specific_password_selector = '#floating_outlined15'
            specific_button_selector = '#signInButton'

            if form_elements.get('hasEmailField') or form_elements.get('hasPasswordField'):
                try:
                    # Use JavaScript to fill the form directly
                    self.speak("Using direct DOM manipulation to fill login form...")
                    js_result = await self.page.evaluate(f"""() => {{
                        try {{
                            console.log("Starting form fill process...");

                            // Try to find email field
                            const emailField = document.getElementById('floating_outlined3');
                            if (emailField) {{
                                emailField.value = "{email}";
                                emailField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                emailField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                console.log("Email field filled with:", "{email}");
                            }} else {{
                                console.log("Email field not found");
                                return {{ success: false, error: "Email field not found" }};
                            }}

                            // Try to find password field
                            const passwordField = document.getElementById('floating_outlined15');
                            if (passwordField) {{
                                passwordField.value = "{password}";
                                passwordField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                passwordField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                console.log("Password field filled with:", "{password}");
                            }} else {{
                                console.log("Password field not found");
                                return {{ success: false, error: "Password field not found" }};
                            }}

                            // Try to find submit button
                            const submitButton = document.getElementById('signInButton');
                            if (submitButton) {{
                                submitButton.click();
                                console.log("Submit button clicked");
                            }} else {{
                                console.log("Submit button not found");
                                return {{ success: true, warning: "Form filled but submit button not found" }};
                            }}

                            return {{ success: true }};
                        }} catch (error) {{
                            console.error("Error in form fill:", error);
                            return {{ success: false, error: error.toString() }};
                        }}
                    }}""")

                    print(f"JavaScript form fill result: {js_result}")
                    if js_result.get('success'):
                        self.speak("Login form submitted using direct DOM manipulation")
                        return True
                    else:
                        print(f"JavaScript form fill failed: {js_result.get('error')}")
                except Exception as e:
                    print(f"Error with JavaScript form fill: {e}")

            # Try specific selectors first
            email_found = False
            try:
                # Check if specific email selector exists
                if await self.page.locator(specific_email_selector).count() > 0:
                    await self._retry_type(specific_email_selector, email, "email address")
                    email_found = True
                    print(f"Found email field with specific selector: {specific_email_selector}")
            except Exception as e:
                print(f"Error with specific email selector: {e}")

            # If specific selector didn't work, try LLM-generated selectors
            if not email_found:
                email_selectors = await self._get_llm_selectors("find email or username input field", context)
                # Add fallback selectors
                fallback_email_selectors = [
                    'input[type="email"]',
                    'input[name="email"]',
                    'input[id*="email"]',
                    'input[placeholder*="email"]',
                    'input[type="text"][name*="user"]',
                    'input[id*="user"]',
                    'input',  # Generic fallback
                    'input[type="text"]',
                    'form input:first-child',
                    'form input'
                ]

                for selector in email_selectors + fallback_email_selectors:
                    try:
                        if await self.page.locator(selector).count() > 0:
                            await self._retry_type(selector, email, "email address")
                            email_found = True
                            break
                    except Exception as e:
                        print(f"Error with email selector {selector}: {e}")
                        continue

            # Try specific password selector first
            password_found = False
            try:
                # Check if specific password selector exists
                if await self.page.locator(specific_password_selector).count() > 0:
                    await self._retry_type(specific_password_selector, password, "password")
                    password_found = True
                    print(f"Found password field with specific selector: {specific_password_selector}")
            except Exception as e:
                print(f"Error with specific password selector: {e}")

            # If specific selector didn't work, try LLM-generated selectors
            if not password_found:
                password_selectors = await self._get_llm_selectors("find password input field", context)
                # Add fallback selectors
                fallback_password_selectors = [
                    'input[type="password"]',
                    'input[name="password"]',
                    'input[id*="password"]',
                    'input[placeholder*="password"]',
                    'input.password',
                    '#password',
                    'form input[type="password"]',
                    'form input:nth-child(2)'
                ]

                for selector in password_selectors + fallback_password_selectors:
                    try:
                        if await self.page.locator(selector).count() > 0:
                            await self._retry_type(selector, password, "password")
                            password_found = True
                            break
                    except Exception as e:
                        print(f"Error with password selector {selector}: {e}")
                        continue

            # Try to click the login button if both fields were found
            if email_found and password_found:
                # Try specific button selector first
                button_clicked = False
                try:
                    if await self.page.locator(specific_button_selector).count() > 0:
                        await self._retry_click(specific_button_selector, "Submit login form")
                        button_clicked = True
                        print(f"Clicked button with specific selector: {specific_button_selector}")
                except Exception as e:
                    print(f"Error with specific button selector: {e}")

                # If specific selector didn't work, try LLM-generated selectors
                if not button_clicked:
                    login_button_selectors = await self._get_llm_selectors("find login or sign in button", context)
                    # Add fallback selectors
                    fallback_button_selectors = [
                        'button[type="submit"]',
                        'input[type="submit"]',
                        'button:has-text("Login")',
                        'button:has-text("Sign in")',
                        'button:has-text("Submit")',
                        '.login-button',
                        '.signin-button',
                        '.submit-button',
                        'button',
                        'input[type="button"]'
                    ]

                    for selector in login_button_selectors + fallback_button_selectors:
                        try:
                            if await self.page.locator(selector).count() > 0:
                                await self._retry_click(selector, "Submit login form")
                                button_clicked = True
                                break
                        except Exception as e:
                            print(f"Error with button selector {selector}: {e}")
                            continue

                if not button_clicked:
                    self.speak("Filled login details but couldn't find login button")

                return True
            else:
                if not email_found:
                    self.speak("Could not find element to Enter email address")
                if not password_found:
                    self.speak("Could not find element to Enter password")
                return False

        search_match = re.search(r'search(?:\s+for)?\s+(.+)', command, re.IGNORECASE)
        if search_match:
            query = search_match.group(1)

            # First try using the LLM to generate actions
            context = await self._get_page_context()

            # Create a specific command for the LLM
            action_data = await self.llm_provider.get_actions(f"search for {query}", context)

            if 'actions' in action_data and len(action_data['actions']) > 0:
                # Try to execute the LLM-generated actions
                success = await self._execute_actions(action_data)
                if success:
                    return True
                else:
                    self.speak("LLM-generated actions failed, trying fallback methods...")

            # If LLM actions failed, try with JavaScript injection first
            self.speak("Trying JavaScript injection for search query...")
            try:
                # Use JavaScript to find and fill the search input
                search_result = await self.page.evaluate("""(searchQuery) => {
                    console.log("Searching for search input field...");

                    // Try common search input selectors
                    const searchSelectors = [
                        'input[type="search"]',
                        'input[name="search"]',
                        'input[placeholder*="search" i]',
                        'input[aria-label*="search" i]',
                        '.search-input',
                        '#search',
                        'input.form-control',
                        'input[type="text"]',
                        '.App input[type="text"]'
                    ];

                    // Try each selector
                    for (const selector of searchSelectors) {
                        const searchInputs = document.querySelectorAll(selector);
                        console.log(`Found ${searchInputs.length} elements matching selector: ${selector}`);

                        if (searchInputs.length > 0) {
                            // Use the first matching input
                            const searchInput = searchInputs[0];
                            console.log(`Using search input: ${selector}`);

                            // Fill the input
                            searchInput.value = searchQuery;
                            searchInput.dispatchEvent(new Event('input', { bubbles: true }));
                            searchInput.dispatchEvent(new Event('change', { bubbles: true }));

                            // Try to submit the form if the input is in a form
                            const form = searchInput.closest('form');
                            if (form) {
                                console.log("Found parent form, submitting it");
                                form.dispatchEvent(new Event('submit', { bubbles: true }));
                                return { success: true, message: "Submitted search form" };
                            }

                            // If no form, try to press Enter
                            console.log("No parent form found, simulating Enter key");
                            searchInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', bubbles: true }));
                            searchInput.dispatchEvent(new KeyboardEvent('keypress', { key: 'Enter', code: 'Enter', bubbles: true }));
                            searchInput.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', bubbles: true }));

                            return { success: true, message: "Filled search input and simulated Enter key" };
                        }
                    }

                    // If we get here, we couldn't find a search input
                    return { success: false, message: "Could not find search input" };
                }""", query)

                print(f"JavaScript search result: {search_result}")

                if search_result and search_result.get('success'):
                    self.speak(f"🔍 Searching for '{query}'")
                    await self.page.wait_for_timeout(3000)
                    return True
                else:
                    print("JavaScript injection failed:", search_result.get('message', 'Unknown error'))
            except Exception as e:
                print(f"JavaScript injection failed: {e}")

            # If JavaScript injection failed, try with selectors
            search_selectors = await self._get_llm_selectors("find search input field", context)

            # Add some common fallback selectors
            fallback_selectors = [
                'input[type="search"]',
                'input[name="search"]',
                'input[placeholder*="search" i]',
                'input[aria-label*="search" i]',
                '.search-input',
                '#search',
                'input.form-control',
                'input[type="text"]',
                '.App input[type="text"]'
            ]

            # Try all selectors
            for selector in search_selectors + fallback_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        # Increase timeout for typing
                        await self._retry_type(selector, query, "search query", max_retries=5, timeout=60000)
                        await self.page.locator(selector).press("Enter")
                        self.speak(f"🔍 Searching for '{query}'")
                        await self.page.wait_for_timeout(3000)
                        return True
                except Exception as e:
                    print(f"Error with search selector {selector}: {e}")
                    continue

            self.speak("Could not find search field")
            return False

        # Handle specific Principal Address dropdown command
        address_dropdown_match = re.search(r'(?:click|select|open)(?:\s+(?:on|the))?\s+(?:principal(?:\s+address)?|address)(?:\s+dropdown)?', command, re.IGNORECASE)
        if address_dropdown_match:
            self.speak("Looking for principal address dropdown...")
            return await self._click_principal_address_dropdown()

        # Handle specific state dropdown command - make this pattern more robust and handle typos
        state_dropdown_match = re.search(r'(?:cl[ci]?[ck]k?|select|open)(?:\s+(?:on|the))?\s+(?:state(?:\s+of\s+formation)?|formation\s+state|state\s+dropdown)(?:\s+dropdown)?', command, re.IGNORECASE)
        if state_dropdown_match:
            self.speak("Looking for state of formation dropdown...")
            # Use the specialized method for state dropdown
            return await self._click_state_dropdown_direct()

        # Handle regular "click" commands - with typo tolerance
        click_match = re.search(r'cl[ci]?[ck]k?(?:\s+on)?\s+(?:the\s+)?(.+)', command, re.IGNORECASE)
        if click_match:
            element_name = click_match.group(1).strip()
            self.speak(f"Looking for {element_name}...")

            # First try using the LLM to generate actions
            context = await self._get_page_context()

            # Create a specific command for the LLM
            action_data = await self.llm_provider.get_actions(f"click on {element_name}", context)

            if 'actions' in action_data and len(action_data['actions']) > 0:
                # Try to execute the LLM-generated actions
                success = await self._execute_actions(action_data)
                if success:
                    return True
                else:
                    self.speak("LLM-generated actions failed, trying fallback methods...")

            # If LLM actions failed, try with selectors
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

            # Try with more specific selectors
            specific_selectors = await self._get_llm_selectors(f"find {element_name} button, link, or menu item", context)

            for selector in specific_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_click(selector, element_name)
                        self.speak(f"Clicked on {element_name}")
                        await self.page.wait_for_timeout(2000)
                        return True
                except Exception as e:
                    print(f"Error with specific selector {selector} for {element_name}: {e}")
                    continue

            # Try using JavaScript to find and click the element
            try:
                clicked = await self.page.evaluate("""(elementName) => {
                    // Function to find elements containing text
                    const findElementsByText = (text) => {
                        const elements = [];

                        // Standard HTML elements
                        const allElements = document.querySelectorAll('a, button, div, span, li, td, th');
                        for (const el of allElements) {
                            if (el.textContent.toLowerCase().includes(text.toLowerCase())) {
                                elements.push(el);
                            }
                        }

                        // PrimeNG/PrimeReact specific elements
                        const primeElements = document.querySelectorAll(
                            // PrimeNG/PrimeReact buttons
                            '.p-button, .p-button-label, ' +
                            // PrimeNG/PrimeReact menu items
                            '.p-menuitem, .p-menuitem-text, .p-menuitem-link, ' +
                            // PrimeNG/PrimeReact tabs
                            '.p-tabview-nav-link, .p-tabview-title, ' +
                            // PrimeNG/PrimeReact panels
                            '.p-panel-title, .p-panel-header, ' +
                            // PrimeNG/PrimeReact accordions
                            '.p-accordion-header, .p-accordion-header-text'
                        );

                        for (const el of primeElements) {
                            if (el.textContent.toLowerCase().includes(text.toLowerCase())) {
                                // For elements with text but that might not be clickable themselves,
                                // try to find the closest clickable parent
                                if (el.classList.contains('p-button-label') ||
                                    el.classList.contains('p-menuitem-text') ||
                                    el.classList.contains('p-tabview-title') ||
                                    el.classList.contains('p-panel-title') ||
                                    el.classList.contains('p-accordion-header-text')) {

                                    const clickableParent = el.closest('.p-button, .p-menuitem, .p-menuitem-link, .p-tabview-nav-link, .p-panel-header, .p-accordion-header');
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
                    self.speak(f"Found and clicked {element_name} using JavaScript")
                    await self.page.wait_for_timeout(2000)
                    return True
            except Exception as e:
                print(f"Error with JavaScript click for {element_name}: {e}")

            self.speak(f"Could not find {element_name}")
            return False

        # Handle menu item click commands
        menu_click_match = re.search(r'(?:click|select)(?:\s+on)?\s+(?:the\s+)?menu\s+(?:item\s+)?(.+)', command, re.IGNORECASE)
        if menu_click_match:
            menu_item = menu_click_match.group(1).strip()
            self.speak(f"Looking for menu item {menu_item}...")

            # First try using the LLM to generate actions
            context = await self._get_page_context()

            # Create a specific command for the LLM
            action_data = await self.llm_provider.get_actions(f"click on menu item {menu_item}", context)

            if 'actions' in action_data and len(action_data['actions']) > 0:
                # Try to execute the LLM-generated actions
                success = await self._execute_actions(action_data)
                if success:
                    return True
                else:
                    self.speak("LLM-generated actions failed, trying fallback methods...")

            # If LLM actions failed, try with selectors
            menu_selectors = await self._get_llm_selectors(f"find menu item '{menu_item}'", context)

            for selector in menu_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_click(selector, f"menu item '{menu_item}'")
                        self.speak(f"Clicked on menu item {menu_item}")
                        await self.page.wait_for_timeout(2000)
                        return True
                except Exception as e:
                    print(f"Error with menu selector {selector} for {menu_item}: {e}")
                    continue

            # Try using JavaScript to find and click the menu item
            try:
                clicked = await self.page.evaluate("""(menuItem) => {
                    // Function to find menu items containing text
                    const findMenuItems = (text) => {
                        const elements = [];

                        // Standard HTML menu items
                        const menuElements = document.querySelectorAll('a, li, [role="menuitem"], .menu-item, .nav-item');
                        for (const el of menuElements) {
                            if (el.textContent.toLowerCase().includes(text.toLowerCase())) {
                                elements.push(el);
                            }
                        }

                        // PrimeNG/PrimeReact specific menu items
                        const primeMenuItems = document.querySelectorAll(
                            // PrimeNG/PrimeReact menu items
                            '.p-menuitem, .p-menuitem-link, .p-menuitem-text, ' +
                            // PrimeNG/PrimeReact menu bar items
                            '.p-menubar-root-list > li, .p-menubar-root-list > li > a, ' +
                            // PrimeNG/PrimeReact sidebar menu items
                            '.p-sidebar-menu .p-menuitem, .p-sidebar-menu .p-menuitem-link, ' +
                            // PrimeNG/PrimeReact tabmenu items
                            '.p-tabmenu-nav > li, .p-tabmenu-nav > li > a, ' +
                            // PrimeNG/PrimeReact steps items
                            '.p-steps-item, .p-steps-title'
                        );

                        for (const el of primeMenuItems) {
                            if (el.textContent.toLowerCase().includes(text.toLowerCase())) {
                                // For text elements that might not be clickable themselves,
                                // try to find the closest clickable parent
                                if (el.classList.contains('p-menuitem-text') ||
                                    el.classList.contains('p-steps-title')) {

                                    const clickableParent = el.closest('.p-menuitem, .p-menuitem-link, .p-steps-item');
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

                    // Find menu items containing the text
                    const menuItems = findMenuItems(menuItem);
                    console.log(`Found ${menuItems.length} menu items containing "${menuItem}"`);

                    // Click the first one found
                    if (menuItems.length > 0) {
                        console.log(`Clicking menu item with text: ${menuItems[0].textContent}`);
                        menuItems[0].click();
                        return true;
                    }

                    return false;
                }""", menu_item)

                if clicked:
                    self.speak(f"Found and clicked menu item {menu_item} using JavaScript")
                    await self.page.wait_for_timeout(2000)
                    return True
            except Exception as e:
                print(f"Error with JavaScript menu click for {menu_item}: {e}")

            self.speak(f"Could not find menu item {menu_item}")
            return False

        # Handle state selection commands - including "state of formation" and similar phrases
        state_match = re.search(r'(?:select|choose|pick)(?:\s+the)?\s+(?:state|province)(?:\s+of\s+\w+)?\s+["\']?([^"\']+)["\']?', command, re.IGNORECASE)

        # Also handle "click the state dropdown and select X" pattern
        if not state_match:
            state_match = re.search(r'(?:click|select)(?:\s+the)?\s+(?:state|state\s+of\s+\w+)(?:\s+dropdown)?(?:\s+and\s+select)\s+["\']?([^"\']+)["\']?', command, re.IGNORECASE)

        # Handle "search for state X" pattern and "click state dropdown and search for X" pattern
        if not state_match:
            state_match = re.search(r'(?:search|find|look)(?:\s+for)?\s+(?:state|the\s+state)\s+["\']?([^"\']+)["\']?', command, re.IGNORECASE)

        # Handle "click state dropdown and search for X" pattern - with typo tolerance
        if not state_match:
            state_match = re.search(r'(?:cl[ci]?[ck]k?|select|open)(?:\s+the)?\s+(?:state|state\s+of\s+\w+)(?:\s+dropdown)?(?:\s+and\s+(?:search|find|look)(?:\s+for)?)\s+["\']?([^"\']+)["\']?', command, re.IGNORECASE)

        # Handle "search X from the state dropdown" pattern
        if not state_match:
            state_match = re.search(r'(?:search|find|look)(?:\s+for)?\s+([^"\']+)(?:\s+from)(?:\s+the)?\s+(?:state|state\s+of\s+\w+)(?:\s+dropdown)?', command, re.IGNORECASE)

        if state_match:
            state_name = state_match.group(1).strip()
            return await self._handle_state_selection(state_name)

        # Handle "make sure entity formation is selected" and similar commands
        entity_formation_match = re.search(r'(?:make\s+sure|ensure|check|verify|confirm)(?:\s+that)?\s+(?:entity|entity\s+type|entity\s+formation)(?:\s+is)?\s+(?:selected|chosen|picked)', command, re.IGNORECASE)
        if entity_formation_match:
            self.speak("Checking entity type selection...")
            return await self._ensure_entity_type_selected()

        # Handle "select entity type X" commands
        entity_type_match = re.search(r'(?:select|choose|pick)(?:\s+the)?\s+(?:entity|entity\s+type)\s+["\']?([^"\']+)["\']?', command, re.IGNORECASE)
        if entity_type_match:
            entity_type = entity_type_match.group(1).strip()
            self.speak(f"Selecting entity type {entity_type}...")
            return await self._select_entity_type(entity_type)

        # Handle check all products command
        check_all_products_match = re.search(r'(?:check|select|mark)(?:\s+(?:all|every))(?:\s+(?:the|available))?\s+(?:products|services|checkboxes)', command, re.IGNORECASE)
        if check_all_products_match:
            self.speak("Checking all available products...")
            return await self._check_all_products()

        # Handle product checkbox commands
        product_checkbox_match = re.search(r'(?:check|select|mark)(?:\s+the)?\s+(?:product|service)(?:\s+checkbox)?\s+(?:for)?\s*["\']?([^"\']+)["\']?', command, re.IGNORECASE)
        if product_checkbox_match:
            product_name = product_checkbox_match.group(1).strip()
            self.speak(f"Looking for product checkbox for {product_name}...")
            return await self._check_product_checkbox(product_name)

        # Handle checkbox commands
        checkbox_match = re.search(r'(?:check|select|mark)(?:\s+the)?\s+(?:checkbox(?:\s+for)?|option(?:\s+for)?)\s+(.+?)$', command, re.IGNORECASE)
        if checkbox_match:
            option_name = checkbox_match.group(1).strip()

            # Check if this might be a product checkbox
            if any(keyword in option_name.lower() for keyword in ['product', 'service', 'ein', 'certificate', 'incorporation', 'corporate', 'agent', 'expedited']):
                self.speak(f"This appears to be a product. Looking for product checkbox for {option_name}...")
                return await self._check_product_checkbox(option_name)

            self.speak(f"Looking for checkbox for {option_name}...")

            # First try using the LLM to generate actions
            context = await self._get_page_context()

            # Create a specific command for the LLM
            action_data = await self.llm_provider.get_actions(f"check the checkbox for {option_name}", context)

            if 'actions' in action_data and len(action_data['actions']) > 0:
                # Try to execute the LLM-generated actions
                success = await self._execute_actions(action_data)
                if success:
                    return True
                else:
                    self.speak("LLM-generated actions failed, trying fallback methods...")

            # If LLM actions failed, try with JavaScript
            try:
                checked = await self.page.evaluate("""(optionName) => {
                    console.log("Using JavaScript to find and check checkbox for:", optionName);

                    // Function to find checkboxes by nearby text
                    const findCheckboxByText = (text) => {
                        // First, find elements containing the text
                        const textElements = Array.from(document.querySelectorAll('*'))
                            .filter(el => el.textContent.toLowerCase().includes(text.toLowerCase()));

                        console.log(`Found ${textElements.length} elements containing "${text}"`);

                        for (const element of textElements) {
                            console.log(`Examining element with text: "${element.textContent.trim()}"`);

                            // Look for checkboxes in this element
                            const checkboxes = element.querySelectorAll('input[type="checkbox"]');
                            if (checkboxes.length > 0) {
                                console.log(`Found ${checkboxes.length} checkboxes in element with text "${text}"`);
                                return checkboxes[0];
                            }

                            // Look for PrimeNG/PrimeReact checkboxes
                            const primeCheckboxes = element.querySelectorAll('.p-checkbox, .p-checkbox-box');
                            if (primeCheckboxes.length > 0) {
                                console.log(`Found ${primeCheckboxes.length} Prime checkboxes in element with text "${text}"`);
                                return primeCheckboxes[0];
                            }

                            // Look for checkboxes in parent
                            const parent = element.parentElement;
                            if (parent) {
                                const parentCheckboxes = parent.querySelectorAll('input[type="checkbox"], .p-checkbox, .p-checkbox-box');
                                if (parentCheckboxes.length > 0) {
                                    console.log(`Found ${parentCheckboxes.length} checkboxes in parent of element with text "${text}"`);
                                    return parentCheckboxes[0];
                                }
                            }

                            // Look for checkboxes in siblings
                            const siblings = Array.from(element.parentElement?.children || []);
                            for (const sibling of siblings) {
                                if (sibling !== element) {
                                    const siblingCheckboxes = sibling.querySelectorAll('input[type="checkbox"], .p-checkbox, .p-checkbox-box');
                                    if (siblingCheckboxes.length > 0) {
                                        console.log(`Found ${siblingCheckboxes.length} checkboxes in sibling of element with text "${text}"`);
                                        return siblingCheckboxes[0];
                                    }
                                }
                            }
                        }

                        return null;
                    };

                    // Try to find checkbox by option name
                    const checkbox = findCheckboxByText(optionName);

                    if (checkbox) {
                        console.log("Found checkbox, clicking it");

                        // For standard HTML checkboxes
                        if (checkbox.tagName === 'INPUT' && checkbox.type === 'checkbox') {
                            checkbox.checked = true;
                            checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                            checkbox.dispatchEvent(new Event('input', { bubbles: true }));
                            checkbox.dispatchEvent(new Event('click', { bubbles: true }));
                            return true;
                        }

                        // For PrimeNG/PrimeReact checkboxes
                        if (checkbox.classList.contains('p-checkbox') || checkbox.classList.contains('p-checkbox-box')) {
                            checkbox.click();
                            return true;
                        }

                        return false;
                    }

                    return false;
                }""", option_name)

                if checked:
                    self.speak(f"✓ Checked option for {option_name}")
                    return True
                else:
                    self.speak(f"Could not find checkbox for {option_name}")
                    return False
            except Exception as e:
                print(f"Error with JavaScript checkbox check: {e}")
                self.speak(f"Error checking checkbox for {option_name}")
                return False

        # Handle specific dropdown commands
        dropdown_type_match = re.search(r'(?:select|click|open)(?:\s+on)?\s+(?:the\s+)?(.+?)(?:\s+dropdown)?$', command, re.IGNORECASE)
        if dropdown_type_match:
            dropdown_name = dropdown_type_match.group(1).strip().lower()

            # Use the generic dropdown method for all dropdowns
            dropdown_label = dropdown_name

            # Special handling for common dropdown names
            if 'entity type' in dropdown_name or dropdown_name == 'entity':
                dropdown_label = "Entity Type"
            elif 'state of formation' in dropdown_name or 'formation state' in dropdown_name or dropdown_name == 'state':
                dropdown_label = "State of Formation"
            elif 'principal address' in dropdown_name or 'address' in dropdown_name or 'principal' in dropdown_name:
                dropdown_label = "Principal Address"

            # Use the generic dropdown method
            return await self._click_generic_dropdown(dropdown_label)

        # Handle specific Principal Address dropdown command
        address_dropdown_match = re.search(r'(?:click|select|open)(?:\s+(?:on|the))?\s+(?:principal(?:\s+address)?|address)(?:\s+dropdown)?', command, re.IGNORECASE)
        if address_dropdown_match:
            self.speak("Looking for principal address dropdown...")
            return await self._click_principal_address_dropdown()

        # Handle specific state dropdown command - make this pattern more robust and handle typos
        state_dropdown_match = re.search(r'(?:cl[ci]?[ck]k?|select|open)(?:\s+(?:on|the))?\s+(?:state(?:\s+of\s+formation)?|formation\s+state|state\s+dropdown)(?:\s+dropdown)?', command, re.IGNORECASE)
        if state_dropdown_match:
            self.speak("Looking for state of formation dropdown...")
            # Use the specialized method for state dropdown
            return await self._click_state_dropdown_direct()

        # Handle dropdown selection commands
        dropdown_match = re.search(r'(?:select|choose|pick)(?:\s+the)?\s+(?:option|value|item)?\s*["\']?([^"\']+)["\']?(?:\s+from(?:\s+the)?\s+(?:dropdown|select|list|menu)\s+(?:of|for|called)?\s+["\']?([^"\']+)["\']?)?', command, re.IGNORECASE)
        if dropdown_match:
            option_value = dropdown_match.group(1).strip()
            dropdown_name = dropdown_match.group(2).strip() if dropdown_match.group(2) else None

            if dropdown_name:
                self.speak(f"Looking for option '{option_value}' in dropdown '{dropdown_name}'...")
            else:
                self.speak(f"Looking for option '{option_value}' in any dropdown...")

            # First try using the LLM to generate actions
            context = await self._get_page_context()

            # Create a specific command for the LLM
            llm_command = f"select {option_value} from {dropdown_name} dropdown" if dropdown_name else f"select {option_value} from dropdown"
            action_data = await self.llm_provider.get_actions(llm_command, context)

            if 'actions' in action_data and len(action_data['actions']) > 0:
                # Try to execute the LLM-generated actions
                success = await self._execute_actions(action_data)
                if success:
                    return True
                else:
                    self.speak("LLM-generated actions failed, trying fallback methods...")

            # First try to find and click the dropdown to open it
            if dropdown_name:
                dropdown_selectors = await self._get_llm_selectors(f"find dropdown '{dropdown_name}'", context)
                dropdown_clicked = False

                for selector in dropdown_selectors:
                    try:
                        if await self.page.locator(selector).count() > 0:
                            await self._retry_click(selector, f"dropdown '{dropdown_name}'")
                            self.speak(f"Clicked on dropdown {dropdown_name}")
                            await self.page.wait_for_timeout(1000)
                            dropdown_clicked = True
                            break
                    except Exception as e:
                        print(f"Error with dropdown selector {selector}: {e}")
                        continue

                if not dropdown_clicked:
                    # Try JavaScript to find and click the dropdown
                    try:
                        clicked = await self.page.evaluate("""(dropdownName) => {
                            // Function to find dropdown elements containing text
                            const findDropdowns = (text) => {
                                const elements = [];

                                // Standard HTML dropdowns
                                const dropdownElements = document.querySelectorAll('select, [role="combobox"], .dropdown, .select, [aria-haspopup="listbox"]');

                                for (const el of dropdownElements) {
                                    if (el.textContent.toLowerCase().includes(text.toLowerCase())) {
                                        elements.push(el);
                                    }
                                }

                                // PrimeNG/PrimeReact specific selectors
                                const primeDropdowns = document.querySelectorAll('.p-dropdown, .p-multiselect, .p-autocomplete, .p-dropdown-trigger, .p-multiselect-trigger, .p-autocomplete-dropdown');
                                for (const el of primeDropdowns) {
                                    if (el.textContent.toLowerCase().includes(text.toLowerCase())) {
                                        elements.push(el);
                                    }
                                }

                                // Look for PrimeNG/PrimeReact dropdown labels
                                const primeLabels = document.querySelectorAll('.p-dropdown-label, .p-multiselect-label, .p-autocomplete-input');
                                for (const label of primeLabels) {
                                    if (label.textContent.toLowerCase().includes(text.toLowerCase())) {
                                        // Get the parent dropdown component
                                        const parent = label.closest('.p-dropdown, .p-multiselect, .p-autocomplete');
                                        if (parent) {
                                            elements.push(parent);
                                        }
                                    }
                                }

                                // Also look for labels that might be associated with dropdowns
                                const labels = document.querySelectorAll('label');
                                for (const label of labels) {
                                    if (label.textContent.toLowerCase().includes(text.toLowerCase())) {
                                        const id = label.getAttribute('for');
                                        if (id) {
                                            const associatedElement = document.getElementById(id);
                                            if (associatedElement && (associatedElement.tagName === 'SELECT' || associatedElement.getAttribute('role') === 'combobox')) {
                                                elements.push(associatedElement);
                                            }
                                        }

                                        // Also check for nearby PrimeNG/PrimeReact dropdowns
                                        const nextElement = label.nextElementSibling;
                                        if (nextElement && (nextElement.classList.contains('p-dropdown') ||
                                                           nextElement.classList.contains('p-multiselect') ||
                                                           nextElement.classList.contains('p-autocomplete'))) {
                                            elements.push(nextElement);
                                        }
                                    }
                                }

                                return elements;
                            };

                            // Find dropdown elements containing the text
                            const dropdowns = findDropdowns(dropdownName);
                            console.log(`Found ${dropdowns.length} dropdowns containing "${dropdownName}"`);

                            // Click the first one found
                            if (dropdowns.length > 0) {
                                console.log(`Clicking dropdown with text: ${dropdowns[0].textContent}`);
                                dropdowns[0].click();
                                return true;
                            }

                            return false;
                        }""", dropdown_name)

                        if clicked:
                            self.speak(f"Found and clicked dropdown {dropdown_name} using JavaScript")
                            await self.page.wait_for_timeout(1000)
                            dropdown_clicked = True
                        else:
                            self.speak(f"Could not find dropdown {dropdown_name}")
                            return False
                    except Exception as e:
                        print(f"Error with JavaScript dropdown click for {dropdown_name}: {e}")
                        self.speak(f"Could not find dropdown {dropdown_name}")
                        return False

            # Now try to find and click the option
            option_selectors = await self._get_llm_selectors(f"find option '{option_value}' in dropdown", context)

            for selector in option_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_click(selector, f"option '{option_value}'")
                        self.speak(f"Selected option {option_value}")
                        await self.page.wait_for_timeout(1000)
                        return True
                except Exception as e:
                    print(f"Error with option selector {selector}: {e}")
                    continue

            # Try JavaScript to find and click the option
            try:
                clicked = await self.page.evaluate("""(optionValue) => {
                    // Function to find option elements containing text
                    const findOptions = (text) => {
                        const elements = [];

                        // Look for standard select options
                        const options = document.querySelectorAll('option');
                        for (const option of options) {
                            if (option.textContent.toLowerCase().includes(text.toLowerCase())) {
                                elements.push(option);
                            }
                        }

                        // Look for dropdown items in custom dropdowns
                        const dropdownItems = document.querySelectorAll('li, [role="option"], .dropdown-item, .select-option');
                        for (const item of dropdownItems) {
                            if (item.textContent.toLowerCase().includes(text.toLowerCase())) {
                                elements.push(item);
                            }
                        }

                        // PrimeNG/PrimeReact specific option selectors
                        const primeOptions = document.querySelectorAll(
                            '.p-dropdown-item, ' +
                            '.p-multiselect-item, ' +
                            '.p-autocomplete-item, ' +
                            '.p-dropdown-panel .p-dropdown-items li, ' +
                            '.p-multiselect-panel .p-multiselect-items li, ' +
                            '.p-autocomplete-panel .p-autocomplete-items li'
                        );

                        for (const item of primeOptions) {
                            if (item.textContent.toLowerCase().includes(text.toLowerCase())) {
                                elements.push(item);
                            }
                        }

                        // If no options found yet, try to find any visible elements with matching text
                        // that might be clickable options
                        if (elements.length === 0) {
                            // Wait a bit to ensure dropdown is fully open
                            setTimeout(() => {}, 500);

                            // Look for any visible elements that might be options
                            const allPossibleOptions = document.querySelectorAll('div, span, li, a');
                            for (const el of allPossibleOptions) {
                                if (el.textContent.trim().toLowerCase().includes(text.toLowerCase()) &&
                                    window.getComputedStyle(el).display !== 'none' &&
                                    window.getComputedStyle(el).visibility !== 'hidden') {

                                    // Check if this element is likely to be an option
                                    const rect = el.getBoundingClientRect();
                                    if (rect.width > 0 && rect.height > 0) {
                                        elements.push(el);
                                    }
                                }
                            }
                        }

                        return elements;
                    };

                    // Find option elements containing the text
                    const options = findOptions(optionValue);
                    console.log(`Found ${options.length} options containing "${optionValue}"`);

                    // Click the first one found
                    if (options.length > 0) {
                        console.log(`Clicking option with text: ${options[0].textContent}`);
                        options[0].click();
                        return true;
                    }

                    return false;
                }""", option_value)

                if clicked:
                    self.speak(f"Selected option {option_value} using JavaScript")
                    await self.page.wait_for_timeout(1000)
                    return True
                else:
                    self.speak(f"Could not find option {option_value}")
                    return False
            except Exception as e:
                print(f"Error with JavaScript option click for {option_value}: {e}")
                self.speak(f"Could not find option {option_value}")
                return False

        # Handle "enter password" command
        password_only_match = re.search(r'(?:enter|input|type|fill)\s+(?:password|pass|pwd|pword|oassword)\s+(\S+)', command, re.IGNORECASE)
        if password_only_match:
            password = password_only_match.group(1)
            self.speak(f"Entering password...")

            # Get the current page context
            context = await self._get_page_context()

            # First try using the LLM to generate actions
            print("Using LLM to generate actions for password field...")
            action_data = await self.llm_provider.get_actions(f"enter password {password}", context)

            if 'actions' in action_data and len(action_data['actions']) > 0:
                # Try to execute the LLM-generated actions
                success = await self._execute_actions(action_data)
                if success:
                    return True
                else:
                    self.speak("LLM-generated actions failed, trying fallback methods...")

            # If LLM actions failed, try with selectors
            print("Using LLM to generate selectors for password field...")
            password_selectors = await self._get_llm_selectors("find password input field", context)

            # Define comprehensive fallback selectors
            fallback_password_selectors = [
                # Site-specific selectors (if known)
                '#floating_outlined15',

                # Common password selectors
                'input[type="password"]',
                'input[name="password"]',
                'input[id*="password"]',
                'input[placeholder*="password"]',
                'input.password',
                '#password',
                'form input[type="password"]',

                # Position-based selectors
                'form input:nth-child(2)',
                'input:nth-of-type(2)',

                # Attribute-based selectors
                'input[autocomplete="current-password"]',
                'input[autocomplete="new-password"]',

                # Common class names
                '.password-input',
                '.form-control[type="password"]',

                # Last resort - any password field
                'input[type="password"]'
            ]

            # Try all selectors
            password_found = False
            all_selectors = password_selectors + fallback_password_selectors

            # First check which selectors actually match elements
            matching_selectors = []
            for selector in all_selectors:
                try:
                    count = await self.page.locator(selector).count()
                    if count > 0:
                        matching_selectors.append(f"{selector} (matches {count} elements)")
                except Exception as e:
                    print(f"Error checking password selector {selector}: {e}")

            if matching_selectors:
                print(f"Found matching password selectors: {matching_selectors}")
            else:
                print("No matching password selectors found on the page")

            # Try to fill using the selectors
            for selector in all_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_type(selector, password, "password")
                        password_found = True
                        self.speak("Password entered successfully")
                        return True
                except Exception as e:
                    print(f"Error with password selector {selector}: {e}")
                    continue

            # If no selectors worked, try JavaScript approach
            if not password_found:
                try:
                    # Use JavaScript to find and fill password fields
                    js_result = await self.page.evaluate(f"""() => {{
                        try {{
                            // Try to find any password field
                            const passwordFields = Array.from(document.querySelectorAll('input[type="password"]'));

                            if (passwordFields.length > 0) {{
                                // Fill the first password field
                                passwordFields[0].value = "{password}";
                                passwordFields[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
                                passwordFields[0].dispatchEvent(new Event('change', {{ bubbles: true }}));
                                console.log("Password field filled using JavaScript");
                                return {{ success: true }};
                            }}

                            // If no password fields found, look for inputs that might be password fields
                            const possiblePasswordFields = Array.from(document.querySelectorAll('input'))
                                .filter(input =>
                                    input.id?.toLowerCase().includes('password') ||
                                    input.name?.toLowerCase().includes('password') ||
                                    input.placeholder?.toLowerCase().includes('password') ||
                                    input.autocomplete === 'current-password' ||
                                    input.autocomplete === 'new-password'
                                );

                            if (possiblePasswordFields.length > 0) {{
                                possiblePasswordFields[0].value = "{password}";
                                possiblePasswordFields[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
                                possiblePasswordFields[0].dispatchEvent(new Event('change', {{ bubbles: true }}));
                                console.log("Possible password field filled using JavaScript");
                                return {{ success: true }};
                            }}

                            return {{ success: false, error: "No password fields found" }};
                        }} catch (error) {{
                            console.error("Error in JavaScript password fill:", error);
                            return {{ success: false, error: error.toString() }};
                        }}
                    }}""")

                    if js_result.get('success'):
                        self.speak("Password entered using JavaScript")
                        return True
                    else:
                        print(f"JavaScript password fill failed: {js_result.get('error')}")
                except Exception as e:
                    print(f"Error with JavaScript password fill: {e}")

            if not password_found:
                self.speak("Could not find password field")
                return False

            return True

        # Handle "enter email" command - similar to original Voice.py
        # First try to extract the exact email address using a simple pattern
        # This approach captures everything after "enter email" as the email address
        # Look specifically for an email pattern with @ symbol
        email_command_match = re.search(r'(?:enter|input|type|fill)\s+(?:email|emaol|e-mail|email\s+address|email\s+adddress)\s+([^\s]+@[^\s]+(?:\.[^\s]+)+)(?:\s+(?:and|with|&)?\s+(?:password|pass|pwd|pword|oassword)\s+(\S+))?', command, re.IGNORECASE)

        if email_command_match:
            # Extract the email - everything after "enter email" and before "and password" if present
            email_part = email_command_match.group(1).strip()
            password_part = email_command_match.group(2) if email_command_match.group(2) else None

            print(f"DEBUG: Extracted email: '{email_part}', password: '{password_part}'")

            # Create appropriate match objects with the extracted values
            if password_part:
                # Both email and password were provided
                enter_email_match = type('obj', (object,), {'groups': lambda: (email_part, password_part)})
                email_only_match = None
            else:
                # Only email was provided
                enter_email_match = None
                email_only_match = type('obj', (object,), {'group': lambda _: email_part})
        else:
            # If the direct approach didn't work, fall back to regex patterns
            # First check for email and password pattern
            enter_email_match = re.search(r'enter\s+(?:email|emaol|e-mail|email\s+address|email\s+adddress)\s+(\S+)(?:\s+(?:and|with|&)?\s+(?:password|pass|pwd|pword|oassword)\s+(\S+))?', command, re.IGNORECASE)

            if not enter_email_match:
                # Try more flexible patterns for email and password
                enter_patterns = [
                    r'(?:enter|input|type)\s+(?:email|email address|email adddress)?\s*(\S+)\s+(?:and|with)\s+(?:password|pass|p[a-z]*)?\s*(\S+)',
                    r'(?:fill|fill in)\s+(?:with)?\s*(?:email|username|email address|email adddress)?\s*(\S+)\s+(?:and|with)\s*(?:password|pass|p[a-z]*)?\s*(\S+)',
                    r'(?:enter|input|type|fill|put)\s+(?:in|the)?\s*(?:email|emaol|e-mail|username|email address|email adddress)?\s*(\S+@\S+)(?:\s+(?:and|with|&)?\s+(?:password|pass|pwd|pword|oassword)\s+(\S+))?',
                    r'(?:email|emaol|e-mail|username|email address|email adddress)\s+(?:is|as)?\s*(\S+@\S+)(?:\s+(?:and|with|&)?\s+(?:password|pass|pwd|pword|oassword)\s+(?:is|as)?\s*(\S+))?'
                ]

                for pattern in enter_patterns:
                    enter_email_match = re.search(pattern, command, re.IGNORECASE)
                    if enter_email_match:
                        print(f"DEBUG: Matched email pattern: {pattern}")
                        break

            # If no match for email+password, check for just email
            email_only_match = None
            if not enter_email_match:
                email_only_patterns = [
                    r'enter (?:email|email address|email adddress)\s+(\S+@\S+)',
                    r'(?:enter|input|type|fill)\s+(?:ema[a-z]+|email address|email adddress)?\s*(\S+@\S+)',  # Handle typos like 'emaol'
                    r'(?:email|ema[a-z]+|email address|email adddress)\s+(\S+@\S+)',  # Handle typos like 'emaol'
                    r'(?:enter|input|type|fill)\s+(?:email|ema[a-z]+|email address|email adddress)\s+(\S+)',  # Catch any word after email command
                    r'(?:email|ema[a-z]+|email address|email adddress)\s+(\S+)'  # Catch any word after email
                ]

                for pattern in email_only_patterns:
                    print(f"DEBUG: Trying email pattern: {pattern}")
                    email_only_match = re.search(pattern, command, re.IGNORECASE)
                    if email_only_match:
                        print(f"DEBUG: Email pattern matched: {pattern}")
                        break

        if email_only_match:
            # Handle email-only case
            email = email_only_match.group(1)
            self.speak(f"Entering email: {email}")

            # Get the current page context
            context = await self._get_page_context()

            # First try using the LLM to generate actions
            print("Using LLM to generate actions for email field...")
            action_data = await self.llm_provider.get_actions(f"enter email {email}", context)

            if 'actions' in action_data and len(action_data['actions']) > 0:
                # Try to execute the LLM-generated actions
                success = await self._execute_actions(action_data)
                if success:
                    return True
                else:
                    self.speak("LLM-generated actions failed, trying fallback methods...")

            # If LLM actions failed, try with selectors
            print("Using LLM to generate selectors for email field...")
            email_selectors = await self._get_llm_selectors("find email or username input field", context)

            # Define fallback selectors to use only if LLM fails
            fallback_email_selectors = [
                '#floating_outlined3',  # Specific ID from the provided HTML
                'input[id="floating_outlined3"]',
                'label:has-text("Email") + input',
                'label:has-text("Email") ~ input',
                'input[type="email"]',
                'input[name="email"]',
                'input[id*="email"]',
                'input[placeholder*="email"]',
                'input[type="text"][name*="user"]',
                'input[id*="user"]',
                # Add more generic selectors that might work on any site
                'input',  # Try any input field
                'input[type="text"]',  # Try any text input
                'form input:first-child',  # First input in a form
                'form input',  # Any input in a form
                '.form-control',  # Bootstrap form control
                'input.form-control',  # Bootstrap input
                'input[autocomplete="email"]',  # Input with email autocomplete
                'input[autocomplete="username"]'  # Input with username autocomplete
            ]

            # First try with just LLM selectors
            all_email_selectors = email_selectors.copy() if email_selectors else []

            # Try to fill the email field using LLM selectors first
            print(f"DEBUG: Trying LLM email selectors: {all_email_selectors}")
            email_found = False
            for selector in all_email_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_type(selector, email, "email address")
                        email_found = True
                        break
                except Exception as e:
                    print(f"Error with email selector {selector}: {e}")
                    continue

            # If LLM selectors didn't work for email, try fallback selectors
            if not email_found and fallback_email_selectors:
                print("LLM email selectors didn't work, trying fallback selectors...")
                print(f"DEBUG: Fallback email selectors: {fallback_email_selectors}")

                # Initialize all_inputs_count to avoid UnboundLocalError
                all_inputs_count = 0
                matching_selectors = []

                # First, let's check what elements are on the page
                print("DEBUG: Checking for any input elements on the page...")
                try:
                    # Wait a bit longer for the page to fully load
                    print("DEBUG: Waiting for page to fully load...")
                    await self.page.wait_for_timeout(20000)

                    # Try to find inputs in the main document
                    all_inputs_count = await self.page.locator('input').count()
                    print(f"DEBUG: Found {all_inputs_count} input elements on the page")

                    # If no inputs found, check if there are any iframes
                    if all_inputs_count == 0:
                        iframe_count = await self.page.locator('iframe').count()
                        print(f"DEBUG: Found {iframe_count} iframes on the page")

                        if iframe_count > 0:
                            print("DEBUG: Checking for inputs in iframes...")
                            for i in range(iframe_count):
                                try:
                                    iframe = self.page.locator('iframe').nth(i)
                                    frame = await iframe.content_frame()
                                    if frame:
                                        iframe_inputs_count = await frame.locator('input').count()
                                        print(f"DEBUG: Found {iframe_inputs_count} inputs in iframe #{i+1}")
                                        if iframe_inputs_count > 0:
                                            print("DEBUG: Will try to use inputs in iframe later")
                                except Exception as e:
                                    print(f"DEBUG: Error checking iframe #{i+1}: {e}")

                    # If there are inputs in the main document, let's get more info about them
                    if all_inputs_count > 0:
                        for i in range(min(all_inputs_count, 5)):  # Check first 5 inputs
                            input_el = self.page.locator('input').nth(i)
                            input_type = await input_el.evaluate("el => el.type || ''")
                            input_id = await input_el.evaluate("el => el.id || ''")
                            input_name = await input_el.evaluate("el => el.name || ''")
                            input_placeholder = await input_el.evaluate("el => el.placeholder || ''")
                            input_value = await input_el.evaluate("el => el.value || ''")
                            is_visible = await input_el.is_visible()
                            print(f"DEBUG: Input #{i+1} - type: {input_type}, id: {input_id}, name: {input_name}, placeholder: {input_placeholder}, value: {input_value}, visible: {is_visible}")

                    # If still no inputs found, try to click on the page to reveal any hidden forms
                    if all_inputs_count == 0:
                        print("DEBUG: No inputs found. Trying to click on the page to reveal forms...")
                        try:
                            # Try clicking on common login-related elements
                            login_elements = [
                                'a:has-text("Login")',
                                'a:has-text("Sign in")',
                                'button:has-text("Login")',
                                'button:has-text("Sign in")',
                                '.login-button',
                                '.signin-button'
                            ]

                            for selector in login_elements:
                                try:
                                    if await self.page.locator(selector).count() > 0:
                                        print(f"DEBUG: Found and clicking {selector}")
                                        await self.page.locator(selector).click()
                                        await self.page.wait_for_timeout(1000)

                                        # Check if inputs appeared
                                        new_inputs_count = await self.page.locator('input').count()
                                        if new_inputs_count > 0:
                                            print(f"DEBUG: Found {new_inputs_count} inputs after clicking")
                                            all_inputs_count = new_inputs_count
                                            break
                                except Exception as e:
                                    print(f"DEBUG: Error clicking {selector}: {e}")
                        except Exception as e:
                            print(f"DEBUG: Error trying to reveal forms: {e}")
                except Exception as e:
                    print(f"DEBUG: Error checking for inputs: {e}")

                # Now check which selectors actually match elements
                # matching_selectors was already initialized above
                for selector in fallback_email_selectors:
                    try:
                        count = await self.page.locator(selector).count()
                        if count > 0:
                            matching_selectors.append(f"{selector} (matches {count} elements)")
                    except Exception as e:
                        print(f"Error checking fallback email selector {selector}: {e}")

                if matching_selectors:
                    print(f"DEBUG: Found matching selectors: {matching_selectors}")
                else:
                    print("DEBUG: No matching selectors found on the page")

                # Try a more aggressive approach - just use the first input field if available
                if all_inputs_count > 0 and not matching_selectors:
                    print("DEBUG: No specific selectors matched, but inputs exist. Will try first input field.")

                # Now try to use the selectors to fill the email field
                for selector in fallback_email_selectors:
                    try:
                        count = await self.page.locator(selector).count()
                        if count > 0:
                            print(f"DEBUG: Trying to fill email using selector: {selector}")
                            await self._retry_type(selector, email, "email address")
                            email_found = True
                            print(f"DEBUG: Successfully filled email using selector: {selector}")
                            break
                    except Exception as e:
                        print(f"Error with fallback email selector {selector}: {e}")
                        continue

                # If no selectors worked but we found input fields, try the first input as a last resort
                if not email_found and all_inputs_count > 0:
                    try:
                        print("DEBUG: Trying to fill email using first input field as last resort")
                        first_input = self.page.locator('input').first
                        await first_input.fill(email)
                        email_found = True
                        print("DEBUG: Successfully filled email using first input field")
                    except Exception as e:
                        print(f"Error with first input field: {e}")

                # If still not found and we have iframes, try inputs in iframes
                if not email_found:
                    iframe_count = await self.page.locator('iframe').count()
                    if iframe_count > 0:
                        print("DEBUG: Trying to fill email in iframes...")
                        for i in range(iframe_count):
                            try:
                                iframe = self.page.locator('iframe').nth(i)
                                frame = await iframe.content_frame()
                                if frame:
                                    iframe_inputs_count = await frame.locator('input').count()
                                    if iframe_inputs_count > 0:
                                        print(f"DEBUG: Trying to fill email in iframe #{i+1}")
                                        first_iframe_input = frame.locator('input').first
                                        await first_iframe_input.fill(email)
                                        email_found = True
                                        print(f"DEBUG: Successfully filled email in iframe #{i+1}")
                                        break
                            except Exception as e:
                                print(f"Error filling email in iframe #{i+1}: {e}")
                                continue

            if email_found:
                self.speak("Email entered successfully")
                return True
            else:
                self.speak("Could not find email field")
                return False

        elif enter_email_match:
            email, password = enter_email_match.groups()

            if password:
                self.speak("Entering email and password...")
            else:
                self.speak("Entering email...")

            # First try using the LLM to generate actions
            context = await self._get_page_context()

            # Create a specific command for the LLM
            llm_command = f"enter email {email} and password {password}" if password else f"enter email {email}"
            action_data = await self.llm_provider.get_actions(llm_command, context)

            if 'actions' in action_data and len(action_data['actions']) > 0:
                # Try to execute the LLM-generated actions
                success = await self._execute_actions(action_data)
                if success:
                    return True
                else:
                    self.speak("LLM-generated actions failed, trying fallback methods...")

            # First check if we need to navigate to the login page
            current_url = self.page.url
            if "signin" not in current_url and "login" not in current_url:
                self.speak("Not on login page. Navigating directly to login page...")

                try:
                    # Navigate directly to the login page
                    await self.page.goto("https://#/signin", wait_until="networkidle", timeout=30000)
                    self.speak("Navigated to login page")
                    # Wait for the page to load
                    await self.page.wait_for_timeout(30000)
                except Exception as e:
                    print(f"Error navigating to login page: {e}")
                    self.speak("Error navigating to login page")
                    return False

            # Wait a bit longer for the page to fully load
            self.speak("Waiting for page to fully load...")
            await self.page.wait_for_timeout(5000)

            # Use direct JavaScript injection to fill the form
            self.speak("Using direct JavaScript to fill the form...")

            try:
                # Inject and execute JavaScript to fill the form
                result = await self.page.evaluate(f"""() => {{
                    // Function to wait for an element to be available
                    function waitForElement(selector, maxWait = 10000) {{
                        return new Promise((resolve, reject) => {{
                            if (document.querySelector(selector)) {{
                                return resolve(document.querySelector(selector));
                            }}

                            const observer = new MutationObserver(mutations => {{
                                if (document.querySelector(selector)) {{
                                    observer.disconnect();
                                    resolve(document.querySelector(selector));
                                }}
                            }});

                            observer.observe(document.body, {{
                                childList: true,
                                subtree: true
                            }});

                            setTimeout(() => {{
                                observer.disconnect();
                                resolve(document.querySelector(selector));
                            }}, maxWait);
                        }});
                    }}

                    // Function to fill the form
                    async function fillLoginForm() {{
                        try {{
                            console.log("Starting form fill process...");

                            // Wait for email field
                            console.log("Waiting for email field...");
                            const emailField = await waitForElement('#floating_outlined3');
                            console.log("Email field found:", emailField);

                            if (emailField) {{
                                // Fill email field
                                emailField.value = "{email}";
                                emailField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                emailField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                console.log("Email field filled with:", "{email}");

                                // If password is provided, fill password field
                                if ("{password}") {{
                                    // Wait for password field
                                    console.log("Waiting for password field...");
                                    const passwordField = await waitForElement('#floating_outlined15');
                                    console.log("Password field found:", passwordField);

                                    if (passwordField) {{
                                        // Fill password field
                                        passwordField.value = "{password}";
                                        passwordField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        passwordField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                        console.log("Password field filled");

                                        // Wait for submit button
                                        console.log("Waiting for submit button...");
                                        const submitButton = await waitForElement('#signInButton');
                                        console.log("Submit button found:", submitButton);

                                        if (submitButton) {{
                                            // Click submit button
                                            submitButton.click();
                                            console.log("Submit button clicked");
                                            return {{ success: true, message: "Form filled and submitted" }};
                                        }} else {{
                                            return {{ success: false, message: "Submit button not found" }};
                                        }}
                                    }} else {{
                                        return {{ success: false, message: "Password field not found" }};
                                    }}
                                }} else {{
                                    return {{ success: true, message: "Email field filled" }};
                                }}
                            }} else {{
                                return {{ success: false, message: "Email field not found" }};
                            }}
                        }} catch (error) {{
                            console.error("Error filling form:", error);
                            return {{ success: false, message: "Error: " + error.message }};
                        }}
                    }}

                    // Execute the form fill function
                    return fillLoginForm();
                }}""")

                print(f"JavaScript form filling result: {result}")

                if result.get('success'):
                    self.speak(result.get('message', 'Form filled successfully'))
                    return True
                else:
                    self.speak(result.get('message', 'Failed to fill form'))

                    # As a last resort, try to use direct selectors
                    self.speak("Trying direct selectors as a last resort...")

                    try:
                        # Try to fill email field
                        await self.page.fill('#floating_outlined3', email)
                        self.speak("Email entered")

                        if password:
                            # Try to fill password field
                            await self.page.fill('#floating_outlined15', password)
                            self.speak("Password entered")

                            # Try to click submit button
                            await self.page.click('#signInButton')
                            self.speak("Form submitted")

                        return True
                    except Exception as e:
                        print(f"Error with direct selectors: {e}")
                        self.speak("Could not fill form with direct selectors")
                        return False
            except Exception as e:
                print(f"Error with JavaScript form filling: {e}")
                self.speak("Error filling form")
                return False

        # Handle address form input commands
        address_line1_match = re.search(r'(?:enter|input|type|fill)(?:\s+in)?\s+(.+?)(?:\s+in(?:to)?)?\s+(?:address\s+line\s*1|first\s+address\s+line)', command, re.IGNORECASE)
        if address_line1_match:
            address_text = address_line1_match.group(1).strip()
            self.speak(f"Entering '{address_text}' in address line 1...")
            return await self._enter_address_field(address_text, "address_line1")

        address_line2_match = re.search(r'(?:enter|input|type|fill)(?:\s+in)?\s+(.+?)(?:\s+in(?:to)?)?\s+(?:address\s+line\s*2|second\s+address\s+line)', command, re.IGNORECASE)
        if address_line2_match:
            address_text = address_line2_match.group(1).strip()
            self.speak(f"Entering '{address_text}' in address line 2...")
            return await self._enter_address_field(address_text, "address_line2")

        city_match = re.search(r'(?:enter|input|type|fill)(?:\s+in)?\s+(.+?)(?:\s+in(?:to)?)?\s+(?:city|city\s+field)', command, re.IGNORECASE)
        if city_match:
            city_text = city_match.group(1).strip()
            self.speak(f"Entering '{city_text}' in city field...")
            return await self._enter_address_field(city_text, "city")

        zip_match = re.search(r'(?:enter|input|type|fill)(?:\s+in)?\s+(.+?)(?:\s+in(?:to)?)?\s+(?:zip|zip\s+code|postal\s+code)', command, re.IGNORECASE)
        if zip_match:
            zip_text = zip_match.group(1).strip()
            self.speak(f"Entering '{zip_text}' in zip code field...")
            return await self._enter_address_field(zip_text, "zip")

        # If we get here, no direct command matched
        # Try to use LLM to interpret the command
        print(f"No direct command match for: '{command}'. Trying LLM interpretation...")

        # Check if the command might be related to entering data
        if re.search(r'(enter|input|type|fill|email|password)', command, re.IGNORECASE):
            action_data = await self._get_actions(command)
            if 'actions' in action_data and len(action_data['actions']) > 0:
                return await self._execute_actions(action_data)

        # If we get here, we couldn't handle the command
        self.speak(f"I'm not sure how to handle: '{command}'")
        return False

    async def _get_llm_selectors(self, task, context_dict):
        """Use LLM to generate selectors for a task based on page context"""
        try:
            # Use the LLM provider to get selectors
            selectors = await self.llm_provider.get_selectors(task, context_dict)
            print(f"🔍 Selector generation response:\n", selectors)

            # Sanitize selectors
            sanitized_selectors = []
            for selector in selectors:
                # Replace :contains() with :has-text() for Playwright
                if ":contains(" in selector:
                    selector = selector.replace(":contains(", ":has-text(")
                sanitized_selectors.append(selector)

            # Add fallback selectors based on the task
            if "email" in task.lower() or "username" in task.lower():
                sanitized_selectors.extend([
                    '#floating_outlined3',  # Specific selector for your site
                    'input[id="floating_outlined3"]',
                    'input[type="email"]',
                    'input[name="email"]',
                    'input[id*="email"]',
                    'input[placeholder*="email"]',
                    'input[type="text"][name*="user"]',
                    'input[id*="user"]',
                    'input',  # Generic fallback
                    'input[type="text"]',
                    'form input:first-child',
                    'form input',
                    '.form-control',
                    'input.form-control',
                    'input[autocomplete="email"]',
                    'input[autocomplete="username"]'
                ])
            elif "password" in task.lower():
                sanitized_selectors.extend([
                    '#floating_outlined15',  # Specific selector for your site
                    'input[id="floating_outlined15"]',
                    'input[type="password"]',
                    'input[name="password"]',
                    'input[id*="password"]',
                    'input[placeholder*="password"]',
                    'input.password',
                    '#password',
                    '[aria-label*="password"]',
                    '[data-testid*="password"]',
                    'input[autocomplete="current-password"]',
                    'input[autocomplete="new-password"]',
                    'form input[type="password"]',
                    'form input:nth-child(2)'
                ])
            elif "login" in task.lower() or "sign in" in task.lower() or "submit" in task.lower() or "button" in task.lower():
                sanitized_selectors.extend([
                    '#signInButton',  # Specific selector for your site
                    'button[id="signInButton"]',
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button:has-text("Login")',
                    'button:has-text("Sign in")',
                    'button:has-text("Submit")',
                    'a:has-text("Login")',
                    'a:has-text("Sign in")',
                    '.login-button',
                    '.signin-button',
                    '.submit-button',
                    '[data-testid="login-button"]',
                    '[data-testid="submit-button"]',
                    'button',  # Generic fallback
                    'input[type="button"]'
                ])

            # Remove duplicates while preserving order
            unique_selectors = []
            for selector in sanitized_selectors:
                if selector not in unique_selectors:
                    unique_selectors.append(selector)

            # Log success message
            print(f"Generated {len(unique_selectors)} selectors for {task}")

            return unique_selectors  # Return all selectors
        except Exception as e:
            print(f"Selector generation error: {e}")

            # Log failure message
            print(f"Failed to generate selectors: {str(e)}")

            # Return default fallback selectors if there's an error
            if "email" in task.lower() or "username" in task.lower():
                return [
                    '#floating_outlined3',  # Specific selector for your site
                    'input[id="floating_outlined3"]',
                    'input[type="email"]',
                    'input[name="email"]',
                    'input',
                    'input[type="text"]',
                    'form input:first-child'
                ]
            elif "password" in task.lower():
                return [
                    '#floating_outlined15',  # Specific selector for your site
                    'input[id="floating_outlined15"]',
                    'input[type="password"]',
                    'input[name="password"]',
                    'form input[type="password"]',
                    'form input:nth-child(2)'
                ]
            elif "login" in task.lower() or "sign in" in task.lower() or "submit" in task.lower() or "button" in task.lower():
                return [
                    '#signInButton',  # Specific selector for your site
                    'button[id="signInButton"]',
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button:has-text("Login")',
                    'button:has-text("Sign in")',
                    'button'
                ]
            return []

    def _format_input_fields(self, input_fields):
        """Format input fields for LLM prompt"""
        result = ""
        for idx, field in enumerate(input_fields):
            result += f"{idx + 1}. {field.get('tag', 'input')} - "
            result += f"type: {field.get('type', '')}, "
            result += f"id: {field.get('id', '')}, "
            result += f"name: {field.get('name', '')}, "
            result += f"placeholder: {field.get('placeholder', '')}, "
            result += f"aria-label: {field.get('aria-label', '')}\n"
        return result

    def _format_menu_items(self, menu_items):
        """Format menu items for LLM prompt"""
        result = ""
        for idx, item in enumerate(menu_items):
            submenu_indicator = " (has submenu)" if item.get("has_submenu") else ""
            result += f"{idx + 1}. {item.get('text', '')}{submenu_indicator}\n"
        return result

    def _format_buttons(self, buttons):
        """Format buttons for LLM prompt"""
        result = ""
        for idx, button in enumerate(buttons):
            result += f"{idx + 1}. {button.get('text', '')} - "
            result += f"id: {button.get('id', '')}, "
            result += f"class: {button.get('class', '')}, "
            result += f"type: {button.get('type', '')}\n"
        return result

    async def _ensure_entity_type_selected(self):
        """Ensure that an entity type is selected"""
        self.speak("Checking if entity type is selected...")

        try:
            # Check if entity type is already selected
            entity_type_selected = await self.page.evaluate("""() => {
                // Get all dropdowns
                const allDropdowns = document.querySelectorAll('.p-dropdown');
                console.log(`Found ${allDropdowns.length} dropdowns for entity type check`);

                if (allDropdowns.length === 0) {
                    return { success: false, message: "No dropdowns found" };
                }

                // Check the first dropdown (entity type)
                const entityDropdown = allDropdowns[0];
                const label = entityDropdown.querySelector('.p-dropdown-label');

                if (!label) {
                    return { success: false, message: "No label found in entity dropdown" };
                }

                const labelText = label.textContent.trim();
                console.log(`Entity dropdown label text: "${labelText}"`);

                // Check if it has a placeholder class (indicating nothing selected)
                const hasPlaceholder = label.classList.contains('p-placeholder');

                // If it has text other than "Select Entity Type" and no placeholder class, it's selected
                if (!hasPlaceholder && labelText !== "Select Entity Type" && labelText !== "") {
                    return {
                        success: true,
                        message: `Entity type already selected: ${labelText}`,
                        selected: true,
                        value: labelText
                    };
                }

                // Otherwise, we need to select an entity type
                return {
                    success: true,
                    message: "Entity type not selected yet",
                    selected: false
                };
            }""")

            print(f"Entity type check result: {entity_type_selected}")

            if entity_type_selected.get('success'):
                if entity_type_selected.get('selected'):
                    # Entity type is already selected
                    self.speak(f"Entity type is already selected: {entity_type_selected.get('value')}")
                    return True
                else:
                    # Entity type is not selected, we need to select one
                    self.speak("Entity type not selected. Selecting LLC...")

                    # Click the entity type dropdown
                    clicked = await self.page.evaluate("""() => {
                        const allDropdowns = document.querySelectorAll('.p-dropdown');
                        if (allDropdowns.length > 0) {
                            console.log("Clicking entity type dropdown");
                            allDropdowns[0].click();
                            return true;
                        }
                        return false;
                    }""")

                    if clicked:
                        # Wait for dropdown panel to appear
                        await self.page.wait_for_selector('.p-dropdown-panel', timeout=2000)

                        # Select LLC option
                        selected = await self.page.evaluate("""() => {
                            // Find LLC option in the dropdown
                            const llcOption = Array.from(document.querySelectorAll('.p-dropdown-item'))
                                .find(item => item.textContent.trim() === 'LLC');

                            if (llcOption) {
                                console.log("Found LLC option, clicking it");
                                llcOption.click();
                                return true;
                            }
                            return false;
                        }""")

                        if selected:
                            self.speak("Selected LLC as entity type")
                            return True
                        else:
                            self.speak("Could not find LLC option")
                            return False
                    else:
                        self.speak("Could not click entity type dropdown")
                        return False
            else:
                self.speak("Could not check entity type selection")
                return False
        except Exception as e:
            print(f"Error checking entity type selection: {e}")
            self.speak("Error checking entity type selection")
            return False

    async def _select_entity_type(self, entity_type):
        """Select a specific entity type from the dropdown"""
        self.speak(f"Selecting entity type {entity_type}...")

        try:
            # Click the entity type dropdown
            clicked = await self.page.evaluate("""() => {
                const allDropdowns = document.querySelectorAll('.p-dropdown');
                if (allDropdowns.length > 0) {
                    console.log("Clicking entity type dropdown");
                    allDropdowns[0].click();
                    return true;
                }
                return false;
            }""")

            if clicked:
                # Wait for dropdown panel to appear
                await self.page.wait_for_selector('.p-dropdown-panel', timeout=2000)

                # Select the specified entity type option
                selected = await self.page.evaluate("""(entityType) => {
                    // Find the specified entity type option in the dropdown
                    const entityTypeOption = Array.from(document.querySelectorAll('.p-dropdown-item'))
                        .find(item => {
                            const itemText = item.textContent.trim().toLowerCase();
                            const searchText = entityType.toLowerCase();
                            return itemText === searchText ||
                                   itemText.startsWith(searchText) ||
                                   itemText.includes(searchText);
                        });

                    if (entityTypeOption) {
                        console.log(`Found entity type option: ${entityTypeOption.textContent.trim()}, clicking it`);
                        entityTypeOption.click();
                        return { success: true, selected: entityTypeOption.textContent.trim() };
                    }
                    return { success: false, message: "Could not find entity type option" };
                }""", entity_type)

                if selected and selected.get('success'):
                    self.speak(f"Selected {selected.get('selected')} as entity type")
                    return True
                else:
                    self.speak(f"Could not find entity type {entity_type}")
                    return False
            else:
                self.speak("Could not click entity type dropdown")
                return False
        except Exception as e:
            print(f"Error selecting entity type: {e}")
            self.speak(f"Error selecting entity type {entity_type}")
            return False

    async def _click_principal_address_dropdown(self):
        """Click the Principal Address dropdown using generic dropdown finding strategies"""
        return await self._click_generic_dropdown("Principal Address")

    async def _click_generic_dropdown(self, dropdown_name):
        """Generic method to click any dropdown by name

        Args:
            dropdown_name: The name/label of the dropdown to click
        """
        try:
            # Use JavaScript to find and click the dropdown
            clicked = await self.page.evaluate("""(dropdownName) => {
                console.log(`Looking for dropdown: "${dropdownName}"`);

                // Normalize the dropdown name for comparison
                const normalizedName = dropdownName.toLowerCase().trim();

                // STRATEGY 1: Try to find by ID that contains the dropdown name
                // Convert dropdown name to possible ID formats
                const possibleIds = [
                    dropdownName.replace(/\s+/g, '_'),  // spaces to underscores
                    dropdownName.replace(/\s+/g, ''),   // remove spaces
                    dropdownName.replace(/\s+/g, '-'),  // spaces to hyphens
                    // Add more ID patterns as needed
                ];

                for (const id of possibleIds) {
                    const dropdownById = document.getElementById(id);
                    if (dropdownById) {
                        console.log(`Found dropdown by ID: ${id}`);
                        dropdownById.click();
                        return true;
                    }

                    // Try case-insensitive ID search
                    const elementsWithIdAttr = document.querySelectorAll('[id]');
                    for (const el of elementsWithIdAttr) {
                        if (el.id.toLowerCase().includes(normalizedName)) {
                            console.log(`Found dropdown with ID containing "${normalizedName}": ${el.id}`);
                            el.click();
                            return true;
                        }
                    }
                }

                // STRATEGY 2: Try to find by text content
                // Find elements containing the dropdown name text
                const textElements = Array.from(document.querySelectorAll('label, span, div, p, h1, h2, h3, h4, h5, h6'))
                    .filter(el => el.textContent.toLowerCase().includes(normalizedName));

                console.log(`Found ${textElements.length} elements containing "${dropdownName}" text`);

                if (textElements.length > 0) {
                    // Try to find a dropdown near each label
                    for (const element of textElements) {
                        console.log(`Found element with text: "${element.textContent.trim()}"`);

                        // Check if this element is a label with a "for" attribute
                        const forAttribute = element.getAttribute('for');
                        if (forAttribute) {
                            const associatedElement = document.getElementById(forAttribute);
                            if (associatedElement) {
                                console.log(`Found associated element by ID: ${forAttribute}`);
                                associatedElement.click();
                                return true;
                            }
                        }

                        // Look for dropdown in parent
                        const parent = element.parentElement;
                        if (parent) {
                            // Try various dropdown selectors
                            const dropdownSelectors = [
                                '.p-dropdown', // PrimeNG/React
                                '.dropdown', // Bootstrap
                                '[role="combobox"]', // Accessibility role
                                'select', // Standard HTML select
                                '.select', // Common class
                                '.v-select', // Vue
                                '.mat-select', // Angular Material
                                '.MuiSelect-root', // Material-UI
                                '.ant-select', // Ant Design
                                '.chakra-select', // Chakra UI
                                '.custom-select', // Bootstrap custom select
                                '.form-select' // Bootstrap 5
                            ];

                            for (const selector of dropdownSelectors) {
                                const dropdownInParent = parent.querySelector(selector);
                                if (dropdownInParent) {
                                    console.log(`Found dropdown (${selector}) in parent of "${dropdownName}" element`);
                                    dropdownInParent.click();
                                    return true;
                                }
                            }
                        }

                        // Look for dropdown in siblings
                        let sibling = element.nextElementSibling;
                        while (sibling) {
                            // Check if sibling is a dropdown
                            if (sibling.classList.contains('p-dropdown') ||
                                sibling.classList.contains('dropdown') ||
                                sibling.getAttribute('role') === 'combobox' ||
                                sibling.tagName === 'SELECT') {
                                console.log(`Found dropdown in sibling of "${dropdownName}" element`);
                                sibling.click();
                                return true;
                            }

                            // Check for dropdown inside sibling
                            const dropdownInSibling = sibling.querySelector('.p-dropdown, .dropdown, [role="combobox"], select');
                            if (dropdownInSibling) {
                                console.log(`Found dropdown inside sibling of "${dropdownName}" element`);
                                dropdownInSibling.click();
                                return true;
                            }

                            sibling = sibling.nextElementSibling;
                        }

                        // Look for dropdown in ancestors and their siblings
                        let ancestor = element.parentElement;
                        let depth = 0;
                        const MAX_DEPTH = 5; // Limit how far up we go to avoid performance issues

                        while (ancestor && depth < MAX_DEPTH) {
                            // Check siblings of ancestor
                            let ancestorSibling = ancestor.nextElementSibling;
                            while (ancestorSibling) {
                                const dropdownInAncestorSibling = ancestorSibling.querySelector('.p-dropdown, .dropdown, [role="combobox"], select');
                                if (dropdownInAncestorSibling) {
                                    console.log(`Found dropdown in ancestor's sibling`);
                                    dropdownInAncestorSibling.click();
                                    return true;
                                }
                                ancestorSibling = ancestorSibling.nextElementSibling;
                            }

                            ancestor = ancestor.parentElement;
                            depth++;
                        }
                    }
                }

                // STRATEGY 3: Try to find any dropdown with empty or placeholder text
                const placeholderTexts = ['empty', 'select...', 'choose...', 'select an option', 'please select'];
                for (const placeholderText of placeholderTexts) {
                    const placeholderDropdowns = Array.from(document.querySelectorAll('.p-dropdown-label, .dropdown-toggle, [role="combobox"], select'))
                        .filter(el => el.textContent.trim().toLowerCase() === placeholderText);

                    console.log(`Found ${placeholderDropdowns.length} dropdowns with "${placeholderText}" text`);

                    if (placeholderDropdowns.length > 0) {
                        // Find the parent dropdown container and click it
                        const dropdownContainer = placeholderDropdowns[0].closest('.p-dropdown, .dropdown, [role="combobox"]');
                        if (dropdownContainer) {
                            console.log(`Found and clicking dropdown container with "${placeholderText}" text`);
                            dropdownContainer.click();
                            return true;
                        } else {
                            // If no container found, click the element itself
                            console.log(`Clicking dropdown element with "${placeholderText}" text directly`);
                            placeholderDropdowns[0].click();
                            return true;
                        }
                    }
                }

                // STRATEGY 4: Look for dropdown triggers/icons near text matching the dropdown name
                const dropdownTriggers = document.querySelectorAll('.p-dropdown-trigger, .dropdown-toggle, [aria-haspopup="listbox"], .select-arrow');
                console.log(`Found ${dropdownTriggers.length} dropdown triggers/icons`);

                for (const trigger of dropdownTriggers) {
                    // Check if the trigger or its parent contains text matching the dropdown name
                    const triggerParent = trigger.parentElement;
                    if (triggerParent && triggerParent.textContent.toLowerCase().includes(normalizedName)) {
                        console.log(`Found dropdown trigger with parent text containing "${dropdownName}"`);
                        trigger.click();
                        return true;
                    }
                }

                // STRATEGY 5: Special handling for State of Formation dropdown
                if (normalizedName.includes('state') && normalizedName.includes('formation')) {
                    console.log("Using special handling for State of Formation dropdown");

                    // Look for dropdown with "Select State" text
                    const stateLabels = Array.from(document.querySelectorAll('.p-dropdown-label'))
                        .filter(el => el.textContent.trim() === 'Select State');

                    if (stateLabels.length > 0) {
                        const dropdownContainer = stateLabels[0].closest('.p-dropdown');
                        if (dropdownContainer) {
                            console.log(`Found and clicking dropdown container with "Select State" text`);
                            dropdownContainer.click();
                            return true;
                        }
                    }

                    // If we have multiple dropdowns, check if the first one is entity type
                    const allDropdowns = document.querySelectorAll('.p-dropdown');
                    if (allDropdowns.length >= 2) {
                        const firstDropdownLabel = allDropdowns[0].querySelector('.p-dropdown-label');
                        const firstLabelText = firstDropdownLabel ? firstDropdownLabel.textContent.trim() : '';

                        // If first dropdown is entity type, click the second one
                        if (firstLabelText.toLowerCase().includes('entity') ||
                            firstLabelText === 'LLC' ||
                            firstLabelText === 'CORP' ||
                            firstLabelText === 'Select Entity Type') {
                            console.log(`First dropdown appears to be entity type, clicking second dropdown for state`);
                            allDropdowns[1].click();
                            return true;
                        }
                    }
                }

                // STRATEGY 6: Last resort - try all visible dropdowns
                const allDropdowns = document.querySelectorAll('.p-dropdown, .dropdown, [role="combobox"], select');
                console.log(`Found ${allDropdowns.length} total dropdowns on the page`);

                // Try to find one that might match our dropdown name
                for (const dropdown of allDropdowns) {
                    if (dropdown.textContent.toLowerCase().includes(normalizedName)) {
                        console.log(`Found dropdown with text containing "${dropdownName}"`);
                        dropdown.click();
                        return true;
                    }
                }

                // Special handling for state dropdown as last resort
                if (normalizedName.includes('state') && allDropdowns.length > 1) {
                    console.log(`Clicking second dropdown as last resort for state dropdown`);
                    allDropdowns[1].click();
                    return true;
                }

                // If we still haven't found it and there are dropdowns, click the first visible one
                if (allDropdowns.length > 0) {
                    // Find a visible dropdown
                    for (const dropdown of allDropdowns) {
                        if (window.getComputedStyle(dropdown).display !== 'none' &&
                            window.getComputedStyle(dropdown).visibility !== 'hidden') {
                            console.log(`Clicking first visible dropdown as last resort`);
                            dropdown.click();
                            return true;
                        }
                    }
                }

                return false;
            }""", dropdown_name)

            if clicked:
                self.speak(f"Clicked the {dropdown_name} dropdown")
                return True
            else:
                self.speak(f"Could not find {dropdown_name} dropdown")
                return False
        except Exception as e:
            print(f"Error with {dropdown_name} dropdown click: {e}")
            self.speak(f"Error clicking {dropdown_name} dropdown")
            return False

    async def _click_state_dropdown_direct(self):
        """Click the state dropdown with specific targeting for state of formation"""
        try:
            # First, let's log all the dropdowns on the page for debugging
            await self.page.evaluate("""() => {
                console.log("DEBUGGING: Logging all dropdowns on the page");

                // Get all dropdowns
                const allDropdowns = document.querySelectorAll('.p-dropdown');
                console.log(`Found ${allDropdowns.length} dropdowns total`);

                // Log all dropdowns for debugging
                for (let i = 0; i < allDropdowns.length; i++) {
                    const dropdown = allDropdowns[i];
                    const label = dropdown.querySelector('.p-dropdown-label');
                    console.log(`Dropdown #${i}: label text="${label ? label.textContent.trim() : 'none'}"`);

                    // Log the dropdown's parent element and its siblings
                    const parent = dropdown.parentElement;
                    if (parent) {
                        console.log(`Dropdown #${i} parent: tag=${parent.tagName}, class=${parent.className}`);

                        // Look for labels or text near this dropdown
                        const prevSibling = parent.previousElementSibling;
                        if (prevSibling) {
                            console.log(`Dropdown #${i} prev sibling: tag=${prevSibling.tagName}, text="${prevSibling.textContent.trim()}"`);
                        }
                    }
                }

                // Look for elements with "State of Formation" text
                const stateFormationElements = Array.from(document.querySelectorAll('*'))
                    .filter(el => {
                        const text = el.textContent.toLowerCase().trim();
                        return text.includes('state') && text.includes('formation');
                    });

                console.log(`Found ${stateFormationElements.length} elements with "State of Formation" text`);

                for (const element of stateFormationElements) {
                    console.log(`State formation element: tag=${element.tagName}, class=${element.className}, text="${element.textContent.trim()}"`);
                }
            }""")

            # Use JavaScript with specific targeting for state dropdown
            clicked = await self.page.evaluate("""() => {
                console.log("Using specialized approach for State of Formation dropdown");

                // STRATEGY 1: Find by exact "Select State" text in dropdown label
                const stateLabels = Array.from(document.querySelectorAll('.p-dropdown-label'))
                    .filter(el => el.textContent.trim() === 'Select State');

                console.log(`Found ${stateLabels.length} elements with exact "Select State" text`);

                if (stateLabels.length > 0) {
                    // Find the parent dropdown container and click it
                    const dropdownContainer = stateLabels[0].closest('.p-dropdown');
                    if (dropdownContainer) {
                        console.log(`Found and clicking dropdown container with "Select State" text`);
                        dropdownContainer.click();
                        return true;
                    } else {
                        // If no container found, click the element itself
                        console.log(`Clicking "Select State" element directly`);
                        stateLabels[0].click();
                        return true;
                    }
                }

                // STRATEGY 2: Find by elements containing "State of Formation" text
                const stateFormationElements = Array.from(document.querySelectorAll('*'))
                    .filter(el => {
                        const text = el.textContent.toLowerCase().trim();
                        return text.includes('state') && text.includes('formation');
                    });

                console.log(`Found ${stateFormationElements.length} elements with "State of Formation" text`);

                if (stateFormationElements.length > 0) {
                    for (const element of stateFormationElements) {
                        console.log(`Found element with text: "${element.textContent.trim()}"`);

                        // Look for nearby dropdowns
                        // First check if this element is near a dropdown
                        let currentElement = element;
                        let depth = 0;
                        const MAX_DEPTH = 5;

                        // Look upward in the DOM
                        while (currentElement && depth < MAX_DEPTH) {
                            // Check siblings of this element
                            let sibling = currentElement.nextElementSibling;
                            while (sibling) {
                                const dropdown = sibling.querySelector('.p-dropdown');
                                if (dropdown) {
                                    console.log(`Found dropdown in sibling of "State of Formation" element`);
                                    dropdown.click();
                                    return true;
                                }

                                if (sibling.classList.contains('p-dropdown')) {
                                    console.log(`Found dropdown sibling of "State of Formation" element`);
                                    sibling.click();
                                    return true;
                                }

                                sibling = sibling.nextElementSibling;
                            }

                            // Check parent's siblings
                            currentElement = currentElement.parentElement;
                            depth++;
                        }
                    }
                }

                // STRATEGY 3: Find by looking at the DOM structure - state dropdown is typically next to a label with asterisk
                const stateLabelsWithAsterisk = Array.from(document.querySelectorAll('label, span, div'))
                    .filter(el => {
                        const text = el.textContent.trim();
                        return text.includes('State of Formation') && text.includes('*');
                    });

                console.log(`Found ${stateLabelsWithAsterisk.length} state labels with asterisk`);

                if (stateLabelsWithAsterisk.length > 0) {
                    for (const label of stateLabelsWithAsterisk) {
                        // Look for nearby dropdowns
                        let parent = label.parentElement;
                        if (parent) {
                            // Look for dropdown in siblings of parent
                            let sibling = parent.nextElementSibling;
                            while (sibling) {
                                const dropdown = sibling.querySelector('.p-dropdown');
                                if (dropdown) {
                                    console.log(`Found dropdown in sibling of parent of state label with asterisk`);
                                    dropdown.click();
                                    return true;
                                }

                                if (sibling.classList.contains('p-dropdown')) {
                                    console.log(`Found dropdown sibling of parent of state label with asterisk`);
                                    sibling.click();
                                    return true;
                                }

                                sibling = sibling.nextElementSibling;
                            }
                        }
                    }
                }

                // STRATEGY 4: Use positional information - state dropdown is typically the second dropdown
                // But first verify we're not clicking the entity type dropdown
                const allDropdowns = document.querySelectorAll('.p-dropdown');
                console.log(`Found ${allDropdowns.length} total dropdowns on the page`);

                // Log all dropdowns for debugging
                for (let i = 0; i < allDropdowns.length; i++) {
                    const dropdown = allDropdowns[i];
                    const label = dropdown.querySelector('.p-dropdown-label');
                    const labelText = label ? label.textContent.trim() : '';
                    console.log(`Dropdown #${i}: text="${labelText}"`);
                }

                // CRITICAL FIX: If we have at least 2 dropdowns, ALWAYS click the second one for state
                // This is based on the observation that the state dropdown is consistently the second one
                if (allDropdowns.length >= 2) {
                    console.log(`CRITICAL FIX: Always clicking the second dropdown for state`);
                    allDropdowns[1].click();
                    return true;
                }

                // STRATEGY 5: Last resort - try to find any dropdown with "State" in its label
                const stateTextDropdowns = Array.from(document.querySelectorAll('.p-dropdown'))
                    .filter(dropdown => {
                        const label = dropdown.querySelector('.p-dropdown-label');
                        return label && label.textContent.toLowerCase().includes('state');
                    });

                if (stateTextDropdowns.length > 0) {
                    console.log(`Found dropdown with "State" in its label`);
                    stateTextDropdowns[0].click();
                    return true;
                }

                // If all else fails and we have multiple dropdowns, try the second one
                if (allDropdowns.length > 1) {
                    console.log(`Falling back to second dropdown as last resort`);
                    allDropdowns[1].click();
                    return true;
                } else if (allDropdowns.length === 1) {
                    // If there's only one dropdown, it might be a different UI state
                    console.log(`Only one dropdown found, clicking it as last resort`);
                    allDropdowns[0].click();
                    return true;
                }

                return false;
            }""")

            if clicked:
                self.speak("Clicked the State of Formation dropdown")
                await self.page.wait_for_timeout(1000)  # Wait a bit for dropdown to open
                return True
            else:
                # If specialized approach failed, fall back to generic method
                self.speak("Specialized approach failed, trying generic method...")
                return await self._click_generic_dropdown("State of Formation")
        except Exception as e:
            print(f"Error with specialized state dropdown click: {e}")
            self.speak("Error with specialized approach, trying generic method...")
            return await self._click_generic_dropdown("State of Formation")

    async def _handle_state_selection(self, state_name):
        """Handle state selection from dropdown"""
        self.speak(f"Looking for state {state_name}...")

        # First, make sure we're working with a clean state name
        state_name = state_name.strip()

        # Handle common state name variations
        state_name_map = {
            "new york": "New York",
            "ny": "New York",
            "california": "California",
            "ca": "California",
            "texas": "Texas",
            "tx": "Texas",
            "florida": "Florida",
            "fl": "Florida",
            "illinois": "Illinois",
            "il": "Illinois",
            "pennsylvania": "Pennsylvania",
            "pa": "Pennsylvania",
            "ohio": "Ohio",
            "oh": "Ohio",
            "georgia": "Georgia",
            "ga": "Georgia",
            "north carolina": "North Carolina",
            "nc": "North Carolina",
            "michigan": "Michigan",
            "mi": "Michigan",
            "new jersey": "New Jersey",
            "nj": "New Jersey",
            "virginia": "Virginia",
            "va": "Virginia",
            "washington": "Washington",
            "wa": "Washington",
            "arizona": "Arizona",
            "az": "Arizona",
            "massachusetts": "Massachusetts",
            "ma": "Massachusetts",
            "tennessee": "Tennessee",
            "tn": "Tennessee",
            "indiana": "Indiana",
            "in": "Indiana",
            "missouri": "Missouri",
            "mo": "Missouri",
            "maryland": "Maryland",
            "md": "Maryland",
            "wisconsin": "Wisconsin",
            "wi": "Wisconsin",
            "minnesota": "Minnesota",
            "mn": "Minnesota",
            "colorado": "Colorado",
            "co": "Colorado",
            "alabama": "Alabama",
            "al": "Alabama",
            "south carolina": "South Carolina",
            "sc": "South Carolina",
            "louisiana": "Louisiana",
            "la": "Louisiana",
            "kentucky": "Kentucky",
            "ky": "Kentucky",
            "oregon": "Oregon",
            "or": "Oregon",
            "oklahoma": "Oklahoma",
            "ok": "Oklahoma",
            "connecticut": "Connecticut",
            "ct": "Connecticut",
            "utah": "Utah",
            "ut": "Utah",
            "iowa": "Iowa",
            "ia": "Iowa",
            "nevada": "Nevada",
            "nv": "Nevada",
            "arkansas": "Arkansas",
            "ar": "Arkansas",
            "mississippi": "Mississippi",
            "ms": "Mississippi",
            "kansas": "Kansas",
            "ks": "Kansas",
            "new mexico": "New Mexico",
            "nm": "New Mexico",
            "nebraska": "Nebraska",
            "ne": "Nebraska",
            "west virginia": "West Virginia",
            "wv": "West Virginia",
            "idaho": "Idaho",
            "id": "Idaho",
            "hawaii": "Hawaii",
            "hi": "Hawaii",
            "new hampshire": "New Hampshire",
            "nh": "New Hampshire",
            "maine": "Maine",
            "me": "Maine",
            "montana": "Montana",
            "mt": "Montana",
            "rhode island": "Rhode Island",
            "ri": "Rhode Island",
            "delaware": "Delaware",
            "de": "Delaware",
            "south dakota": "South Dakota",
            "sd": "South Dakota",
            "north dakota": "North Dakota",
            "nd": "North Dakota",
            "alaska": "Alaska",
            "ak": "Alaska",
            "vermont": "Vermont",
            "vt": "Vermont",
            "wyoming": "Wyoming",
            "wy": "Wyoming",
            "district of columbia": "District of Columbia",
            "dc": "District of Columbia",
            "washington dc": "District of Columbia",
            "washington d.c.": "District of Columbia",
        }

        # Normalize the state name
        normalized_state_name = state_name.lower()
        if normalized_state_name in state_name_map:
            state_name = state_name_map[normalized_state_name]
            print(f"Normalized state name to: {state_name}")

        # Get the current page context
        context = await self._get_page_context()

        # First try using the LLM to generate actions
        action_data = await self.llm_provider.get_actions(f"select state {state_name}", context)

        if 'actions' in action_data and len(action_data['actions']) > 0:
            # Try to execute the LLM-generated actions
            success = await self._execute_actions(action_data)
            if success:
                self.speak(f"Selected state {state_name}")
                return True
            else:
                self.speak("LLM-generated actions failed, trying fallback methods...")

        # Try a direct approach for searching and selecting a state
        try:
            # First try to find and click the search input in the dropdown
            search_result = await self.page.evaluate("""(stateName) => {
                // First check if the dropdown is already open
                const dropdownPanel = document.querySelector('.p-dropdown-panel');
                if (!dropdownPanel || window.getComputedStyle(dropdownPanel).display === 'none') {
                    // Dropdown is not open, find and click it first
                    console.log("Dropdown not open, opening it first");

                    // EXTREME DIRECT APPROACH: Force click on the second dropdown only
                    console.log("EXTREME DIRECT APPROACH: Force click on the second dropdown only");

                    // Get all dropdowns
                    const allDropdowns = document.querySelectorAll('.p-dropdown');
                    console.log(`Found ${allDropdowns.length} dropdowns total`);

                    // Log all dropdowns for debugging
                    for (let i = 0; i < allDropdowns.length; i++) {
                        const dropdown = allDropdowns[i];
                        const label = dropdown.querySelector('.p-dropdown-label');
                        console.log(`Dropdown #${i}: label text="${label ? label.textContent.trim() : 'none'}"`);
                    }

                    // CRITICAL: We know the second dropdown is the State of Formation
                    // So we'll directly click the second dropdown (index 1) if it exists
                    if (allDropdowns.length > 1) {
                        console.log("DIRECTLY clicking the SECOND dropdown (index 1)");
                        return {
                            success: true,
                            message: "Directly clicking second dropdown",
                            action: () => {
                                allDropdowns[1].click();
                                return true;
                            }
                        };
                    }

                    // If there's only one dropdown, we can't be sure which one it is
                    console.log("Not enough dropdowns found");
                    return { success: false, message: "Not enough dropdowns found" };

                    // If we still haven't found the dropdown, try one last approach
                    // Look for elements with "State of Formation" text
                    const stateFormationElements = allLabels.filter(el =>
                        el.textContent.toLowerCase().includes('state') &&
                        el.textContent.toLowerCase().includes('formation'));

                    if (stateFormationElements.length > 0) {
                        console.log(`Found ${stateFormationElements.length} elements with "State of Formation" text`);

                        // Try to find a dropdown near each element
                        for (const element of stateFormationElements) {
                            // Look for the closest dropdown
                            let current = element;
                            let foundDropdown = null;

                            // Check siblings
                            while (current.nextElementSibling) {
                                current = current.nextElementSibling;
                                if (current.classList.contains('p-dropdown')) {
                                    foundDropdown = current;
                                    break;
                                }
                                const nestedDropdown = current.querySelector('.p-dropdown');
                                if (nestedDropdown) {
                                    foundDropdown = nestedDropdown;
                                    break;
                                }
                            }

                            if (foundDropdown) {
                                console.log("Found dropdown after State of Formation element");
                                foundDropdown.click();
                                return { success: true, message: "Opened dropdown after State of Formation element", needsSearch: true };
                            }
                        }
                    }

                    // TARGET APPROACH: Find dropdown with "Select State" text
                    console.log("TARGET APPROACH: Finding dropdown with 'Select State' text");

                    // Find all dropdown labels
                    const allDropdownLabels = document.querySelectorAll('.p-dropdown-label');
                    console.log(`Found ${allDropdownLabels.length} dropdown labels`);

                    // Log all dropdown labels for debugging
                    for (let i = 0; i < allDropdownLabels.length; i++) {
                        const label = allDropdownLabels[i];
                        console.log(`Dropdown label #${i}: text="${label.textContent.trim()}"`);
                    }

                    // Find the label with "Select State" text
                    let stateLabel = null;
                    for (let i = 0; i < allDropdownLabels.length; i++) {
                        const label = allDropdownLabels[i];
                        if (label.textContent.trim() === 'Select State') {
                            console.log(`Found "Select State" label at index ${i}`);
                            stateLabel = label;
                            break;
                        }
                    }

                    if (stateLabel) {
                        // Find the parent dropdown container and click it
                        const dropdownContainer = stateLabel.closest('.p-dropdown');
                        if (dropdownContainer) {
                            console.log(`Found and clicking dropdown container for "Select State"`);
                            dropdownContainer.click();
                            return { success: true, message: "Opened dropdown with 'Select State' text", needsSearch: true };
                        } else {
                            console.log(`Found "Select State" label but couldn't find parent dropdown`);
                            // Try clicking the label directly as a fallback
                            stateLabel.click();
                            return { success: true, message: "Clicked 'Select State' label directly", needsSearch: true };
                        }
                    }

                    // Fallback: If we can't find by text, try the second dropdown
                    console.log("Couldn't find dropdown with 'Select State' text, trying second dropdown");
                    const allDropdowns = document.querySelectorAll('.p-dropdown');
                    if (allDropdowns.length > 1) {
                        console.log(`Falling back to second dropdown (index 1) out of ${allDropdowns.length}`);
                        allDropdowns[1].click();
                        return { success: true, message: "Opened second dropdown as fallback", needsSearch: true };
                    }

                    console.log("Could not find state dropdown");
                    return { success: false, message: "Could not find state dropdown" };
                } else {
                    console.log("Dropdown is already open");
                    return { success: true, message: "Dropdown already open", needsSearch: true };
                }
            }""", state_name)

            print(f"Search dropdown result: {search_result}")

            if search_result and search_result.get('success'):
                # Wait for dropdown panel to appear
                await self.page.wait_for_selector('.p-dropdown-panel', timeout=2000)

                # Now try to search for the state
                search_and_select_result = await self.page.evaluate("""(stateName) => {
                    // IMPORTANT: Make sure we're working with the State of Formation dropdown
                    // First check if we're in the correct dropdown panel
                    const dropdownPanels = document.querySelectorAll('.p-dropdown-panel');
                    console.log(`Found ${dropdownPanels.length} dropdown panels`);

                    // Check each panel to see which one is visible
                    let visiblePanel = null;
                    for (let i = 0; i < dropdownPanels.length; i++) {
                        const panel = dropdownPanels[i];
                        if (window.getComputedStyle(panel).display !== 'none') {
                            console.log(`Panel #${i} is visible`);
                            visiblePanel = panel;
                            break;
                        }
                    }

                    if (!visiblePanel) {
                        console.log("No visible dropdown panel found");
                        return { success: false, message: "No visible dropdown panel found" };
                    }

                    // Check if this is the State dropdown by looking for state names
                    const stateNames = ['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California',
                        'Colorado', 'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii',
                        'Idaho', 'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana',
                        'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi',
                        'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey',
                        'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma',
                        'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
                        'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington',
                        'West Virginia', 'Wisconsin', 'Wyoming', 'District of Columbia'];

                    const panelItems = visiblePanel.querySelectorAll('.p-dropdown-item');
                    let isStateDropdown = false;

                    // Check if any of the items match state names
                    for (const item of panelItems) {
                        const itemText = item.textContent.trim();
                        if (stateNames.includes(itemText)) {
                            isStateDropdown = true;
                            console.log(`Found state name "${itemText}" in dropdown, confirming this is the state dropdown`);
                            break;
                        }
                    }

                    // If this doesn't appear to be the state dropdown, try to close it and open the correct one
                    if (!isStateDropdown && dropdownPanels.length > 1) {
                        console.log("This doesn't appear to be the state dropdown, trying to close it");

                        // Click outside to close the current dropdown
                        document.body.click();

                        // Wait a moment for the dropdown to close
                        console.log("Waiting for dropdown to close...");

                        // Return a special result indicating we need to try again with the state dropdown
                        return {
                            success: false,
                            message: "Wrong dropdown opened, need to try with state dropdown",
                            needStateDropdown: true
                        };
                    }

                    // Look for search input in the dropdown panel
                    const searchInput = visiblePanel.querySelector('.p-dropdown-filter');
                    if (searchInput) {
                        console.log("Found search input, typing state name");
                        // Clear any existing value
                        searchInput.value = '';
                        // Type the state name
                        searchInput.value = stateName;
                        searchInput.dispatchEvent(new Event('input', { bubbles: true }));
                        searchInput.dispatchEvent(new Event('change', { bubbles: true }));

                        console.log(`Typed "${stateName}" into search input`);

                        // Wait a moment for filtering to take effect
                        setTimeout(() => {}, 500);

                        // Now find and click the matching state option
                        const stateOptions = Array.from(visiblePanel.querySelectorAll('.p-dropdown-item'));
                        console.log(`Found ${stateOptions.length} options after filtering`);

                        // First try exact match
                        let matchedOption = stateOptions.find(option =>
                            option.textContent.trim().toLowerCase() === stateName.toLowerCase());

                        // If no exact match, try starts with
                        if (!matchedOption) {
                            matchedOption = stateOptions.find(option =>
                                option.textContent.trim().toLowerCase().startsWith(stateName.toLowerCase()));
                        }

                        // If still no match, try contains
                        if (!matchedOption) {
                            matchedOption = stateOptions.find(option =>
                                option.textContent.trim().toLowerCase().includes(stateName.toLowerCase()));
                        }

                        if (matchedOption) {
                            console.log(`Found matching state option: ${matchedOption.textContent.trim()}`);
                            matchedOption.click();
                            return { success: true, message: `Selected state ${matchedOption.textContent.trim()}` };
                        } else {
                            return { success: false, message: "No matching state found after search" };
                        }
                    } else {
                        // No search input, try to find the state directly
                        console.log("No search input found, looking for state directly");

                        const stateOptions = Array.from(visiblePanel.querySelectorAll('.p-dropdown-item'));
                        console.log(`Found ${stateOptions.length} state options`);

                        // First try exact match
                        let matchedOption = stateOptions.find(option =>
                            option.textContent.trim().toLowerCase() === stateName.toLowerCase());

                        // If no exact match, try starts with
                        if (!matchedOption) {
                            matchedOption = stateOptions.find(option =>
                                option.textContent.trim().toLowerCase().startsWith(stateName.toLowerCase()));
                        }

                        // If still no match, try contains
                        if (!matchedOption) {
                            matchedOption = stateOptions.find(option =>
                                option.textContent.trim().toLowerCase().includes(stateName.toLowerCase()));
                        }

                        if (matchedOption) {
                            console.log(`Found matching state option: ${matchedOption.textContent.trim()}`);
                            matchedOption.click();
                            return { success: true, message: `Selected state ${matchedOption.textContent.trim()}` };
                        } else {
                            return { success: false, message: "No matching state found" };
                        }
                    }
                }""", state_name)

                print(f"Search and select result: {search_and_select_result}")

                if search_and_select_result and search_and_select_result.get('success'):
                    self.speak(search_and_select_result.get('message', f"Selected state {state_name}"))
                    return True
                elif search_and_select_result and search_and_select_result.get('needStateDropdown'):
                    # Wrong dropdown was opened, try to close it and open the state dropdown
                    self.speak("Opening the state dropdown instead...")

                    # Wait a moment for the wrong dropdown to close
                    await self.page.wait_for_timeout(1000)

                    # Try to click the state dropdown specifically
                    try:
                        # TARGET APPROACH: Find dropdown with "Select State" text
                        clicked = await self.page.evaluate("""() => {
                            console.log("TARGET APPROACH: Finding dropdown with 'Select State' text");

                            // Find all dropdown labels
                            const allDropdownLabels = document.querySelectorAll('.p-dropdown-label');
                            console.log(`Found ${allDropdownLabels.length} dropdown labels`);

                            // Log all dropdown labels for debugging
                            for (let i = 0; i < allDropdownLabels.length; i++) {
                                const label = allDropdownLabels[i];
                                console.log(`Dropdown label #${i}: text="${label.textContent.trim()}"`);
                            }

                            // Find the label with "Select State" text
                            let stateLabel = null;
                            for (let i = 0; i < allDropdownLabels.length; i++) {
                                const label = allDropdownLabels[i];
                                if (label.textContent.trim() === 'Select State') {
                                    console.log(`Found "Select State" label at index ${i}`);
                                    stateLabel = label;
                                    break;
                                }
                            }

                            if (stateLabel) {
                                // Find the parent dropdown container and click it
                                const dropdownContainer = stateLabel.closest('.p-dropdown');
                                if (dropdownContainer) {
                                    console.log(`Found and clicking dropdown container for "Select State"`);
                                    dropdownContainer.click();
                                    return true;
                                } else {
                                    console.log(`Found "Select State" label but couldn't find parent dropdown`);
                                    // Try clicking the label directly as a fallback
                                    stateLabel.click();
                                    return true;
                                }
                            }

                            // Fallback: If we can't find by text, try the second dropdown
                            console.log("Couldn't find dropdown with 'Select State' text, trying second dropdown");
                            const allDropdowns = document.querySelectorAll('.p-dropdown');
                            if (allDropdowns.length > 1) {
                                console.log(`Falling back to second dropdown (index 1) out of ${allDropdowns.length}`);
                                allDropdowns[1].click();
                                return true;
                            }

                            console.log("Could not find state dropdown");
                            return false;
                        }""")

                        if clicked:
                            # Wait for dropdown panel to appear
                            await self.page.wait_for_selector('.p-dropdown-panel', timeout=2000)

                            # Try the search again
                            return await self._handle_state_selection(state_name)
                    except Exception as e:
                        print(f"Error trying to click state dropdown: {e}")
        except Exception as e:
            print(f"Error with direct state search and selection: {e}")

        # First try to find and click the state dropdown to open it
        dropdown_selectors = await self._get_llm_selectors("find state dropdown", context)
        dropdown_clicked = False

        for selector in dropdown_selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    await self._retry_click(selector, "state dropdown")
                    self.speak("Clicked on state dropdown")
                    await self.page.wait_for_timeout(1000)
                    dropdown_clicked = True
                    break
            except Exception as e:
                print(f"Error with dropdown selector {selector}: {e}")
                continue

        if not dropdown_clicked:
            # Try JavaScript to find and click the state dropdown
            try:
                clicked = await self.page.evaluate("""() => {
                    // Specifically looking for State of Formation dropdown
                    console.log("Specifically looking for State of Formation dropdown");

                    // First try to find the exact dropdown element with "Select State" text or a state name
                    const stateNames = ['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California',
                        'Colorado', 'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii',
                        'Idaho', 'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana',
                        'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi',
                        'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey',
                        'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma',
                        'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
                        'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington',
                        'West Virginia', 'Wisconsin', 'Wyoming', 'District of Columbia'];

                    const selectStateElements = Array.from(document.querySelectorAll('.p-dropdown-label'))
                        .filter(el => {
                            const text = el.textContent.trim();
                            return text === 'Select State' || stateNames.includes(text);
                        });

                    if (selectStateElements.length > 0) {
                        console.log(`Found ${selectStateElements.length} elements with exact "Select State" text`);

                        for (const element of selectStateElements) {
                            console.log(`Found element with text: "${element.textContent.trim()}"`);

                            // Find the parent dropdown container and click it
                            const dropdownContainer = element.closest('.p-dropdown');
                            if (dropdownContainer) {
                                console.log(`Found dropdown container for "Select State"`);
                                dropdownContainer.click();
                                return true;
                            }

                            // If no parent dropdown container, try clicking the element itself
                            console.log(`Clicking "Select State" element directly`);
                            element.click();
                            return true;
                        }
                    }

                    // If we couldn't find the exact "Select State" element, look for elements containing "State of Formation" text
                    const stateLabels = Array.from(document.querySelectorAll('*'))
                        .filter(el => {
                            const text = el.textContent.trim().toLowerCase();
                            return text.includes('state') && text.includes('formation');
                        });

                    console.log(`Found ${stateLabels.length} elements with "State of Formation" text`);

                    // Try to find dropdowns near these state labels
                    for (const label of stateLabels) {
                        console.log(`Found state label with text: "${label.textContent.trim()}"`);

                        // Check if this element is a label with a "for" attribute
                        const forAttribute = label.getAttribute('for');
                        if (forAttribute) {
                            const associatedElement = document.getElementById(forAttribute);
                            if (associatedElement) {
                                console.log(`Found associated element by ID: ${forAttribute}`);
                                associatedElement.click();
                                return true;
                            }
                        }

                        // Check next sibling
                        let sibling = label.nextElementSibling;
                        while (sibling) {
                            if (sibling.classList.contains('p-dropdown') ||
                                sibling.getAttribute('role') === 'combobox' ||
                                sibling.tagName === 'SELECT') {
                                console.log(`Found dropdown in next sibling of state label`);
                                sibling.click();
                                return true;
                            }

                            const dropdownInSibling = sibling.querySelector('.p-dropdown, [role="combobox"], select');
                            if (dropdownInSibling) {
                                console.log(`Found dropdown inside sibling of state label`);
                                dropdownInSibling.click();
                                return true;
                            }

                            sibling = sibling.nextElementSibling;
                        }

                        // Check parent element
                        const parent = label.parentElement;
                        if (parent) {
                            // Look for dropdown in the parent element
                            const dropdownInParent = parent.querySelector('.p-dropdown, [role="combobox"], select');
                            if (dropdownInParent) {
                                console.log(`Found dropdown in parent of state label`);
                                dropdownInParent.click();
                                return true;
                            }

                            // Look for siblings of the parent
                            const parentSibling = parent.nextElementSibling;
                            if (parentSibling) {
                                const dropdownInParentSibling = parentSibling.querySelector('.p-dropdown, [role="combobox"], select');
                                if (dropdownInParentSibling) {
                                    console.log(`Found dropdown in parent's sibling of state label`);
                                    dropdownInParentSibling.click();
                                    return true;
                                }
                            }
                        }
                    }

                    // If we still couldn't find the state dropdown by label, try by index
                    const allDropdowns = document.querySelectorAll('.p-dropdown, [role="combobox"], select');
                    console.log(`Found ${allDropdowns.length} total dropdowns on the page`);

                    // Log all dropdowns for debugging
                    for (let i = 0; i < allDropdowns.length; i++) {
                        const dropdown = allDropdowns[i];
                        console.log(`Dropdown #${i}: class=${dropdown.className}, text=${dropdown.textContent.trim()}`);
                    }

                    // For state of formation, use index 1 (second dropdown)
                    if (allDropdowns.length > 1) {
                        console.log(`Clicking the SECOND dropdown (state of formation) on the page`);
                        allDropdowns[1].click();
                        return true;
                    } else if (allDropdowns.length > 0) {
                        console.log(`Clicking first dropdown as last resort`);
                        allDropdowns[0].click();
                        return true;
                    }

                    return false;
                }""")

                if clicked:
                    self.speak("Found and clicked state dropdown using JavaScript")
                    await self.page.wait_for_timeout(1000)
                    dropdown_clicked = True
            except Exception as e:
                print(f"Error with JavaScript dropdown click: {e}")

        # Now try to select the state from the dropdown
        # Wait for dropdown panel to appear
        try:
            await self.page.wait_for_selector('.p-dropdown-panel, .dropdown-menu, .select-dropdown', timeout=2000)
            print("Dropdown panel appeared")
        except Exception as e:
            print(f"Dropdown panel did not appear: {e}")

        # Try to find and click the state option
        option_selectors = await self._get_llm_selectors(f"find option '{state_name}' in dropdown", context)

        for selector in option_selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    await self._retry_click(selector, f"state option '{state_name}'")
                    self.speak(f"Selected state {state_name}")
                    await self.page.wait_for_timeout(1000)
                    return True
            except Exception as e:
                print(f"Error with option selector {selector}: {e}")
                continue

        # Try JavaScript to find and click the state
        try:
            clicked = await self.page.evaluate("""(stateName) => {
                // Function to find state elements with exact and partial matching
                const findStateOption = (text) => {
                    // PrimeNG/PrimeReact specific selectors (most specific first)
                    const primeItems = document.querySelectorAll('.p-dropdown-item, .p-dropdown-items li, li.p-dropdown-item');

                    // Try exact match first
                    for (const item of primeItems) {
                        if (item.textContent.trim().toLowerCase() === text.toLowerCase() ||
                            item.getAttribute('aria-label')?.toLowerCase() === text.toLowerCase()) {
                            console.log('Found exact match PrimeNG/React state item:', item.textContent);
                            return item;
                        }
                    }

                    // Standard select options
                    const options = document.querySelectorAll('option');
                    for (const option of options) {
                        if (option.textContent.trim().toLowerCase() === text.toLowerCase()) {
                            console.log('Found exact match select option:', option.textContent);
                            return option;
                        }
                    }

                    // Generic dropdown items
                    const items = document.querySelectorAll('li[role="option"], .dropdown-item');
                    for (const item of items) {
                        if (item.textContent.trim().toLowerCase() === text.toLowerCase()) {
                            console.log('Found exact match dropdown item:', item.textContent);
                            return item;
                        }
                    }

                    // Any list item with matching text
                    const listItems = document.querySelectorAll('li');
                    for (const item of listItems) {
                        if (item.textContent.trim().toLowerCase() === text.toLowerCase()) {
                            console.log('Found exact match list item:', item.textContent);
                            return item;
                        }
                    }

                    // If no exact match, try partial matches

                    // PrimeNG/PrimeReact items
                    for (const item of primeItems) {
                        if (item.textContent.trim().toLowerCase().includes(text.toLowerCase())) {
                            console.log('Found partial match PrimeNG/React state item:', item.textContent);
                            return item;
                        }
                    }

                    // Standard select options
                    for (const option of options) {
                        if (option.textContent.trim().toLowerCase().includes(text.toLowerCase())) {
                            console.log('Found partial match select option:', option.textContent);
                            return option;
                        }
                    }

                    // Generic dropdown items
                    for (const item of items) {
                        if (item.textContent.trim().toLowerCase().includes(text.toLowerCase())) {
                            console.log('Found partial match dropdown item:', item.textContent);
                            return item;
                        }
                    }

                    // Any list item with matching text
                    for (const item of listItems) {
                        if (item.textContent.trim().toLowerCase().includes(text.toLowerCase())) {
                            console.log('Found partial match list item:', item.textContent);
                            return item;
                        }
                    }

                    // If still no match, try any visible element with the text
                    const allElements = document.querySelectorAll('*');
                    for (const el of allElements) {
                        if (el.textContent.trim().toLowerCase() === text.toLowerCase() &&
                            window.getComputedStyle(el).display !== 'none' &&
                            window.getComputedStyle(el).visibility !== 'hidden') {
                            console.log('Found matching text in element:', el.tagName, el.textContent);
                            return el;
                        }
                    }

                    return null;
                };

                const stateOption = findStateOption(stateName);
                if (stateOption) {
                    console.log(`Clicking state option: ${stateOption.textContent.trim()}`);
                    stateOption.click();
                    return true;
                }

                console.log(`Could not find state option: ${stateName}`);
                return false;
            }""", state_name)

            if clicked:
                self.speak(f"Selected state {state_name}")
                await self.page.wait_for_timeout(1000)
                return True
            else:
                self.speak(f"Could not find state {state_name} in the dropdown")
        except Exception as e:
            print(f"Error with JavaScript state selection: {e}")

        return False

    async def _get_page_context(self):
        """Get current page context"""
        try:
            await self.page.wait_for_timeout(1000)

            input_fields = []
            inputs = self.page.locator("input:visible, textarea:visible, select:visible")
            count = await inputs.count()

            for i in range(min(count, 10)):
                try:
                    field = inputs.nth(i)
                    field_info = {
                        "tag": await field.evaluate("el => el.tagName.toLowerCase()"),
                        "type": await field.evaluate("el => el.type || ''"),
                        "id": await field.evaluate("el => el.id || ''"),
                        "name": await field.evaluate("el => el.name || ''"),
                        "placeholder": await field.evaluate("el => el.placeholder || ''"),
                        "aria-label": await field.evaluate("el => el.getAttribute('aria-label') || ''")
                    }
                    input_fields.append(field_info)
                except Exception as e:
                    print(f"Error getting input field info: {e}")
                    pass

            menu_items = []
            try:
                menus = self.page.locator(
                    "[role='menubar'] [role='menuitem'], .p-menuitem, nav a, .navigation a, .menu a, header a")
                menu_count = await menus.count()

                for i in range(min(menu_count, 20)):
                    try:
                        menu_item = menus.nth(i)
                        text = await menu_item.inner_text()
                        text = text.strip()
                        if text:
                            has_submenu = await menu_item.locator(
                                ".p-submenu-icon, [class*='submenu'], [class*='dropdown'], [class*='caret']").count() > 0
                            menu_items.append({
                                "text": text,
                                "has_submenu": has_submenu
                            })
                    except Exception as e:
                        print(f"Error getting menu item: {e}")
                        pass
            except Exception as e:
                print(f"Error getting menu items: {e}")
                pass

            buttons = []
            try:
                button_elements = self.page.locator(
                    "button:visible, [role='button']:visible, input[type='submit']:visible, input[type='button']:visible")
                button_count = await button_elements.count()

                for i in range(min(button_count, 10)):
                    try:
                        button = button_elements.nth(i)
                        text = await button.inner_text()
                        text = text.strip()
                        buttons.append({
                            "text": text,
                            "id": await button.evaluate("el => el.id || ''"),
                            "class": await button.evaluate("el => el.className || ''"),
                            "type": await button.evaluate("el => el.type || ''")
                        })
                    except Exception as e:
                        print(f"Error getting button: {e}")
                        pass
            except Exception as e:
                print(f"Error getting buttons: {e}")
                pass

            body_locator = self.page.locator("body")
            inner_text = await body_locator.inner_text()
            inner_html = await body_locator.inner_html()

            # Create a PageContext object
            page_context = PageContext(
                url=self.page.url,
                title=await self.page.title(),
                text=inner_text[:1000],
                html=self._filter_html(inner_html[:4000]),
                input_fields=input_fields,
                menu_items=menu_items,
                buttons=buttons
            )

            # Return as dictionary for compatibility with existing code
            return page_context.to_dict()
        except Exception as e:
            print(f"Context error: {e}")
            return {}

    async def _check_for_input_fields(self):
        """Check if there are any input fields on the page"""
        try:
            # Use JavaScript to check for form elements directly in the DOM
            # This is more reliable than using Playwright selectors
            form_elements = await self.page.evaluate("""() => {
                // Check for specific elements we know exist in the form
                const emailField = document.getElementById('floating_outlined3');
                const passwordField = document.getElementById('floating_outlined15');
                const signInButton = document.getElementById('signInButton');

                // Check for any input elements
                const inputs = document.querySelectorAll('input');
                const forms = document.querySelectorAll('form');

                // Log what we found for debugging
                console.log('DOM inspection results:', {
                    emailField: emailField ? true : false,
                    passwordField: passwordField ? true : false,
                    signInButton: signInButton ? true : false,
                    inputCount: inputs.length,
                    formCount: forms.length
                });

                // Return detailed information about what we found
                return {
                    hasEmailField: emailField ? true : false,
                    hasPasswordField: passwordField ? true : false,
                    hasSignInButton: signInButton ? true : false,
                    inputCount: inputs.length,
                    formCount: forms.length,

                    // Include details about inputs for debugging
                    inputs: Array.from(inputs).slice(0, 5).map(input => ({
                        id: input.id,
                        type: input.type,
                        name: input.name,
                        placeholder: input.placeholder,
                        isVisible: input.offsetParent !== null
                    }))
                };
            }""")

            # Log the results
            print(f"DOM inspection results: {form_elements}")

            # Check if we found any of the specific elements
            if form_elements.get('hasEmailField'):
                print("Found email field with ID #floating_outlined3")
                return True

            if form_elements.get('hasPasswordField'):
                print("Found password field with ID #floating_outlined15")
                return True

            if form_elements.get('hasSignInButton'):
                print("Found sign in button with ID #signInButton")
                return True

            # Check if we found any inputs
            if form_elements.get('inputCount', 0) > 0:
                print(f"Found {form_elements.get('inputCount')} input elements")
                return True

            # Check if we found any forms
            if form_elements.get('formCount', 0) > 0:
                print(f"Found {form_elements.get('formCount')} form elements")
                return True

            print("No input fields or forms found in the DOM")
            return False
        except Exception as e:
            print(f"Error checking for input fields: {e}")
            return False

    def _filter_html(self, html):
        """Filter HTML to focus on important elements"""
        return re.sub(
            r'<(input|button|a|form|select|textarea|div|ul|li)[^>]*>',
            lambda m: m.group(0) + '\n',
            html
        )[:3000]

    async def _get_actions(self, command):
        """Get actions for a command using LLM provider"""
        context = await self._get_page_context()

        try:
            # Use the LLM provider to get actions
            actions = await self.llm_provider.get_actions(command, context)
            print("🔍 Raw LLM response:\n", actions)
            return actions
        except Exception as e:
            print(f"LLM Error: {e}")
            return {"error": str(e)}

    # These methods are now handled by the LLM provider

    async def _execute_actions(self, action_data):
        """Execute actions"""
        if 'error' in action_data:
            self.speak("⚠️ Action could not be completed. Switching to fallback...")
            return False

        result = InteractionResult(success=True, message="Actions executed successfully")

        for action in action_data.get('actions', []):
            try:
                await self._perform_action(action)
                await self.page.wait_for_timeout(1000)
            except Exception as e:
                error_message = f"❌ Failed to {action.get('purpose', 'complete action')}"
                self.speak(error_message)
                print(f"Action Error: {str(e)}")
                result = InteractionResult(success=False, message=error_message, details={"error": str(e)})
                return result.success

        return result.success

    async def _perform_action(self, action):
        """Perform an action"""
        action_type = action.get('action', '').lower()

        if action_type == 'click':
            selector = action.get('selector', '')
            fallbacks = action.get('fallback_selectors', [])
            await self._try_selectors_for_click([selector] + fallbacks, action.get('purpose', 'click element'))
        elif action_type == 'type':
            selector = action.get('selector', '')
            fallbacks = action.get('fallback_selectors', [])
            await self._try_selectors_for_type([selector] + fallbacks, action.get('text', ''), action.get('purpose', 'enter text'))
        elif action_type == 'navigate':
            url = action.get('url', '')
            if url:
                await self.browse_website(url)
            else:
                self.speak("No URL provided for navigation")
        elif action_type == 'hover':
            selector = action.get('selector', '')
            fallbacks = action.get('fallback_selectors', [])
            await self._try_selectors_for_hover([selector] + fallbacks, action.get('purpose', 'hover over element'))
        elif action_type == 'check' or action_type == 'check_checkbox':
            selector = action.get('selector', '')
            fallbacks = action.get('fallback_selectors', [])
            await self._try_selectors_for_check([selector] + fallbacks, action.get('purpose', 'check checkbox'))

    async def _try_selectors_for_click(self, selectors, purpose):
        """Try multiple selectors for clicking"""
        for selector in selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    await self._retry_click(selector, purpose)
                    return InteractionResult.success_result(f"Clicked {purpose}").success
            except Exception as e:
                print(f"Error with click selector {selector}: {e}")
                continue

        error_message = f"Could not find element to {purpose}"
        self.speak(error_message)
        return InteractionResult.failure_result(error_message).success

    async def _try_selectors_for_type(self, selectors, text, purpose, max_retries=3, timeout=30000):
        """Try multiple selectors for typing

        Args:
            selectors: List of CSS selectors to try
            text: Text to type
            purpose: Description of what we're typing (for logging)
            max_retries: Maximum number of retry attempts
            timeout: Timeout in milliseconds for each attempt
        """
        for selector in selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    await self._retry_type(selector, text, purpose, max_retries=max_retries, timeout=timeout)
                    return InteractionResult.success_result(f"Typed {purpose} with text").success
            except Exception as e:
                print(f"Error with type selector {selector}: {e}")
                continue

        error_message = f"Could not find element to {purpose}"
        self.speak(error_message)
        return InteractionResult.failure_result(error_message).success

    async def _try_selectors_for_hover(self, selectors, purpose):
        """Try multiple selectors for hovering"""
        for selector in selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    await self.page.locator(selector).hover()
                    self.speak(f"Hovering over {purpose}")
                    return InteractionResult.success_result(f"Hovered over {purpose}").success
            except Exception as e:
                print(f"Error with hover selector {selector}: {e}")
                continue

        error_message = f"Could not find element to hover over for {purpose}"
        self.speak(error_message)
        return InteractionResult.failure_result(error_message).success

    async def _try_selectors_for_check(self, selectors, purpose):
        """Try multiple selectors for checking checkboxes"""
        for selector in selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    # First try the standard check method
                    try:
                        await self.page.locator(selector).check(timeout=5000)
                        self.speak(f"✓ Checked {purpose}")
                        return InteractionResult.success_result(f"Checked {purpose}").success
                    except Exception as e:
                        print(f"Standard check failed for {selector}, trying click instead: {e}")
                        # If standard check fails, try clicking the checkbox
                        await self.page.locator(selector).click(timeout=5000)
                        self.speak(f"✓ Checked {purpose} by clicking")
                        return InteractionResult.success_result(f"Checked {purpose} by clicking").success
            except Exception as e:
                print(f"Error with checkbox selector {selector}: {e}")
                continue

    async def _check_product_checkbox(self, product_name):
        """Specifically check a product checkbox from a product list

        Args:
            product_name: The name of the product to check
        """
        try:
            # Use JavaScript to find and check the product checkbox
            checked = await self.page.evaluate("""(productName) => {
                console.log("Looking for product checkbox for:", productName);

                // Function to find product checkboxes by product name
                const findProductCheckbox = (name) => {
                    // Normalize the product name for comparison
                    const normalizedName = name.toLowerCase().trim();

                    // Find all product containers
                    const productContainers = document.querySelectorAll('.wizard-card-checkbox-container, .hover-card');
                    console.log(`Found ${productContainers.length} potential product containers`);

                    // Look through each container for matching product text
                    for (const container of productContainers) {
                        const containerText = container.textContent.toLowerCase();

                        // Check if this container has text matching our product name
                        if (containerText.includes(normalizedName)) {
                            console.log(`Found container with text matching "${name}"`);

                            // Look for checkbox in this container
                            const checkbox = container.querySelector('input[type="checkbox"]');
                            if (checkbox) {
                                console.log(`Found standard checkbox in container for "${name}"`);
                                return checkbox;
                            }

                            // Look for PrimeNG/PrimeReact checkbox
                            const primeCheckbox = container.querySelector('.p-checkbox');
                            if (primeCheckbox) {
                                console.log(`Found PrimeNG/React checkbox in container for "${name}"`);
                                return primeCheckbox;
                            }

                            // Look for any element with checkbox class
                            const checkboxElement = container.querySelector('[class*="checkbox"]');
                            if (checkboxElement) {
                                console.log(`Found element with checkbox class in container for "${name}"`);
                                return checkboxElement;
                            }
                        }
                    }

                    // If we couldn't find by container, try to find by proximity to text
                    const textElements = Array.from(document.querySelectorAll('*'))
                        .filter(el => el.textContent.toLowerCase().includes(normalizedName));

                    console.log(`Found ${textElements.length} elements containing "${name}" text`);

                    for (const element of textElements) {
                        // Look for checkbox in parent container
                        let parent = element;
                        let depth = 0;
                        const MAX_DEPTH = 5;

                        while (parent && depth < MAX_DEPTH) {
                            // Check for checkbox in this parent
                            const checkbox = parent.querySelector('input[type="checkbox"]');
                            if (checkbox) {
                                console.log(`Found checkbox in ancestor of "${name}" text`);
                                return checkbox;
                            }

                            // Check for PrimeNG/PrimeReact checkbox
                            const primeCheckbox = parent.querySelector('.p-checkbox');
                            if (primeCheckbox) {
                                console.log(`Found PrimeNG/React checkbox in ancestor of "${name}" text`);
                                return primeCheckbox;
                            }

                            parent = parent.parentElement;
                            depth++;
                        }
                    }

                    return null;
                };

                // Try to find the product checkbox
                const checkbox = findProductCheckbox(productName);

                if (checkbox) {
                    console.log(`Found checkbox for product "${productName}", clicking it`);

                    // For standard HTML checkboxes
                    if (checkbox.tagName === 'INPUT' && checkbox.type === 'checkbox') {
                        checkbox.checked = true;
                        checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                        checkbox.dispatchEvent(new Event('input', { bubbles: true }));
                        checkbox.dispatchEvent(new Event('click', { bubbles: true }));
                        return true;
                    }

                    // For PrimeNG/PrimeReact checkboxes
                    if (checkbox.classList.contains('p-checkbox')) {
                        // Find the actual checkbox element inside the container
                        const checkboxBox = checkbox.querySelector('.p-checkbox-box');
                        if (checkboxBox) {
                            checkboxBox.click();
                        } else {
                            checkbox.click();
                        }
                        return true;
                    }

                    // For any other element that might be a checkbox
                    checkbox.click();
                    return true;
                }

                // If we couldn't find the specific product, try to find any unchecked product checkboxes
                const allProductCheckboxes = document.querySelectorAll('.wizard-card-checkbox-container input[type="checkbox"]:not(:checked), .wizard-card-checkbox-container .p-checkbox:not(.p-checkbox-checked)');
                console.log(`Found ${allProductCheckboxes.length} unchecked product checkboxes`);

                if (allProductCheckboxes.length > 0) {
                    console.log("Clicking first unchecked product checkbox");

                    // For standard HTML checkboxes
                    if (allProductCheckboxes[0].tagName === 'INPUT' && allProductCheckboxes[0].type === 'checkbox') {
                        allProductCheckboxes[0].checked = true;
                        allProductCheckboxes[0].dispatchEvent(new Event('change', { bubbles: true }));
                        allProductCheckboxes[0].dispatchEvent(new Event('input', { bubbles: true }));
                        allProductCheckboxes[0].dispatchEvent(new Event('click', { bubbles: true }));
                        return true;
                    }

                    // For PrimeNG/PrimeReact checkboxes
                    if (allProductCheckboxes[0].classList.contains('p-checkbox')) {
                        const checkboxBox = allProductCheckboxes[0].querySelector('.p-checkbox-box');
                        if (checkboxBox) {
                            checkboxBox.click();
                        } else {
                            allProductCheckboxes[0].click();
                        }
                        return true;
                    }

                    // For any other element
                    allProductCheckboxes[0].click();
                    return true;
                }

                return false;
            }""", product_name)

            if checked:
                self.speak(f"✓ Checked product {product_name}")
                return True
            else:
                self.speak(f"Could not find product checkbox for {product_name}")
                return False
        except Exception as e:
            print(f"Error checking product checkbox: {e}")
            self.speak(f"Error checking product checkbox for {product_name}")
            return False

    async def _check_all_products(self):
        """Check all product checkboxes in the product list"""
        try:
            # Use JavaScript to find and check all product checkboxes
            result = await self.page.evaluate("""() => {
                console.log("Looking for all product checkboxes");

                // Find all product containers
                const productContainers = document.querySelectorAll('.wizard-card-checkbox-container, .hover-card');
                console.log(`Found ${productContainers.length} potential product containers`);

                let checkedCount = 0;

                // Go through each container and check its checkbox
                for (const container of productContainers) {
                    // Look for checkbox in this container
                    const checkbox = container.querySelector('input[type="checkbox"]');
                    if (checkbox && !checkbox.checked) {
                        console.log(`Found and checking standard checkbox in container`);
                        checkbox.checked = true;
                        checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                        checkbox.dispatchEvent(new Event('input', { bubbles: true }));
                        checkbox.dispatchEvent(new Event('click', { bubbles: true }));
                        checkedCount++;
                        continue;
                    }

                    // Look for PrimeNG/PrimeReact checkbox
                    const primeCheckbox = container.querySelector('.p-checkbox:not(.p-checkbox-checked)');
                    if (primeCheckbox) {
                        console.log(`Found and checking PrimeNG/React checkbox in container`);
                        // Find the actual checkbox element inside the container
                        const checkboxBox = primeCheckbox.querySelector('.p-checkbox-box');
                        if (checkboxBox) {
                            checkboxBox.click();
                        } else {
                            primeCheckbox.click();
                        }
                        checkedCount++;
                        continue;
                    }

                    // Look for any element with checkbox class
                    const checkboxElement = container.querySelector('[class*="checkbox"]');
                    if (checkboxElement) {
                        console.log(`Found and checking element with checkbox class in container`);
                        checkboxElement.click();
                        checkedCount++;
                    }
                }

                return {
                    success: checkedCount > 0,
                    count: checkedCount,
                    totalContainers: productContainers.length
                };
            }""")

            if result.get('success'):
                self.speak(f"✓ Checked {result.get('count')} products out of {result.get('totalContainers')} found")
                return True
            else:
                self.speak(f"Could not find any product checkboxes to check")
                return False
        except Exception as e:
            print(f"Error checking all product checkboxes: {e}")
            self.speak(f"Error checking all product checkboxes")
            return False

    async def _retry_click(self, selector, purpose):
        """Retry clicking an element"""
        tries = 3
        for attempt in range(tries):
            try:
                await self.page.locator(selector).first.click(timeout=10000)
                self.speak(f"👆 Clicked {purpose}")
                return True
            except Exception as e:
                if attempt == tries - 1:
                    raise e
                await self.page.wait_for_timeout(1000)
        return False

    async def _retry_type(self, selector, text, purpose, max_retries=3, timeout=30000):
        """Retry typing text into an element with JavaScript fallback

        Args:
            selector: CSS selector for the element
            text: Text to type
            purpose: Description of what we're typing (for logging)
            max_retries: Maximum number of retry attempts
            timeout: Timeout in milliseconds for each attempt
        """
        for attempt in range(max_retries):
            try:
                await self.page.locator(selector).first.fill(text, timeout=timeout)
                self.speak(f"⌨️ Entered {purpose}")
                return True
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"Failed to type into {purpose} using standard method after {max_retries} attempts: {e}")
                    print(f"Trying JavaScript injection for {purpose}...")

                    # Try using JavaScript to find and fill the element
                    try:
                        # First try with the specific selector
                        js_result = await self.page.evaluate("""(selector, text) => {
                            try {
                                const element = document.querySelector(selector);
                                if (element) {
                                    element.value = text;
                                    element.dispatchEvent(new Event('input', { bubbles: true }));
                                    element.dispatchEvent(new Event('change', { bubbles: true }));
                                    console.log('Filled element using selector:', selector);
                                    return true;
                                }
                                return false;
                            } catch (e) {
                                console.error('Error filling element:', e);
                                return false;
                            }
                        }""", selector, text)

                        if js_result:
                            print(f"Successfully filled {purpose} using JavaScript with selector")
                            self.speak(f"⌨️ Entered {purpose}")
                            return True

                        # If specific selector didn't work, try a more aggressive approach
                        print(f"Specific selector not found, trying generic input")
                        js_result = await self.page.evaluate("""(text, elementType) => {
                            // Try to find input elements by type or placeholder
                            const findInputs = () => {
                                const inputs = [];

                                // Get all input elements
                                const allInputs = document.querySelectorAll('input, textarea');

                                // Filter inputs based on element type
                                for (const input of allInputs) {
                                    if (elementType.toLowerCase().includes('email') &&
                                        (input.type === 'email' ||
                                         input.name?.toLowerCase().includes('email') ||
                                         input.id?.toLowerCase().includes('email') ||
                                         input.placeholder?.toLowerCase().includes('email'))) {
                                        inputs.push(input);
                                    } else if (elementType.toLowerCase().includes('password') &&
                                               (input.type === 'password' ||
                                                input.name?.toLowerCase().includes('password') ||
                                                input.id?.toLowerCase().includes('password'))) {
                                        inputs.push(input);
                                    } else if (!elementType.toLowerCase().includes('email') &&
                                               !elementType.toLowerCase().includes('password')) {
                                        // For other types, just add all inputs
                                        inputs.push(input);
                                    }
                                }

                                return inputs;
                            };

                            // Find inputs based on element type
                            const inputs = findInputs();
                            console.log(`Found ${inputs.length} potential ${elementType} inputs`);

                            // Try to fill the first matching input
                            if (inputs.length > 0) {
                                inputs[0].value = text;
                                inputs[0].dispatchEvent(new Event('input', { bubbles: true }));
                                inputs[0].dispatchEvent(new Event('change', { bubbles: true }));
                                console.log(`Filled ${elementType} input with:`, text);
                                return true;
                            }

                            // If no inputs found, try to find inputs in iframes
                            const iframes = document.querySelectorAll('iframe');
                            for (let i = 0; i < iframes.length; i++) {
                                try {
                                    const iframe = iframes[i];
                                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;

                                    // Find inputs in iframe
                                    const iframeInputs = [];
                                    const allIframeInputs = iframeDoc.querySelectorAll('input, textarea');

                                    // Filter inputs based on element type
                                    for (const input of allIframeInputs) {
                                        if (elementType.toLowerCase().includes('email') &&
                                            (input.type === 'email' ||
                                             input.name?.toLowerCase().includes('email') ||
                                             input.id?.toLowerCase().includes('email') ||
                                             input.placeholder?.toLowerCase().includes('email'))) {
                                            iframeInputs.push(input);
                                        } else if (elementType.toLowerCase().includes('password') &&
                                                   (input.type === 'password' ||
                                                    input.name?.toLowerCase().includes('password') ||
                                                    input.id?.toLowerCase().includes('password'))) {
                                            iframeInputs.push(input);
                                        } else if (!elementType.toLowerCase().includes('email') &&
                                                   !elementType.toLowerCase().includes('password')) {
                                            // For other types, just add all inputs
                                            iframeInputs.push(input);
                                        }
                                    }

                                    console.log(`Found ${iframeInputs.length} potential ${elementType} inputs in iframe ${i}`);

                                    // Try to fill the first matching input in iframe
                                    if (iframeInputs.length > 0) {
                                        iframeInputs[0].value = text;
                                        iframeInputs[0].dispatchEvent(new Event('input', { bubbles: true }));
                                        iframeInputs[0].dispatchEvent(new Event('change', { bubbles: true }));
                                        console.log(`Filled ${elementType} input in iframe ${i} with:`, text);
                                        return true;
                                    }
                                } catch (e) {
                                    console.error(`Error accessing iframe ${i}:`, e);
                                }
                            }

                            // If still no inputs found, try to find any visible element that might be an input
                            console.log("No inputs found. Performing DOM inspection to find input fields...");

                            // Count all input elements for debugging
                            const allInputCount = document.querySelectorAll('input').length;
                            console.log(`DOM inspection found ${allInputCount} input elements`);

                            // Check if specific ID exists
                            const specificInput = document.getElementById('floating_outlined3');
                            console.log(`DOM inspection ${specificInput ? 'found' : 'did not find'} #floating_outlined3`);

                            return false;
                        }""", text, purpose)

                        if js_result:
                            print(f"Successfully filled {purpose} using JavaScript with generic approach")
                            self.speak(f"⌨️ Entered {purpose}")
                            return True
                    except Exception as js_error:
                        print(f"JavaScript injection failed: {js_error}")

                    raise e
                await self.page.wait_for_timeout(10000)
        return False

    async def _check_for_input_fields(self):
        """Check if there are any input fields on the page using direct DOM inspection"""
        try:
            # Use JavaScript to check for form elements directly in the DOM
            form_elements = await self.page.evaluate("""() => {
                // Check for specific elements we know exist in the form
                const emailField = document.getElementById('floating_outlined3');
                const passwordField = document.getElementById('floating_outlined15');
                const signInButton = document.getElementById('signInButton');

                // Check for any input elements
                const inputs = document.querySelectorAll('input');
                const forms = document.querySelectorAll('form');

                // Return detailed information
                return {
                    hasEmailField: !!emailField,
                    hasPasswordField: !!passwordField,
                    hasSignInButton: !!signInButton,
                    inputCount: inputs.length,
                    formCount: forms.length,
                    inputTypes: Array.from(inputs).map(input => input.type || 'unknown'),
                    inputIds: Array.from(inputs).map(input => input.id || 'no-id'),
                    formIds: Array.from(forms).map(form => form.id || 'no-id')
                };
            }""")

            # Log the results
            print(f"DOM inspection found {form_elements.get('inputCount', 0)} input elements")
            print(f"DOM inspection found {form_elements.get('formCount', 0)} form elements")
            print(f"DOM inspection {'' if form_elements.get('hasEmailField') else 'did not find'} #floating_outlined3")
            print(f"DOM inspection {'' if form_elements.get('hasPasswordField') else 'did not find'} #floating_outlined15")

            return form_elements
        except Exception as e:
            print(f"DOM inspection error: {e}")
            return {
                "error": str(e),
                "inputCount": 0,
                "formCount": 0,
                "hasEmailField": False,
                "hasPasswordField": False
            }

    async def _enter_address_field(self, text, field_type):
        """Enter text into an address form field"""
        try:
            # Define selectors for different address fields
            selectors = {
                "address_line1": {
                    "id": "#floating_outlined2100",
                    "label": "Address Line 1",
                    "fallbacks": [
                        "input[name='cityName1']",
                        "input[aria-label='Address Line 1']",
                        "input[placeholder*='Address Line 1']",
                        "label:has-text('Address Line 1') + input",
                        "label:has-text('Address Line 1') ~ input"
                    ]
                },
                "address_line2": {
                    "id": "#floating_outlined22",
                    "label": "Address Line 2",
                    "fallbacks": [
                        "input[name='cityName2']",
                        "input[aria-label='Address Line 2']",
                        "input[placeholder*='Address Line 2']",
                        "label:has-text('Address Line 2') + input",
                        "label:has-text('Address Line 2') ~ input"
                    ]
                },
                "city": {
                    "id": "#floating_outlined2401",
                    "label": "City",
                    "fallbacks": [
                        "input[name='city']",
                        "input[aria-label='City']",
                        "input[placeholder*='City']",
                        "label:has-text('City') + input",
                        "label:has-text('City') ~ input"
                    ]
                },
                "zip": {
                    "id": "#floating_outlined2601",
                    "label": "Zip Code",
                    "fallbacks": [
                        "input[name='zipCode']",
                        "input[aria-label='Zip Code']",
                        "input[placeholder*='Zip']",
                        "input[maxlength='5']",
                        "label:has-text('Zip') + input",
                        "label:has-text('Zip') ~ input"
                    ]
                }
            }

            # Get the selectors for the specified field type
            field_selectors = selectors.get(field_type)
            if not field_selectors:
                self.speak(f"Unknown field type: {field_type}")
                return False

            # First try the specific ID selector
            try:
                if await self.page.locator(field_selectors["id"]).count() > 0:
                    await self._retry_type(field_selectors["id"], text, field_selectors["label"])
                    self.speak(f"Entered text in {field_selectors['label']} field")
                    return True
            except Exception as e:
                print(f"Error with specific ID selector {field_selectors['id']}: {e}")

            # If specific ID didn't work, try fallback selectors
            for selector in field_selectors["fallbacks"]:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_type(selector, text, field_selectors["label"])
                        self.speak(f"Entered text in {field_selectors['label']} field")
                        return True
                except Exception as e:
                    print(f"Error with fallback selector {selector}: {e}")

            # If selectors didn't work, try JavaScript
            try:
                js_result = await self.page.evaluate("""(fieldType, text) => {
                    console.log(`Trying to fill ${fieldType} field with JavaScript`);

                    // Map field types to identifiers
                    const fieldMap = {
                        "address_line1": {
                            id: "floating_outlined2100",
                            name: "cityName1",
                            label: "Address Line 1"
                        },
                        "address_line2": {
                            id: "floating_outlined22",
                            name: "cityName",
                            label: "Address Line 2"
                        },
                        "city": {
                            id: "floating_outlined2401",
                            name: "cityName",
                            label: "City"
                        },
                        "zip": {
                            id: "floating_outlined2601",
                            name: "cityName",
                            label: "Zip Code"
                        }
                    };

                    const fieldInfo = fieldMap[fieldType];
                    if (!fieldInfo) {
                        return { success: false, message: `Unknown field type: ${fieldType}` };
                    }

                    // Try by ID first
                    let field = document.getElementById(fieldInfo.id);
                    if (field) {
                        field.value = text;
                        field.dispatchEvent(new Event('input', { bubbles: true }));
                        field.dispatchEvent(new Event('change', { bubbles: true }));
                        console.log(`Filled ${fieldInfo.label} field by ID`);
                        return { success: true, message: `Filled ${fieldInfo.label} field` };
                    }

                    // Try by name
                    field = document.querySelector(`input[name="${fieldInfo.name}"]`);
                    if (field) {
                        field.value = text;
                        field.dispatchEvent(new Event('input', { bubbles: true }));
                        field.dispatchEvent(new Event('change', { bubbles: true }));
                        console.log(`Filled ${fieldInfo.label} field by name`);
                        return { success: true, message: `Filled ${fieldInfo.label} field` };
                    }

                    // Try by label text
                    const labels = Array.from(document.querySelectorAll('label'));
                    for (const label of labels) {
                        if (label.textContent.includes(fieldInfo.label)) {
                            // Try to find the input associated with this label
                            const forAttr = label.getAttribute('for');
                            if (forAttr) {
                                field = document.getElementById(forAttr);
                                if (field) {
                                    field.value = text;
                                    field.dispatchEvent(new Event('input', { bubbles: true }));
                                    field.dispatchEvent(new Event('change', { bubbles: true }));
                                    console.log(`Filled ${fieldInfo.label} field by label's for attribute`);
                                    return { success: true, message: `Filled ${fieldInfo.label} field` };
                                }
                            }

                            // Try sibling or parent-child relationship
                            const parent = label.parentElement;
                            if (parent) {
                                field = parent.querySelector('input');
                                if (field) {
                                    field.value = text;
                                    field.dispatchEvent(new Event('input', { bubbles: true }));
                                    field.dispatchEvent(new Event('change', { bubbles: true }));
                                    console.log(`Filled ${fieldInfo.label} field by parent-child relationship`);
                                    return { success: true, message: `Filled ${fieldInfo.label} field` };
                                }
                            }
                        }
                    }

                    return { success: false, message: `Could not find ${fieldInfo.label} field` };
                }""", field_type, text)

                if js_result and js_result.get('success'):
                    self.speak(js_result.get('message', f"Entered text in {field_selectors['label']} field"))
                    return True
                else:
                    print(f"JavaScript field fill failed: {js_result.get('message')}")
            except Exception as e:
                print(f"Error with JavaScript field fill: {e}")

            # If we get here, we couldn't find the field
            self.speak(f"Could not find {field_selectors['label']} field")
            return False

        except Exception as e:
            print(f"Error entering address field: {e}")
            self.speak(f"Error entering text in {field_type} field")
            return False

    def show_help(self):
        """Show help information"""
        help_text = """
        🔍 Voice Web Assistant Help:

        Basic Navigation:
        - "Go to [website]" - Navigate to a website
        - "Navigate to [section]" - Go to a specific section on the current site
        - "Open [website]" - Open a website

        Login:
        - "Login with email [email] and password [password]" - Log in to a website
        - "Enter email [email] and password [password]" - Fill in login form without submitting

        Search:
        - "Search for [query]" - Search on the current website

        Forms and Selections:
        - "Check product [product name]" - Check a product checkbox in a product list
        - "Check all products" - Check all available product checkboxes
        - "Select product [product name]" - Select a product from a list
        - "Check checkbox for [option]" - Check a checkbox for a specific option
        - "Click on [element]" - Click on a specific element
        - "Select [dropdown name] dropdown" - Open a dropdown menu
        - "Select [option] from [dropdown] dropdown" - Select an option from a dropdown

        Address Form:
        - "Enter [text] in address line 1" - Fill in the first address line
        - "Enter [text] in address line 2" - Fill in the second address line
        - "Enter [text] in city" - Fill in the city field
        - "Enter [text] in zip code" - Fill in the zip code field
        - "Select [state] from state dropdown" - Select a state from the dropdown

        General:
        - "Help" - Show this help message
        - "Exit" or "Quit" - Close the assistant
        """
        print(help_text)
        self.speak("Here's the help information. You can see the full list on screen.")


async def main():
    """Main entry point"""
    try:
        # Load environment variables if .env file exists
        if os.path.exists(".env"):
            from dotenv import load_dotenv
            load_dotenv()

        print("Initializing Voice Assistant...")
        # Create configuration
        config = AssistantConfig.from_env()

        # Initialize the assistant
        assistant = VoiceAssistant(config)
        await assistant.initialize()

        assistant.speak("Web Assistant ready. Say 'help' for available commands.")

        print("\nWelcome to Voice Web Assistant!")
        print("Type 'help' for available commands or 'exit' to quit.")

        # Main command loop
        while True:
            try:
                # Get user input directly
                command = input("\nCommand: ").strip()

                # Handle empty command
                if not command:
                    print("Empty command. Please try again.")
                    continue

                print(f"USER: {command}")

                # Process the command
                if not await assistant.process_command(command):
                    break

            except KeyboardInterrupt:
                print("\nKeyboard interrupt detected. Exiting...")
                break
            except Exception as e:
                import traceback
                print(f"Error processing command: {e}")
                traceback.print_exc()

    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
    finally:
        print("\nProgram ended. Browser will remain open.")
            


if __name__ == "__main__":
    asyncio.run(main())
