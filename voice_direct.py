"""
Direct implementation of Voice.py with text input
"""

import os
import re
import json
import asyncio
import pyttsx3
import google.generativeai as genai
from playwright.async_api import async_playwright

# Configuration
DEFAULT_API_KEY = "AIzaSyAvNz1x-OZl3kUDEm4-ZhwzJJy1Tqq6Flg"
DEFAULT_START_URL = "https://www.google.com"
EXIT_COMMANDS = ["exit", "quit"]
HELP_COMMAND = "help"

class VoiceAssistant:
    def __init__(self):
        self.engine = None
        self.llm = None
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def initialize(self):
        """Initialize components"""
        # Initialize text-to-speech
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 0.9)

        # Initialize LLM
        api_key = os.environ.get("GEMINI_API_KEY", DEFAULT_API_KEY)
        genai.configure(api_key=api_key)
        self.llm = genai.GenerativeModel('gemini-1.5-flash')

        # Initialize browser
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 800}
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
                # If it's just a path like "/#/signin", it's not a valid URL
                if url.startswith('/') and not any(c.isalpha() for c in url.split('/')[1] if len(url.split('/')) > 1):
                    self.speak(f"Invalid URL: {url}. Please provide a valid domain.")
                    return False

                # Add https:// prefix
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
        login_match = re.search(r'login with email\s+(\S+)\s+and password\s+(\S+)', command, re.IGNORECASE)
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
            self.speak("Logging in...")

            # First get the current page context
            context = await self._get_page_context()

            # First try to use LLM to generate selectors
            print("Using LLM to generate selectors for login form...")
            email_selectors = await self._get_llm_selectors("find email or username input field", context)
            password_selectors = await self._get_llm_selectors("find password input field", context)

            # Define fallback selectors to use only if LLM fails
            fallback_email_selectors = [
                '#floating_outlined3',
                'input[type="email"]',
                'input[name="email"]',
                'input[id*="email"]',
                'input[placeholder*="email"]',
                'input[type="text"][name*="user"]',
                'input[id*="user"]'
            ]

            fallback_password_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                'input[id*="password"]',
                'input[placeholder*="password"]',
                'input.password',
                '#password',
                '[aria-label*="password"]',
                '[data-testid*="password"]'
            ]

            # First try with just LLM selectors
            all_email_selectors = email_selectors.copy() if email_selectors else []
            all_password_selectors = password_selectors.copy() if password_selectors else []

            # Check if login form fields are visible using LLM selectors first
            email_field_visible = False
            for selector in all_email_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        email_field_visible = True
                        print(f"Found email field with LLM selector: {selector}")
                        break
                except Exception as e:
                    continue

            # If email field not found with LLM selectors, try fallback selectors just for visibility check
            if not email_field_visible:
                for selector in fallback_email_selectors:
                    try:
                        if await self.page.locator(selector).count() > 0:
                            email_field_visible = True
                            print(f"Found email field with fallback selector: {selector}")
                            break
                    except Exception as e:
                        continue

            password_field_visible = False
            for selector in all_password_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        password_field_visible = True
                        print(f"Found password field with LLM selector: {selector}")
                        break
                except Exception as e:
                    continue

            # If password field not found with LLM selectors, try fallback selectors just for visibility check
            if not password_field_visible:
                for selector in fallback_password_selectors:
                    try:
                        if await self.page.locator(selector).count() > 0:
                            password_field_visible = True
                            print(f"Found password field with fallback selector: {selector}")
                            break
                    except Exception as e:
                        continue

            # If login form is not visible, try to find and click a login button
            if not (email_field_visible and password_field_visible):
                self.speak("Login form not visible. Looking for login button...")
                # First try to use LLM to find login button
                print("Using LLM to find login button...")
                login_button_selectors = await self._get_llm_selectors("find login or sign in link or button", context)

                # Define fallback selectors
                fallback_login_button_selectors = [
                    'a:has-text("Login")',
                    'a:has-text("Sign in")',
                    'button:has-text("Login")',
                    'button:has-text("Sign in")',
                    '.login-button',
                    '.signin-button',
                    '[data-testid="login-button"]',
                    '[aria-label="Login"]',
                    '[aria-label="Sign in"]'
                ]

                # First try with just LLM selectors
                all_login_button_selectors = login_button_selectors.copy() if login_button_selectors else []

                # Try to click login button using LLM selectors first
                login_button_clicked = False
                for selector in all_login_button_selectors:
                    try:
                        if await self.page.locator(selector).count() > 0:
                            self.speak(f"Found login button with LLM selector. Clicking to reveal form...")
                            await self.page.locator(selector).click()
                            login_button_clicked = True
                            # Wait for form to appear with specific selectors for the form shown in the HTML
                            self.speak("Waiting for login form to appear...")
                            try:
                                # Wait for specific elements from the provided HTML
                                await self.page.wait_for_selector('.signup-card-container, #floating_outlined3, #floating_outlined15, #signInButton',
                                                               timeout=5000)
                                self.speak("Login form is now visible")
                            except Exception as e:
                                print(f"Error waiting for login form: {e}")
                                # Fallback to a simple timeout
                                await self.page.wait_for_timeout(3000)
                            break
                    except Exception as e:
                        print(f"Error clicking login button {selector}: {e}")
                        continue

                # If LLM selectors didn't work, try fallback selectors
                if not login_button_clicked and fallback_login_button_selectors:
                    print("LLM login button selectors didn't work, trying fallback selectors...")
                    for selector in fallback_login_button_selectors:
                        try:
                            if await self.page.locator(selector).count() > 0:
                                self.speak(f"Found login button with fallback selector. Clicking to reveal form...")
                                await self.page.locator(selector).click()
                                login_button_clicked = True
                                # Wait for form to appear with specific selectors for the form shown in the HTML
                                self.speak("Waiting for login form to appear...")
                                try:
                                    # Wait for specific elements from the provided HTML
                                    await self.page.wait_for_selector('.signup-card-container, #floating_outlined3, #floating_outlined15, #signInButton',
                                                                   timeout=5000)
                                    self.speak("Login form is now visible")
                                except Exception as e:
                                    print(f"Error waiting for login form: {e}")
                                    # Fallback to a simple timeout
                                    await self.page.wait_for_timeout(3000)
                                break
                        except Exception as e:
                            print(f"Error clicking fallback login button {selector}: {e}")
                            continue

                if login_button_clicked:
                    # Get updated context after clicking login button
                    context = await self._get_page_context()
                    # Update selectors with new context
                    email_selectors = await self._get_llm_selectors("find email or username input field", context)
                    all_email_selectors = email_selectors + fallback_email_selectors
                    password_selectors = await self._get_llm_selectors("find password input field", context)
                    all_password_selectors = password_selectors + fallback_password_selectors
                else:
                    self.speak("Could not find login button")

            # Now try to fill the form using LLM selectors first
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
                for selector in fallback_email_selectors:
                    try:
                        if await self.page.locator(selector).count() > 0:
                            await self._retry_type(selector, email, "email address")
                            email_found = True
                            break
                    except Exception as e:
                        print(f"Error with fallback email selector {selector}: {e}")
                        continue

            # Try LLM password selectors
            print(f"DEBUG: Trying LLM password selectors: {all_password_selectors}")
            password_found = False
            for selector in all_password_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_type(selector, password, "password")
                        password_found = True
                        break
                except Exception as e:
                    print(f"Error with password selector {selector}: {e}")
                    continue

            # If LLM selectors didn't work for password, try fallback selectors
            if not password_found and fallback_password_selectors:
                print("LLM password selectors didn't work, trying fallback selectors...")
                for selector in fallback_password_selectors:
                    try:
                        if await self.page.locator(selector).count() > 0:
                            await self._retry_type(selector, password, "password")
                            password_found = True
                            break
                    except Exception as e:
                        print(f"Error with fallback password selector {selector}: {e}")
                        continue

            # If both fields were filled, click login/submit button
            if email_found and password_found:
                # First try to use LLM to find submit button
                print("Using LLM to find submit button...")
                submit_button_selectors = await self._get_llm_selectors("find login or submit button", context)

                # Define fallback selectors
                fallback_submit_selectors = [
                    '#signInButton',  # Specific ID from the provided HTML
                    'button[id="signInButton"]',
                    'button:has-text("Sign In")',
                    '.signup-btn',  # Class from the provided HTML
                    '.vstate-button',  # Class from the provided HTML
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button:has-text("Login")',
                    'button:has-text("Sign in")',
                    'button:has-text("Submit")',
                    '.login-button',
                    '.submit-button',
                    '[data-testid="login-button"]',
                    '[data-testid="submit-button"]'
                ]

                # First try with just LLM selectors
                all_submit_selectors = submit_button_selectors.copy() if submit_button_selectors else []

                # Try to click submit button using LLM selectors first
                button_clicked = False
                for selector in all_submit_selectors:
                    try:
                        if await self.page.locator(selector).count() > 0:
                            self.speak(f"Found submit button with LLM selector. Clicking to submit form...")
                            await self._retry_click(selector, "login/submit button")
                            button_clicked = True
                            return True
                    except Exception as e:
                        print(f"Error with button selector {selector}: {e}")
                        continue

                # If LLM selectors didn't work, try fallback selectors
                if not button_clicked and fallback_submit_selectors:
                    print("LLM submit button selectors didn't work, trying fallback selectors...")
                    for selector in fallback_submit_selectors:
                        try:
                            if await self.page.locator(selector).count() > 0:
                                self.speak(f"Found submit button with fallback selector. Clicking to submit form...")
                                await self._retry_click(selector, "login/submit button")
                                button_clicked = True
                                return True
                        except Exception as e:
                            print(f"Error with fallback button selector {selector}: {e}")
                            continue

                if not button_clicked:
                    self.speak("Filled login details but couldn't find login button")
                return True
            else:
                self.speak("Could not find all required login fields")
                return False

        search_match = re.search(r'search(?:\s+for)?\s+(.+)', command, re.IGNORECASE)
        if search_match:
            query = search_match.group(1)

            context = await self._get_page_context()
            search_selectors = await self._get_llm_selectors("find search input field", context)

            for selector in search_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_type(selector, query, "search query")
                        await self.page.locator(selector).press("Enter")
                        self.speak(f"🔍 Searching for '{query}'")
                        await self.page.wait_for_timeout(3000)
                        return True
                except Exception as e:
                    print(f"Error with search selector {selector}: {e}")
                    continue

            self.speak("Could not find search field")
            return False

        # Handle "enter email" command
        # First check for email and password pattern
        enter_email_match = re.search(r'enter (?:email|email address)\s+(\S+)\s+and (?:password|pass)\s+(\S+)', command, re.IGNORECASE)
        if not enter_email_match:
            # Try more flexible patterns for email and password
            enter_patterns = [
                r'(?:enter|input|type)\s+(?:email|email address)?\s*(\S+)\s+(?:and|with)\s+(?:password|pass|p[a-z]*)?\s*(\S+)',
                r'(?:fill|fill in)\s+(?:with)?\s*(?:email|username)?\s*(\S+)\s+(?:and|with)\s*(?:password|pass|p[a-z]*)?\s*(\S+)'
            ]

            for pattern in enter_patterns:
                enter_email_match = re.search(pattern, command, re.IGNORECASE)
                if enter_email_match:
                    break

        # If no match for email+password, check for just email
        email_only_match = None
        if not enter_email_match:
            email_only_patterns = [
                r'enter (?:email|email address)\s+(\S+@\S+)',
                r'(?:enter|input|type|fill)\s+(?:ema[a-z]+|email address)?\s*(\S+@\S+)',  # Handle typos like 'emaol'
                r'(?:email|ema[a-z]+|email address)\s+(\S+@\S+)',  # Handle typos like 'emaol'
                r'(?:enter|input|type|fill)\s+(?:email|ema[a-z]+)\s+(\S+)',  # Catch any word after email command
                r'(?:email|ema[a-z]+)\s+(\S+)'  # Catch any word after email
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
            self.speak(f"Entering email address: {email}")

            # Get the current page context
            context = await self._get_page_context()

            # First try to use LLM to generate selectors
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

                # First, let's check which selectors actually match elements
                matching_selectors = []
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

            if email_found:
                self.speak("Email entered successfully")
                return True
            else:
                self.speak("Could not find email field")
                return False

        elif enter_email_match:
            email, password = enter_email_match.groups()
            self.speak("Entering credentials...")

            # First get the current page context
            context = await self._get_page_context()

            # First try to use LLM to generate selectors
            print("Using LLM to generate selectors for login form...")
            email_selectors = await self._get_llm_selectors("find email or username input field", context)
            password_selectors = await self._get_llm_selectors("find password input field", context)

            # Define fallback selectors to use only if LLM fails
            # Include specific selectors from the HTML provided
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

            fallback_password_selectors = [
                '#floating_outlined15',  # Specific ID from the provided HTML
                'input[id="floating_outlined15"]',
                'label:has-text("Password") + input',
                'label:has-text("Password") ~ input',
                'input[type="password"]',
                'input[name="password"]',
                'input[id*="password"]',
                'input[placeholder*="password"]',
                'input.password',
                '#password',
                '[aria-label*="password"]',
                '[data-testid*="password"]',
                # Add more generic selectors
                'input[autocomplete="current-password"]',
                'input[autocomplete="new-password"]',
                'form input[type="password"]',
                'form input:nth-child(2)'  # Often the second input in a form is the password
            ]

            # First try with just LLM selectors
            all_email_selectors = email_selectors.copy() if email_selectors else []
            all_password_selectors = password_selectors.copy() if password_selectors else []

            # Check if login form fields are visible using LLM selectors first
            email_field_visible = False
            for selector in all_email_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        email_field_visible = True
                        print(f"Found email field with LLM selector: {selector}")
                        break
                except Exception as e:
                    continue

            # If email field not found with LLM selectors, try fallback selectors just for visibility check
            if not email_field_visible:
                for selector in fallback_email_selectors:
                    try:
                        if await self.page.locator(selector).count() > 0:
                            email_field_visible = True
                            print(f"Found email field with fallback selector: {selector}")
                            break
                    except Exception as e:
                        continue

            password_field_visible = False
            for selector in all_password_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        password_field_visible = True
                        print(f"Found password field with LLM selector: {selector}")
                        break
                except Exception as e:
                    continue

            # If password field not found with LLM selectors, try fallback selectors just for visibility check
            if not password_field_visible:
                for selector in fallback_password_selectors:
                    try:
                        if await self.page.locator(selector).count() > 0:
                            password_field_visible = True
                            print(f"Found password field with fallback selector: {selector}")
                            break
                    except Exception as e:
                        continue

            # If login form is not visible, try to find and click a login button
            if not (email_field_visible and password_field_visible):
                self.speak("Login form not visible. Looking for login button...")
                # First try to use LLM to find login button
                print("Using LLM to find login button...")
                login_button_selectors = await self._get_llm_selectors("find login or sign in link or button", context)

                # Define fallback selectors
                fallback_login_button_selectors = [
                    'a:has-text("Login")',
                    'a:has-text("Sign in")',
                    'button:has-text("Login")',
                    'button:has-text("Sign in")',
                    '.login-button',
                    '.signin-button',
                    '[data-testid="login-button"]',
                    '[aria-label="Login"]',
                    '[aria-label="Sign in"]'
                ]

                # First try with just LLM selectors
                all_login_button_selectors = login_button_selectors.copy() if login_button_selectors else []

                # Try to click login button using LLM selectors first
                login_button_clicked = False
                for selector in all_login_button_selectors:
                    try:
                        if await self.page.locator(selector).count() > 0:
                            self.speak(f"Found login button with LLM selector. Clicking to reveal form...")
                            await self.page.locator(selector).click()
                            login_button_clicked = True
                            # Wait for form to appear
                            await self.page.wait_for_timeout(2000)
                            break
                    except Exception as e:
                        print(f"Error clicking login button {selector}: {e}")
                        continue

                # If LLM selectors didn't work, try fallback selectors
                if not login_button_clicked and fallback_login_button_selectors:
                    print("LLM login button selectors didn't work, trying fallback selectors...")
                    for selector in fallback_login_button_selectors:
                        try:
                            if await self.page.locator(selector).count() > 0:
                                self.speak(f"Found login button with fallback selector. Clicking to reveal form...")
                                await self.page.locator(selector).click()
                                login_button_clicked = True
                                # Wait for form to appear
                                await self.page.wait_for_timeout(2000)
                                break
                        except Exception as e:
                            print(f"Error clicking fallback login button {selector}: {e}")
                            continue

                if login_button_clicked:
                    # Get updated context after clicking login button
                    context = await self._get_page_context()
                    # Update selectors with new context
                    email_selectors = await self._get_llm_selectors("find email or username input field", context)
                    all_email_selectors = email_selectors.copy() if email_selectors else []
                    password_selectors = await self._get_llm_selectors("find password input field", context)
                    all_password_selectors = password_selectors.copy() if password_selectors else []
                else:
                    self.speak("Could not find login button")

            # Now try to fill the form using LLM selectors first
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

                # First, let's check which selectors actually match elements
                matching_selectors = []
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

            # Try LLM password selectors
            print(f"DEBUG: Trying LLM password selectors: {all_password_selectors}")
            password_found = False
            for selector in all_password_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_type(selector, password, "password")
                        password_found = True
                        break
                except Exception as e:
                    print(f"Error with password selector {selector}: {e}")
                    continue

            # If LLM selectors didn't work for password, try fallback selectors
            if not password_found and fallback_password_selectors:
                print("LLM password selectors didn't work, trying fallback selectors...")
                print(f"DEBUG: Fallback password selectors: {fallback_password_selectors}")

                # First, let's check which selectors actually match elements
                matching_selectors = []
                for selector in fallback_password_selectors:
                    try:
                        count = await self.page.locator(selector).count()
                        if count > 0:
                            matching_selectors.append(f"{selector} (matches {count} elements)")
                    except Exception as e:
                        print(f"Error checking fallback password selector {selector}: {e}")

                if matching_selectors:
                    print(f"DEBUG: Found matching password selectors: {matching_selectors}")
                else:
                    print("DEBUG: No matching password selectors found on the page")

                # Now try to use the selectors to fill the password field
                for selector in fallback_password_selectors:
                    try:
                        count = await self.page.locator(selector).count()
                        if count > 0:
                            print(f"DEBUG: Trying to fill password using selector: {selector}")
                            await self._retry_type(selector, password, "password")
                            password_found = True
                            print(f"DEBUG: Successfully filled password using selector: {selector}")
                            break
                    except Exception as e:
                        print(f"Error with fallback password selector {selector}: {e}")
                        continue

            if email_found and password_found:
                self.speak("Email and password entered successfully")
                return True
            else:
                if not email_found:
                    self.speak("Could not find email field")
                if not password_found:
                    self.speak("Could not find password field")
                return False

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

    async def _get_llm_selectors(self, task, context):
        """Use LLM to generate selectors for a task based on page context"""
        prompt = f"""
        Based on the current web page context, generate the 5 most likely CSS selectors to {task}.
        Focus on precise selectors that would uniquely identify the element.

        Current Page:
        Title: {context.get('title', 'N/A')}
        URL: {context.get('url', 'N/A')}

        Input Fields Found:
        {self._format_input_fields(context.get('input_fields', []))}

        Menu Items Found:
        {self._format_menu_items(context.get('menu_items', []))}

        Buttons Found:
        {self._format_buttons(context.get('buttons', []))}

        Relevant HTML:
        {context.get('html', '')[:1000]}

        IMPORTANT RULES:
        1. DO NOT use the :contains() pseudo-class as it's not a standard CSS selector
        2. For text matching, use :text() or :has-text() which are Playwright-specific
        3. Use button:has-text("Login") instead of button:contains("Login")
        4. Avoid complex selectors with multiple conditions when possible
        5. If this appears to be a PrimeNG component (classes containing p-dropdown, p-component, etc.),
           prioritize selectors that target PrimeNG specific elements:
           - Dropdown: .p-dropdown, .p-dropdown-trigger
           - Panel: .p-dropdown-panel
           - Items: .p-dropdown-item, .p-dropdown-items li
           - Filter: .p-dropdown-filter

        Respond ONLY with a JSON array of selector strings. Example:
        ["selector1", "selector2", "selector3", "selector4", "selector5"]
        """

        try:
            response = self.llm.generate_content(prompt)
            print(f"🔍 Selector generation response:\n", response.text)
            selectors_match = re.search(r'\[.*\]', response.text, re.DOTALL)
            if selectors_match:
                selectors_json = selectors_match.group(0)
                selectors = json.loads(selectors_json)

                # Sanitize selectors
                sanitized_selectors = []
                for selector in selectors:
                    # Replace :contains() with :has-text() for Playwright
                    if ":contains(" in selector:
                        selector = selector.replace(":contains(", ":has-text(")
                    sanitized_selectors.append(selector)

                # Add some fallback selectors for login-related elements
                if "login" in task.lower() or "sign in" in task.lower():
                    if "button" in task.lower():
                        sanitized_selectors.extend([
                            'button[type="submit"]',
                            'input[type="submit"]',
                            'button:has-text("Login")',
                            'button:has-text("Sign in")',
                            'a:has-text("Login")',
                            'a:has-text("Sign in")',
                            '.login-button',
                            '.signin-button',
                            '[data-testid="login-button"]'
                        ])
                    elif "email" in task.lower() or "username" in task.lower():
                        sanitized_selectors.extend([
                            'input[type="email"]',
                            'input[name="email"]',
                            'input[id*="email"]',
                            'input[placeholder*="email"]',
                            'input[type="text"][name*="user"]',
                            'input[id*="user"]'
                        ])
                    elif "password" in task.lower():
                        sanitized_selectors.extend([
                            'input[type="password"]',
                            'input[name="password"]',
                            'input[id*="password"]'
                        ])

                # Remove duplicates while preserving order
                unique_selectors = []
                for selector in sanitized_selectors:
                    if selector not in unique_selectors:
                        unique_selectors.append(selector)

                return unique_selectors[:10]  # Return up to 10 selectors
            else:
                return []
        except Exception as e:
            print(f"Selector generation error: {e}")
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

            return {
                "title": await self.page.title(),
                "url": self.page.url,
                "text": inner_text[:1000],
                "html": self._filter_html(inner_html[:4000]),
                "input_fields": input_fields,
                "menu_items": menu_items,
                "buttons": buttons
            }
        except Exception as e:
            print(f"Context error: {e}")
            return {}

    def _filter_html(self, html):
        """Filter HTML to focus on important elements"""
        return re.sub(
            r'<(input|button|a|form|select|textarea|div|ul|li)[^>]*>',
            lambda m: m.group(0) + '\n',
            html
        )[:3000]

    async def _get_actions(self, command):
        """Get actions for a command using LLM"""
        context = await self._get_page_context()
        prompt = self._create_prompt(command, context)

        try:
            response = self.llm.generate_content(prompt)
            print("🔍 Raw LLM response:\n", response.text)
            return self._parse_response(response.text)
        except Exception as e:
            print(f"LLM Error: {e}")
            return {"error": str(e)}

    def _create_prompt(self, command, context):
        """Create prompt for LLM"""
        input_fields_info = ""
        if "input_fields" in context and context["input_fields"]:
            input_fields_info = "Input Fields Found:\n"
            for idx, field in enumerate(context["input_fields"]):
                input_fields_info += f"{idx + 1}. {field.get('tag', 'input')} - type: {field.get('type', '')}, id: {field.get('id', '')}, name: {field.get('name', '')}, placeholder: {field.get('placeholder', '')}, aria-label: {field.get('aria-label', '')}\n"

        menu_items_info = ""
        if "menu_items" in context and context["menu_items"]:
            menu_items_info = "Menu Items Found:\n"
            for idx, item in enumerate(context["menu_items"]):
                submenu_indicator = " (has submenu)" if item.get("has_submenu") else ""
                menu_items_info += f"{idx + 1}. {item.get('text', '')}{submenu_indicator}\n"

        buttons_info = ""
        if "buttons" in context and context["buttons"]:
            buttons_info = "Buttons Found:\n"
            for idx, button in enumerate(context["buttons"]):
                buttons_info += f"{idx + 1}. {button.get('text', '')} - id: {button.get('id', '')}, class: {button.get('class', '')}, type: {button.get('type', '')}\n"

        return f"""Analyze the web page and generate precise Playwright selectors to complete: "{command}".

Selector Priority:
1. ID (input#email, input#password)
2. Type and Name (input[type='email'], input[name='email'])
3. ARIA labels ([aria-label='Search'])
4. Data-testid ([data-testid='login-btn'])
5. Button text (button:has-text('Sign In'))
6. Semantic CSS classes (.login-button, .p-menuitem)
7. Input placeholder (input[placeholder='Email'])

For tiered menus:
- Parent menus: .p-menuitem, [role='menuitem']
- Submenu items: .p-submenu-list .p-menuitem, ul[role='menu'] [role='menuitem']
- For dropdown/select interactions: Use 'select_option' action when appropriate

Current Page:
Title: {context.get('title', 'N/A')}
URL: {context.get('url', 'N/A')}
Visible Text: {context.get('text', '')[:500]}

{input_fields_info}
{menu_items_info}
{buttons_info}

Relevant HTML:
{context.get('html', '')}

Respond ONLY with JSON in this format:
{{
  "actions": [
    {{
      "action": "click|type|navigate|hover|select_option|check|uncheck|toggle",
      "selector": "CSS selector",
      "text": "(only for type)",
      "purpose": "description",
      "url": "(only for navigate actions)",
      "option": "(only for select_option)",
      "fallback_selectors": ["alternate selector 1", "alternate selector 2"]
    }}
  ]
}}"""

    def _parse_response(self, raw_response):
        """Parse LLM response"""
        try:
            json_str = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if not json_str:
                raise ValueError("No JSON found in response")

            json_str = json_str.group(0)
            return json.loads(json_str)
        except Exception as e:
            print(f"Parse error: {e}")
            return {"error": str(e)}

    async def _execute_actions(self, action_data):
        """Execute actions"""
        if 'error' in action_data:
            self.speak("⚠️ Action could not be completed. Switching to fallback...")
            return False

        for action in action_data.get('actions', []):
            try:
                await self._perform_action(action)
                await self.page.wait_for_timeout(1000)
            except Exception as e:
                self.speak(f"❌ Failed to {action.get('purpose', 'complete action')}")
                print(f"Action Error: {str(e)}")
                return False
        return True

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

    async def _try_selectors_for_click(self, selectors, purpose):
        """Try multiple selectors for clicking"""
        for selector in selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    await self._retry_click(selector, purpose)
                    return True
            except Exception as e:
                print(f"Error with click selector {selector}: {e}")
                continue

        self.speak(f"Could not find element to {purpose}")
        return False

    async def _try_selectors_for_type(self, selectors, text, purpose):
        """Try multiple selectors for typing"""
        for selector in selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    await self._retry_type(selector, text, purpose)
                    return True
            except Exception as e:
                print(f"Error with type selector {selector}: {e}")
                continue

        self.speak(f"Could not find element to {purpose}")
        return False

    async def _try_selectors_for_hover(self, selectors, purpose):
        """Try multiple selectors for hovering"""
        for selector in selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    await self.page.locator(selector).hover()
                    self.speak(f"Hovering over {purpose}")
                    return True
            except Exception as e:
                print(f"Error with hover selector {selector}: {e}")
                continue

        self.speak(f"Could not find element to hover over for {purpose}")
        return False

    async def _retry_click(self, selector, purpose):
        """Retry clicking an element"""
        tries = 3
        for attempt in range(tries):
            try:
                await self.page.locator(selector).first.click(timeout=5000)
                self.speak(f"👆 Clicked {purpose}")
                return True
            except Exception as e:
                if attempt == tries - 1:
                    raise e
                await self.page.wait_for_timeout(1000)
        return False

    async def _retry_type(self, selector, text, purpose):
        """Retry typing text into an element"""
        tries = 3
        for attempt in range(tries):
            try:
                await self.page.locator(selector).first.fill(text)
                self.speak(f"⌨️ Entered {purpose}")
                return True
            except Exception as e:
                if attempt == tries - 1:
                    raise e
                await self.page.wait_for_timeout(1000)
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

        General:
        - "Help" - Show this help message
        - "Exit" or "Quit" - Close the assistant
        """
        print(help_text)
        self.speak("Here's the help information. You can see the full list on screen.")


async def main():
    """Main entry point"""
    try:
        print("Initializing Voice Assistant...")
        assistant = VoiceAssistant()
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
        # Note: We're intentionally NOT closing the browser here
        # to keep it open for inspection even if there's an error


if __name__ == "__main__":
    asyncio.run(main())
