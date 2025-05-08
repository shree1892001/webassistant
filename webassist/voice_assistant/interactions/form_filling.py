import re

class FormFillingHandler:
    """Handles form filling commands"""

    def __init__(self, page, speak_func, llm_utils, browser_utils):
        """Initialize the form filling handler

        Args:
            page: Playwright page object
            speak_func: Function to speak text
            llm_utils: LLM utilities for generating selectors and actions
            browser_utils: Browser utilities for common operations
        """
        self.page = page
        self.speak = speak_func
        self.llm_utils = llm_utils
        self.browser_utils = browser_utils

    async def handle_command(self, command):
        """Handle form filling commands

        Args:
            command: User command string

        Returns:
            bool: True if command was handled, False otherwise
        """
        # Handle address selection commands
        address_select_match = re.search(r'(?:select|choose|pick)\s+(?:the\s+)?(?:address|location)\s+(?:of\s+)?([^"]+?)(?:\s+from\s+dropdown)?$', command.lower())
        if address_select_match:
            address = address_select_match.group(1).strip()
            print(f"Handling address selection command: select '{address}' from dropdown")
            return await self._select_address_from_dropdown(address)
        # Handle login command
        login_match = re.search(r'login with email\s+(\S+)\s+and password\s+(\S+)', command, re.IGNORECASE)

        if not login_match:
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
            return await self._handle_login(email, password)

        # Handle address field commands
        address_field_match = re.search(r'enter\s+(.+?)\s+(?:in|into|for)\s+(?:the\s+)?(?:address\s+line\s+1|address1|first\s+address)', command, re.IGNORECASE)
        if address_field_match:
            text = address_field_match.group(1).strip()
            return await self._enter_address_field(text, "address_line1")

        address_field_match = re.search(r'enter\s+(.+?)\s+(?:in|into|for)\s+(?:the\s+)?(?:address\s+line\s+2|address2|second\s+address)', command, re.IGNORECASE)
        if address_field_match:
            text = address_field_match.group(1).strip()
            return await self._enter_address_field(text, "address_line2")

        address_field_match = re.search(r'enter\s+(.+?)\s+(?:in|into|for)\s+(?:the\s+)?(?:city)', command, re.IGNORECASE)
        if address_field_match:
            text = address_field_match.group(1).strip()
            return await self._enter_address_field(text, "city")

        address_field_match = re.search(r'enter\s+(.+?)\s+(?:in|into|for)\s+(?:the\s+)?(?:zip|zip\s+code|postal\s+code)', command, re.IGNORECASE)
        if address_field_match:
            text = address_field_match.group(1).strip()
            return await self._enter_address_field(text, "zip")

        # Handle "enter email" command
        email_match = re.search(r'enter\s+(?:email|email\s+address)\s+(.+?)(?:\s+(?:in|into|for)\s+(?:the\s+)?(?:email|email\s+field|email\s+address))?', command, re.IGNORECASE)
        if email_match:
            email = email_match.group(1).strip()
            return await self._enter_email(email)

        # Handle LLC field specifically - using direct approach with known ID
        llc_field_match = re.search(r'(?:enter|input|type|fill|put)\s+(?:in\s+)?(?:the\s+)?([^"]+?)\s+(?:as|in|into|for|to)\s+(?:the\s+)?(?:llc|llc\s+name)(?:\s+field)?$', command.lower())
        if llc_field_match:
            value = llc_field_match.group(1).strip()
            print(f"Handling LLC field command: enter '{value}' into LLC field")

            # Define all the selectors we'll try
            llc_selectors = [
                '#CD_LLC_Name',
                'input[name="CD_LLC_Name"]',
                'input[id*="LLC" i]',
                'input[name*="LLC" i]',
                'input.dialog-form-input-field-wizard',
                'input.p-inputtext.dialog-form-input-field-wizard',
                'input[maxlength="50"]'
            ]

            # Try each selector with direct typing
            for selector in llc_selectors:
                try:
                    print(f"Trying LLC field with selector: {selector}")

                    # Check if the element exists
                    if await self.page.locator(selector).count() > 0:
                        # Try to click it first to ensure it's focused
                        try:
                            await self.page.click(selector, timeout=2000)
                            print(f"Clicked on LLC field with selector: {selector}")
                            await self.page.wait_for_timeout(500)  # Wait for focus
                        except Exception as click_error:
                            print(f"Click error (continuing anyway): {click_error}")

                        # Try Playwright's fill method
                        try:
                            await self.page.fill(selector, value, timeout=5000)
                            print(f"Filled LLC field with '{value}' using fill method")
                            await self.speak(f"Entered {value} into LLC field")
                            return True
                        except Exception as fill_error:
                            print(f"Fill error: {fill_error}")

                            # If fill fails, try type method
                            try:
                                # Clear the field first
                                await self.page.click(selector, timeout=2000)
                                await self.page.keyboard.press('Control+a')
                                await self.page.keyboard.press('Backspace')

                                # Then type the value
                                await self.page.type(selector, value, delay=100)
                                print(f"Typed '{value}' into LLC field using type method")
                                await self.speak(f"Entered {value} into LLC field")
                                return True
                            except Exception as type_error:
                                print(f"Type error: {type_error}")
                except Exception as e:
                    print(f"Error with selector {selector}: {e}")

            # If direct Playwright methods fail, try JavaScript
            print("Trying JavaScript approach for LLC field...")

            # First, get all input fields and their properties for debugging
            debug_info = await self.page.evaluate("""
                () => {
                    const inputs = Array.from(document.querySelectorAll('input'));
                    return inputs.map(input => ({
                        id: input.id,
                        name: input.name,
                        class: input.className,
                        type: input.type,
                        value: input.value,
                        visible: !(window.getComputedStyle(input).display === 'none' ||
                                  window.getComputedStyle(input).visibility === 'hidden')
                    }));
                }
            """)

            print("Input fields found on page:")
            for input_info in debug_info:
                print(f"  ID: {input_info.get('id', 'N/A')}, Name: {input_info.get('name', 'N/A')}, " +
                      f"Class: {input_info.get('class', 'N/A')}, Type: {input_info.get('type', 'N/A')}, " +
                      f"Visible: {input_info.get('visible', 'N/A')}")

            # Try JavaScript with the known ID
            js_result = await self.page.evaluate(f"""
                () => {{
                    try {{
                        // Try with exact ID first
                        let llcField = document.getElementById('CD_LLC_Name');
                        if (llcField) {{
                            console.log("Found LLC field by ID");
                            llcField.value = "{value}";
                            llcField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            llcField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return true;
                        }}

                        // Try with querySelector
                        llcField = document.querySelector('input[name="CD_LLC_Name"]');
                        if (llcField) {{
                            console.log("Found LLC field by name");
                            llcField.value = "{value}";
                            llcField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            llcField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return true;
                        }}

                        // Try with class
                        llcField = document.querySelector('input.dialog-form-input-field-wizard');
                        if (llcField) {{
                            console.log("Found LLC field by class");
                            llcField.value = "{value}";
                            llcField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            llcField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return true;
                        }}

                        // Try finding any input with LLC in id or name
                        const inputs = Array.from(document.querySelectorAll('input'));
                        for (const input of inputs) {{
                            if ((input.id && input.id.toLowerCase().includes('llc')) ||
                                (input.name && input.name.toLowerCase().includes('llc'))) {{
                                console.log("Found LLC field by partial id/name match");
                                input.value = "{value}";
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                return true;
                            }}
                        }}

                        // Last resort: try all visible text inputs
                        for (const input of inputs) {{
                            if (input.type === 'text' &&
                                window.getComputedStyle(input).display !== 'none' &&
                                window.getComputedStyle(input).visibility !== 'hidden') {{
                                console.log("Trying visible text input as last resort");
                                input.value = "{value}";
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                return true;
                            }}
                        }}

                        return false;
                    }} catch (error) {{
                        console.error("Error in LLC JavaScript:", error);
                        return false;
                    }}
                }}
            """)

            if js_result:
                print(f"Filled LLC field with '{value}' using JavaScript")
                await self.speak(f"Entered {value} into LLC field")
                return True

            # Last resort: try direct keyboard interaction
            try:
                # Try to find any input field that might be the LLC field
                visible_inputs = await self.page.evaluate("""
                    () => {
                        const inputs = Array.from(document.querySelectorAll('input[type="text"]'));
                        return inputs
                            .filter(input =>
                                window.getComputedStyle(input).display !== 'none' &&
                                window.getComputedStyle(input).visibility !== 'hidden')
                            .map(input => ({
                                id: input.id,
                                name: input.name,
                                class: input.className
                            }));
                    }
                """)

                print(f"Found {len(visible_inputs)} visible text inputs")

                # Try to click each visible input and type into it
                for idx, input_info in enumerate(visible_inputs):
                    input_id = input_info.get('id')
                    input_name = input_info.get('name')
                    input_class = input_info.get('class')

                    print(f"Trying visible input #{idx+1}: ID={input_id}, Name={input_name}, Class={input_class}")

                    # Try to construct a selector
                    selector = None
                    if input_id:
                        selector = f"#{input_id}"
                    elif input_name:
                        selector = f"input[name='{input_name}']"
                    elif input_class:
                        selector = f"input.{input_class.replace(' ', '.')}"
                    else:
                        continue

                    try:
                        # Try to click and type
                        await self.page.click(selector, timeout=2000)
                        await self.page.keyboard.press('Control+a')
                        await self.page.keyboard.press('Backspace')
                        await self.page.keyboard.type(value, delay=100)
                        print(f"Typed '{value}' into input #{idx+1}")
                        await self.speak(f"Entered {value} into LLC field")
                        return True
                    except Exception as e:
                        print(f"Error typing into input #{idx+1}: {e}")
            except Exception as e:
                print(f"Error in last resort approach: {e}")

            # If all else fails, inform the user
            print("All approaches failed to fill the LLC field")
            await self.speak(f"I'm having trouble entering {value} into the LLC field. Please try typing it manually.")
            return False

        # Handle generic form field filling commands - also using LLM strategy
        form_field_match = re.search(r'(?:enter|input|type|fill|put)\s+(?:in\s+)?(?:the\s+)?([^"]+?)\s+(?:as|in|into|for|to)\s+(?:the\s+)?([^"]+?)(?:\s+field)?$', command.lower())
        if form_field_match:
            value = form_field_match.group(1).strip()
            field_name = form_field_match.group(2).strip()

            print(f"Handling generic form field command: enter '{value}' into '{field_name}' field")

            # Skip email/password fields as they're handled separately
            if 'email' in field_name.lower() or 'password' in field_name.lower():
                return False

            # Get page context for LLM
            context = await self.llm_utils.get_page_context()

            # Ask LLM for the best approach to fill the field
            prompt = f"""
            I need to fill a form field named "{field_name}" with the value "{value}" on a web form.
            Current page context: URL={context.get('url', '')}, Title={context.get('title', '')}

            Analyze the context and suggest the best approach to find and fill this field.
            Return a JSON object with the following structure:
            {{
                "approach": "selector|javascript|combined",
                "selectors": ["list", "of", "css", "selectors"],
                "javascript": "JavaScript code to find and fill the field (if approach is javascript or combined)",
                "explanation": "Brief explanation of your reasoning"
            }}
            """

            # Get LLM response
            llm_response = await self.llm_utils.get_llm_response(prompt)
            print(f"LLM response for {field_name} field approach: {llm_response}")

            # Parse LLM response (handle potential JSON parsing errors)
            try:
                import json
                llm_strategy = json.loads(llm_response)
            except:
                print(f"Failed to parse LLM response as JSON, using default approach for {field_name}")
                # Generate default selectors based on field name
                clean_field_name = field_name.lower().replace(" ", "-").replace("_", "-")
                llm_strategy = {
                    "approach": "combined",
                    "selectors": [
                        f'input[name="{clean_field_name}"]',
                        f'input[id="{clean_field_name}"]',
                        f'input[placeholder*="{field_name}" i]',
                        f'label:has-text("{field_name}") + input',
                        f'*:has-text("{field_name}") input'
                    ]
                }

            # Execute the strategy recommended by the LLM
            return await self._enter_field_with_llm_strategy(value, field_name, llm_strategy)

        return False

    async def _handle_login(self, email, password):
        """Handle login command"""
        await self.speak("Logging in with email and password...")

        url = self.page.url
        if not ('signin' in url or 'login' in url):
            await self.speak("Navigating to signin page first...")
            # Navigate to the correct signin URL
            try:
                await self.page.goto("https://www.redberyltest.in/#/signin", wait_until="networkidle", timeout=20000)
                await self.speak("Navigated to signin page")
                # Wait for the page to load
                await self.page.wait_for_timeout(5000)
            except Exception as e:
                await self.speak(f"Failed to navigate to signin page: {str(e)}")
                return False

        # Now we should be on the login page
        await self.speak("Found login page. Looking for login form...")
        # Try to find and click login button if needed
        login_selectors = await self.llm_utils.get_selectors("find login or sign in link or button",
                                                            await self.llm_utils.get_page_context())
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
                    await self.speak("Found and clicked login option. Waiting for form to appear...")
                    await self.page.wait_for_timeout(5000)  # Wait for form to appear
                    break
            except Exception:
                continue

        # Perform DOM inspection to find form elements
        form_elements = await self._check_for_input_fields()
        print(f"DOM inspection results: {form_elements}")

        # Get page context after potential navigation
        context = await self.llm_utils.get_page_context()

        # Define specific selectors for known form elements
        specific_email_selector = '#floating_outlined3'
        specific_password_selector = '#floating_outlined15'
        specific_button_selector = '#signInButton'

        if form_elements.get('hasEmailField') or form_elements.get('hasPasswordField'):
            try:
                # Use JavaScript to fill the form directly
                await self.speak("Using direct DOM manipulation to fill login form...")
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
                    await self.speak("Login form submitted using direct DOM manipulation")
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
                await self.browser_utils.retry_type(specific_email_selector, email, "email address")
                email_found = True
                print(f"Found email field with specific selector: {specific_email_selector}")
        except Exception as e:
            print(f"Error with specific email selector: {e}")

        # If specific selector didn't work, try LLM-generated selectors
        if not email_found:
            email_selectors = await self.llm_utils.get_selectors("find email or username input field", context)
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
                        await self.browser_utils.retry_type(selector, email, "email address")
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
                await self.browser_utils.retry_type(specific_password_selector, password, "password")
                password_found = True
                print(f"Found password field with specific selector: {specific_password_selector}")
        except Exception as e:
            print(f"Error with specific password selector: {e}")

        # If specific selector didn't work, try LLM-generated selectors
        if not password_found:
            password_selectors = await self.llm_utils.get_selectors("find password input field", context)
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
                        await self.browser_utils.retry_type(selector, password, "password")
                        password_found = True
                        break
                except Exception as e:
                    print(f"Error with password selector {selector}: {e}")
                    continue

        # Try to click the login button if both fields were found
        if email_found and password_found:
            button_clicked = False
            try:
                if await self.page.locator(specific_button_selector).count() > 0:
                    await self.browser_utils.retry_click(specific_button_selector, "Submit login form")
                    button_clicked = True
                    print(f"Clicked button with specific selector: {specific_button_selector}")
            except Exception as e:
                print(f"Error with specific button selector: {e}")

            if not button_clicked:
                login_button_selectors = await self.llm_utils.get_selectors("find login or sign in button", context)
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
                            await self.browser_utils.retry_click(selector, "Submit login form")
                            button_clicked = True
                            break
                    except Exception as e:
                        print(f"Error with button selector {selector}: {e}")
                        continue

            if not button_clicked:
                await self.speak("Filled login details but couldn't find login button")

            return True
        else:
            if not email_found:
                await self.speak("Could not find element to Enter email address")
            if not password_found:
                await self.speak("Could not find element to Enter password")
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
                await self.speak(f"Unknown field type: {field_type}")
                return False

            # First try the specific ID selector
            try:
                if await self.page.locator(field_selectors["id"]).count() > 0:
                    await self.browser_utils.retry_type(field_selectors["id"], text, field_selectors["label"])
                    await self.speak(f"Entered text in {field_selectors['label']} field")
                    return True
            except Exception as e:
                print(f"Error with specific ID selector {field_selectors['id']}: {e}")

            # If specific ID didn't work, try fallback selectors
            for selector in field_selectors["fallbacks"]:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self.browser_utils.retry_type(selector, text, field_selectors["label"])
                        await self.speak(f"Entered text in {field_selectors['label']} field")
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

    async def _enter_llc_field(self, value):
        """Enter a value into the LLC name field

        Args:
            value: The LLC name to enter

        Returns:
            bool: True if successful, False otherwise
        """
        await self.speak(f"Entering {value} into LLC field...")

        try:
            # Try direct JavaScript injection for LLC field
            print(f"Trying JavaScript injection for llc field...")
            js_code = f"""
                () => {{
                    try {{
                        console.log("Looking for LLC field");

                        // Try to find by label text containing "LLC"
                        const labels = Array.from(document.querySelectorAll('label'));
                        for (const label of labels) {{
                            if (label.textContent.toLowerCase().includes('llc')) {{
                                console.log("Found label with LLC text:", label.textContent);

                                // Try to find the input by id if label has a for attribute
                                if (label.htmlFor) {{
                                    const input = document.getElementById(label.htmlFor);
                                    if (input) {{
                                        input.value = "{value}";
                                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                        console.log("Filled LLC field by label.htmlFor");
                                        return true;
                                    }}
                                }}

                                // Try to find input as a child of the label
                                const labelInput = label.querySelector('input');
                                if (labelInput) {{
                                    labelInput.value = "{value}";
                                    labelInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                    labelInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    console.log("Filled LLC field as child of label");
                                    return true;
                                }}

                                // Try to find input near the label
                                const labelParent = label.parentElement;
                                if (labelParent) {{
                                    const nearbyInput = labelParent.querySelector('input');
                                    if (nearbyInput) {{
                                        nearbyInput.value = "{value}";
                                        nearbyInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        nearbyInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                        console.log("Filled LLC field near label");
                                        return true;
                                    }}
                                }}
                            }}
                        }}

                        // Try to find input with LLC in name, id, or placeholder
                        const inputs = Array.from(document.querySelectorAll('input'));
                        for (const input of inputs) {{
                            if ((input.name && input.name.toLowerCase().includes('llc')) ||
                                (input.id && input.id.toLowerCase().includes('llc')) ||
                                (input.placeholder && input.placeholder.toLowerCase().includes('llc'))) {{
                                input.value = "{value}";
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                console.log("Filled LLC field by name/id/placeholder");
                                return true;
                            }}
                        }}

                        // Try to find any input near text containing "LLC"
                        const allElements = Array.from(document.querySelectorAll('*'));
                        for (const el of allElements) {{
                            if (el.textContent && el.textContent.toLowerCase().includes('llc')) {{
                                // Look for an input in this element or its parent
                                const container = el.closest('div, form, fieldset');
                                if (container) {{
                                    const containerInput = container.querySelector('input');
                                    if (containerInput) {{
                                        containerInput.value = "{value}";
                                        containerInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        containerInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                        console.log("Filled LLC field near matching text");
                                        return true;
                                    }}
                                }}
                            }}
                        }}

                        console.log("Could not find LLC field");
                        return false;
                    }} catch (error) {{
                        console.error("Error finding/filling LLC field:", error);
                        return false;
                    }}
                }}
            """

            js_result = await self.page.evaluate(js_code)

            if js_result:
                print(f"Filled LLC field with '{value}' using JavaScript")
                await self.speak(f"Entered {value} into LLC field")
                return True

            # If JavaScript approach failed, try using selectors
            print("JavaScript approach failed, trying selectors...")

            # Generate selectors for LLC field
            llc_selectors = [
                'input[name*="llc" i]',
                'input[id*="llc" i]',
                'input[placeholder*="llc" i]',
                'label:has-text("LLC") + input',
                'label:has-text("LLC") ~ input',
                'div:has-text("LLC") input',
                '*:has-text("LLC") input'
            ]

            # Get LLM-generated selectors
            context = await self.llm_utils.get_page_context()
            llm_selectors = await self.llm_utils.get_selectors("find LLC name input field", context)

            # Try each selector
            for selector in llm_selectors + llc_selectors:
                try:
                    print(f"Trying LLC field selector: {selector}")
                    if await self.page.locator(selector).count() > 0:
                        await self.browser_utils.retry_type(selector, value, "LLC field")
                        print(f"Filled LLC field with '{value}' using selector: {selector}")
                        await self.speak(f"Entered {value} into LLC field")
                        return True
                except Exception as e:
                    print(f"Error with LLC field selector {selector}: {e}")
                    continue

            await self.speak(f"Could not find LLC field")
            return False

        except Exception as e:
            print(f"Error filling LLC field: {e}")
            import traceback
            traceback.print_exc()
            await self.speak(f"Error entering {value} into LLC field")
            return False

    async def _enter_field_with_llm_strategy(self, value, field_name, llm_strategy):
        """Enter a value into a field using the strategy recommended by the LLM

        Args:
            value: The value to enter
            field_name: The name of the field (for display purposes)
            llm_strategy: The strategy object from the LLM

        Returns:
            bool: True if successful, False otherwise
        """
        await self.speak(f"Entering {value} into {field_name} field...")

        try:
            approach = llm_strategy.get("approach", "combined")
            selectors = llm_strategy.get("selectors", [])
            javascript = llm_strategy.get("javascript", "")

            print(f"Using {approach} approach for {field_name} field")

            # Try selectors if approach is selector or combined
            if approach in ["selector", "combined"]:
                for selector in selectors:
                    try:
                        print(f"Trying selector: {selector}")
                        if await self.page.locator(selector).count() > 0:
                            # Check if the element is hidden or disabled
                            is_hidden = await self.page.evaluate(f"""(selector) => {{
                                const element = document.querySelector(selector);
                                if (!element) return true;

                                const style = window.getComputedStyle(element);
                                return style.display === 'none' ||
                                       style.visibility === 'hidden' ||
                                       style.opacity === '0' ||
                                       element.disabled ||
                                       element.readOnly;
                            }}""", selector)

                            if is_hidden:
                                print(f"Element found but it's hidden or disabled. Trying to click it first...")
                                try:
                                    # Try to click the element or its container to activate it
                                    await self.page.evaluate(f"""(selector) => {{
                                        const element = document.querySelector(selector);
                                        if (!element) return false;

                                        // Try to click the element itself
                                        try {{
                                            element.click();
                                            return true;
                                        }} catch (e) {{
                                            console.log("Couldn't click element directly:", e);
                                        }}

                                        // Try to click the parent (might be a dropdown container)
                                        try {{
                                            const parent = element.parentElement;
                                            if (parent) {{
                                                parent.click();
                                                return true;
                                            }}
                                        }} catch (e) {{
                                            console.log("Couldn't click parent:", e);
                                        }}

                                        // Try to find a clickable container
                                        try {{
                                            const container = element.closest('.p-dropdown, .dropdown, select');
                                            if (container) {{
                                                container.click();
                                                return true;
                                            }}
                                        }} catch (e) {{
                                            console.log("Couldn't click container:", e);
                                        }}

                                        return false;
                                    }}""", selector)

                                    # Wait a moment for any dropdown to appear
                                    await self.page.wait_for_timeout(1000)

                                    # Now try to find the option with the desired value
                                    option_clicked = await self.page.evaluate(f"""(value) => {{
                                        // Look for dropdown items or options
                                        const options = Array.from(document.querySelectorAll('.p-dropdown-item, option, li'));
                                        console.log("Found " + options.length + " potential options");

                                        for (const option of options) {{
                                            if (option.textContent.trim().toLowerCase().includes(value.toLowerCase())) {{
                                                console.log("Found matching option:", option.textContent);
                                                option.click();
                                                return true;
                                            }}
                                        }}

                                        return false;
                                    }}""", value)

                                    if option_clicked:
                                        print(f"Successfully selected '{value}' from dropdown")
                                        await self.speak(f"Selected {value} from {field_name} dropdown")
                                        return True
                                except Exception as e:
                                    print(f"Error trying to click element or select option: {e}")

                            # If it's not hidden or the click approach didn't work, try typing
                            await self.browser_utils.retry_type(selector, value, f"{field_name} field")
                            print(f"Filled {field_name} field with '{value}' using selector: {selector}")
                            await self.speak(f"Entered {value} into {field_name} field")
                            return True
                    except Exception as e:
                        print(f"Error with selector {selector}: {e}")
                        continue

            # Try JavaScript if approach is javascript or combined
            if approach in ["javascript", "combined"]:
                if javascript:
                    try:
                        # If the JavaScript is provided as a function body, wrap it
                        if not javascript.strip().startswith("function") and not javascript.strip().startswith("("):
                            js_code = f"""
                                () => {{
                                    try {{
                                        {javascript}
                                    }} catch (error) {{
                                        console.error("Error in JavaScript:", error);
                                        return false;
                                    }}
                                }}
                            """
                        else:
                            js_code = javascript

                        print(f"Executing JavaScript for {field_name} field")
                        js_result = await self.page.evaluate(js_code)

                        if js_result:
                            print(f"Filled {field_name} field with '{value}' using JavaScript")
                            await self.speak(f"Entered {value} into {field_name} field")
                            return True
                    except Exception as e:
                        print(f"Error executing JavaScript: {e}")
                else:
                    # Use default JavaScript if none provided
                    js_code = f"""
                        () => {{
                            try {{
                                console.log("Looking for {field_name} field");

                                // Check if this might be a dropdown field
                                const isLikelyDropdown = '{field_name.lower()}'.includes('type') ||
                                                        '{field_name.lower()}'.includes('state') ||
                                                        '{field_name.lower()}'.includes('county') ||
                                                        '{field_name.lower()}'.includes('llc') ||
                                                        '{field_name.lower()}'.includes('select');

                                // Try to find by label text
                                const labels = Array.from(document.querySelectorAll('label'));
                                for (const label of labels) {{
                                    if (label.textContent.toLowerCase().includes('{field_name.lower()}')) {{
                                        console.log("Found label with text:", label.textContent);

                                        // Check for dropdown first if likely
                                        if (isLikelyDropdown) {{
                                            // Try to find dropdown by label's for attribute
                                            if (label.htmlFor) {{
                                                const dropdown = document.getElementById(label.htmlFor);
                                                if (dropdown && (dropdown.tagName === 'SELECT' ||
                                                                dropdown.classList.contains('p-dropdown') ||
                                                                dropdown.classList.contains('dropdown'))) {{
                                                    console.log("Found dropdown by label's for attribute");
                                                    dropdown.click();
                                                    // Wait a bit for dropdown to open
                                                    // Direct approach instead of setTimeout
                                                    // Wait a small amount of time for the dropdown to open
                                                    for (let i = 0; i < 10; i++) {{
                                                        const options = Array.from(document.querySelectorAll('.p-dropdown-item, option, li'));
                                                        console.log("Found " + options.length + " potential options");

                                                        if (options.length > 0) {{
                                                            for (const option of options) {{
                                                                if (option.textContent.trim().toLowerCase().includes('{value.lower()}')) {{
                                                                    console.log("Found matching option:", option.textContent);
                                                                    option.click();
                                                                    return true;
                                                                }}
                                                            }}
                                                            break; // Found options but none matched
                                                        }}

                                                        // Small delay without using setTimeout
                                                        const start = new Date().getTime();
                                                        while (new Date().getTime() < start + 50) {{ /* wait */ }}
                                                    }}
                                                    return true;
                                                }}
                                            }}

                                            // Try to find dropdown near the label
                                            const labelParent = label.parentElement;
                                            if (labelParent) {{
                                                const nearbyDropdown = labelParent.querySelector('.p-dropdown, select, .dropdown');
                                                if (nearbyDropdown) {{
                                                    console.log("Found dropdown near label");
                                                    nearbyDropdown.click();
                                                    // Wait a bit for dropdown to open
                                                    // Direct approach instead of setTimeout
                                                    // Wait a small amount of time for the dropdown to open
                                                    for (let i = 0; i < 10; i++) {{
                                                        const options = Array.from(document.querySelectorAll('.p-dropdown-item, option, li'));
                                                        console.log("Found " + options.length + " potential options");

                                                        if (options.length > 0) {{
                                                            for (const option of options) {{
                                                                if (option.textContent.trim().toLowerCase().includes('{value.lower()}')) {{
                                                                    console.log("Found matching option:", option.textContent);
                                                                    option.click();
                                                                    return true;
                                                                }}
                                                            }}
                                                            break; // Found options but none matched
                                                        }}

                                                        // Small delay without using setTimeout
                                                        const start = new Date().getTime();
                                                        while (new Date().getTime() < start + 50) {{ /* wait */ }}
                                                    }}
                                                    return true;
                                                }}
                                            }}
                                        }}

                                        // Try to find the input by id if label has a for attribute
                                        if (label.htmlFor) {{
                                            const input = document.getElementById(label.htmlFor);
                                            if (input) {{
                                                input.value = "{value}";
                                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                                return true;
                                            }}
                                        }}

                                        // Try to find input as a child of the label
                                        const labelInput = label.querySelector('input');
                                        if (labelInput) {{
                                            labelInput.value = "{value}";
                                            labelInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                            labelInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                            return true;
                                        }}

                                        // Try to find input near the label
                                        const labelParent = label.parentElement;
                                        if (labelParent) {{
                                            const nearbyInput = labelParent.querySelector('input');
                                            if (nearbyInput) {{
                                                nearbyInput.value = "{value}";
                                                nearbyInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                                nearbyInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                                return true;
                                            }}
                                        }}
                                    }}
                                }}

                                // If likely a dropdown, try to find it directly
                                if (isLikelyDropdown) {{
                                    // Look for elements containing the field name
                                    const elements = Array.from(document.querySelectorAll('*'));
                                    for (const el of elements) {{
                                        if (el.textContent && el.textContent.toLowerCase().includes('{field_name.lower()}')) {{
                                            // Check if this element is a dropdown or contains one
                                            const dropdown = el.classList.contains('p-dropdown') || el.classList.contains('dropdown') ?
                                                            el : el.querySelector('.p-dropdown, select, .dropdown');

                                            if (dropdown) {{
                                                console.log("Found dropdown by text content");
                                                dropdown.click();
                                                // Wait a bit for dropdown to open
                                                // Direct approach instead of setTimeout
                                                // Wait a small amount of time for the dropdown to open
                                                for (let i = 0; i < 10; i++) {{
                                                    const options = Array.from(document.querySelectorAll('.p-dropdown-item, option, li'));
                                                    console.log("Found " + options.length + " potential options");

                                                    if (options.length > 0) {{
                                                        for (const option of options) {{
                                                            if (option.textContent.trim().toLowerCase().includes('{value.lower()}')) {{
                                                                console.log("Found matching option:", option.textContent);
                                                                option.click();
                                                                return true;
                                                            }}
                                                        }}
                                                        break; // Found options but none matched
                                                    }}

                                                    // Small delay without using setTimeout
                                                    const start = new Date().getTime();
                                                    while (new Date().getTime() < start + 50) {{ /* wait */ }}
                                                }}
                                                return true;
                                            }}
                                        }}
                                    }}
                                }}

                                // Try to find any input near text containing the field name
                                const allElements = Array.from(document.querySelectorAll('*'));
                                for (const el of allElements) {{
                                    if (el.textContent && el.textContent.toLowerCase().includes('{field_name.lower()}')) {{
                                        // Look for an input in this element or its parent
                                        const container = el.closest('div, form, fieldset');
                                        if (container) {{
                                            const containerInput = container.querySelector('input');
                                            if (containerInput) {{
                                                containerInput.value = "{value}";
                                                containerInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                                containerInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                                return true;
                                            }}
                                        }}
                                    }}
                                }}

                                return false;
                            }} catch (error) {{
                                console.error("Error finding/filling field:", error);
                                return false;
                            }}
                        }}
                    """

                    print(f"Executing default JavaScript for {field_name} field")
                    js_result = await self.page.evaluate(js_code)

                    if js_result:
                        print(f"Filled {field_name} field with '{value}' using default JavaScript")
                        await self.speak(f"Entered {value} into {field_name} field")
                        return True

            # If we get here, we couldn't find the field
            await self.speak(f"Could not find {field_name} field")
            return False

        except Exception as e:
            print(f"Error filling {field_name} field: {e}")
            import traceback
            traceback.print_exc()
            await self.speak(f"Error entering {value} into {field_name} field")
            return False

    async def _enter_generic_field(self, field_name, value):
        """Enter a value into a generic form field

        Args:
            field_name: The name of the field
            value: The value to enter

        Returns:
            bool: True if successful, False otherwise
        """
        await self.speak(f"Entering {value} into {field_name} field...")

        try:
            # Clean up field name for use in selectors
            clean_field_name = field_name.lower().replace(" ", "-").replace("_", "-")

            # Generate selectors for the field
            selectors = [
                f'input[name="{clean_field_name}"]',
                f'input[name="{field_name}"]',
                f'input[id="{clean_field_name}"]',
                f'input[id="{field_name}"]',
                f'input[placeholder*="{field_name}" i]',
                f'input[aria-label*="{field_name}" i]',
                f'textarea[name="{clean_field_name}"]',
                f'textarea[id="{clean_field_name}"]',
                f'textarea[placeholder*="{field_name}" i]',
                f'textarea[aria-label*="{field_name}" i]',
                f'input[name*="{clean_field_name}"]',
                f'input[id*="{clean_field_name}"]',
                f'input[name*="{field_name}"]',
                f'input[id*="{field_name}"]',
                f'#{clean_field_name}',
                f'.{clean_field_name}',
                f'label:has-text("{field_name}") + input',
                f'label:has-text("{field_name}") input',
                f'div:has-text("{field_name}") input',
                f'*:has-text("{field_name}") input'
            ]

            # Get LLM-generated selectors
            context = await self.llm_utils.get_page_context()
            llm_selectors = await self.llm_utils.get_selectors(f"find {field_name} input field", context)

            # Try each selector
            for selector in llm_selectors + selectors:
                try:
                    print(f"Trying field selector: {selector}")
                    if await self.page.locator(selector).count() > 0:
                        await self.browser_utils.retry_type(selector, value, f"{field_name} field")
                        print(f"Filled {field_name} field with '{value}' using selector: {selector}")
                        await self.speak(f"Entered {value} into {field_name} field")
                        return True
                except Exception as e:
                    print(f"Error with field selector {selector}: {e}")
                    continue

            # If no selector worked, try using JavaScript
            print("Trying JavaScript approach for finding and filling the field...")

            # Create a JavaScript function with embedded field name and value
            js_code = f"""
                () => {{
                    try {{
                        const fieldName = "{field_name}";
                        const value = "{value}";
                        console.log("Looking for field: " + fieldName);

                        // Try to find input by label text
                        const labels = Array.from(document.querySelectorAll('label'));
                        for (const label of labels) {{
                            if (label.textContent.toLowerCase().includes(fieldName.toLowerCase())) {{
                                // Try to find the input by id if label has a for attribute
                                if (label.htmlFor) {{
                                    const input = document.getElementById(label.htmlFor);
                                    if (input) {{
                                        input.value = value;
                                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                        console.log("Filled field by label.htmlFor: ", input);
                                        return true;
                                    }}
                                }}

                                // Try to find input as a child of the label
                                const labelInput = label.querySelector('input, textarea, select');
                                if (labelInput) {{
                                    labelInput.value = value;
                                    labelInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                    labelInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    console.log("Filled field as child of label: ", labelInput);
                                    return true;
                                }}

                                // Try to find input near the label
                                const labelParent = label.parentElement;
                                if (labelParent) {{
                                    const nearbyInput = labelParent.querySelector('input, textarea, select');
                                    if (nearbyInput) {{
                                        nearbyInput.value = value;
                                        nearbyInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        nearbyInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                        console.log("Filled field near label: ", nearbyInput);
                                        return true;
                                    }}
                                }}
                            }}
                        }}

                        // Try to find input by name or id
                        const inputs = Array.from(document.querySelectorAll('input, textarea, select'));
                        for (const input of inputs) {{
                            if (input.name && input.name.toLowerCase().includes(fieldName.toLowerCase()) ||
                                input.id && input.id.toLowerCase().includes(fieldName.toLowerCase()) ||
                                input.placeholder && input.placeholder.toLowerCase().includes(fieldName.toLowerCase())) {{
                                input.value = value;
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                console.log("Filled field by name/id/placeholder: ", input);
                                return true;
                            }}
                        }}

                        // Try to find any input near text matching the field name
                        const allElements = Array.from(document.querySelectorAll('*'));
                        for (const el of allElements) {{
                            if (el.textContent.toLowerCase().includes(fieldName.toLowerCase())) {{
                                // Look for an input in this element or its parent
                                const container = el.closest('div, form, fieldset');
                                if (container) {{
                                    const containerInput = container.querySelector('input, textarea, select');
                                    if (containerInput) {{
                                        containerInput.value = value;
                                        containerInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        containerInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                        console.log("Filled field near matching text: ", containerInput);
                                        return true;
                                    }}
                                }}
                            }}
                        }}

                        console.log("Could not find field");
                        return false;
                    }} catch (error) {{
                        console.error("Error finding/filling field: ", error);
                        return false;
                    }}
                }}
            """
            js_result = await self.page.evaluate(js_code)

            if js_result:
                print(f"Filled {field_name} field with '{value}' using JavaScript")
                await self.speak(f"Entered {value} into {field_name} field")
                return True

            await self.speak(f"Could not find {field_name} field")
            return False
        except Exception as e:
            print(f"Error filling {field_name} field: {e}")
            import traceback
            traceback.print_exc()
            await self.speak(f"Error entering {value} into {field_name} field")
            return False

    async def _enter_email(self, email):
        """Enter email in an email input field

        Args:
            email: The email address to enter

        Returns:
            bool: True if successful, False otherwise
        """
        await self.speak(f"Entering email: {email}")

        try:
            # Define specific selectors for email fields
            specific_email_selector = '#floating_outlined3'

            # Try specific selector first
            try:
                if await self.page.locator(specific_email_selector).count() > 0:
                    await self.browser_utils.retry_type(specific_email_selector, email, "email address")
                    await self.speak(f"Entered email address")
                    return True
            except Exception as e:
                print(f"Error with specific email selector: {e}")

            # Get page context for LLM
            context = await self.llm_utils.get_page_context()

            # Get LLM-generated selectors
            email_selectors = await self.llm_utils.get_selectors("find email input field", context)

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

            # Try all selectors
            for selector in email_selectors + fallback_email_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self.browser_utils.retry_type(selector, email, "email address")
                        await self.speak(f"Entered email address")
                        return True
                except Exception as e:
                    print(f"Error with email selector {selector}: {e}")
                    continue

            # If selectors didn't work, try JavaScript
            try:
                js_result = await self.page.evaluate(f"""() => {{
                    try {{
                        console.log("Trying to fill email field with JavaScript");

                        // Try specific ID first
                        let emailField = document.getElementById('floating_outlined3');
                        if (emailField) {{
                            emailField.value = "{email}";
                            emailField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            emailField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            console.log("Email field filled with:", "{email}");
                            return {{ success: true, message: "Filled email field by ID" }};
                        }}

                        // Try by type and name
                        emailField = document.querySelector('input[type="email"], input[name="email"], input[id*="email"]');
                        if (emailField) {{
                            emailField.value = "{email}";
                            emailField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            emailField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            console.log("Email field filled with:", "{email}");
                            return {{ success: true, message: "Filled email field by type/name" }};
                        }}

                        // Try by placeholder
                        emailField = document.querySelector('input[placeholder*="email"], input[placeholder*="Email"]');
                        if (emailField) {{
                            emailField.value = "{email}";
                            emailField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            emailField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            console.log("Email field filled with:", "{email}");
                            return {{ success: true, message: "Filled email field by placeholder" }};
                        }}

                        // Try by label
                        const labels = Array.from(document.querySelectorAll('label'));
                        for (const label of labels) {{
                            if (label.textContent.toLowerCase().includes('email')) {{
                                const forAttr = label.getAttribute('for');
                                if (forAttr) {{
                                    emailField = document.getElementById(forAttr);
                                    if (emailField) {{
                                        emailField.value = "{email}";
                                        emailField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        emailField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                        console.log("Email field filled with:", "{email}");
                                        return {{ success: true, message: "Filled email field by label" }};
                                    }}
                                }}

                                // Try sibling or parent-child relationship
                                const parent = label.parentElement;
                                if (parent) {{
                                    emailField = parent.querySelector('input');
                                    if (emailField) {{
                                        emailField.value = "{email}";
                                        emailField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        emailField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                        console.log("Email field filled with:", "{email}");
                                        return {{ success: true, message: "Filled email field by parent-child relationship" }};
                                    }}
                                }}
                            }}
                        }}

                        // Last resort: try first input
                        const inputs = document.querySelectorAll('input');
                        if (inputs.length > 0) {{
                            inputs[0].value = "{email}";
                            inputs[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
                            inputs[0].dispatchEvent(new Event('change', {{ bubbles: true }}));
                            console.log("First input field filled with:", "{email}");
                            return {{ success: true, message: "Filled first input field as last resort" }};
                        }}

                        return {{ success: false, message: "Could not find email field" }};
                    }} catch (error) {{
                        console.error("Error in email fill:", error);
                        return {{ success: false, error: error.toString() }};
                    }}
                }}""")

                if js_result and js_result.get('success'):
                    await self.speak(js_result.get('message', "Entered email address"))
                    return True
                else:
                    print(f"JavaScript email fill failed: {js_result.get('error') or js_result.get('message')}")
            except Exception as e:
                print(f"Error with JavaScript email fill: {e}")

            await self.speak("Could not find email field")
            return False
        except Exception as e:
            print(f"Error entering email: {e}")
            await self.speak(f"Error entering email")
            return False
