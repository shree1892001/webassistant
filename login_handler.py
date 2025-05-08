"""
Login Handler - A specialized handler for login functionality.

This module provides a specialized handler for login functionality,
with direct DOM manipulation and multiple fallback mechanisms.
"""

import re
import asyncio
import logging

logger = logging.getLogger(__name__)

class LoginHandler:
    """Handler for login functionality"""
    
    def __init__(self, page, speak_func, llm_utils, browser_utils):
        """Initialize the handler"""
        self.page = page
        self.speak = speak_func
        self.llm_utils = llm_utils
        self.browser_utils = browser_utils
        
    async def handle_command(self, command):
        """Handle a login-related command"""
        # Check if this is a login command
        if re.search(r'(log\s*in|sign\s*in|login|signin)', command, re.IGNORECASE):
            # Extract email and password if provided
            email_match = re.search(r'email\s+([^\s]+)', command, re.IGNORECASE)
            password_match = re.search(r'password\s+([^\s]+)', command, re.IGNORECASE)
            
            email = email_match.group(1) if email_match else None
            password = password_match.group(1) if password_match else None
            
            if email and password:
                await self.speak(f"Attempting to log in with email {email}")
                return await self.login_with_credentials(email, password)
            else:
                await self.speak("Looking for login button...")
                return await self.click_login_button()
                
        # Check for enter email command
        elif re.search(r'enter\s+email', command, re.IGNORECASE):
            email_match = re.search(r'email\s+([^\s]+)', command, re.IGNORECASE)
            if email_match:
                email = email_match.group(1)
                await self.speak(f"Entering email: {email}")
                return await self.fill_email_field(email)
            else:
                await self.speak("Please specify an email address")
                return True
                
        # Check for enter password command
        elif re.search(r'enter\s+password', command, re.IGNORECASE):
            password_match = re.search(r'password\s+([^\s]+)', command, re.IGNORECASE)
            if password_match:
                password = password_match.group(1)
                await self.speak(f"Entering password")
                return await self.fill_password_field(password)
            else:
                await self.speak("Please specify a password")
                return True
                
        # Not a login-related command
        return False
        
    async def login_with_credentials(self, email, password):
        """Log in with email and password"""
        try:
            # First try with common selectors
            await self.speak("Attempting to fill login form...")
            
            # Try to fill email field
            email_filled = await self.fill_email_field(email)
            
            # Try to fill password field
            password_filled = await self.fill_password_field(password)
            
            if email_filled and password_filled:
                # Try to click login button
                await self.speak("Clicking login button...")
                button_clicked = await self.click_login_button()
                
                if button_clicked:
                    await self.speak("Login form submitted")
                    return True
                else:
                    await self.speak("Could not find login button")
                    return True
            else:
                await self.speak("Could not fill all login fields")
                return True
                
        except Exception as e:
            logger.error(f"Error during login: {e}")
            await self.speak(f"Error during login: {str(e)}")
            return True
            
    async def fill_email_field(self, email):
        """Fill the email field"""
        try:
            # Try common email field selectors
            selectors = [
                "#email",
                "#username",
                "input[type='email']",
                "input[name='email']",
                "input[name='username']",
                "#floating_outlined3",  # Specific selector from user's requirements
                "input.email",
                "input.username"
            ]
            
            # Try each selector
            for selector in selectors:
                try:
                    # Check if the selector exists
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.fill(email)
                        logger.info(f"Filled email field with selector: {selector}")
                        return True
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            # If no selector worked, try using JavaScript
            js_result = await self.page.evaluate(f"""
                (email) => {{
                    // Try to find email input by various attributes
                    const emailInputs = Array.from(document.querySelectorAll('input')).filter(el => 
                        el.type === 'email' || 
                        el.name === 'email' || 
                        el.id === 'email' || 
                        el.placeholder?.toLowerCase().includes('email') ||
                        el.id === 'floating_outlined3'
                    );
                    
                    if (emailInputs.length > 0) {{
                        emailInputs[0].value = email;
                        return true;
                    }}
                    return false;
                }}
            """, email)
            
            if js_result:
                logger.info("Filled email field using JavaScript")
                return True
                
            # If still not found, ask LLM for help
            await self.speak("Asking AI for help with email field...")
            llm_selectors = await self.llm_utils.get_element_selectors("email input field")
            
            for selector in llm_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.fill(email)
                        logger.info(f"Filled email field with LLM selector: {selector}")
                        return True
                except Exception as e:
                    logger.debug(f"Error with LLM selector {selector}: {e}")
                    continue
            
            await self.speak("Could not find email field")
            return False
            
        except Exception as e:
            logger.error(f"Error filling email field: {e}")
            await self.speak(f"Error filling email field: {str(e)}")
            return False
            
    async def fill_password_field(self, password):
        """Fill the password field"""
        try:
            # Try common password field selectors
            selectors = [
                "#password",
                "input[type='password']",
                "input[name='password']",
                "#floating_outlined15",  # Specific selector from user's requirements
                "input.password"
            ]
            
            # Try each selector
            for selector in selectors:
                try:
                    # Check if the selector exists
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.fill(password)
                        logger.info(f"Filled password field with selector: {selector}")
                        return True
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            # If no selector worked, try using JavaScript
            js_result = await self.page.evaluate(f"""
                (password) => {{
                    // Try to find password input by various attributes
                    const passwordInputs = Array.from(document.querySelectorAll('input')).filter(el => 
                        el.type === 'password' || 
                        el.name === 'password' || 
                        el.id === 'password' ||
                        el.id === 'floating_outlined15'
                    );
                    
                    if (passwordInputs.length > 0) {{
                        passwordInputs[0].value = password;
                        return true;
                    }}
                    return false;
                }}
            """, password)
            
            if js_result:
                logger.info("Filled password field using JavaScript")
                return True
                
            # If still not found, ask LLM for help
            await self.speak("Asking AI for help with password field...")
            llm_selectors = await self.llm_utils.get_element_selectors("password input field")
            
            for selector in llm_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.fill(password)
                        logger.info(f"Filled password field with LLM selector: {selector}")
                        return True
                except Exception as e:
                    logger.debug(f"Error with LLM selector {selector}: {e}")
                    continue
            
            await self.speak("Could not find password field")
            return False
            
        except Exception as e:
            logger.error(f"Error filling password field: {e}")
            await self.speak(f"Error filling password field: {str(e)}")
            return False
            
    async def click_login_button(self):
        """Click the login button"""
        try:
            # Try common login button selectors
            selectors = [
                "#login",
                "#signin",
                "#signInButton",  # Specific selector from user's requirements
                "button[type='submit']",
                "input[type='submit']",
                "button:contains('Log in')",
                "button:contains('Sign in')",
                "a:contains('Log in')",
                "a:contains('Sign in')"
            ]
            
            # Try each selector
            for selector in selectors:
                try:
                    # Check if the selector exists
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.click()
                        logger.info(f"Clicked login button with selector: {selector}")
                        return True
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            # If no selector worked, try using JavaScript
            js_result = await self.page.evaluate("""
                () => {
                    // Try to find login button by various attributes and text content
                    const loginTexts = ['log in', 'login', 'sign in', 'signin', 'submit'];
                    
                    // Check buttons
                    const buttons = Array.from(document.querySelectorAll('button'));
                    for (const button of buttons) {
                        const text = button.textContent.toLowerCase();
                        if (loginTexts.some(loginText => text.includes(loginText)) || 
                            button.id === 'signInButton' ||
                            button.type === 'submit') {
                            button.click();
                            return true;
                        }
                    }
                    
                    // Check links
                    const links = Array.from(document.querySelectorAll('a'));
                    for (const link of links) {
                        const text = link.textContent.toLowerCase();
                        if (loginTexts.some(loginText => text.includes(loginText))) {
                            link.click();
                            return true;
                        }
                    }
                    
                    // Check inputs
                    const inputs = Array.from(document.querySelectorAll('input[type="submit"]'));
                    if (inputs.length > 0) {
                        inputs[0].click();
                        return true;
                    }
                    
                    return false;
                }
            """)
            
            if js_result:
                logger.info("Clicked login button using JavaScript")
                return True
                
            # If still not found, ask LLM for help
            await self.speak("Asking AI for help with login button...")
            llm_selectors = await self.llm_utils.get_element_selectors("login button or submit button")
            
            for selector in llm_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.click()
                        logger.info(f"Clicked login button with LLM selector: {selector}")
                        return True
                except Exception as e:
                    logger.debug(f"Error with LLM selector {selector}: {e}")
                    continue
            
            await self.speak("Could not find login button")
            return False
            
        except Exception as e:
            logger.error(f"Error clicking login button: {e}")
            await self.speak(f"Error clicking login button: {str(e)}")
            return False
