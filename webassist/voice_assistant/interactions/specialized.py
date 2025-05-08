"""
Specialized interaction handlers for the Voice Assistant.

This module contains specialized handlers for specific interactions that require
custom logic, such as state dropdown selection, login handling, etc.
"""

import re
import asyncio
from typing import Dict, List, Any, Optional

from webassist.Common.constants import *
from webassist.voice_assistant.interactions.member_manager import MemberManagerHandler


class SpecializedHandler:
    """Handler for specialized interactions that require custom logic"""

    def __init__(self, page, speak_func, llm_utils, browser_utils):
        """Initialize the specialized handler"""
        self.page = page
        self.speak = speak_func
        self.llm_utils = llm_utils
        self.browser_utils = browser_utils

        # Initialize sub-handlers
        self.member_manager_handler = MemberManagerHandler(page, speak_func, llm_utils, browser_utils)

    async def handle_command(self, command: str) -> bool:
        """Handle specialized commands"""
        # First try to handle with the member manager handler
        if await self.member_manager_handler.handle_command(command):
            return True

        # Handle dropdown filter command
        filter_dropdown_match = re.search(r'filter (?:dropdown|list) (?:for )?(.*)', command, re.IGNORECASE)
        if filter_dropdown_match:
            search_text = filter_dropdown_match.group(1).strip()
            success = await self.handle_primeng_dropdown_filter(search_text)
            if success:
                await self.speak(f"Successfully filtered dropdown for '{search_text}'")
            else:
                await self.speak("Failed to filter dropdown")
            return True

        # Handle state selection command
        state_match = re.search(r'(?:select|choose|pick)\s+(?:state\s+)?([A-Za-z\s]+)(?:\s+(?:state|as\s+state))?', command, re.IGNORECASE)
        if state_match:
            state_name = state_match.group(1).strip()
            return await self.handle_state_selection(state_name)

        # Handle state dropdown command (address form)
        state_dropdown_match = re.search(r'(?:click|select|open)\s+(?:the\s+)?state(?:\s+dropdown)?', command, re.IGNORECASE)
        if state_dropdown_match:
            await self.speak("Looking for state dropdown in address form...")
            return await self.click_address_state_dropdown()

        # Handle state dropdown command (formation)
        state_dropdown_match = re.search(r'(?:cl[ci]?[ck]k?|select|open)(?:\s+(?:on|the))?\s+(?:state(?:\s+of\s+formation)?|formation\s+state|state\s+dropdown)(?:\s+dropdown)?', command, re.IGNORECASE)
        if state_dropdown_match:
            await self.speak("Looking for state of formation dropdown...")
            return await self.click_state_dropdown_direct()

        # Handle principal address dropdown command
        address_dropdown_match = re.search(r'(?:click|select|open)(?:\s+(?:on|the))?\s+(?:principal(?:\s+address)?|address)(?:\s+dropdown)?', command, re.IGNORECASE)
        if address_dropdown_match:
            await self.speak("Looking for principal address dropdown...")
            return await self.click_principal_address_dropdown()

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
            await self.speak("Logging in with email and password...")
            return await self.handle_login(email, password)

        return False

    async def handle_primeng_dropdown_filter(self, search_text: str) -> bool:
        """Handle filtering a PrimeNG dropdown"""
        try:
            # Check if dropdown panel is open
            panel_visible = await self.page.evaluate("""() => {
                return document.querySelector('.p-dropdown-panel') !== null;
            }""")

            if not panel_visible:
                await self.speak("Please open a dropdown first")
                return False

            # Use JavaScript to find and fill the filter input
            filtered = await self.page.evaluate("""(searchText) => {
                const filterInput = document.querySelector('.p-dropdown-filter');
                if (!filterInput) {
                    console.log("No filter input found");
                    return false;
                }

                // Fill the filter input
                filterInput.value = searchText;
                filterInput.dispatchEvent(new Event('input', { bubbles: true }));
                return true;
            }""", search_text)

            return filtered
        except Exception as e:
            print(f"Error filtering dropdown: {e}")
            return False

    async def handle_state_selection(self, state_name: str) -> bool:
        """Handle state selection from dropdown"""
        await self.speak(f"Looking for state {state_name}...")

        try:
            # First try to click the state dropdown using JavaScript
            clicked = await self.page.evaluate("""() => {
                // STRATEGY 1: Find by exact "Select a State" text in dropdown label
                const stateLabels = Array.from(document.querySelectorAll('.p-dropdown-label'))
                    .filter(el => el.textContent.trim() === 'Select a State');

                if (stateLabels.length > 0) {
                    const dropdownContainer = stateLabels[0].closest('.p-dropdown');
                    if (dropdownContainer) {
                        dropdownContainer.click();
                        return true;
                    }
                }

                // STRATEGY 2: Find by label with asterisk
                const stateLabelsWithAsterisk = Array.from(document.querySelectorAll('label, span, div'))
                    .filter(el => {
                        const text = el.textContent.trim();
                        return text.includes('State') && text.includes('*');
                    });

                if (stateLabelsWithAsterisk.length > 0) {
                    for (const label of stateLabelsWithAsterisk) {
                        let current = label;
                        while (current.nextElementSibling) {
                            current = current.nextElementSibling;
                            if (current.classList.contains('p-dropdown')) {
                                current.click();
                                return true;
                            }
                        }
                    }
                }

                // STRATEGY 3: Find dropdown by position (state is typically after city)
                const cityField = document.querySelector('input[placeholder*="City" i]');
                if (cityField) {
                    let current = cityField.parentElement;
                    while (current.nextElementSibling) {
                        current = current.nextElementSibling;
                        const dropdown = current.querySelector('.p-dropdown');
                        if (dropdown) {
                            dropdown.click();
                            return true;
                        }
                    }
                }

                // STRATEGY 4: Find by class and position
                const dropdowns = document.querySelectorAll('.p-dropdown');
                if (dropdowns.length >= 2) {
                    // State dropdown is typically the second dropdown in address forms
                    dropdowns[1].click();
                    return true;
                }

                return false;
            }""")

            if not clicked:
                await self.speak("Could not find state dropdown")
                return False

            # Wait for dropdown panel to appear
            await self.page.wait_for_timeout(1000)

            # Try to select the state using JavaScript
            selected = await self.page.evaluate("""(stateName) => {
                const items = Array.from(document.querySelectorAll('.p-dropdown-item'));
                const stateItem = items.find(item => item.textContent.trim() === stateName);

                if (stateItem) {
                    stateItem.click();
                    return true;
                }

                return false;
            }""", state_name)

            if selected:
                await self.speak(f"Selected state {state_name}")
                return True
            else:
                await self.speak(f"Could not find state option: {state_name}")
                return False

        except Exception as e:
            await self.speak(f"Error selecting state: {str(e)}")
            return False

    async def click_address_state_dropdown(self) -> bool:
        """Click the state dropdown in the address form"""
        try:
            # Use JavaScript to find and click the state dropdown
            clicked = await self.page.evaluate("""() => {
                // STRATEGY 1: Find by exact "Select a State" text in dropdown label
                const stateLabels = Array.from(document.querySelectorAll('.p-dropdown-label'))
                    .filter(el => el.textContent.trim() === 'Select a State');

                if (stateLabels.length > 0) {
                    const dropdownContainer = stateLabels[0].closest('.p-dropdown');
                    if (dropdownContainer) {
                        dropdownContainer.click();
                        return true;
                    }
                }

                // STRATEGY 2: Find by label with asterisk
                const stateLabelsWithAsterisk = Array.from(document.querySelectorAll('label, span, div'))
                    .filter(el => {
                        const text = el.textContent.trim();
                        return text.includes('State') && text.includes('*');
                    });

                if (stateLabelsWithAsterisk.length > 0) {
                    for (const label of stateLabelsWithAsterisk) {
                        let current = label;
                        while (current.nextElementSibling) {
                            current = current.nextElementSibling;
                            if (current.classList.contains('p-dropdown')) {
                                current.click();
                                return true;
                            }
                        }
                    }
                }

                // STRATEGY 3: Find dropdown by position (state is typically after city)
                const cityField = document.querySelector('input[placeholder*="City" i]');
                if (cityField) {
                    let current = cityField.parentElement;
                    while (current.nextElementSibling) {
                        current = current.nextElementSibling;
                        const dropdown = current.querySelector('.p-dropdown');
                        if (dropdown) {
                            dropdown.click();
                            return true;
                        }
                    }
                }

                // STRATEGY 4: Find by class and position
                const dropdowns = document.querySelectorAll('.p-dropdown');
                if (dropdowns.length >= 2) {
                    // State dropdown is typically the second dropdown in address forms
                    dropdowns[1].click();
                    return true;
                }

                return false;
            }""")

            if clicked:
                await self.speak("Clicked the State dropdown in address form.")
                await self.page.wait_for_timeout(1000)
                return True
            else:
                await self.speak("Could not find the State dropdown in address form.")
                return False

        except Exception as e:
            print(f"Error clicking state dropdown: {e}")
            return False

    async def click_state_dropdown_direct(self) -> bool:
        """Click the state of formation dropdown using direct DOM manipulation"""
        try:
            # Log dropdown information for debugging
            await self.page.evaluate("""() => {
                console.log("Logging dropdown information...");
                const allDropdowns = document.querySelectorAll('.p-dropdown');
                console.log(`Found ${allDropdowns.length} dropdowns on the page`);

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
                await self.speak("Clicked the State of Formation dropdown")
                await self.page.wait_for_timeout(1000)  # Wait a bit for dropdown to open
                return True
            else:
                # If specialized approach failed, fall back to generic method
                await self.speak("Specialized approach failed, trying generic method...")
                return await self.click_generic_dropdown("State of Formation")
        except Exception as e:
            print(f"Error with specialized state dropdown click: {e}")
            await self.speak("Error with specialized approach, trying generic method...")
            return await self.click_generic_dropdown("State of Formation")

    async def click_principal_address_dropdown(self) -> bool:
        """Click the principal address dropdown"""
        try:
            # Use JavaScript to find and click the principal address dropdown
            clicked = await self.page.evaluate("""() => {
                // Look for elements with "Principal Address" text
                const addressElements = Array.from(document.querySelectorAll('*'))
                    .filter(el => {
                        const text = el.textContent.toLowerCase().trim();
                        return text.includes('principal') && text.includes('address');
                    });

                console.log(`Found ${addressElements.length} elements with "Principal Address" text`);

                if (addressElements.length > 0) {
                    for (const element of addressElements) {
                        console.log(`Found element with text: "${element.textContent.trim()}"`);

                        // Look for nearby dropdowns
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
                                    console.log(`Found dropdown in sibling of "Principal Address" element`);
                                    dropdown.click();
                                    return true;
                                }

                                if (sibling.classList.contains('p-dropdown')) {
                                    console.log(`Found dropdown sibling of "Principal Address" element`);
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

                // If we couldn't find by text, try by position
                const dropdowns = document.querySelectorAll('.p-dropdown');
                if (dropdowns.length >= 3) {
                    // Principal address dropdown is typically the third dropdown
                    console.log(`Using positional heuristic: clicking the third dropdown`);
                    dropdowns[2].click();
                    return true;
                }

                return false;
            }""")

            if clicked:
                await self.speak("Clicked the Principal Address dropdown")
                await self.page.wait_for_timeout(1000)
                return True
            else:
                await self.speak("Could not find the Principal Address dropdown")
                return False

        except Exception as e:
            print(f"Error clicking principal address dropdown: {e}")
            return False

    async def click_generic_dropdown(self, dropdown_name: str) -> bool:
        """Click a dropdown by name using generic methods"""
        try:
            # Use JavaScript to find and click the dropdown
            clicked = await self.page.evaluate("""(dropdownName) => {
                // Convert to lowercase for case-insensitive comparison
                const searchName = dropdownName.toLowerCase();

                // STRATEGY 1: Find by label text
                const labels = Array.from(document.querySelectorAll('label, span, div'))
                    .filter(el => el.textContent.toLowerCase().includes(searchName));

                console.log(`Found ${labels.length} elements with text containing "${searchName}"`);

                if (labels.length > 0) {
                    for (const label of labels) {
                        // Look for nearby dropdowns
                        let current = label;
                        while (current.nextElementSibling) {
                            current = current.nextElementSibling;
                            if (current.classList.contains('p-dropdown')) {
                                current.click();
                                return true;
                            }

                            const dropdown = current.querySelector('.p-dropdown');
                            if (dropdown) {
                                dropdown.click();
                                return true;
                            }
                        }

                        // Check parent's siblings
                        const parent = label.parentElement;
                        if (parent) {
                            let sibling = parent.nextElementSibling;
                            while (sibling) {
                                if (sibling.classList.contains('p-dropdown')) {
                                    sibling.click();
                                    return true;
                                }

                                const dropdown = sibling.querySelector('.p-dropdown');
                                if (dropdown) {
                                    dropdown.click();
                                    return true;
                                }

                                sibling = sibling.nextElementSibling;
                            }
                        }
                    }
                }

                // STRATEGY 2: Find by dropdown label text
                const dropdownLabels = Array.from(document.querySelectorAll('.p-dropdown-label'))
                    .filter(el => el.textContent.toLowerCase().includes(searchName));

                if (dropdownLabels.length > 0) {
                    const dropdownContainer = dropdownLabels[0].closest('.p-dropdown');
                    if (dropdownContainer) {
                        dropdownContainer.click();
                        return true;
                    }
                }

                return false;
            }""", dropdown_name)

            if clicked:
                await self.speak(f"Clicked the {dropdown_name} dropdown")
                await self.page.wait_for_timeout(1000)
                return True
            else:
                await self.speak(f"Could not find the {dropdown_name} dropdown")
                return False

        except Exception as e:
            print(f"Error clicking {dropdown_name} dropdown: {e}")
            return False

    async def handle_login(self, email: str, password: str) -> bool:
        """Handle login with email and password"""
        try:
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
            login_selectors = await self.llm_utils.get_selectors("find login or sign in link or button", await self.browser_utils.get_page_context())
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
            form_elements = await self.check_for_input_fields()
            print(f"DOM inspection results: {form_elements}")

            # Get page context after potential navigation
            context = await self.browser_utils.get_page_context()

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
        except Exception as e:
            print(f"Error handling login: {e}")
            await self.speak(f"Error during login: {str(e)}")
            return False

    async def check_for_input_fields(self):
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
                        placeholder: input.placeholder
                    }))
                };
            }""")

            return form_elements
        except Exception as e:
            print(f"Error checking for input fields: {e}")
            return {}
