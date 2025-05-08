"""
Login Fix - A script to fix login functionality in the Voice Direct Modular Web Assistant.

This script provides a direct implementation of login functionality that can be used
with the Voice Direct Modular Web Assistant.
"""

import os
import asyncio
import logging
import sys
import re
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def login_with_credentials(page, email, password):
    """Log in with email and password"""
    try:
        print(f"Attempting to log in with email {email}")
        
        # Try to fill email field
        email_filled = await fill_email_field(page, email)
        
        # Try to fill password field
        password_filled = await fill_password_field(page, password)
        
        if email_filled and password_filled:
            # Try to click login button
            print("Clicking login button...")
            button_clicked = await click_login_button(page)
            
            if button_clicked:
                print("Login form submitted")
                return True
            else:
                print("Could not find login button")
                return False
        else:
            print("Could not fill all login fields")
            return False
            
    except Exception as e:
        logger.error(f"Error during login: {e}")
        print(f"Error during login: {str(e)}")
        return False


async def fill_email_field(page, email):
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
                element = await page.query_selector(selector)
                if element:
                    await element.fill(email)
                    logger.info(f"Filled email field with selector: {selector}")
                    return True
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                continue
        
        # If no selector worked, try using JavaScript
        js_result = await page.evaluate(f"""
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
            
        print("Could not find email field")
        return False
        
    except Exception as e:
        logger.error(f"Error filling email field: {e}")
        print(f"Error filling email field: {str(e)}")
        return False


async def fill_password_field(page, password):
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
                element = await page.query_selector(selector)
                if element:
                    await element.fill(password)
                    logger.info(f"Filled password field with selector: {selector}")
                    return True
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                continue
        
        # If no selector worked, try using JavaScript
        js_result = await page.evaluate(f"""
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
            
        print("Could not find password field")
        return False
        
    except Exception as e:
        logger.error(f"Error filling password field: {e}")
        print(f"Error filling password field: {str(e)}")
        return False


async def click_login_button(page):
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
                element = await page.query_selector(selector)
                if element:
                    await element.click()
                    logger.info(f"Clicked login button with selector: {selector}")
                    return True
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                continue
        
        # If no selector worked, try using JavaScript
        js_result = await page.evaluate("""
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
            
        print("Could not find login button")
        return False
        
    except Exception as e:
        logger.error(f"Error clicking login button: {e}")
        print(f"Error clicking login button: {str(e)}")
        return False


async def main():
    """Main entry point for testing"""
    try:
        print("This script provides login functionality for the Voice Direct Modular Web Assistant.")
        print("To use it, import the functions into your main script.")
        
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        import traceback
        logger.error(f"Fatal error: {e}")
        traceback.print_exc()
