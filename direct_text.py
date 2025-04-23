"""
Direct text input version of WebAssist
"""

import os
import asyncio
import pyttsx3
import google.generativeai as genai
import re
import json
from playwright.async_api import async_playwright

# Configuration
DEFAULT_API_KEY = "AIzaSyAvNz1x-OZl3kUDEm4-ZhwzJJy1Tqq6Flg"
DEFAULT_START_URL = "https://www.google.com"
EXIT_COMMANDS = ["exit", "quit"]
HELP_COMMAND = "help"

# Global variables
browser = None
page = None
context = None
playwright = None
engine = None
model = None


def speak(text):
    """Speak text"""
    print(f"ASSISTANT: {text}")
    engine.say(text)
    engine.runAndWait()


async def navigate(url):
    """Navigate to URL"""
    try:
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"

        await page.goto(url, wait_until="networkidle", timeout=20000)
        speak(f"Loaded: {await page.title()}")
        return True
    except Exception as e:
        speak(f"Navigation failed: {str(e)}")
        return False


async def get_page_context():
    """Get current page context"""
    try:
        await page.wait_for_timeout(1000)

        input_fields = []
        inputs = page.locator("input:visible, textarea:visible, select:visible")
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
            except:
                pass

        buttons = []
        try:
            button_elements = page.locator(
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
                except:
                    pass
        except:
            pass

        body_locator = page.locator("body")
        inner_text = await body_locator.inner_text()
        inner_html = await body_locator.inner_html()

        return {
            "title": await page.title(),
            "url": page.url,
            "text": inner_text[:1000],
            "html": inner_html[:4000],
            "input_fields": input_fields,
            "buttons": buttons
        }
    except Exception as e:
        print(f"Context error: {e}")
        return {}


def format_input_fields(input_fields):
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


def format_buttons(buttons):
    """Format buttons for LLM prompt"""
    result = ""
    for idx, button in enumerate(buttons):
        result += f"{idx + 1}. {button.get('text', '')} - "
        result += f"id: {button.get('id', '')}, "
        result += f"class: {button.get('class', '')}, "
        result += f"type: {button.get('type', '')}\n"
    return result


def parse_llm_response(raw_response):
    """Parse the response from the LLM"""
    try:
        import json
        import re

        json_str = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if not json_str:
            raise ValueError("No JSON found in response")

        json_str = json_str.group(0)
        return json.loads(json_str)
    except Exception as e:
        print(f"Parse error: {e}")
        return {"error": str(e)}


async def get_llm_selectors(task, context):
    """Use LLM to generate selectors for a task based on page context"""
    prompt = f"""
    Based on the current web page context, generate the 5 most likely CSS selectors to {task}.
    Focus on precise selectors that would uniquely identify the element.

    Current Page:
    Title: {context.get('title', 'N/A')}
    URL: {context.get('url', 'N/A')}

    Input Fields Found:
    {format_input_fields(context.get('input_fields', []))}

    Buttons Found:
    {format_buttons(context.get('buttons', []))}

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
        response = model.generate_content(prompt)
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


async def retry_click(selector, purpose):
    """Retry clicking an element"""
    tries = 3
    for attempt in range(tries):
        try:
            await page.locator(selector).first.click(timeout=5000)
            speak(f"👆 Clicked {purpose}")
            return True
        except Exception as e:
            if attempt == tries - 1:
                raise e
            await page.wait_for_timeout(1000)
    return False


async def retry_type(selector, text, purpose):
    """Retry typing text into an element"""
    tries = 3
    for attempt in range(tries):
        try:
            await page.locator(selector).first.fill(text)
            speak(f"⌨️ Entered {purpose}")
            return True
        except Exception as e:
            if attempt == tries - 1:
                raise e
            await page.wait_for_timeout(1000)
    return False


async def process_command(command):
    """Process a command"""
    # Print the command for debugging
    print(f"DEBUG: Processing command: '{command}'")

    if command.lower() in EXIT_COMMANDS:
        speak("Goodbye!")
        return False

    if command.lower() == HELP_COMMAND:
        show_help()
        return True

    if command.lower().startswith(("go to ", "navigate to ", "open ")):
        # Extract URL
        parts = command.split(" ", 2)
        if len(parts) >= 3:
            url = parts[2]
            await navigate(url)
            return True

    # Handle "enter email" command - try multiple patterns
    enter_patterns = [
        r'enter (?:email|email address)\s+(\S+)\s+and (?:password|pass)\s+(\S+)',  # Standard pattern
        r'(?:enter|input|type)\s+(?:email|email address)?\s*(\S+)\s+(?:and|with)\s+(?:password|pass)?\s*(\S+)',  # More flexible
        r'(?:fill|fill in)\s+(?:with)?\s*(?:email|username)?\s*(\S+)\s+(?:and|with)\s*(?:password|pass)?\s*(\S+)'  # Very flexible
    ]

    enter_email_match = None
    matched_pattern = None

    for pattern in enter_patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            enter_email_match = match
            matched_pattern = pattern
            break

    print(f"DEBUG: Enter patterns tried, Match: {enter_email_match is not None}, Pattern: {matched_pattern}")

    if enter_email_match:
        try:
            email, password = enter_email_match.groups()
            speak(f"Attempting to enter email and password...")

            # Get page context
            context = await get_page_context()

            # Use LLM to find email field
            email_selectors = await get_llm_selectors("find email or username input field", context)
            email_found = False
            for selector in email_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        await retry_type(selector, email, "email address")
                        email_found = True
                        break
                except Exception as e:
                    print(f"Error with email selector {selector}: {e}")
                    continue

            # Use LLM to find password field
            password_selectors = await get_llm_selectors("find password input field", context)
            password_found = False
            for selector in password_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        await retry_type(selector, password, "password")
                        password_found = True
                        break
                except Exception as e:
                    print(f"Error with password selector {selector}: {e}")
                    continue

            if email_found and password_found:
                speak("Email and password entered successfully.")
            else:
                if not email_found:
                    speak("Could not find email field")
                if not password_found:
                    speak("Could not find password field")

            return True
        except Exception as e:
            speak(f"Failed to enter email and password: {str(e)}")
            return True

    # Handle login command - try multiple patterns with typo tolerance
    login_patterns = [
        # Standard patterns
        r'login with (?:email|email address)\s+(\S+)\s+and (?:password|pass)\s+(\S+)',
        # Typo-tolerant patterns
        r'log[a-z]* w[a-z]* (?:email|email address)?\s+(\S+)\s+[a-z]* (?:password|pass|p[a-z]*)\s+(\S+)',
        # Very flexible patterns
        r'login\s+(?:with|using|w[a-z]*)\s+(?:email|email address)?\s*(\S+)\s+(?:and|with|[a-z]*)\s+(?:password|pass|p[a-z]*)\s*(\S+)',
        r'(?:login|sign in|signin)\s+(?:with|using|w[a-z]*)?\s*(?:email|username)?\s*(\S+)\s+(?:and|with|[a-z]*)\s*(?:password|pass|p[a-z]*)?\s*(\S+)',
        # Catch-all pattern for login commands
        r'log[a-z]*.*?(\S+@\S+).*?(\S+)'  # This will match any login-like command with an email and another word
    ]

    login_match = None
    matched_pattern = None

    for pattern in login_patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            login_match = match
            matched_pattern = pattern
            break

    print(f"DEBUG: Login patterns tried, Match: {login_match is not None}, Pattern: {matched_pattern}")

    if login_match:
        try:
            email, password = login_match.groups()
            speak("Logging in...")

            # Get page context
            context = await get_page_context()

            # Use LLM to find email field
            email_selectors = await get_llm_selectors("find email or username input field", context)
            email_found = False
            for selector in email_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        await retry_type(selector, email, "email address")
                        email_found = True
                        break
                except Exception as e:
                    print(f"Error with email selector {selector}: {e}")
                    continue

            # Use LLM to find password field
            password_selectors = await get_llm_selectors("find password input field", context)
            password_found = False
            for selector in password_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        await retry_type(selector, password, "password")
                        password_found = True
                        break
                except Exception as e:
                    print(f"Error with password selector {selector}: {e}")
                    continue

            # If both fields were found, click login button
            if email_found and password_found:
                login_button_selectors = await get_llm_selectors("find login or sign in button", context)
                for selector in login_button_selectors:
                    try:
                        if await page.locator(selector).count() > 0:
                            await retry_click(selector, "login button")
                            return True
                    except Exception as e:
                        print(f"Error with button selector {selector}: {e}")
                        continue

                speak("Filled login details but couldn't find login button")
                return True
            else:
                speak("Could not find all required login fields")
                return False
        except Exception as e:
            speak(f"Login failed: {str(e)}")
            return True

    # For other commands, use LLM to generate a response
    try:
        # Use synchronous version for simplicity
        response = model.generate_content(f"User command: {command}. Respond briefly.")
        speak(response.text)
    except Exception as e:
        speak(f"Error processing command: {str(e)}")

    return True


def show_help():
    """Show help information"""
    help_text = """
    🔍 Voice Web Assistant Help:

    Basic Navigation:
    - "Go to [website]" - Navigate to a website
    - "Navigate to [section]" - Go to a specific section on the current site
    - "Open [website]" - Open a website

    General:
    - "Help" - Show this help message
    - "Exit" or "Quit" - Close the assistant
    """
    print(help_text)
    speak("Here's the help information. You can see the full list on screen.")


async def main():
    """Main entry point"""
    global browser, page, context, playwright, engine, model

    try:
        print("Initializing components...")

        # Initialize text-to-speech
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.9)

        # Initialize LLM
        api_key = os.environ.get("GEMINI_API_KEY", DEFAULT_API_KEY)
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Initialize browser
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()

        # Navigate to start URL
        await page.goto(DEFAULT_START_URL)
        print(f"Loaded: {await page.title()}")

        speak("Web Assistant ready. Say 'help' for available commands.")

        print("\nWelcome to WebAssist!")
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
                if not await process_command(command):
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
        # Close browser
        if context:
            await context.close()
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()
        print("Browser closed")


if __name__ == "__main__":
    asyncio.run(main())
