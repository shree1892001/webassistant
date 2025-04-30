import re
from typing import List, Dict, Any

class LoginHandler:
    def __init__(self, assistant):
        self.assistant = assistant

    async def handle_login(self, command: str) -> bool:
        """Handle login commands"""
        # Simple login pattern
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
            return await self._perform_login(email, password)
        return False

    async def _perform_login(self, email: str, password: str) -> bool:
        """Perform the actual login process"""
        self.assistant.speak("Logging in with email and password...")

        url = self.assistant.page.url
        if not ('signin' in url or 'login' in url):
            self.assistant.speak("Navigating to signin page first...")
            # Navigate to the correct signin URL
            try:
                await self.assistant.page.goto("https://www.redberyltest.in/#/signin", wait_until="networkidle", timeout=20000)
                self.assistant.speak("Navigated to signin page")
                # Wait for the page to load
                await self.assistant.page.wait_for_timeout(5000)
            except Exception as e:
                self.assistant.speak(f"Failed to navigate to signin page: {str(e)}")
                return False

        # Now we should be on the login page
        self.assistant.speak("Found login page. Looking for login form...")
        # Try to find and click login button if needed
        login_selectors = await self.assistant._get_llm_selectors("find login or sign in link or button", await self.assistant._get_page_context())
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
                if await self.assistant.page.locator(selector).count() > 0:
                    await self.assistant.page.locator(selector).first.click()
                    self.assistant.speak("Found and clicked login option. Waiting for form to appear...")
                    await self.assistant.page.wait_for_timeout(5000)  # Wait for form to appear
                    break
            except Exception:
                continue

        # Perform DOM inspection to find form elements
        form_elements = await self.assistant._check_for_input_fields()
        print(f"DOM inspection results: {form_elements}")

        # Get page context after potential navigation
        context = await self.assistant._get_page_context()

        # Define specific selectors for known form elements
        specific_email_selector = '#floating_outlined3'
        specific_password_selector = '#floating_outlined15'
        specific_button_selector = '#signInButton'

        if form_elements.get('hasEmailField') or form_elements.get('hasPasswordField'):
            try:
                # Use JavaScript to fill the form directly
                self.assistant.speak("Using direct DOM manipulation to fill login form...")
                js_result = await self.assistant.page.evaluate(f"""() => {{
                    try {{
                        console.log("Starting form fill process...");
                        // Find email field
                        let emailField = document.querySelector('{specific_email_selector}');
                        if (!emailField) {{
                            console.log("Email field not found with specific selector, trying alternatives...");
                            emailField = document.querySelector('input[type="email"]') || 
                                        document.querySelector('input[name="email"]') ||
                                        document.querySelector('input[placeholder*="email" i]');
                        }}
                        
                        // Find password field
                        let passwordField = document.querySelector('{specific_password_selector}');
                        if (!passwordField) {{
                            console.log("Password field not found with specific selector, trying alternatives...");
                            passwordField = document.querySelector('input[type="password"]') || 
                                           document.querySelector('input[name="password"]') ||
                                           document.querySelector('input[placeholder*="password" i]');
                        }}
                        
                        // Find submit button
                        let submitButton = document.querySelector('{specific_button_selector}');
                        if (!submitButton) {{
                            console.log("Submit button not found with specific selector, trying alternatives...");
                            submitButton = document.querySelector('button[type="submit"]') || 
                                          document.querySelector('input[type="submit"]') ||
                                          document.querySelector('button:has-text("Login")') ||
                                          document.querySelector('button:has-text("Sign in")');
                        }}
                        
                        if (emailField && passwordField && submitButton) {{
                            console.log("All form elements found, filling form...");
                            emailField.value = '{email}';
                            passwordField.value = '{password}';
                            
                            // Trigger input events
                            emailField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            passwordField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            
                            // Click submit button
                            submitButton.click();
                            return true;
                        }} else {{
                            console.log("Missing form elements:", {{
                                emailField: !!emailField,
                                passwordField: !!passwordField,
                                submitButton: !!submitButton
                            }});
                            return false;
                        }}
                    }} catch (error) {{
                        console.error("Error in form fill:", error);
                        return false;
                    }}
                }}""")

                if js_result:
                    self.assistant.speak("Login form filled and submitted")
                    await self.assistant.page.wait_for_timeout(5000)  # Wait for login to process
                    return True
                else:
                    self.assistant.speak("Failed to fill login form using JavaScript")
                    return False
            except Exception as e:
                self.assistant.speak(f"Error during login: {str(e)}")
                return False

        return False 