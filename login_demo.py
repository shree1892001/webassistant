"""
Login Demo - A simple demonstration of login functionality.

This script provides a simple demonstration of how to use the login functionality
from login_fix.py with the Voice Direct Modular Web Assistant.
"""

import os
import asyncio
import logging
import sys
from dotenv import load_dotenv

from playwright.async_api import async_playwright

# Import login functions
from login_fix import login_with_credentials, fill_email_field, fill_password_field, click_login_button

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def main():
    """Main entry point"""
    try:
        print("\n" + "="*50)
        print("Login Demo - Web Assistant")
        print("="*50 + "\n")

        print("Initializing browser...")
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=False)
            page = await browser.new_page()
            
            # Ask for the URL
            print("Enter the URL of the login page: ", end='', flush=True)
            url = input().strip()
            
            if not url.startswith("http"):
                url = "https://" + url
                
            print(f"Navigating to: {url}")
            await page.goto(url)
            
            # Ask for email and password
            print("Enter email: ", end='', flush=True)
            email = input().strip()
            
            print("Enter password: ", end='', flush=True)
            password = input().strip()
            
            # Attempt to login
            print("\nAttempting to log in...")
            success = await login_with_credentials(page, email, password)
            
            if success:
                print("Login successful!")
            else:
                print("Login failed. Trying individual steps...")
                
                # Try filling email field
                print("Filling email field...")
                email_filled = await fill_email_field(page, email)
                
                if email_filled:
                    print("Email field filled successfully")
                else:
                    print("Failed to fill email field")
                
                # Try filling password field
                print("Filling password field...")
                password_filled = await fill_password_field(page, password)
                
                if password_filled:
                    print("Password field filled successfully")
                else:
                    print("Failed to fill password field")
                
                # Try clicking login button
                print("Clicking login button...")
                button_clicked = await click_login_button(page)
                
                if button_clicked:
                    print("Login button clicked successfully")
                else:
                    print("Failed to click login button")
            
            # Wait for user to press Enter before closing
            print("\nPress Enter to close the browser...", end='', flush=True)
            input()
            
            await browser.close()
            
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
