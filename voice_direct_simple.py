import os
import sys
import asyncio
import logging
from logging.handlers import RotatingFileHandler
import threading
import time
import json
from queue import Queue
from dotenv import load_dotenv
import re
import datetime
import queue
# Import constants
from webassist.voice_assistant.constants import (
    LOGIN_URL, NAVIGATION_TIMEOUT, PAGE_LOAD_WAIT, DROPDOWN_OPEN_WAIT,FILTER_WAIT, SELECTION_WAIT,
    TAB_LOAD_WAIT, NAVIGATION_WAIT,VOICE_PROMPT, TEXT_PROMPT, VOICE_MODE_SWITCH_MESSAGE,
    TEXT_MODE_SWITCH_MESSAGE,TAB_PATTERN, STATE_SEARCH_PATTERN, LOGIN_PATTERN,EMAIL_SELECTORS,
    PASSWORD_SELECTORS, LOGIN_BUTTON_SELECTORS, LOGIN_LINK_SELECTORS,
    STATE_DROPDOWN_SELECTORS, STATE_FILTER_SELECTORS,HELP_TEXT,JS_FIND_STATE_DROPDOWN,
    JS_FIND_STATE_FILTER, JS_FIND_STATE_ITEM, JS_FIND_TAB,
    JS_FIND_LOGIN_LINK, JS_FILL_EMAIL,
    # New constants for service checkboxes, payment options, organizer dropdown
    SERVICE_CHECKBOX_SELECTORS, SERVICE_NAME_PATTERNS, PAYMENT_OPTION_SELECTORS,
    ORGANIZER_DROPDOWN_SELECTORS, ADD_ORGANIZER_BUTTON_SELECTORS,
    BILLING_INFO_DROPDOWN_SELECTORS, CHECKBOX_SELECTORS,
    JS_FIND_SERVICE_CHECKBOX, JS_FIND_PAYMENT_OPTION, JS_FIND_ORGANIZER_DROPDOWN,
    JS_FIND_ADD_ORGANIZER_BUTTON, JS_FIND_BILLING_INFO_DROPDOWN,
    JS_FIND_NAMED_CHECKBOX, JS_FIND_ANY_CHECKBOX
)

# Set up logging configuration
def setup_logging():
    """Configure comprehensive logging system with console and file output"""
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # Generate log filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(log_dir, f'voice_assistant_{timestamp}.log')

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)  # Keep log level as INFO as requested

    # Clear any existing handlers
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_format)

    file_handler = RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=10, encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    file_handler.setFormatter(file_format)

    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized")

    return logger

# Initialize logger
logger = setup_logging()

# Initialize global variables
running = True
input_mode = "text"  # Default to text mode
command_queue = Queue()

def display_prompt():
    """Display the appropriate prompt based on input mode"""
    global input_mode
    if input_mode == "text":
        print(f"\n{TEXT_PROMPT}")
    else:
        print(f"\n{VOICE_PROMPT}")
    sys.stdout.flush()

def display_voice_prompt():
    """Display the voice mode prompt"""
    global input_mode
    print(f"\n{VOICE_PROMPT}")
    sys.stdout.flush()

try:

    from webassist.Common.constants import *

    from webassist.voice_assistant.speech.enhanced_recognizer import create_enhanced_recognizer
    from webassist.voice_assistant.speech.synthesizer import create_synthesizer

    from webassist.voice_assistant.utils.browser_utils import BrowserUtils
    from webassist.voice_assistant.utils.llm_utils import LLMUtils

    from webassist.voice_assistant.interactions.navigation import NavigationHandler
    from webassist.voice_assistant.interactions.form_filling import FormFillingHandler
    from webassist.voice_assistant.interactions.selection import SelectionHandler
    from webassist.voice_assistant.interactions.specialized import SpecializedHandler
    from webassist.voice_assistant.interactions.member_manager import MemberManagerHandler
    from webassist.voice_assistant.interactions.business_purpose import BusinessPurposeHandler
    import speech_recognition as sr


    modules_loaded = True
    print("Successfully imported all modules")
except ImportError as e:
    modules_loaded = False
    print(f"Error importing modules: {e}")
    print("Some features may not be available")

class SimpleVoiceAssistant:
    def __init__(self):
        """Initialize the voice assistant"""
        self.browser = None
        self.page = None
        self.context = None
        self.ready_event = asyncio.Event()
        self.command_history = []
        self.last_command = None
        self.recognizer = None
        self.microphone = None
        self.synthesizer = None
        self.input_mode = "text"  # Default to text mode
        self.running = True
        self.llm_utils = None
        self.browser_utils = None
        self.handlers = {}
        self.logger = logging.getLogger(__name__)

        # Initialize speech recognition components
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()

            # Configure recognizer settings
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.energy_threshold = 300  # Lower threshold for better sensitivity
            self.recognizer.pause_threshold = 0.8  # Shorter pause threshold
            self.recognizer.phrase_threshold = 0.3  # More sensitive phrase detection
            self.recognizer.non_speaking_duration = 0.5  # Shorter non-speaking duration

            # Test microphone
            with self.microphone as source:
                print("Testing microphone...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print(f"Microphone initialized with energy threshold: {self.recognizer.energy_threshold}")

        except Exception as e:
            print(f"Error initializing speech components: {e}")
            import traceback
            traceback.print_exc()
            self.recognizer = None
            self.microphone = None

        # Initialize speech components
        try:
            # Initialize speech synthesizer
            if 'create_synthesizer' in globals():
                try:
                    self.synthesizer = create_synthesizer(config=self.speech_config)
                    logger.info("Speech synthesizer initialized")
                except Exception as synth_error:
                    logger.error(f"Error initializing speech synthesizer: {synth_error}")
                    logger.error("Speech synthesis will not be available")
                    self.synthesizer = None
            else:
                logger.warning("Speech synthesizer creation function not found")
                self.synthesizer = None

            # Initialize speech recognizer with fallback to text mode if voice fails
            global input_mode  # Declare global at the beginning of the block

            if 'create_enhanced_recognizer' in globals():
                try:
                    # First try to initialize in the requested mode
                    logger.info(f"Attempting to initialize speech recognizer in {input_mode} mode")
                    self.recognizer = create_enhanced_recognizer(config=self.speech_config, mode=input_mode, speak_func=self.speak)
                    logger.info(f"Speech recognizer initialized in {input_mode} mode")
                except Exception as rec_error:
                    logger.error(f"Error initializing speech recognizer in {input_mode} mode: {rec_error}")

                    # If voice mode failed, fall back to text mode
                    if input_mode == "voice":
                        logger.info("Falling back to text mode")
                        input_mode = "text"
                        try:
                            self.recognizer = create_enhanced_recognizer(config=self.speech_config, mode="text", speak_func=self.speak)
                            logger.info("Speech recognizer initialized in text mode")
                        except Exception as text_error:
                            logger.error(f"Error initializing text mode recognizer: {text_error}")
                            self.recognizer = None
            else:
                logger.warning("Speech recognizer creation function not found")
                self.recognizer = None

        except Exception as e:
            logger.error(f"Error initializing speech components: {e}")
            self.synthesizer = None
            self.recognizer = None

        self.llm_utils = None
        self.browser_utils = None
        self.navigation_handler = None
        self.selection_handler = None
        self.form_filling_handler = None
        self.specialized_handler = None
        self.member_manager_handler = None
        self.business_purpose_handler = None

        # Command history tracking
        self.command_history = []
        self.max_history_size = 50

        # Confirmation state for critical commands
        self.pending_confirmation = None
        self.confirmation_timeout = 30  # seconds

    async def initialize(self):
        """Initialize the assistant"""
        try:
            # Initialize speech recognition components first
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()

            # Configure recognizer settings
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.energy_threshold = 300  # Lower threshold for better sensitivity
            self.recognizer.pause_threshold = 0.8  # Shorter pause threshold
            self.recognizer.phrase_threshold = 0.3  # More sensitive phrase detection
            self.recognizer.non_speaking_duration = 0.5  # Shorter non-speaking duration

            # Test microphone
            with self.microphone as source:
                print("Testing microphone...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print(f"Microphone initialized with energy threshold: {self.recognizer.energy_threshold}")

            # Initialize browser
            await self._initialize_browser()

            # Initialize handlers
            await self._initialize_handlers()

            return True

        except Exception as e:
            print(f"Error during initialization: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _initialize_browser(self):
        """Initialize the browser with playwright"""
        try:
            print("Importing Playwright...")
            from playwright.async_api import async_playwright

            print("Starting Playwright...")
            logger.info("Starting Playwright")
            playwright = await async_playwright().start()

            print("Launching Chromium browser...")
            logger.info("Launching Chromium browser")
            # Launch browser with specific options to ensure it opens visibly
            browser = await playwright.chromium.launch(
                headless=False,
                args=[
                    '--start-maximized',
                    '--disable-extensions',
                    '--disable-popup-blocking',
                    '--disable-infobars'
                ]
            )

            print("Browser launched successfully!")
            return browser
        except ImportError as e:
            error_msg = f"Playwright not installed: {e}"
            print(f"\n❌ {error_msg}")
            logger.error(error_msg)
            logger.error("Please install it with: pip install playwright")
            logger.error("Then install browsers with: playwright install")
            raise
        except Exception as e:
            error_msg = f"Error initializing browser: {e}"
            print(f"\n❌ {error_msg}")
            logger.error(error_msg)
            import traceback
            traceback.print_exc()
            raise

    async def _initialize_handlers(self):
        """Initialize all interaction handlers"""
        logger.info("Initializing interaction handlers...")

        if not all([hasattr(self, "page"), hasattr(self, "llm_utils"), hasattr(self, "browser_utils")]):
            logger.error("Cannot initialize handlers - missing required components")
            return

        try:
            if 'NavigationHandler' in globals():
                self.navigation_handler = NavigationHandler(
                    self.page, self.speak, self.llm_utils, self.browser_utils
                )
                logger.info("Navigation handler initialized")

            if 'SelectionHandler' in globals():
                self.selection_handler = SelectionHandler(
                    self.page, self.speak, self.llm_utils, self.browser_utils
                )
                logger.info("Selection handler initialized")

            if 'FormFillingHandler' in globals():
                self.form_filling_handler = FormFillingHandler(
                    self.page, self.speak, self.llm_utils, self.browser_utils
                )
                logger.info("Form filling handler initialized")

            if 'SpecializedHandler' in globals():
                self.specialized_handler = SpecializedHandler(
                    self.page, self.speak, self.llm_utils, self.browser_utils
                )
                logger.info("Specialized handler initialized")

            if 'MemberManagerHandler' in globals():
                self.member_manager_handler = MemberManagerHandler(
                    self.page, self.speak, self.llm_utils, self.browser_utils
                )
                logger.info("Member/Manager handler initialized")

            if 'BusinessPurposeHandler' in globals():
                self.business_purpose_handler = BusinessPurposeHandler(
                    self.page, self.speak, self.llm_utils, self.browser_utils
                )
                logger.info("Business Purpose handler initialized")

            logger.info("All handlers initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing handlers: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def speak(self, text):
        """Synthesize speech or print text based on mode"""
        # Declare global variables at the beginning of the function
        global input_mode

        logger.info(f"ASSISTANT: {text}")

        if input_mode == "voice" and self.synthesizer:
            try:
                logger.info(f"Speaking text in voice mode: '{text[:30]}...' (truncated)")
                await self.synthesizer.speak(text)
            except Exception as e:
                logger.error(f"Error synthesizing speech: {e}")

        # Always display the appropriate prompt after speaking
        if input_mode == "voice":
            # Make the voice prompt EXTREMELY visible
            print("\n\n\n")
            print("!" * 100)
            print("!" * 100)
            print("🎤 VOICE MODE ACTIVE - READY FOR COMMANDS".center(100))
            print("!" * 100)
            print(f"\n{VOICE_PROMPT}".center(100))
            print("!" * 100)
            print("!" * 100)
            # Force flush to ensure output is displayed immediately
            sys.stdout.flush()
            # Add a longer delay to ensure the output is visible
            time.sleep(1.0)
        else:
            display_prompt()

        return True

    async def navigate_to(self, url):
        """Navigate to a URL"""
        logger.info(f"Navigating to: {url}")
        try:
            await self.page.goto(url)
            title = await self.page.title()
            logger.info(f"Page loaded successfully: {title}")
            await self.speak(f"Loaded: {title}")
            return True
        except Exception as e:
            logger.error(f"Error navigating to {url}: {str(e)}")
            await self.speak(f"Error navigating to {url}: {str(e)}")
            return False

    async def process_command(self, command):
        """Process a user command"""
        # Declare global variables at the beginning of the function
        global input_mode

        if not command:
            logger.info("Empty command received, ignoring")
            return True

        logger.info(f"Processing command: {command}")

        # Log the command for history tracking
        self._add_to_command_history(command)

        # Process voice commands with enhanced handling
        if input_mode == "voice":
            return await self._process_voice_command(command)
        else:
            # Process text commands with standard handling
            return await self._process_text_command(command)

    async def _process_voice_command(self, command):
        """Process a voice command with enhanced handling"""
        logger.info(f"Processing voice command: {command}")

        # First check if there's a pending confirmation
        if self.pending_confirmation:
            confirmation_result = await self._check_confirmation(command)
            if confirmation_result is not None:
                return confirmation_result

        # Handle exit commands - require confirmation
        if any(exit_cmd in command.lower() for exit_cmd in ["exit", "quit", "goodbye", "bye", "stop"]):
            logger.info("Exit command received via voice - requesting confirmation")
            return await self._request_confirmation("exit the assistant", timeout=15)

        # Handle help command
        if command.lower() in ["help", "help me", "what can you do", "show commands", "available commands"]:
            logger.info("Help command received via voice")
            await self.help_command()
            return True

        # Handle command history request
        if any(history_cmd in command.lower() for history_cmd in ["show history", "command history", "previous commands", "what did i say"]):
            logger.info("Command history request received")
            await self._show_command_history()
            return True

        # Handle repeat last command
        if any(repeat_cmd in command.lower() for repeat_cmd in ["repeat last command", "repeat previous command", "do that again"]):
            logger.info("Repeat last command request received")
            return await self._repeat_last_command()

        # Continue with regular command processing
        return await self._process_text_command(command)

    async def _process_text_command(self, command):
        """Process a text command with standard handling"""
        # Handle exit commands
        if command.lower() in ["exit", "quit"]:
            logger.info("Exit command received")
            await self.speak("Goodbye!")
            return False

        # Handle help command
        if command.lower() == "help":
            logger.info("Help command received")
            await self.help_command()
            return True

        # Handle mode switching commands
        if command.lower() in ["voice", "voice mode", "switch to voice", "switch to voice mode"]:
            logger.info("Voice mode command received")
            await self.switch_recognizer_mode("voice")
            return True

        if command.lower() in ["text", "text mode", "switch to text", "switch to text mode"]:
            logger.info("Text mode command received")
            await self.switch_recognizer_mode("text")
            return True

        # Process navigation commands directly
        if command.lower().startswith("go to ") or command.lower().startswith("navigate to ") or command.lower().startswith("goto "):
            logger.info("Navigation command detected")

            # Extract the URL part
            if command.lower().startswith("goto "):
                url = command[5:].strip()
            else:
                url = command.split(" ", 2)[-1].strip()

            # Preserve the exact domain name as specified by the user
            original_domain = url

            # Ensure the URL is properly formatted
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            # Remove any trailing slashes or spaces
            url = url.rstrip('/ ')

            # Log the exact URL we're navigating to
            logger.info(f"Navigating to URL: {url} (original input: {original_domain})")

            # Special handling for redberyltest.in
            if any(variant in original_domain.lower() for variant in [
                "red beryl test", "redberyl test", "redberyltest",
                "red berry test", "redberry test"
            ]):
                # User is likely trying to go to redberyltest.in
                url = "https://www.redberyltest.in"
                logger.info(f"Detected attempt to navigate to redberyltest.in, corrected URL to: {url}")

            # Use LLM to verify the domain if available
            if hasattr(self, 'llm_utils') and self.llm_utils:
                try:
                    # Create a prompt to verify the domain
                    prompt = f"""
                    The user is trying to navigate to: "{original_domain}"

                    Analyze if this is likely a speech recognition error for a common domain.

                    If it's clearly a speech recognition error for "redberyltest.in", respond with ONLY "redberyltest.in".
                    If it's a legitimate domain like "redbus.in" or any other valid domain, respond with ONLY the original domain: "{original_domain}".

                    Return ONLY the domain name without any explanations.
                    """

                    # Get the verified domain from the LLM
                    verified_domain = None

                    # Try different LLM methods based on what's available
                    if hasattr(self.llm_utils, 'get_llm_response'):
                        logger.info("Using LLM to verify domain...")
                        verified_domain = await self.llm_utils.get_llm_response(prompt)
                    elif hasattr(self.llm_utils.llm_provider, 'generate_content'):
                        logger.info("Using LLM to verify domain...")
                        response = self.llm_utils.llm_provider.generate_content(prompt)
                        verified_domain = response.text
                    elif hasattr(self.llm_utils.llm_provider, 'generate'):
                        logger.info("Using LLM to verify domain...")
                        verified_domain = await self.llm_utils.llm_provider.generate(prompt)

                    # Clean up the verified domain
                    if verified_domain:
                        verified_domain = verified_domain.strip().strip('"\'').strip().lower()

                        if verified_domain == "redberyltest.in":
                            url = "https://www.redberyltest.in"
                            logger.info(f"LLM verified domain as redberyltest.in, corrected URL to: {url}")
                        else:
                            logger.info(f"LLM verified domain as: {verified_domain}, keeping original URL")

                except Exception as e:
                    logger.error(f"Error verifying domain with LLM: {e}")
                    # Continue with the current URL if verification fails

            await self.navigate_to(url)
            return True

        # Handle state search commands
        state_search_match = re.search(STATE_SEARCH_PATTERN, command.lower())
        if state_search_match:
            state_name = state_search_match.group(1).strip()
            logger.info(f"State search command detected for state: {state_name}")
            await self.speak(f"Searching for state: {state_name}")
            success = await self.search_state(state_name)
            if success:
                logger.info(f"Successfully found and selected state: {state_name}")
                await self.speak(f"Found and selected state: {state_name}")
            else:
                logger.warning(f"Could not find state: {state_name}")
                await self.speak(f"Could not find state: {state_name}")
            return True

        # Handle tab click commands
        tab_match = re.search(TAB_PATTERN, command.lower())
        if tab_match:
            tab_name = tab_match.group(1)
            logger.info(f"Tab click command detected for tab: {tab_name}")
            await self.speak(f"Looking for {tab_name} tab...")
            success = await self.click_tab(tab_name)
            if success:
                logger.info(f"Successfully clicked {tab_name} tab")
                await self.speak(f"Clicked {tab_name} tab")
            else:
                logger.warning(f"Could not find {tab_name} tab")
                await self.speak(f"Could not find {tab_name} tab")
            return True

        # Handle login commands with improved pattern matching
        login_patterns = [
            r'(?:login|log in|signin|sign in)',
            r'(?:click|press|tap|select)(?:\s+(?:the|on))?\s+(?:login|log in|signin|sign in)(?:\s+button)?',
            r'(?:find|locate)(?:\s+(?:the))?\s+(?:login|log in|signin|sign in)(?:\s+button)?'
        ]

        if any(re.search(pattern, command.lower()) for pattern in login_patterns):
            logger.info("Login command detected")
            await self.speak("Looking for login button...")

            # Get the raw LLM response for login button selectors if available
            raw_llm_response = None
            if hasattr(self, 'llm_utils') and self.llm_utils:
                try:
                    # Get the current page context
                    context = await self._get_page_context()
                    logger.info(f"Got page context: URL={context.get('url', '')}, Title={context.get('title', '')}")

                    # Ask the LLM for login button selectors
                    prompt = f"Generate CSS selectors for finding a login button on this page. Return ONLY a JSON array of selector strings. Context: {context.get('url', '')}, {context.get('title', '')}"
                    logger.info("Requesting login button selectors from LLM")

                    if hasattr(self.llm_utils.llm_provider, 'generate_content'):
                        response = self.llm_utils.llm_provider.generate_content(prompt)
                        raw_llm_response = response.text
                    else:
                        # Fallback to a simple method if generate_content is not available
                        logger.warning("LLM provider doesn't have generate_content method, using fallback selectors")
                        raw_llm_response = '["#signInButton", "button:has-text(\\"Login\\")", "button:has-text(\\"Sign in\\")"]'

                    logger.info(f"Raw LLM response for selectors: {raw_llm_response[:100]}..." if len(raw_llm_response) > 100 else raw_llm_response)
                except Exception as e:
                    logger.error(f"Error getting LLM response: {e}")

            # Try to click the login button with parsed selectors if available
            logger.info("Attempting to click login button")
            success = await self.click_login_button(raw_llm_response)

            if success:
                logger.info("Successfully clicked login button")
                await self.speak("Clicked login button")
            else:
                logger.warning("Could not find login button")
                await self.speak("Could not find login button")
            return True


        # Improved email command pattern with better handling of speech recognition errors
        email_command_match = re.search(r'(?:enter|input|type|fill|put|use|set|write)\s+(?:email|emaol|e-mail|email\s+address|email\s+adddress|mail|e mail)\s+([^\s]+@[^\s]+(?:\.[^\s]+)+)(?:\s+(?:and|with|&|plus|using)?\s+(?:password|pass|pwd|pword|oassword|pasword|passord)\s+(\S+))?', command, re.IGNORECASE)

        if email_command_match:
            # Extract the email - everything after "enter email" and before "and password" if present
            email_part = email_command_match.group(1).strip()
            password_part = email_command_match.group(2) if email_command_match.group(2) else None

            logger.info(f"Email command detected. Extracted email: '{email_part}', password: {'*****' if password_part else 'None'}")

            # Create appropriate match objects with the extracted values
            if password_part:
                # Both email and password were provided
                logger.info("Both email and password provided in command")
                enter_email_match = type('obj', (object,), {'groups': lambda: (email_part, password_part)})
                email_only_match = None
            else:
                # Only email was provided
                logger.info("Only email provided in command")
                enter_email_match = None
                email_only_match = type('obj', (object,), {'group': lambda _: email_part})
        else:
            # If the direct approach didn't work, fall back to regex patterns
            logger.info("Direct email pattern didn't match, trying fallback patterns")

            # First check for email and password pattern
            enter_email_match = re.search(r'enter\s+(?:email|emaol|e-mail|email\s+address|email\s+adddress)\s+(\S+)(?:\s+(?:and|with|&)?\s+(?:password|pass|pwd|pword|oassword)\s+(\S+))?', command, re.IGNORECASE)

            if not enter_email_match:
                # Try more flexible patterns for email and password
                logger.info("Trying flexible email+password patterns")
                enter_patterns = [
                    r'(?:enter|input|type)\s+(?:email|email address|email adddress)?\s*(\S+)\s+(?:and|with)\s+(?:password|pass|p[a-z]*)?\s*(\S+)',
                    r'(?:fill|fill in)\s+(?:with)?\s*(?:email|username|email address|email adddress)?\s*(\S+)\s+(?:and|with)\s*(?:password|pass|p[a-z]*)?\s*(\S+)',
                    r'(?:enter|input|type|fill|put)\s+(?:in|the)?\s*(?:email|emaol|e-mail|username|email address|email adddress)?\s*(\S+@\S+)(?:\s+(?:and|with|&)?\s+(?:password|pass|pwd|pword|oassword)\s+(\S+))?',
                    r'(?:email|emaol|e-mail|username|email address|email adddress)\s+(?:is|as)?\s*(\S+@\S+)(?:\s+(?:and|with|&)?\s+(?:password|pass|pwd|pword|oassword)\s+(?:is|as)?\s*(\S+))?'
                ]

                for pattern in enter_patterns:
                    enter_email_match = re.search(pattern, command, re.IGNORECASE)
                    if enter_email_match:
                        logger.info(f"Matched email+password pattern: {pattern}")
                        break

            # If no match for email+password, check for just email
            email_only_match = None
            if not enter_email_match:
                logger.info("No email+password pattern matched, trying email-only patterns")
                email_only_patterns = [
                    r'enter (?:email|email address|email adddress)\s+(\S+@\S+)',
                    r'(?:enter|input|type|fill)\s+(?:ema[a-z]+|email address|email adddress)?\s*(\S+@\S+)',  # Handle typos like 'emaol'
                    r'(?:email|ema[a-z]+|email address|email adddress)\s+(\S+@\S+)',  # Handle typos like 'emaol'
                    r'(?:enter|input|type|fill)\s+(?:email|ema[a-z]+|email address|email adddress)\s+(\S+)',  # Catch any word after email command
                    r'(?:email|ema[a-z]+|email address|email adddress)\s+(\S+)'  # Catch any word after email
                ]

                for pattern in email_only_patterns:
                    logger.debug(f"Trying email-only pattern: {pattern}")
                    email_only_match = re.search(pattern, command, re.IGNORECASE)
                    if email_only_match:
                        logger.info(f"Matched email-only pattern: {pattern}")
                        break

        if email_only_match:
            # Handle email-only case
            email = email_only_match.group(1)
            logger.info(f"Processing email-only command with email: {email}")
            await self.speak(f"Entering email: {email}")
            success = await self.fill_email_field(email)
            if success:
                logger.info("Successfully filled email field")
                await self.speak("Email entered successfully")
            else:
                logger.warning("Could not find email field")
                await self.speak("Could not find email field")
            return True

        elif enter_email_match:
            email, password = enter_email_match.groups()
            logger.info(f"Processing email+password command with email: {email}, password: {'*****' if password else 'None'}")

            if password:
                await self.speak(f"Entering email and password...")
            else:
                await self.speak(f"Entering email...")

            success = await self.login_with_credentials(email, password if password else "")
            if success:
                logger.info("Login successful")
                await self.speak("Login successful")
            else:
                logger.warning("Login failed")
                await self.speak("Login failed")
            return True

        # Simple login pattern
        logger.info("Checking for login pattern")
        login_match = re.search(r'login with email\s+(\S+)\s+and password\s+(\S+)', command, re.IGNORECASE)

        # If simple pattern doesn't match, try more flexible patterns
        if not login_match:
            logger.info("Simple login pattern didn't match, trying flexible patterns")
            login_patterns = [
                r'log[a-z]* w[a-z]* (?:email|email address)?\s+(\S+)\s+[a-z]*xxxxx (?:password|pass|p[a-z]*)\s+(\S+)',
                r'login\s+(?:with|using|w[a-z]*)\s+(?:email|email address)?\s*(\S+)\s+(?:and|with|[a-z]*)\s+(?:password|pass|p[a-z]*)\s*(\S+)',
                r'(?:login|sign in|signin)\s+(?:with|using|w[a-z]*)?\s*(?:email|username)?\s*(\S+)\s+(?:and|with|[a-z]*)\s*(?:password|pass|p[a-z]*)?\s*(\S+)',
                r'log[a-z]*.*?(\S+@\S+).*?(\S+)'
            ]

            for pattern in login_patterns:
                login_match = re.search(pattern, command, re.IGNORECASE)
                if login_match:
                    logger.info(f"Matched login pattern: {pattern}")
                    break

        # If we found a login match with any pattern
        if login_match:
            email, password = login_match.groups()
            logger.info(f"Login command detected with email: {email}, password: {'*****'}")
            await self.speak(f"Attempting to log in with email {email}")
            success = await self.login_with_credentials(email, password)
            if success:
                logger.info("Login successful")
                await self.speak("Login successful")
            else:
                logger.warning("Login failed")
                await self.speak("Login failed")
            return True

        # Handle "enter password" command with more robust pattern matching
        logger.info("Checking for password-only command")
        password_match = re.search(r'(?:enter|input|type|fill|use)\s+(?:the\s+)?(?:password|pass|passwd|pwd|pword|oassword)\s+(\S+)', command, re.IGNORECASE)
        if not password_match:
            password_match = re.search(r'(?:password|pass|passwd|pwd|pword|oassword)\s+(?:is\s+)?(\S+)', command, re.IGNORECASE)

        if password_match:
            password = password_match.group(1)
            logger.info("Password-only command detected")
            await self.speak("Entering password")
            success = await self.fill_password_field(password)
            if success:
                logger.info("Successfully filled password field")
                await self.speak("Password entered successfully")
            else:
                logger.warning("Could not find password field")
                await self.speak("Could not find password field")
            return True

        # Try specialized handler first
        if self.specialized_handler:
            logger.info("Delegating to specialized handler")
            try:
                if await self.specialized_handler.handle_command(command):
                    logger.info("Command handled by specialized handler")
                    return True
            except Exception as e:
                logger.error(f"Error in specialized handler: {e}")
                import traceback
                logger.error(traceback.format_exc())

        # Try form filling handler
        if self.form_filling_handler:
            logger.info("Delegating to form filling handler")
            try:
                if await self.form_filling_handler.handle_command(command):
                    logger.info("Command handled by form filling handler")
                    return True
            except Exception as e:
                logger.error(f"Error in form filling handler: {e}")
                import traceback
                logger.error(traceback.format_exc())

        # Try business purpose handler
        if self.business_purpose_handler:
            logger.info("Delegating to business purpose handler")
            try:
                if await self.business_purpose_handler.handle_command(command):
                    logger.info("Command handled by business purpose handler")
                    return True
            except Exception as e:
                logger.error(f"Error in business purpose handler: {e}")
                import traceback
                logger.error(traceback.format_exc())

        # Try member/manager handler
        if self.member_manager_handler:
            logger.info("Delegating to member/manager handler")
            try:
                if await self.member_manager_handler.handle_command(command):
                    logger.info("Command handled by member/manager handler")
                    return True
            except Exception as e:
                logger.error(f"Error in member/manager handler: {e}")
                import traceback
                logger.error(traceback.format_exc())

        # Try selection handler
        if self.selection_handler:
            logger.info("Delegating to selection handler")
            try:
                if await self.selection_handler.handle_command(command):
                    logger.info("Command handled by selection handler")
                    return True
            except Exception as e:
                logger.error(f"Error in selection handler: {e}")
                import traceback
                logger.error(traceback.format_exc())

        # Try navigation handler
        if self.navigation_handler:
            logger.info("Delegating to navigation handler")
            try:
                if await self.navigation_handler.handle_command(command):
                    logger.info("Command handled by navigation handler")
                    return True
            except Exception as e:
                logger.error(f"Error in navigation handler: {e}")
                import traceback
                logger.error(traceback.format_exc())



        # Handle clicking orders with specific IDs (with typo tolerance for "click")
        order_id_match = re.search(r'(?:click|clcik|clik|clck|clk)\s+(?:on\s+)?(?:the\s+)?order\s+(?:with\s+)?(?:id\s+)?(\d+)', command.lower())
        if order_id_match:
            order_id = order_id_match.group(1).strip()
            logger.info(f"Order click command detected for order ID: {order_id}")
            await self.speak(f"Looking for order with id {order_id}...")

            # Get the raw LLM response for order selectors if available
            raw_llm_response = None
            if hasattr(self, 'llm_utils') and self.llm_utils:
                try:
                    # Get the current page context
                    context = await self._get_page_context()
                    logger.info(f"Got page context for order search: URL={context.get('url', '')}, Title={context.get('title', '')}")

                    # Ask the LLM for order selectors
                    prompt = f"Generate CSS selectors for finding an order with ID {order_id} on this page. Return ONLY a JSON array of selector strings. Context: {context.get('url', '')}, {context.get('title', '')}"
                    logger.info(f"Requesting order selectors from LLM for order ID: {order_id}")

                    # Use the correct method based on what's available
                    if hasattr(self.llm_utils, 'get_llm_response'):
                        logger.info("Using get_llm_response method")
                        raw_llm_response = await self.llm_utils.get_llm_response(prompt)
                    elif hasattr(self.llm_utils.llm_provider, 'generate_content'):
                        logger.info("Using generate_content method")
                        response = self.llm_utils.llm_provider.generate_content(prompt)
                        raw_llm_response = response.text
                    elif hasattr(self.llm_utils.llm_provider, 'generate'):
                        logger.info("Using generate method")
                        raw_llm_response = await self.llm_utils.llm_provider.generate(prompt)
                    else:
                        # Fallback to a simple method if none of the above are available
                        logger.warning("No suitable LLM method found, using fallback selectors")
                        raw_llm_response = '["#order-' + order_id + '", "[id=\\"' + order_id + '\\"]", "tr[data-order-id=\\"' + order_id + '\\"]"]'

                    logger.info(f"Raw LLM response for order selectors: {raw_llm_response[:100]}..." if len(raw_llm_response) > 100 else raw_llm_response)
                except Exception as e:
                    logger.error(f"Error getting LLM response for order selectors: {e}")
                    import traceback
                    logger.error(traceback.format_exc())

            # Try to click the order with the specific ID
            logger.info(f"Attempting to click order with ID: {order_id}")
            success = await self.click_order_with_id(order_id, raw_llm_response)

            if success:
                logger.info(f"Successfully clicked order with ID {order_id}")
                await self.speak(f"Clicked order with id {order_id}")
            else:
                logger.warning(f"Could not find order with ID {order_id}")
                await self.speak(f"Could not find order with id {order_id}")
            return True

        # Handle principal address dropdown specifically
        principal_address_match = re.search(r'(?:click|select|open|choose)\s+(?:on\s+)?(?:the\s+)?(?:principal\s+address|principal\s+address\s+dropdown)', command.lower())
        if principal_address_match:
            logger.info("Principal address dropdown command detected")
            await self.speak("Looking for principal address dropdown...")

            success = await self.click_principal_address_dropdown()

            if success:
                logger.info("Successfully clicked principal address dropdown")
                await self.speak("Clicked principal address dropdown")
            else:
                logger.warning("Could not find principal address dropdown")
                await self.speak("Could not find principal address dropdown")
            return True

        # Handle billing info dropdown specifically
        billing_info_match = re.search(r'(?:click|select|open|choose)\s+(?:on\s+)?(?:the\s+)?(?:billing\s+info|billing\s+information|billing\s+dropdown)', command.lower())
        if billing_info_match:
            logger.info("Billing info dropdown command detected")
            await self.speak("Looking for billing info dropdown...")

            success = await self.click_billing_info_dropdown()

            if success:
                logger.info("Successfully clicked billing info dropdown")
                await self.speak("Clicked billing info dropdown")
            else:
                logger.warning("Could not find billing info dropdown")
                await self.speak("Could not find billing info dropdown")
            return True

        # Handle mailing info dropdown specifically
        mailing_info_match = re.search(r'(?:click|select|open|choose)\s+(?:on\s+)?(?:the\s+)?(?:mailing\s+info|mailing\s+information|mailing\s+dropdown)', command.lower())
        if mailing_info_match:
            logger.info("Mailing info dropdown command detected")
            await self.speak("Looking for mailing info dropdown...")

            success = await self.click_mailing_info_dropdown()

            if success:
                logger.info("Successfully clicked mailing info dropdown")
                await self.speak("Clicked mailing info dropdown")
            else:
                logger.warning("Could not find mailing info dropdown")
                await self.speak("Could not find mailing info dropdown")
            return True



        # Handle service checkbox specifically
        service_match = re.search(r'(?:click|check|select|toggle|mark)\s+(?:on\s+)?(?:the\s+)?(?:service|service\s+checkbox)(?:\s+(?:for|labeled|named|with\s+name|with\s+label)\s+(.+))?', command.lower())
        if service_match:
            logger.info("Service checkbox command detected")

            # Check if a specific service name was provided
            service_name = service_match.group(1) if service_match.group(1) else None

            if service_name:
                logger.info(f"Looking for service checkbox for: {service_name}")
                await self.speak(f"Looking for service {service_name}...")

                success = await self.click_service_checkbox(service_name)

                if success:
                    logger.info(f"Successfully clicked service checkbox for {service_name}")
                    await self.speak(f"Selected service {service_name}")
                else:
                    logger.warning(f"Could not find service checkbox for {service_name}")
                    await self.speak(f"Could not find service {service_name}")
            else:
                logger.info("No specific service name provided")
                await self.speak("Please specify which service you want to select")
            return True

        # Handle payment option checkbox specifically
        payment_option_match = re.search(r'(?:click|check|select|toggle|mark)\s+(?:on\s+)?(?:the\s+)?(?:pay\s+now|pay\s+later)', command.lower())
        if payment_option_match:
            payment_option = payment_option_match.group(0).lower()
            if "now" in payment_option:
                option = "Pay now"
            else:
                option = "Pay later"

            logger.info(f"{option} checkbox command detected")
            await self.speak(f"Looking for {option} checkbox...")

            success = await self.click_payment_option(option)

            if success:
                logger.info(f"Successfully clicked {option} checkbox")
                await self.speak(f"Selected {option}")
            else:
                logger.warning(f"Could not find {option} checkbox")
                await self.speak(f"Could not find {option} checkbox")
            return True

        # Handle checkbox specifically - with optional name
        checkbox_match = re.search(r'(?:click|check|select|toggle|mark)\s+(?:on\s+)?(?:the\s+)?(?:checkbox|check\s+box|tick\s+box)(?:\s+(?:for|labeled|named|with\s+name|with\s+label)\s+(.+))?', command.lower())
        if checkbox_match:
            logger.info("Checkbox command detected")

            # Check if a specific checkbox name was provided
            checkbox_name = checkbox_match.group(1) if checkbox_match.group(1) else None

            if checkbox_name:
                logger.info(f"Looking for checkbox with name: {checkbox_name}")
                await self.speak(f"Looking for checkbox labeled {checkbox_name}...")

                success = await self.click_checkbox(checkbox_name)

                if success:
                    logger.info(f"Successfully clicked checkbox labeled {checkbox_name}")
                    await self.speak(f"Clicked checkbox labeled {checkbox_name}")
                else:
                    logger.warning(f"Could not find checkbox labeled {checkbox_name}")
                    await self.speak(f"Could not find checkbox labeled {checkbox_name}")
            else:
                logger.info("Looking for any checkbox")
                await self.speak("Looking for checkbox...")

                success = await self.click_checkbox()

                if success:
                    logger.info("Successfully clicked checkbox")
                    await self.speak("Clicked checkbox")
                else:
                    logger.warning("Could not find checkbox")
                    await self.speak("Could not find checkbox")
            return True

        # Handle add billing info button specifically
        add_billing_info_match = re.search(r'(?:click|press|tap|select)\s+(?:on\s+)?(?:the\s+)?(?:add\s+billing\s+info|add\s+billing\s+information|add\s+billing)(?:\s+button)?', command.lower())
        if add_billing_info_match:
            logger.info("Add billing info button command detected")
            await self.speak("Looking for add billing info button...")

            success = await self.click_add_billing_info_button()

            if success:
                logger.info("Successfully clicked add billing info button")
                await self.speak("Clicked add billing info button")
            else:
                logger.warning("Could not find add billing info button")
                await self.speak("Could not find add billing info button")
            return True

        # Handle organizer dropdown specifically
        organizer_dropdown_match = re.search(r'(?:click|select|open|choose)\s+(?:on\s+)?(?:the\s+)?(?:organizer\s+dropdown|select\s+organizer|organizer)', command.lower())
        if organizer_dropdown_match:
            logger.info("Organizer dropdown command detected")
            await self.speak("Looking for organizer dropdown...")

            success = await self.click_organizer_dropdown()

            if success:
                logger.info("Successfully clicked organizer dropdown")
                await self.speak("Clicked organizer dropdown")
            else:
                logger.warning("Could not find organizer dropdown")
                await self.speak("Could not find organizer dropdown")
            return True

        # Handle add organizer button specifically
        add_organizer_match = re.search(r'(?:click|press|tap|select)\s+(?:on\s+)?(?:the\s+)?(?:add\s+organizer)(?:\s+button)?', command.lower())
        if add_organizer_match:
            logger.info("Add organizer button command detected")
            await self.speak("Looking for add organizer button...")

            success = await self.click_add_organizer_button()

            if success:
                logger.info("Successfully clicked add organizer button")
                await self.speak("Clicked add organizer button")
            else:
                logger.warning("Could not find add organizer button")
                await self.speak("Could not find add organizer button")
            return True

        # Handle generic click commands (with typo tolerance for "click")
        click_match = re.search(r'(?:click|clcik|clik|clck|clk)\s+(?:on\s+)?(?:the\s+)?(.+)', command.lower())
        if click_match:
            element_name = click_match.group(1).strip()

            # Skip if it's a login button (already handled above)
            if "login" in element_name or "sign in" in element_name:
                return True

            # Skip if it's the principal address dropdown (already handled above)
            if "principal address" in element_name:
                return True

            await self.speak(f"Looking for {element_name}...")

            # Get the raw LLM response for element selectors if available
            raw_llm_response = None
            if hasattr(self, 'llm_utils') and self.llm_utils:
                try:
                    # Get the current page context
                    context = await self._get_page_context()

                    # Ask the LLM for element selectors
                    prompt = f"Generate CSS selectors for finding a {element_name} on this page. Return ONLY a JSON array of selector strings. Context: {context.get('url', '')}, {context.get('title', '')}"
                    # Use the correct method based on what's available
                    if hasattr(self.llm_utils, 'get_llm_response'):
                        raw_llm_response = await self.llm_utils.get_llm_response(prompt)
                    elif hasattr(self.llm_utils.llm_provider, 'generate_content'):
                        response = self.llm_utils.llm_provider.generate_content(prompt)
                        raw_llm_response = response.text
                    elif hasattr(self.llm_utils.llm_provider, 'generate'):
                        raw_llm_response = await self.llm_utils.llm_provider.generate(prompt)
                    else:
                        # Fallback to a simple method if none of the above are available
                        raw_llm_response = '["button:has-text(\\"' + element_name + '\\")"]'
                    print(f"🔍 Raw LLM response:\n {raw_llm_response}")
                except Exception as e:
                    print(f"Error getting LLM response: {e}")

            # Try to click the element with parsed selectors if available
            success = await self.click_element(element_name, raw_llm_response)

            if success:
                await self.speak(f"Clicked {element_name}")
            else:
                await self.speak(f"Could not find {element_name}")
            return True

        # Handle various navigation commands with or without spaces
        navigation_prefixes = {
            "goto ": 5,           # "goto example.com"
            "go to ": 6,          # "go to example.com"
            "navigate to ": 12,    # "navigate to example.com"
            "open ": 5,           # "open example.com"
            "browse to ": 10,      # "browse to example.com"
            "visit ": 6,          # "visit example.com"
            "load ": 5,           # "load example.com"
            "show me ": 8,        # "show me example.com"
            "take me to ": 11      # "take me to example.com"
        }

        # Check for any of the navigation command prefixes
        for prefix, length in navigation_prefixes.items():
            if command.lower().startswith(prefix):
                # Extract the URL from the command
                url = command[length:].strip()
                logger.info(f"Detected navigation command '{prefix.strip()}' for URL: {url}")

                # Preserve the exact domain name as specified by the user
                original_domain = url

                # Ensure the URL is properly formatted
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url

                # Remove any trailing slashes or spaces
                url = url.rstrip('/ ')

                # Log the exact URL we're navigating to
                logger.info(f"Navigating to URL: {url} (original input: {original_domain})")

                # Special handling for specific domains
                if "redberyltest.in" in original_domain.lower() and "redberyltest.in" not in url.lower():
                    # Force the correct domain for redberyltest.in
                    url = "https://www.redberyltest.in"
                    logger.info(f"Corrected URL to: {url}")

                # Special handling for other domains that might be misrecognized
                domain_corrections = {
                    "web.com": "web.com",
                    "google.com": "google.com",
                    "facebook.com": "facebook.com",
                    "twitter.com": "twitter.com",
                    "youtube.com": "youtube.com",
                    "amazon.com": "amazon.com",
                    "reddit.com": "reddit.com",
                    "wikipedia.org": "wikipedia.org",
                    "linkedin.com": "linkedin.com",
                    "github.com": "github.com"
                }

                # Check if any domain correction is needed
                for correct_domain, replacement in domain_corrections.items():
                    # Use fuzzy matching to detect similar domains
                    if correct_domain in original_domain.lower() and correct_domain not in url.lower():
                        url = f"https://www.{replacement}"
                        logger.info(f"Corrected URL to: {url}")
                        break

                await self.navigate_to(url)
                return True

        # Process page commands (refresh, back, forward, etc.)
        page_commands = {
            # Refresh commands
            "refresh": self._refresh_page,
            "refresh page": self._refresh_page,
            "reload": self._refresh_page,
            "reload page": self._refresh_page,
            "update page": self._refresh_page,
            "update": self._refresh_page,

            # Back commands
            "back": self._go_back,
            "go back": self._go_back,
            "previous page": self._go_back,
            "previous": self._go_back,
            "return": self._go_back,

            # Forward commands
            "forward": self._go_forward,
            "go forward": self._go_forward,
            "next page": self._go_forward,
            "next": self._go_forward,

            # Scroll commands
            "scroll down": self._scroll_down,
            "scroll up": self._scroll_up,
            "page down": self._scroll_down,
            "page up": self._scroll_up,
            "bottom": self._scroll_to_bottom,
            "top": self._scroll_to_top,
            "scroll to bottom": self._scroll_to_bottom,
            "scroll to top": self._scroll_to_top
        }

        # Check for exact matches first
        if command.lower() in page_commands:
            logger.info(f"Processing page command: {command.lower()}")
            await page_commands[command.lower()]()
            return True

        # Check for commands that start with these prefixes
        for cmd_prefix, handler in page_commands.items():
            if command.lower().startswith(cmd_prefix + " "):
                logger.info(f"Processing page command with prefix: {cmd_prefix}")
                await handler()
                return True

        # If no handler processed the command, try to process it as a URL
        if command.startswith("http") or command.startswith("www.") or "." in command:
            # Skip if it contains common command words
            if any(word in command.lower() for word in ["goto", "go to", "navigate", "click", "enter", "login", "sign in",
                                                       "refresh", "reload", "back", "forward", "scroll", "page"]):
                logger.info(f"Skipping URL processing for command that looks like another command: {command}")
                return False

            url = command.strip()

            # Preserve the exact domain name as specified by the user
            original_domain = url

            if not url.startswith("http"):
                url = "https://" + url

            # Remove any trailing slashes or spaces
            url = url.rstrip('/ ')

            # Log the exact URL we're navigating to
            logger.info(f"Processing as direct URL: {url} (original input: {original_domain})")

            # Double-check that we're using the correct domain for specific sites
            if "redberyltest.in" in original_domain.lower() and "redberyltest.in" not in url.lower():
                # Force the correct domain for redberyltest.in
                url = "https://www.redberyltest.in"
                logger.info(f"Corrected URL to: {url}")

            await self.navigate_to(url)
            return True

        # If nothing else worked, let the user know
        await self.speak("I'm not sure how to process that command. Type 'help' for available commands.")
        return True

    async def help_command(self):
        """Show help information"""
        # Create enhanced help text with voice command information
        enhanced_help_text = HELP_TEXT + """

Voice Command Enhancements:
- 'show history' or 'command history': Display your recent commands
- 'repeat last command' or 'do that again': Repeat your previous command
- 'what can you do': Show this help message
- 'confirm' or 'yes': Confirm a pending action
- 'cancel' or 'no': Cancel a pending action

Voice commands require confirmation for critical actions like exiting the application.
"""

        # Display the enhanced help text
        print("\n" + "=" * 80)
        print("VOICE ASSISTANT HELP")
        print("=" * 80)
        print(enhanced_help_text)
        print("=" * 80)

        # Speak a shorter version
        await self.speak("I've displayed the full help information on screen. You can use voice commands like 'show history', 'repeat last command', and more.")

        return True

    async def switch_recognizer_mode(self, mode):
        """Switch the recognizer between voice and text modes"""
        global input_mode

        if mode not in ["voice", "text"]:
            logger.error(f"Invalid mode: {mode}")
            return False

        try:
            # Recreate the recognizer with the new mode
            if 'create_recognizer' in globals():
                try:
                    logger.info(f"Attempting to switch recognizer to {mode} mode")

                    # If switching to voice mode, first check if we can initialize the voice recognizer
                    if mode == "voice":
                        try:
                            import speech_recognition as sr
                            test_recognizer = sr.Recognizer()
                            with sr.Microphone() as source:
                                test_recognizer.adjust_for_ambient_noise(source, duration=1)
                        except Exception as mic_error:
                            logger.error(f"Microphone test failed: {mic_error}")
                            await self.speak("Cannot switch to voice mode. Microphone not available.")
                            return False

                    # Create new recognizer in the requested mode
                    self.recognizer = create_enhanced_recognizer(
                        config=self.speech_config,
                        mode=mode,
                        speak_func=self.speak
                    )

                    # Update the input mode
                    input_mode = mode

                    # Provide feedback
                    if mode == "voice":
                        await self.speak("Switched to voice mode. You can now speak commands.")
                        display_voice_prompt()
                    else:
                        await self.speak("Switched to text mode. You can now type commands.")
                        display_prompt()

                    logger.info(f"Successfully switched recognizer to {mode} mode")
                    return True

                except Exception as e:
                    logger.error(f"Error switching to {mode} mode: {e}")
                    await self.speak(f"Failed to switch to {mode} mode. Staying in {input_mode} mode.")
                    return False
            else:
                logger.error("Speech recognizer creation function not found")
                return False

        except Exception as e:
            logger.error(f"Error in switch_recognizer_mode: {e}")
            return False

    async def login_with_credentials(self, email, password):
        """Log in with email and password"""
        try:
            print(f"Attempting to log in with email: {email}")

            # Check if we're on a login page
            try:
                current_url = self.page.url
                print(f"Current URL: {current_url}")

                # If we're not on a login page, try to navigate to the signin page
                if not ('signin' in current_url.lower() or 'login' in current_url.lower()):
                    print("Not on a login page. Navigating to signin page first...")
                    # Navigate to the correct signin URL
                    try:
                        await self.page.goto("https://www.redberyltest.in/#/signin", wait_until="networkidle", timeout=20000)
                        print("Navigated to signin page")
                        # Wait for the page to load
                        await asyncio.sleep(20)
                    except Exception as e:
                        print(f"Failed to navigate to signin page: {e}")
                        # Try to find and click login button if needed
                        print("Trying to find login option...")
                        login_selectors = [
                            'a:has-text("Login")',
                            'a:has-text("Sign in")',
                            'button:has-text("Login")',
                            'button:has-text("Sign in")',
                            '.login-button',
                            '.signin-button',
                            'button.blue-btnnn:has-text("Login/Register")',
                            'a:has-text("Login/Register")'
                        ]

                        for selector in login_selectors:
                            try:
                                if await self.page.locator(selector).count() > 0:
                                    await self.page.locator(selector).first.click()
                                    print("Found and clicked login option. Waiting for form to appear...")
                                    await asyncio.sleep(5)  # Wait for form to appear
                                    break
                            except Exception as e:
                                print(f"Error with login selector {selector}: {e}")
                                continue
            except Exception as e:
                print(f"Error checking URL: {e}")
                # Continue anyway

            # Perform DOM inspection to find form elements
            form_elements = await self._check_for_input_fields()
            print(f"DOM inspection results: {form_elements}")

            # Define specific selectors for known form elements
            specific_email_selector = '#floating_outlined3'
            specific_password_selector = '#floating_outlined15'
            specific_button_selector = '#signInButton'

            if form_elements.get('hasEmailField') or form_elements.get('hasPasswordField'):
                try:
                    # Use JavaScript to fill the form directly
                    print("Using direct DOM manipulation to fill login form...")
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
                        print("Login form submitted using direct DOM manipulation")

                        # Wait for login process to complete
                        print("Waiting for login process to complete...")
                        try:
                            # Wait for navigation or network idle
                            await self.page.wait_for_load_state("networkidle", timeout=20000)
                            print("Page loaded after login")

                            # Additional wait to ensure everything is fully loaded
                            await asyncio.sleep(5)
                        except Exception as e:
                            print(f"Error waiting after form submission: {e}")
                            # Continue anyway

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
                # Get page context
                context = await self._get_page_context()

                # Get LLM-generated selectors
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
                # Get page context
                context = await self._get_page_context()

                # Get LLM-generated selectors
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
                    # Get page context
                    context = await self._get_page_context()

                    # Get LLM-generated selectors
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
                    print("Filled login details but couldn't find login button")
                    return False

                # Wait for login process to complete and next page to load
                print("Waiting for login process to complete...")
                try:
                    # Wait for navigation or network idle
                    await self.page.wait_for_load_state("networkidle", timeout=20000)
                    print("Page loaded after login")

                    # Additional wait to ensure everything is fully loaded
                    await asyncio.sleep(5)

                    # Check if we're still on the login page
                    current_url = self.page.url
                    if 'signin' in current_url.lower() or 'login' in current_url.lower():
                        print("Still on login page after clicking login button. Login might have failed.")

                        # Check for error messages
                        error_message = await self._check_for_login_errors()
                        if error_message:
                            print(f"Login error detected: {error_message}")
                            return False
                    else:
                        print("Successfully navigated away from login page")
                except Exception as e:
                    print(f"Error waiting for login completion: {e}")
                    # Continue anyway, as the login might still have succeeded

                return True
            else:
                if not email_found:
                    print("Could not find element to Enter email address")
                if not password_found:
                    print("Could not find element to Enter password")
                return False

        except Exception as e:
            print(f"Error during login: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _retry_type(self, selector, text, field_name, max_retries=3, timeout=10000):
        """Retry typing into a field multiple times"""
        for attempt in range(max_retries):
            try:
                print(f"Typing attempt {attempt+1} for {field_name}")
                await self.page.locator(selector).first.fill(text, timeout=timeout)
                print(f"Successfully typed into {field_name}")
                return True
            except Exception as e:
                print(f"Error typing into {field_name} (attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    # Wait a bit before retrying
                    await asyncio.sleep(1)
                else:
                    print(f"Failed to type into {field_name} after {max_retries} attempts")
                    raise

    async def _retry_click(self, selector, element_name, max_retries=3, timeout=10000):
        """Retry clicking an element multiple times"""
        for attempt in range(max_retries):
            try:
                print(f"Click attempt {attempt+1} for {element_name}")
                await self.page.locator(selector).first.click(timeout=timeout)
                print(f"Successfully clicked {element_name}")
                return True
            except Exception as e:
                print(f"Error clicking {element_name} (attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    # Wait a bit before retrying
                    await asyncio.sleep(1)
                else:
                    print(f"Failed to click {element_name} after {max_retries} attempts")
                    raise

    async def _check_for_login_errors(self):
        """Check for login error messages on the page"""
        try:
            # Use JavaScript to check for error messages
            error_message = await self.page.evaluate("""() => {
                // Common error message selectors
                const errorSelectors = [
                    '.error-message',
                    '.alert-danger',
                    '.text-danger',
                    '.validation-error',
                    '.form-error',
                    '[role="alert"]',
                    '.toast-error',
                    '.notification-error',
                    '.error',
                    '.invalid-feedback'
                ];

                // Check each selector
                for (const selector of errorSelectors) {
                    const elements = document.querySelectorAll(selector);
                    for (const element of elements) {
                        if (element.offsetParent !== null) { // Check if visible
                            const text = element.textContent.trim();
                            if (text) {
                                return text;
                            }
                        }
                    }
                }

                // Check for any element with error-related text
                const errorTexts = ['invalid', 'incorrect', 'failed', 'wrong', 'error', 'not recognized'];
                const allElements = document.querySelectorAll('*');

                for (const element of allElements) {
                    if (element.offsetParent !== null) { // Check if visible
                        const text = element.textContent.trim().toLowerCase();
                        if (text && errorTexts.some(errorText => text.includes(errorText))) {
                            return element.textContent.trim();
                        }
                    }
                }

                return null;
            }""")

            return error_message
        except Exception as e:
            print(f"Error checking for login errors: {e}")
            return None

    async def _get_llm_selectors(self, task, context=None):
        """Generate selectors for a task based on page context"""
        try:
            # Log context information for debugging if available
            if context:
                # Make sure context is a dictionary before trying to access its properties
                if isinstance(context, dict):
                    print(f"Context URL: {context.get('url', 'N/A')}")
                    print(f"Context title: {context.get('title', 'N/A')}")
                    print(f"Input fields found: {len(context.get('input_fields', []))}")
                    print(f"Buttons found: {len(context.get('buttons', []))}")
                else:
                    print(f"Context is not a dictionary: {type(context)}")

            # Use predefined selectors based on the task
            if "email" in task or "username" in task:
                print(f"Using predefined EMAIL_SELECTORS")
                return EMAIL_SELECTORS.copy()
            elif "password" in task:
                print(f"Using predefined PASSWORD_SELECTORS")
                return PASSWORD_SELECTORS.copy()
            elif "login" in task or "sign in" in task or "submit" in task or "button" in task:
                print(f"Using predefined LOGIN_BUTTON_SELECTORS")
                return LOGIN_BUTTON_SELECTORS.copy()
            else:
                # Generate generic selectors based on the task
                element_name = task.lower().replace("find ", "").replace("click ", "").strip()
                print(f"Generating generic selectors for: {element_name}")

                # Generate selectors for the element
                selectors = [
                    f'button:has-text("{element_name}")',
                    f'a:has-text("{element_name}")',
                    f'[role="button"]:has-text("{element_name}")',
                    f'[role="tab"]:has-text("{element_name}")',
                    f'.p-tabview-nav li:has-text("{element_name}")',
                    f'.nav-item:has-text("{element_name}")',
                    f'.tab:has-text("{element_name}")',
                    f'#{element_name.replace(" ", "-")}-tab',
                    f'.{element_name.replace(" ", "-")}-tab',
                    f'[data-tab="{element_name.replace(" ", "-")}"]',
                    f'[data-testid="{element_name.replace(" ", "-")}-tab"]',
                    f'li:has-text("{element_name}")',
                    f'div:has-text("{element_name}")'
                ]

                return selectors

        except Exception as e:
            print(f"Error generating selectors: {e}")
            return []

    async def click_order_with_id(self, order_id, llm_response=None):
        """Click on an order with a specific ID"""
        try:
            print(f"Looking for order with ID {order_id}...")

            # Generate selectors for the order based on the specific UI structure
            selectors = [
                # Specific selectors for the observed UI structure
                f'p.srch-cand-text1:has-text("ORDER-ID {order_id}")',
                f'p:has-text("ORDER-ID {order_id}")',
                f'tr:has-text("ORDER-ID {order_id}")',
                f'div.srch-cand-card:has-text("ORDER-ID {order_id}")',
                f'tr.p-selectable-row:has-text("{order_id}")',

                # More specific selectors for the exact text
                f'p:text("ORDER-ID {order_id}")',
                f'p:text-is("ORDER-ID {order_id}")',
                f'p:text-matches("ORDER-ID\\s+{order_id}")',

                # Target the row containing the order ID
                f'tr:has(p:has-text("ORDER-ID {order_id}"))',
                f'tr:has(div:has-text("ORDER-ID {order_id}"))',
                f'tr:has(p:text("ORDER-ID {order_id}"))',

                # Target the clickable card
                f'div.srch-cand-card:has(p:has-text("ORDER-ID {order_id}"))',
                f'div.srch-cand-card:has(p:text("ORDER-ID {order_id}"))',

                # Generic selectors as fallbacks
                f'#order-{order_id}',
                f'.order-row[data-order-id="{order_id}"]',
                f'tr[data-order-id="{order_id}"]',
                f'div[data-order-id="{order_id}"]',
                f'li[data-order-id="{order_id}"]',
                f'*[id*="order"][id*="{order_id}"]',
                f'*[data-id="{order_id}"]',
                f'*[data-order="{order_id}"]',
                f'*[data-orderid="{order_id}"]',
                f'*[data-order-id="{order_id}"]',
                f'*:has-text("Order #{order_id}")',
                f'*:has-text("Order ID: {order_id}")',
                f'*:has-text("Order: {order_id}")',
                f'tr:has-text("{order_id}")',
                f'td:has-text("{order_id}")',
                f'[id="{order_id}"]',
                f'[data-id="{order_id}"]',
                f'[data-testid="order-{order_id}"]',
                f'[data-order="{order_id}"]',
                f'[data-orderid="{order_id}"]',
                f'[data-order-id="{order_id}"]',
                f'a:has-text("{order_id}")',
                f'button:has-text("{order_id}")',
                f'div:has-text("{order_id}")',
                f'span:has-text("{order_id}")',
                f'p:has-text("{order_id}")',
                f'*:has-text("{order_id}")'
            ]

            # If LLM response is provided, try to parse it for additional selectors
            if llm_response:
                parsed_selectors = self._parse_llm_selectors(llm_response)
                if parsed_selectors:
                    print(f"Using {len(parsed_selectors)} parsed selectors from LLM response")
                    selectors = parsed_selectors + selectors

            # Try each selector
            for selector in selectors:
                try:
                    print(f"Trying order selector: {selector}")
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_click(selector, f"order with ID {order_id}")
                        print(f"Clicked order with ID {order_id} using selector: {selector}")

                        # Wait for any content to load
                        await self.page.wait_for_timeout(5000)
                        return True
                except Exception as e:
                    print(f"Error with order selector {selector}: {e}")
                    continue

            # If no selector worked, try using JavaScript
            print("Trying JavaScript approach for finding and clicking the order...")
            from webassist.voice_assistant.constants import JS_FIND_ORDER
            js_result = await self.page.evaluate(JS_FIND_ORDER, order_id)

            if js_result:
                print(f"Clicked order with ID {order_id} using JavaScript")
                await self.page.wait_for_timeout(5000)
                return True

            print(f"Could not find order with ID {order_id}")
            return False
        except Exception as e:
            print(f"Error clicking order with ID {order_id}: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def fill_form_field(self, field_name, value, llm_response=None):
        """Fill a form field with the given value"""
        try:
            print(f"Looking for {field_name} field to enter {value}...")

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

            # If LLM response is provided, try to parse it for additional selectors
            if llm_response:
                parsed_selectors = self._parse_llm_selectors(llm_response)
                if parsed_selectors:
                    print(f"Using {len(parsed_selectors)} parsed selectors from LLM response")
                    selectors = parsed_selectors + selectors

            # Try each selector
            for selector in selectors:
                try:
                    print(f"Trying field selector: {selector}")
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_type(selector, value, f"{field_name} field")
                        print(f"Filled {field_name} field with '{value}' using selector: {selector}")
                        return True
                except Exception as e:
                    print(f"Error with field selector {selector}: {e}")
                    continue

            # If no selector worked, try using JavaScript
            print("Trying JavaScript approach for finding and filling the field...")
            js_result = await self.page.evaluate(f"""
                (fieldName, value) => {{
                    try {{
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
            """, field_name, value)

            if js_result:
                print(f"Filled {field_name} field with '{value}' using JavaScript")
                return True

            print(f"Could not find {field_name} field")
            return False
        except Exception as e:
            print(f"Error filling {field_name} field: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def click_element(self, element_name, llm_response=None):
        """Click on an element with the given name"""
        try:
            print(f"Looking for element: {element_name}...")

            # Generate selectors for the element
            selectors = [
                f'button:has-text("{element_name}")',
                f'a:has-text("{element_name}")',
                f'[role="button"]:has-text("{element_name}")',
                f'[role="tab"]:has-text("{element_name}")',
                f'.p-tabview-nav li:has-text("{element_name}")',
                f'.nav-item:has-text("{element_name}")',
                f'.tab:has-text("{element_name}")',
                f'#{element_name.replace(" ", "-")}',
                f'.{element_name.replace(" ", "-")}',
                f'[data-testid="{element_name.replace(" ", "-")}"]',
                f'li:has-text("{element_name}")',
                f'div:has-text("{element_name}")'
            ]

            # If LLM response is provided, try to parse it for additional selectors
            if llm_response:
                parsed_selectors = self._parse_llm_selectors(llm_response)
                if parsed_selectors:
                    print(f"Using {len(parsed_selectors)} parsed selectors from LLM response")
                    selectors = parsed_selectors + selectors

            # Try each selector
            for selector in selectors:
                try:
                    print(f"Trying element selector: {selector}")
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_click(selector, element_name)
                        print(f"Clicked {element_name} using selector: {selector}")

                        # Wait for any content to load
                        await self.page.wait_for_timeout(5000)
                        return True
                except Exception as e:
                    print(f"Error with element selector {selector}: {e}")
                    continue

            # If no selector worked, try using JavaScript
            print("Trying JavaScript approach for finding and clicking the element...")
            js_result = await self.page.evaluate(f"""
                (elementName) => {{
                    try {{
                        console.log("Looking for element: " + elementName);

                        // Try to find elements with matching text
                        const elements = Array.from(document.querySelectorAll('*'));
                        for (const el of elements) {{
                            if (el.textContent.toLowerCase().includes(elementName.toLowerCase()) &&
                                (el.tagName === 'BUTTON' ||
                                 el.tagName === 'A' ||
                                 el.tagName === 'DIV' ||
                                 el.tagName === 'LI' ||
                                 el.getAttribute('role') === 'button' ||
                                 el.getAttribute('role') === 'tab' ||
                                 el.onclick)) {{
                                console.log("Found element: ", el);
                                el.click();
                                console.log("Clicked element");
                                return true;
                            }}
                        }}

                        console.log("Could not find element");
                        return false;
                    }} catch (error) {{
                        console.error("Error finding/clicking element: ", error);
                        return false;
                    }}
                }}
            """, element_name)

            if js_result:
                print(f"Clicked {element_name} using JavaScript")
                await self.page.wait_for_timeout(5000)
                return True

            print(f"Could not find element: {element_name}")
            return False
        except Exception as e:
            print(f"Error clicking element {element_name}: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _get_llm_selectors_with_parsing(self, task, context=None, llm_response=None):
        """Generate selectors for a task based on page context and parse LLM response if provided"""
        try:
            # If LLM response is provided, try to parse it
            if llm_response:
                print("Parsing LLM response for selectors...")
                parsed_selectors = self._parse_llm_selectors(llm_response)
                if parsed_selectors:
                    print(f"Using {len(parsed_selectors)} parsed selectors from LLM response")
                    return parsed_selectors
                else:
                    print("Failed to parse selectors from LLM response, falling back to predefined selectors")

            # Fall back to regular selector generation
            return await self._get_llm_selectors(task, context)
        except Exception as e:
            print(f"Error in _get_llm_selectors_with_parsing: {e}")
            import traceback
            traceback.print_exc()
            # Fall back to regular selector generation
            return await self._get_llm_selectors(task, context)

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

            # Get page title and URL safely
            try:
                page_title = await self.page.title()
            except Exception as e:
                print(f"Error getting page title: {e}")
                page_title = "Unknown"

            try:
                page_url = self.page.url
            except Exception as e:
                print(f"Error getting page URL: {e}")
                page_url = "Unknown"

            # Get input fields
            input_fields = []
            try:
                inputs = await self.page.locator("input:visible, textarea:visible, select:visible").all()

                for i in range(min(len(inputs), 10)):
                    try:
                        field = inputs[i]
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
                        print(f"Error getting field info: {e}")
                        continue
            except Exception as e:
                print(f"Error getting input fields: {e}")

            # Get buttons
            buttons = []
            try:
                button_elements = await self.page.locator(
                    "button:visible, [role='button']:visible, input[type='submit']:visible, input[type='button']:visible"
                ).all()

                for i in range(min(len(button_elements), 10)):
                    try:
                        button = button_elements[i]
                        try:
                            text = await button.inner_text()
                        except Exception:
                            text = ""
                        button_info = {
                            "text": text.strip(),
                            "id": await button.evaluate("el => el.id || ''"),
                            "class": await button.evaluate("el => el.className || ''"),
                            "type": await button.evaluate("el => el.type || ''")
                        }
                        buttons.append(button_info)
                    except Exception as e:
                        print(f"Error getting button info: {e}")
                        continue
            except Exception as e:
                print(f"Error getting buttons: {e}")

            # Get tabs and menu items
            tabs = []
            try:
                tab_elements = await self.page.locator(
                    ".p-tabview-nav li, [role='tab'], .nav-item, .tab"
                ).all()

                for i in range(min(len(tab_elements), 10)):
                    try:
                        tab = tab_elements[i]
                        try:
                            text = await tab.inner_text()
                        except Exception:
                            text = ""
                        tab_info = {
                            "text": text.strip(),
                            "id": await tab.evaluate("el => el.id || ''"),
                            "class": await tab.evaluate("el => el.className || ''")
                        }
                        tabs.append(tab_info)
                    except Exception as e:
                        print(f"Error getting tab info: {e}")
                        continue
            except Exception as e:
                print(f"Error getting tabs: {e}")

            # Perform DOM inspection to find form elements
            try:
                form_elements = await self._check_for_input_fields()
            except Exception as e:
                print(f"Error checking for input fields: {e}")
                form_elements = {}

            # Get page HTML
            try:
                html = await self.page.evaluate("() => document.body.innerHTML")
            except Exception as e:
                print(f"Error getting page HTML: {e}")
                html = ""

            # Get page text
            try:
                page_text = await self.page.locator("body").inner_text()
            except Exception as e:
                print(f"Error getting page text: {e}")
                page_text = ""

            # Return the context
            return {
                "title": page_title,
                "url": page_url,
                "text": page_text,
                "html": self._filter_html(html[:4000]) if html else "",
                "input_fields": input_fields,
                "buttons": buttons,
                "tabs": tabs,
                "form_elements": form_elements
            }
        except Exception as e:
            print(f"Error getting page context: {e}")
            import traceback
            traceback.print_exc()
            return {
                "title": "Unknown",
                "url": "Unknown",
                "text": "",
                "html": "",
                "input_fields": [],
                "buttons": [],
                "tabs": [],
                "form_elements": {}
            }

    def _filter_html(self, html):
        """Filter HTML to make it more readable"""
        try:
            # Add line breaks after opening tags for better readability
            filtered_html = re.sub(
                r'<(input|button|a|form|select|textarea|div|ul|li)[^>]*>',
                lambda m: m.group(0) + '\n',
                html
            )
            return filtered_html[:3000]
        except Exception as e:
            print(f"Error filtering HTML: {e}")
            return html[:3000]

    async def _check_for_input_fields(self):
        """Check if there are any input fields on the page"""
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

    async def fill_email_field(self, email):
        """Fill the email field"""
        try:
            print(f"Attempting to fill email field with: {email}")

            # First check if we're on a login page
            try:
                current_url = self.page.url
                print(f"Current URL: {current_url}")

                # If we're not on a login page, try to navigate directly to the login page
                if not any(term in current_url.lower() for term in ['login', 'signin', 'sign-in', 'auth', '#/signin']):
                    print("Not on a login page. Trying to navigate directly to login page...")
                    try:
                        # Navigate directly to the login page
                        await self.page.goto(LOGIN_URL, wait_until="networkidle", timeout=NAVIGATION_TIMEOUT)
                        print("Navigated to login page")
                        # Wait for the page to load
                        await self.page.wait_for_timeout(PAGE_LOAD_WAIT)

                        # Check if we're now on a login page
                        current_url = self.page.url
                        if any(term in current_url.lower() for term in ['login', 'signin', 'sign-in', 'auth', '#/signin']):
                            print(f"Successfully navigated to login page: {current_url}")
                        else:
                            print(f"Navigation didn't reach login page. Current URL: {current_url}")
                    except Exception as e:
                        print(f"Error navigating to login page: {e}")
                        # If direct navigation fails, try to find and click a login link
                        print("Direct navigation failed. Looking for login link...")
                        login_link_clicked = await self.find_and_click_login_link()
                        if login_link_clicked:
                            # Wait for navigation and page to load
                            try:
                                # Wait for network idle
                                await self.page.wait_for_load_state("networkidle", timeout=20000)
                                print("Network activity completed")

                                # Additional wait to ensure form is visible
                                await asyncio.sleep(5)

                                # Check if we're now on a login page
                                current_url = self.page.url
                                print(f"After waiting, current URL: {current_url}")
                            except Exception as e:
                                print(f"Error waiting for page to load: {e}")
                        else:
                            print("Could not find login link. Trying to find login form directly...")
            except Exception as e:
                print(f"Error checking URL: {e}")
                # Continue anyway

            # Wait a bit longer for the page to fully load
            print("Waiting for page to fully load...")
            await self.page.wait_for_timeout(PAGE_LOAD_WAIT)

            # Try common email field selectors
            selectors = [
                "#email",
                "#username",
                "input[type='email']",
                "input[name='email']",
                "input[name='username']",
                "#floating_outlined3",  # Specific selector from user's requirements
                "input.email",
                "input.username",
                "input[placeholder*='email' i]",
                "input[placeholder*='username' i]",
                "input[aria-label*='email' i]",
                "input[aria-label*='username' i]"
            ]

            # Try each selector
            for selector in selectors:
                try:
                    print(f"Trying selector: {selector}")
                    # Check if the selector exists
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.fill(email)
                        print(f"Filled email field with selector: {selector}")
                        return True
                except Exception as e:
                    print(f"Error with selector {selector}: {e}")
                    continue

            # Try finding any visible input field
            print("Trying to find any visible input field...")
            try:
                # Get all input fields
                input_fields = await self.page.query_selector_all("input:not([type='hidden'])")

                # Try to find the first visible input field
                for input_field in input_fields:
                    try:
                        # Check if the field is visible
                        is_visible = await input_field.is_visible()
                        if is_visible:
                            await input_field.fill(email)
                            print("Filled first visible input field")
                            return True
                    except Exception as e:
                        print(f"Error checking visibility: {e}")
                        continue
            except Exception as e:
                print(f"Error finding visible input fields: {e}")

            # If no selector worked, try using JavaScript with more aggressive approach
            print("Trying JavaScript approach...")
            js_result = await self.page.evaluate(JS_FILL_EMAIL, email)

            if js_result:
                print("Filled email field using JavaScript")
                return True

            # If we still can't find the email field, try clicking the login button first
            print("Could not find email field. Trying to click login button first...")
            login_button_clicked = await self.click_login_button()

            if login_button_clicked:
                # Wait for the form to appear
                await asyncio.sleep(NAVIGATION_WAIT)

                # Try again to fill the email field
                print("Trying again to fill email field after clicking login button...")
                return await self.fill_email_field(email)

            # Last resort: Try to get all form elements and print them for debugging
            print("Last resort: Analyzing page for form elements...")
            form_elements = await self.page.evaluate("""
                () => {
                    const forms = Array.from(document.querySelectorAll('form'));
                    const inputs = Array.from(document.querySelectorAll('input'));

                    return {
                        formCount: forms.length,
                        inputCount: inputs.length,
                        inputTypes: inputs.map(i => i.type),
                        inputNames: inputs.map(i => i.name),
                        inputIds: inputs.map(i => i.id),
                        inputPlaceholders: inputs.map(i => i.placeholder)
                    };
                }
            """)

            print(f"Form analysis: {form_elements}")

            print("Could not find email field")
            return False

        except Exception as e:
            print(f"Error filling email field: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def fill_password_field(self, password):
        """Fill the password field"""
        try:
            print(f"Attempting to fill password field")

            # Try common password field selectors
            selectors = [
                "#password",
                "input[type='password']",
                "input[name='password']",
                "#floating_outlined15",  # Specific selector from user's requirements
                "input.password",
                "input[placeholder*='password' i]",
                "input[aria-label*='password' i]"
            ]

            # Try each selector
            for selector in selectors:
                try:
                    print(f"Trying selector: {selector}")
                    # Check if the selector exists
                    element = await self.page.query_selector(selector)
                    if element:
                        await element.fill(password)
                        print(f"Filled password field with selector: {selector}")
                        return True
                except Exception as e:
                    print(f"Error with selector {selector}: {e}")
                    continue

            # Try finding any password input field
            print("Trying to find any password input field...")
            try:
                # Get all password fields
                password_fields = await self.page.query_selector_all("input[type='password']")

                # Try to fill the first password field
                if len(password_fields) > 0:
                    await password_fields[0].fill(password)
                    print("Filled first password field")
                    return True
            except Exception as e:
                print(f"Error finding password fields: {e}")

            # If no selector worked, try using JavaScript with more aggressive approach
            print("Trying JavaScript approach...")
            js_result = await self.page.evaluate(f"""
                (password) => {{
                    // Try to find password input by various attributes
                    let passwordInputs = Array.from(document.querySelectorAll('input')).filter(el =>
                        el.type === 'password' ||
                        el.name === 'password' ||
                        el.id === 'password' ||
                        el.id === 'floating_outlined15' ||
                        (el.placeholder && el.placeholder.toLowerCase().includes('password')) ||
                        (el.labels && Array.from(el.labels).some(label => label.textContent.toLowerCase().includes('password')))
                    );

                    // If no password inputs found, try any input after the email field
                    if (passwordInputs.length === 0) {{
                        const emailInput = Array.from(document.querySelectorAll('input')).find(el =>
                            el.type === 'email' ||
                            el.name === 'email' ||
                            el.id === 'email'
                        );

                        if (emailInput) {{
                            const allInputs = Array.from(document.querySelectorAll('input'));
                            const emailIndex = allInputs.indexOf(emailInput);

                            if (emailIndex >= 0 && emailIndex < allInputs.length - 1) {{
                                passwordInputs = [allInputs[emailIndex + 1]];
                            }}
                        }}
                    }}

                    // If still no inputs found, try any input that's not the first one
                    if (passwordInputs.length === 0) {{
                        const allInputs = Array.from(document.querySelectorAll('input')).filter(el =>
                            el.type !== 'hidden' && el.type !== 'submit' && el.type !== 'button'
                        );

                        if (allInputs.length > 1) {{
                            passwordInputs = [allInputs[1]];
                        }}
                    }}

                    if (passwordInputs.length > 0) {{
                        passwordInputs[0].value = password;
                        passwordInputs[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
                        passwordInputs[0].dispatchEvent(new Event('change', {{ bubbles: true }}));
                        console.log('Filled password with JavaScript: ' + passwordInputs[0].outerHTML);
                        return true;
                    }}

                    console.log('No suitable password field found');
                    return false;
                }}
            """, password)

            if js_result:
                print("Filled password field using JavaScript")
                return True

            return False

        except Exception as e:
            print(f"Error filling password field: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _parse_llm_selectors(self, response_text):
        """Parse selectors from LLM response text that might be in JSON format with markdown code blocks"""
        try:
            # Clean up the response text
            # First, check if the response is already a valid JSON array string
            if response_text.strip().startswith('[') and response_text.strip().endswith(']'):
                try:
                    # Try to parse as JSON directly
                    selectors = json.loads(response_text)
                    print(f"Successfully parsed {len(selectors)} selectors from direct JSON array")
                    # Filter out invalid selectors
                    selectors = self._filter_valid_selectors(selectors)
                    print(f"After filtering, {len(selectors)} valid selectors remain")
                    return selectors
                except json.JSONDecodeError as e:
                    print(f"Error parsing direct JSON array: {e}")

            # Next, try to extract JSON content from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response_text, re.DOTALL)
            if json_match:
                json_content = json_match.group(1)
                try:
                    # Try to parse as JSON
                    selectors = json.loads(json_content)
                    print(f"Successfully parsed {len(selectors)} selectors from JSON code block")
                    # Filter out invalid selectors
                    selectors = self._filter_valid_selectors(selectors)
                    print(f"After filtering, {len(selectors)} valid selectors remain")
                    return selectors
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON from code block: {e}")

            # If the response is a list of strings (like from splitlines()), try to extract the JSON array
            if isinstance(response_text, list) or '\n' in response_text:
                lines = response_text if isinstance(response_text, list) else response_text.splitlines()
                # Look for lines that might be part of a JSON array
                json_lines = []
                in_json_block = False
                for line in lines:
                    line = line.strip()
                    if line == '```json' or line == '```' or line == '[':
                        in_json_block = True
                        json_lines = []
                    elif line == '```' or line == ']':
                        in_json_block = False
                        break
                    elif in_json_block and line:
                        # Clean up the line - remove trailing commas and comments
                        line = line.split('//')[0].strip()  # Remove comments

                        # Extract quoted strings from the line
                        quoted_matches = re.findall(r'"([^"]+)"', line)
                        for quoted_string in quoted_matches:
                            # Check if it looks like a CSS selector
                            if any(char in quoted_string for char in ['#', '.', '[', '>', '*', ':', '~']):
                                json_lines.append(quoted_string)

                # If we found any selectors in the JSON block
                if json_lines:
                    print(f"Extracted {len(json_lines)} selectors from JSON block")
                    # Filter out invalid selectors
                    selectors = self._filter_valid_selectors(json_lines)
                    print(f"After filtering, {len(selectors)} valid selectors remain")
                    return selectors

            # Try to parse the entire response as JSON
            try:
                # Clean up the response text - remove any non-JSON content
                cleaned_response = response_text.strip() if isinstance(response_text, str) else str(response_text)
                # If the response starts with a JSON object that has an "actions" field, it might be a Gemini response
                if ('"actions"' in cleaned_response or "'actions'" in cleaned_response) and (cleaned_response.startswith('{') or cleaned_response.startswith('```')):
                    try:
                        # Clean up the response if it's wrapped in code blocks
                        if cleaned_response.startswith('```'):
                            # Extract the JSON part
                            json_match = re.search(r'```(?:json)?\s*({.*?})(?:\s*```)?', cleaned_response, re.DOTALL)
                            if json_match:
                                cleaned_response = json_match.group(1)

                        # Parse the JSON object
                        json_obj = json.loads(cleaned_response)
                        # Extract selectors from the actions array
                        if 'actions' in json_obj and isinstance(json_obj['actions'], list):
                            selectors = []
                            for action in json_obj['actions']:
                                if 'selector' in action:
                                    selectors.append(action['selector'])
                                if 'fallback_selectors' in action and isinstance(action['fallback_selectors'], list):
                                    selectors.extend(action['fallback_selectors'])
                                # Add more selectors for order IDs
                                if 'purpose' in action and 'order' in action['purpose'] and 'id' in action['purpose']:
                                    # Try to extract the order ID from the purpose
                                    order_id_match = re.search(r'order\s+(?:with\s+)?(?:id\s+)?(\d+)', action['purpose'])
                                    if order_id_match:
                                        order_id = order_id_match.group(1)
                                        # Add specific selectors for this order ID
                                        selectors.append(f'p.srch-cand-text1:has-text("ORDER-ID {order_id}")')
                                        selectors.append(f'tr:has-text("ORDER-ID {order_id}")')
                                        selectors.append(f'div.srch-cand-card:has-text("ORDER-ID {order_id}")')

                            if selectors:
                                print(f"Extracted {len(selectors)} selectors from actions array")
                                # Filter out invalid selectors
                                selectors = self._filter_valid_selectors(selectors)
                                print(f"After filtering, {len(selectors)} valid selectors remain")
                                return selectors
                    except Exception as e:
                        print(f"Error extracting selectors from actions: {e}")
                        import traceback
                        traceback.print_exc()
                        # Continue with the regular extraction

                    # If we couldn't extract selectors from the actions, try to extract a JSON array
                    array_match = re.search(r'\[.*?\]', cleaned_response, re.DOTALL)
                    if array_match:
                        cleaned_response = array_match.group(0)

                # Try to parse as JSON
                selectors = json.loads(cleaned_response)
                print(f"Successfully parsed {len(selectors)} selectors from cleaned JSON")
                # Filter out invalid selectors
                selectors = self._filter_valid_selectors(selectors)
                print(f"After filtering, {len(selectors)} valid selectors remain")
                return selectors
            except json.JSONDecodeError as e:
                print(f"Error parsing cleaned JSON: {e}")

            # If JSON parsing failed, try to extract selectors directly
            # Look for patterns like ["selector1", "selector2", ...]
            selector_match = re.search(r'\[\s*"([^"]+)"(?:\s*,\s*"([^"]+)")*\s*\]', response_text)
            if selector_match:
                selectors = [group for group in selector_match.groups() if group]
                print(f"Extracted {len(selectors)} selectors from regex match")
                # Filter out invalid selectors
                selectors = self._filter_valid_selectors(selectors)
                print(f"After filtering, {len(selectors)} valid selectors remain")
                return selectors

            # If all else fails, split by lines and look for quoted strings
            lines = response_text.split('\n')
            selectors = []
            for line in lines:
                # Extract quoted strings
                quoted_matches = re.findall(r'"([^"]+)"', line)
                selectors.extend(quoted_matches)

            if selectors:
                print(f"Extracted {len(selectors)} selectors from line-by-line parsing")
                # Filter out invalid selectors
                selectors = self._filter_valid_selectors(selectors)
                print(f"After filtering, {len(selectors)} valid selectors remain")
                return selectors

            # If we still couldn't extract selectors, return an empty list
            print("Could not extract any selectors from LLM response")
            return []
        except Exception as e:
            print(f"Error parsing LLM selectors: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _filter_valid_selectors(self, selectors):
        """Filter out invalid CSS selectors"""
        valid_selectors = []
        for selector in selectors:
            # Skip if not a string
            if not isinstance(selector, str):
                continue

            # Skip empty selectors
            if not selector.strip():
                continue

            # Skip selectors with invalid characters
            if re.search(r'[^\w\s\-_\[\]\(\)\.:#="\'\*>~+,]', selector):
                print(f"Skipping selector with invalid characters: {selector}")
                continue

            # Skip selectors that start with a number (invalid in CSS)
            if re.match(r'^\d', selector):
                print(f"Skipping selector that starts with a number: {selector}")
                continue

            # Skip selectors with unbalanced brackets
            if selector.count('[') != selector.count(']') or selector.count('(') != selector.count(')'):
                print(f"Skipping selector with unbalanced brackets: {selector}")
                continue

            # Skip selectors with unbalanced quotes
            if selector.count('"') % 2 != 0 or selector.count("'") % 2 != 0:
                print(f"Skipping selector with unbalanced quotes: {selector}")
                continue

            # Fix common issues with ID selectors
            if re.match(r'^#\d', selector):
                # IDs can't start with a number in CSS, so add a prefix
                fixed_selector = f'[id="{selector[1:]}"]'
                print(f"Fixed invalid ID selector: {selector} -> {fixed_selector}")
                valid_selectors.append(fixed_selector)
                continue

            # Fix tr#123 type selectors (invalid in CSS)
            if re.search(r'tr#\d+', selector):
                # Convert to a valid selector
                fixed_selector = selector.replace('tr#', 'tr[id="')
                fixed_selector = fixed_selector + '"]'
                print(f"Fixed invalid tr# selector: {selector} -> {fixed_selector}")
                valid_selectors.append(fixed_selector)
                continue

            # If we got here, the selector is probably valid
            valid_selectors.append(selector)

        return valid_selectors

    async def click_login_button(self, llm_response=None):
        """Click the login button"""
        try:
            print("Looking for login button...")

            # First check if we're on a login page
            try:
                current_url = self.page.url
                print(f"Current URL: {current_url}")

                # If we're not on a login page, try to find and click a login link first
                if not any(term in current_url.lower() for term in ['login', 'signin', 'sign-in', 'auth']):
                    print("Not on a login page. Looking for login link...")
                    await self.find_and_click_login_link()
                    # Wait for navigation
                    await asyncio.sleep(NAVIGATION_WAIT)
            except Exception as e:
                print(f"Error checking URL: {e}")
                # Continue anyway

            # Get selectors from LLM response if available
            if llm_response:
                print("🔍 Selector generation response:")
                # Split the response into lines without using backslashes in f-strings
                response_lines = llm_response.splitlines()
                print(" " + str(response_lines))

                # Parse the LLM response to get selectors
                parsed_selectors = self._parse_llm_selectors(llm_response)
                if parsed_selectors:
                    print(f"Using {len(parsed_selectors)} parsed selectors from LLM response")

                    # Try each parsed selector
                    for selector in parsed_selectors:
                        try:
                            print(f"Trying specific selector: {selector}")
                            # Check if the selector exists
                            count = await self.page.locator(selector).count()
                            if count > 0:
                                await self.page.locator(selector).first.click()
                                print(f"Clicked login button with specific selector: {selector}")
                                return True
                        except Exception as e:
                            print(f"Error with specific selector {selector}: {e}")
                            continue
                else:
                    print("Failed to parse selectors from LLM response, falling back to predefined selectors")

            # Use predefined login button selectors
            print("Using predefined LOGIN_BUTTON_SELECTORS")
            selectors = LOGIN_BUTTON_SELECTORS.copy()  # Make a copy to avoid modifying the original

            # Try each selector
            for selector in selectors:
                try:
                    print(f"Trying selector: {selector}")
                    # Check if the selector exists
                    count = await self.page.locator(selector).count()
                    if count > 0:
                        await self.page.locator(selector).first.click()
                        print(f"Clicked login button with selector: {selector}")
                        return True
                except Exception as e:
                    print(f"Error with selector {selector}: {e}")
                    continue

            # Try specific login button for redberyltest.in
            try:
                print("Trying specific login button for redberyltest.in...")
                # Try to find the login button by its class
                login_button = await self.page.locator("#signInButton").count()
                if login_button > 0:
                    await self.page.locator("#signInButton").click()
                    print("Clicked login button with id 'signInButton'")
                    await asyncio.sleep(NAVIGATION_WAIT)
                    return True
            except Exception as e:
                print(f"Error with specific login button: {e}")

            # If no selector worked, try using JavaScript with more aggressive approach
            print("Trying JavaScript approach...")
            js_result = await self.page.evaluate("""
                () => {
                    // Try to find login button by various attributes and text content
                    const loginTexts = ['log in', 'login', 'sign in', 'signin', 'submit', 'continue', 'next'];

                    // Check buttons
                    const buttons = Array.from(document.querySelectorAll('button'));
                    for (const button of buttons) {
                        const text = button.textContent.toLowerCase();
                        if (loginTexts.some(loginText => text.includes(loginText)) ||
                            button.id === 'signInButton' ||
                            button.type === 'submit') {
                            console.log('Clicking button: ' + button.outerHTML);
                            button.click();
                            return true;
                        }
                    }

                    // Check links
                    const links = Array.from(document.querySelectorAll('a'));
                    for (const link of links) {
                        const text = link.textContent.toLowerCase();
                        if (loginTexts.some(loginText => text.includes(loginText))) {
                            console.log('Clicking link: ' + link.outerHTML);
                            link.click();
                            return true;
                        }
                    }

                    // Check inputs
                    const inputs = Array.from(document.querySelectorAll('input[type="submit"]'));
                    if (inputs.length > 0) {
                        console.log('Clicking input: ' + inputs[0].outerHTML);
                        inputs[0].click();
                        return true;
                    }

                    // Check any clickable element with login text
                    const allElements = Array.from(document.querySelectorAll('*'));
                    for (const el of allElements) {
                        const text = el.textContent.toLowerCase();
                        if (loginTexts.some(loginText => text.includes(loginText)) &&
                            (el.onclick || el.getAttribute('role') === 'button')) {
                            console.log('Clicking element with login text: ' + el.outerHTML);
                            el.click();
                            return true;
                        }
                    }

                    // Try specific button for redberyltest.in
                    const signInButton = document.getElementById('signInButton');
                    if (signInButton) {
                        console.log('Clicking signInButton: ' + signInButton.outerHTML);
                        signInButton.click();
                        return true;
                    }

                    // If a form exists, try to submit it
                    const forms = document.querySelectorAll('form');
                    if (forms.length > 0) {
                        console.log('Submitting form: ' + forms[0].outerHTML);
                        forms[0].submit();
                        return true;
                    }

                    console.log('No login button found');
                    return false;
                }
            """)

            if js_result:
                print("Clicked login button using JavaScript")

                # Wait for navigation or network idle after clicking
                try:
                    await self.page.wait_for_load_state("networkidle", timeout=NAVIGATION_TIMEOUT)
                    print("Page loaded after clicking login button")

                    # Additional wait to ensure everything is fully loaded
                    await asyncio.sleep(NAVIGATION_WAIT)
                except Exception as e:
                    print(f"Error waiting after clicking login button: {e}")
                    # Continue anyway

                return True

            print("Could not find login button")
            return False

        except Exception as e:
            print(f"Error clicking login button: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def find_and_click_login_link(self):
        """Find and click a login link on the page"""
        try:
            print("Looking for login link...")

            # Try each selector
            for selector in LOGIN_LINK_SELECTORS:
                try:
                    print(f"Trying selector: {selector}")
                    # Check if the selector exists
                    count = await self.page.locator(selector).count()
                    if count > 0:
                        await self.page.locator(selector).first.click()
                        print(f"Clicked login link with selector: {selector}")
                        # Wait for navigation
                        await asyncio.sleep(NAVIGATION_WAIT)
                        return True
                except Exception as e:
                    print(f"Error with selector {selector}: {e}")
                    continue

            # Try specific login button for redberyltest.in
            try:
                print("Trying specific login button for redberyltest.in...")
                # Try to find the login button by its class
                login_button = await self.page.locator("button.blue-btnnn").count()
                if login_button > 0:
                    await self.page.locator("button.blue-btnnn").click()
                    print("Clicked login button with class 'blue-btnnn'")
                    await asyncio.sleep(NAVIGATION_WAIT)
                    return True
            except Exception as e:
                print(f"Error with specific login button: {e}")

            # If no selector worked, try using JavaScript
            print("Trying JavaScript approach...")
            js_result = await self.page.evaluate(JS_FIND_LOGIN_LINK)

            if js_result:
                print("Clicked login link using JavaScript")
                # Wait for navigation
                await asyncio.sleep(NAVIGATION_WAIT)
                return True

            print("Could not find login link")
            return False

        except Exception as e:
            print(f"Error finding login link: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def search_state(self, state_name):
        """Search for a state in a dropdown and select it"""
        try:
            print(f"Searching for state: {state_name}")

            # First, try to find and click the state dropdown
            # Try to click the dropdown to open it
            dropdown_clicked = False
            for selector in STATE_DROPDOWN_SELECTORS:
                try:
                    print(f"Trying to click state dropdown with selector: {selector}")
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_click(selector, "state dropdown")
                        print(f"Clicked state dropdown with selector: {selector}")
                        dropdown_clicked = True
                        # Wait for dropdown to open
                        await self.page.wait_for_timeout(DROPDOWN_OPEN_WAIT)
                        break
                except Exception as e:
                    print(f"Error clicking state dropdown with selector {selector}: {e}")
                    continue

            if not dropdown_clicked:
                # Try using JavaScript to find and click the dropdown
                print("Trying JavaScript approach to find and click state dropdown...")
                js_result = await self.page.evaluate(JS_FIND_STATE_DROPDOWN)

                if js_result:
                    print("Clicked state dropdown using JavaScript")
                    dropdown_clicked = True
                    await self.page.wait_for_timeout(DROPDOWN_OPEN_WAIT)

            if not dropdown_clicked:
                print("Could not find and click state dropdown")
                return False

            # Now that the dropdown is open, try to find the filter input
            # Try to type in the filter input
            filter_typed = False
            for selector in STATE_FILTER_SELECTORS:
                try:
                    print(f"Trying to type in filter with selector: {selector}")
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_type(selector, state_name, "state filter")
                        print(f"Typed '{state_name}' in filter with selector: {selector}")
                        filter_typed = True
                        # Wait for filtering to complete
                        await self.page.wait_for_timeout(FILTER_WAIT)
                        break
                except Exception as e:
                    print(f"Error typing in filter with selector {selector}: {e}")
                    continue

            if not filter_typed:
                # Try using JavaScript to find and type in the filter
                print("Trying JavaScript approach to find and type in state filter...")
                js_result = await self.page.evaluate(JS_FIND_STATE_FILTER, state_name)

                if js_result:
                    print(f"Typed '{state_name}' in filter using JavaScript")
                    filter_typed = True
                    await self.page.wait_for_timeout(FILTER_WAIT)

            # Now try to select the state from the filtered list
            # Wait a bit for the filtering to complete
            await self.page.wait_for_timeout(FILTER_WAIT)

            # Try to click the state item
            state_selectors = [
                f'.p-dropdown-item:has-text("{state_name}")',
                f'li:has-text("{state_name}")',
                f'.p-dropdown-items li:has-text("{state_name}")',
                f'[role="option"]:has-text("{state_name}")'
            ]

            state_clicked = False
            for selector in state_selectors:
                try:
                    print(f"Trying to click state with selector: {selector}")
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_click(selector, f"state {state_name}")
                        print(f"Clicked state {state_name} with selector: {selector}")
                        state_clicked = True
                        # Wait for selection to complete
                        await self.page.wait_for_timeout(SELECTION_WAIT)
                        break
                except Exception as e:
                    print(f"Error clicking state with selector {selector}: {e}")
                    continue

            if not state_clicked:
                # Try using JavaScript to find and click the state item
                print("Trying JavaScript approach to find and click state item...")
                js_result = await self.page.evaluate(JS_FIND_STATE_ITEM, state_name)

                if js_result:
                    print(f"Clicked state {state_name} using JavaScript")
                    state_clicked = True
                    await self.page.wait_for_timeout(SELECTION_WAIT)

            return state_clicked
        except Exception as e:
            print(f"Error searching for state {state_name}: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def click_tab(self, tab_name):
        """Click on a tab with the given name"""
        try:
            print(f"Looking for {tab_name} tab...")

            # Generate tab selectors
            tab_selectors = [
                f'.p-tabview-nav li:has-text("{tab_name}")',
                f'a:has-text("{tab_name}")',
                f'button:has-text("{tab_name}")',
                f'.nav-item:has-text("{tab_name}")',
                f'[role="tab"]:has-text("{tab_name}")',
                f'.tab:has-text("{tab_name}")',
                f'#{tab_name.lower()}-tab',
                f'.{tab_name.lower()}-tab',
                f'[data-tab="{tab_name.lower()}"]',
                f'[data-testid="{tab_name.lower()}-tab"]',
                f'li.p-highlight:has-text("{tab_name}")',
                f'.p-tabview-selected:has-text("{tab_name}")'
            ]

            # Try each selector
            for selector in tab_selectors:
                try:
                    print(f"Trying tab selector: {selector}")
                    if await self.page.locator(selector).count() > 0:
                        await self._retry_click(selector, f"{tab_name} tab")
                        print(f"Clicked {tab_name} tab with selector: {selector}")

                        # Wait for any content to load
                        await self.page.wait_for_timeout(TAB_LOAD_WAIT)
                        return True
                except Exception as e:
                    print(f"Error with tab selector {selector}: {e}")
                    continue

            # If no selector worked, try using JavaScript
            print("Trying JavaScript approach for tab selection...")
            js_result = await self.page.evaluate(JS_FIND_TAB, tab_name)

            if js_result:
                print(f"Clicked {tab_name} tab using JavaScript")
                await self.page.wait_for_timeout(TAB_LOAD_WAIT)
                return True

            print(f"Could not find {tab_name} tab")
            return False
        except Exception as e:
            print(f"Error clicking {tab_name} tab: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _add_to_command_history(self, command):
        """Add a command to the history"""
        if command and command.strip():
            # Add timestamp and command to history
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.command_history.append({
                "timestamp": timestamp,
                "command": command.strip(),
                "mode": input_mode
            })

            # Trim history if it exceeds max size
            if len(self.command_history) > self.max_history_size:
                self.command_history = self.command_history[-self.max_history_size:]

            logger.debug(f"Added command to history: {command}")

    async def _request_confirmation(self, action, timeout=None):
        """Request confirmation for a critical action"""
        if timeout is None:
            timeout = self.confirmation_timeout

        # Store the pending confirmation
        self.pending_confirmation = {
            "action": action,
            "timestamp": datetime.datetime.now(),
            "timeout": timeout
        }

        # Ask for confirmation
        await self.speak(f"Please confirm that you want to {action}. Say 'confirm' or 'yes' to proceed, or 'cancel' to abort.")

        # Return True to indicate confirmation is pending
        return True

    async def _check_confirmation(self, command):
        """Check if the command is a confirmation for a pending action"""
        if not self.pending_confirmation:
            return False

        # Check if confirmation has timed out
        now = datetime.datetime.now()
        confirmation_time = self.pending_confirmation["timestamp"]
        timeout = self.pending_confirmation["timeout"]

        if (now - confirmation_time).total_seconds() > timeout:
            # Confirmation has timed out
            await self.speak("Confirmation timeout. The action has been cancelled.")
            self.pending_confirmation = None
            return False

        # Check if command is a confirmation
        if command.lower() in ["confirm", "yes", "proceed", "continue", "do it"]:
            action = self.pending_confirmation["action"]
            await self.speak(f"Confirmed. Proceeding with: {action}")
            result = self.pending_confirmation.get("callback")
            self.pending_confirmation = None

            # If there's a callback function, execute it
            if callable(result):
                return await result()
            return True

        # Check if command is a cancellation
        if command.lower() in ["cancel", "abort", "stop", "no", "don't"]:
            await self.speak("Action cancelled.")
            self.pending_confirmation = None
            return True

        # If command is neither confirmation nor cancellation, remind the user
        await self.speak(f"Please confirm or cancel the pending action: {self.pending_confirmation['action']}")
        return True

    async def _show_command_history(self, limit=5):
        """Show the recent command history"""
        if not self.command_history:
            await self.speak("No command history available.")
            return True

        # Get the most recent commands up to the limit
        recent_commands = self.command_history[-limit:] if len(self.command_history) > limit else self.command_history

        # Format the history for display and speech
        history_text = "Recent commands:\n"
        speech_text = "Here are your recent commands: "

        for i, cmd in enumerate(recent_commands):
            timestamp = cmd["timestamp"]
            command = cmd["command"]
            mode = cmd["mode"]

            # Add to display text
            history_text += f"{i+1}. [{timestamp}] ({mode}) {command}\n"

            # Add to speech text (simpler format)
            speech_text += f"{i+1}: {command}. "

        # Display the history
        print("\n" + "=" * 50)
        print("COMMAND HISTORY")
        print("=" * 50)
        print(history_text)
        print("=" * 50)

        # Speak the history
        await self.speak(speech_text)

        return True

    async def _repeat_last_command(self):
        """Repeat the last command"""
        if not self.command_history or len(self.command_history) < 2:
            await self.speak("No previous command to repeat.")
            return True

        # Get the second-to-last command (last one is the "repeat" command itself)
        last_command = self.command_history[-2]["command"]

        await self.speak(f"Repeating last command: {last_command}")

        # Process the command again
        return await self.process_command(last_command)

    # Page navigation methods
    async def _refresh_page(self):
        """Refresh the current page"""
        logger.info("Refreshing page")
        try:
            await self.page.reload()
            await self.speak("Page refreshed")
            return True
        except Exception as e:
            logger.error(f"Error refreshing page: {e}")
            await self.speak("Error refreshing page")
            return False

    async def _go_back(self):
        """Go back to the previous page"""
        logger.info("Going back to previous page")
        try:
            await self.page.go_back()
            await self.speak("Navigated back")
            return True
        except Exception as e:
            logger.error(f"Error going back: {e}")
            await self.speak("Error going back")
            return False

    async def _go_forward(self):
        """Go forward to the next page"""
        logger.info("Going forward to next page")
        try:
            await self.page.go_forward()
            await self.speak("Navigated forward")
            return True
        except Exception as e:
            logger.error(f"Error going forward: {e}")
            await self.speak("Error going forward")
            return False

    async def _scroll_down(self):
        """Scroll down on the page"""
        logger.info("Scrolling down")
        try:
            await self.page.evaluate("window.scrollBy(0, 500)")
            return True
        except Exception as e:
            logger.error(f"Error scrolling down: {e}")
            return False

    async def _scroll_up(self):
        """Scroll up on the page"""
        logger.info("Scrolling up")
        try:
            await self.page.evaluate("window.scrollBy(0, -500)")
            return True
        except Exception as e:
            logger.error(f"Error scrolling up: {e}")
            return False

    async def _scroll_to_bottom(self):
        """Scroll to the bottom of the page"""
        logger.info("Scrolling to bottom")
        try:
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            return True
        except Exception as e:
            logger.error(f"Error scrolling to bottom: {e}")
            return False

    async def _scroll_to_top(self):
        """Scroll to the top of the page"""
        logger.info("Scrolling to top")
        try:
            await self.page.evaluate("window.scrollTo(0, 0)")
            return True
        except Exception as e:
            logger.error(f"Error scrolling to top: {e}")
            return False

    async def click_billing_info_dropdown(self):
        """Click the billing info dropdown specifically"""
        logger.info("Attempting to click billing info dropdown")

        try:
            # Try each selector from the constants
            for selector in BILLING_INFO_DROPDOWN_SELECTORS:
                logger.info(f"Trying selector: {selector}")
                try:
                    # Check if the element exists
                    element = await self.page.query_selector(selector)
                    if element:
                        logger.info(f"Found billing info dropdown with selector: {selector}")
                        # Click the element
                        await element.click()
                        logger.info("Clicked billing info dropdown")
                        # Wait a moment for the dropdown to open
                        await asyncio.sleep(1)
                        return True
                except Exception as e:
                    logger.warning(f"Error with selector {selector}: {e}")
                    continue

            # If none of the selectors worked, try JavaScript approach
            logger.info("Trying JavaScript approach to find and click billing info dropdown")
            js_result = await self.page.evaluate(JS_FIND_BILLING_INFO_DROPDOWN)

            if js_result:
                logger.info("Successfully clicked billing info dropdown using JavaScript")
                await asyncio.sleep(1)
                return True

            logger.warning("Could not find billing info dropdown")
            return False

        except Exception as e:
            logger.error(f"Error clicking billing info dropdown: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def click_service_checkbox(self, service_name):
        """Click a service checkbox based on the service name

        Args:
            service_name (str): The name of the service to select

        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"Attempting to click service checkbox for '{service_name}'")

        try:
            # Normalize the service name for comparison
            service_name_lower = service_name.lower()

            # Find the matching service text patterns using the constants
            matching_patterns = []
            for key, patterns in SERVICE_NAME_PATTERNS.items():
                if any(pattern in service_name_lower for pattern in patterns) or any(service_name_lower in pattern for pattern in patterns):
                    matching_patterns.extend(patterns)

            if not matching_patterns:
                # If no specific match, use the original service name
                matching_patterns = [service_name_lower]

            logger.info(f"Looking for service patterns: {matching_patterns}")

            # Use the JavaScript from constants to find and click the service checkbox
            js_result = await self.page.evaluate(JS_FIND_SERVICE_CHECKBOX, matching_patterns)

            if js_result and js_result.get('success'):
                reason = js_result.get('reason', '')
                if reason == 'already_checked':
                    logger.info(f"Service {service_name} is already selected")
                    await self.speak(f"Service {service_name} is already selected")
                else:
                    logger.info(f"Successfully clicked service checkbox for {service_name}")
                return True
            elif js_result and js_result.get('reason') == 'disabled':
                logger.info(f"Service {service_name} checkbox is disabled")
                await self.speak(f"Service {service_name} checkbox is disabled and cannot be changed")
                return False
            else:
                logger.warning(f"Could not find service checkbox for {service_name}")
                return False

        except Exception as e:
            logger.error(f"Error clicking service checkbox: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def click_payment_option(self, option):
        """Click a payment option checkbox (Pay now/Pay later)

        Args:
            option (str): The payment option to select ("Pay now" or "Pay later")

        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"Attempting to click payment option: {option}")

        try:
            # JavaScript to find and click the payment option
            js_result = await self.page.evaluate("""
            (option) => {
                // Find all payment option sections
                const sections = document.querySelectorAll('section > div');
                console.log('Found', sections.length, 'payment sections');

                for (const section of sections) {
                    // Get the text content
                    const textContent = section.textContent.trim();
                    console.log('Checking section:', textContent);

                    // Check if this section matches our option
                    if (textContent.includes(option)) {
                        console.log('Found matching payment option:', textContent);

                        // Find the checkbox within this section
                        const checkbox = section.querySelector('.p-checkbox');
                        if (checkbox) {
                            // Check if it's already checked
                            const isChecked = checkbox.classList.contains('p-checkbox-checked');
                            if (isChecked) {
                                console.log('Checkbox is already checked');
                                return { success: true, reason: 'already_checked' };
                            }

                            // Click the checkbox
                            checkbox.click();
                            console.log('Clicked checkbox');
                            return { success: true, reason: 'clicked' };
                        } else {
                            console.log('No checkbox found in section');
                        }
                    }
                }

                return { success: false, reason: 'not_found' };
            }
            """, option)

            if js_result and js_result.get('success'):
                reason = js_result.get('reason', '')
                if reason == 'already_checked':
                    logger.info(f"Payment option {option} is already selected")
                    await self.speak(f"Payment option {option} is already selected")
                else:
                    logger.info(f"Successfully clicked payment option {option}")
                return True
            else:
                logger.warning(f"Could not find payment option {option}")
                return False

        except Exception as e:
            logger.error(f"Error clicking payment option: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False





    async def click_checkbox(self, checkbox_name=None):
        """Click a checkbox on the page, optionally with a specific name/label

        Args:
            checkbox_name (str, optional): The name or label of the checkbox to click. Defaults to None.
        """
        if checkbox_name:
            logger.info(f"Attempting to click checkbox labeled '{checkbox_name}'")
        else:
            logger.info("Attempting to click any checkbox")

        try:
            # Try multiple selectors for checkboxes
            selectors = [
                ".p-checkbox",  # General PrimeNG checkbox class
                ".p-checkbox-box",  # PrimeNG checkbox box
                ".p-checkbox-icon",  # From the provided HTML
                "span.p-checkbox-icon",
                "input[type='checkbox']",
                ".p-checkbox input",
                "div.p-checkbox",
                "div.checkbox",
                "label.checkbox",
                "[role='checkbox']",
                ".form-check-input",
                ".custom-control-input"
            ]

            # Try each selector
            for selector in selectors:
                logger.info(f"Trying selector: {selector}")
                try:
                    # Check if the element exists
                    elements = await self.page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        # Click the first visible checkbox
                        for element in elements:
                            # Check if the element is visible
                            is_visible = await element.is_visible()
                            if is_visible:
                                logger.info(f"Found visible checkbox with selector: {selector}")
                                # Click the element
                                await element.click()
                                logger.info("Clicked checkbox")
                                # Wait a moment after clicking
                                await asyncio.sleep(0.5)
                                return True
                except Exception as e:
                    logger.warning(f"Error with selector {selector}: {e}")
                    continue

            # If none of the selectors worked, try JavaScript approach
            logger.info("Trying JavaScript approach to find and click checkbox")

            # If a checkbox name was provided, use it in the JavaScript
            if checkbox_name:
                js_result = await self.page.evaluate("""
                (checkboxName) => {
                    const checkboxNameLower = checkboxName.toLowerCase();
                    console.log('Looking for checkbox with name:', checkboxNameLower);

                    // Method 1: Find by associated label text
                    const labels = Array.from(document.querySelectorAll('label'));
                    for (const label of labels) {
                        if (label.offsetParent !== null && label.textContent.toLowerCase().includes(checkboxNameLower)) {
                            console.log('Found label with matching text:', label.textContent);

                            // Try to find the checkbox associated with this label
                            const forId = label.getAttribute('for');
                            if (forId) {
                                const input = document.getElementById(forId);
                                if (input && (input.type === 'checkbox' || input.classList.contains('p-checkbox'))) {
                                    console.log('Found checkbox by label for attribute');
                                    input.click();
                                    return true;
                                }
                            }

                            // Check if the label contains a checkbox
                            const containedCheckbox = label.querySelector('input[type="checkbox"], .p-checkbox');
                            if (containedCheckbox) {
                                console.log('Found checkbox within label');
                                containedCheckbox.click();
                                return true;
                            }

                            // If we found a matching label but no checkbox, try clicking the label itself
                            console.log('Clicking the label itself');
                            label.click();
                            return true;
                        }
                    }

                    // Method 2: Find checkbox near text matching the name
                    const textNodes = [];
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                    let node;
                    while (node = walker.nextNode()) {
                        if (node.textContent.toLowerCase().includes(checkboxNameLower)) {
                            textNodes.push(node);
                        }
                    }

                    for (const textNode of textNodes) {
                        // Look for checkboxes near this text node
                        let element = textNode.parentElement;
                        for (let i = 0; i < 5; i++) { // Check up to 5 levels up
                            if (!element) break;

                            // Check for checkboxes within this element
                            const nearbyCheckbox = element.querySelector('input[type="checkbox"], .p-checkbox, .p-checkbox-box, .p-checkbox-icon');
                            if (nearbyCheckbox) {
                                console.log('Found checkbox near matching text');
                                nearbyCheckbox.click();
                                return true;
                            }

                            element = element.parentElement;
                        }
                    }

                    // Method 3: Try to find checkbox by name, id, or aria-label attributes
                    const checkboxSelectors = [
                        `input[name="${checkboxNameLower}"]`,
                        `input[id*="${checkboxNameLower}"]`,
                        `input[aria-label*="${checkboxNameLower}"]`,
                        `[role="checkbox"][aria-label*="${checkboxNameLower}"]`,
                        `.p-checkbox[aria-label*="${checkboxNameLower}"]`
                    ];

                    for (const selector of checkboxSelectors) {
                        const element = document.querySelector(selector);
                        if (element && element.offsetParent !== null) {
                            console.log('Found checkbox by attribute selector:', selector);
                            element.click();
                            return true;
                        }
                    }

                    return false;
                }
                """, checkbox_name)
            else:
                # If no checkbox name was provided, use the original JavaScript to find any checkbox
                js_result = await self.page.evaluate("""
                () => {
                    // Try to find checkboxes by various methods

                    // Method 1: Find by class
                    const checkboxes = document.querySelectorAll('.p-checkbox, .p-checkbox-box, .p-checkbox-icon, input[type="checkbox"]');
                    for (const checkbox of checkboxes) {
                        if (checkbox.offsetParent !== null) { // Check if visible
                            console.log('Found checkbox by class');
                            checkbox.click();
                            return true;
                        }
                    }

                    // Method 2: Find by role
                    const roleCheckboxes = document.querySelectorAll('[role="checkbox"]');
                    for (const checkbox of roleCheckboxes) {
                        if (checkbox.offsetParent !== null) { // Check if visible
                            console.log('Found checkbox by role');
                            checkbox.click();
                            return true;
                        }
                    }

                    // Method 3: Find by common checkbox patterns
                    const labels = document.querySelectorAll('label');
                    for (const label of labels) {
                        if (label.offsetParent !== null) { // Check if visible
                            const input = label.querySelector('input[type="checkbox"]');
                            if (input) {
                                console.log('Found checkbox within label');
                                input.click();
                                return true;
                            }

                            // Check if the label itself is clickable and looks like a checkbox
                            if (label.classList.contains('checkbox') ||
                                label.classList.contains('p-checkbox') ||
                                label.querySelector('.checkbox') ||
                                label.querySelector('.p-checkbox')) {
                                console.log('Found checkbox-like label');
                                label.click();
                                return true;
                            }
                        }
                    }

                    // Method 4: Look for any element that visually appears to be a checkbox
                    const allElements = document.querySelectorAll('*');
                    for (const el of allElements) {
                        if (el.offsetParent !== null) { // Check if visible
                            const style = window.getComputedStyle(el);
                            // Check if it's a small square element that might be a checkbox
                            if ((style.width === style.height) &&
                                (parseInt(style.width) <= 24) &&
                                (style.border !== 'none' || style.backgroundColor !== 'transparent')) {
                                console.log('Found potential checkbox by appearance');
                                el.click();
                                return true;
                            }
                        }
                    }

                    return false;
                }
                """)

            if js_result:
                logger.info("Successfully clicked checkbox using JavaScript")
                await asyncio.sleep(0.5)
                return True

            logger.warning("Could not find checkbox")
            return False

        except Exception as e:
            logger.error(f"Error clicking checkbox: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def click_mailing_info_dropdown(self):
        """Click the mailing info dropdown specifically"""
        logger.info("Attempting to click mailing info dropdown")

        try:
            # Try multiple selectors for the mailing info dropdown
            selectors = [
                "#RA_Mailing_Information",  # ID from the provided HTML
                "div[id='RA_Mailing_Information']",
                ".p-dropdown:has-text('Select Mailing Info')",
                ".p-dropdown-label:has-text('Mailing Info')",
                "div.p-dropdown:has(.p-dropdown-label:has-text('Mailing Info'))",
                "span.p-float-label:has(div#RA_Mailing_Information)",
                "div.field:has(label:has-text('Select Mailing Info')) .p-dropdown",
                "div.field:has(label:has-text('Mailing Info')) .p-dropdown"
            ]

            # Try each selector
            for selector in selectors:
                logger.info(f"Trying selector: {selector}")
                try:
                    # Check if the element exists
                    element = await self.page.query_selector(selector)
                    if element:
                        logger.info(f"Found mailing info dropdown with selector: {selector}")
                        # Click the element
                        await element.click()
                        logger.info("Clicked mailing info dropdown")
                        # Wait a moment for the dropdown to open
                        await asyncio.sleep(1)
                        return True
                except Exception as e:
                    logger.warning(f"Error with selector {selector}: {e}")
                    continue

            # If none of the selectors worked, try JavaScript approach
            logger.info("Trying JavaScript approach to find and click mailing info dropdown")
            js_result = await self.page.evaluate("""
            () => {
                // Try to find by ID
                const byId = document.getElementById('RA_Mailing_Information');
                if (byId) {
                    console.log('Found by ID');
                    byId.click();
                    return true;
                }

                // Try to find by text content
                const labels = Array.from(document.querySelectorAll('label'));
                for (const label of labels) {
                    if (label.textContent.includes('Mailing Info') || label.textContent.includes('Select Mailing')) {
                        const field = label.closest('.field');
                        if (field) {
                            const dropdown = field.querySelector('.p-dropdown');
                            if (dropdown) {
                                console.log('Found by label text');
                                dropdown.click();
                                return true;
                            }
                        }
                    }
                }

                // Try to find any dropdown
                const dropdowns = document.querySelectorAll('.p-dropdown');
                for (const dropdown of dropdowns) {
                    const label = dropdown.textContent.toLowerCase();
                    if (label.includes('mailing') || label.includes('mail')) {
                        console.log('Found by dropdown text');
                        dropdown.click();
                        return true;
                    }
                }

                return false;
            }
            """)

            if js_result:
                logger.info("Successfully clicked mailing info dropdown using JavaScript")
                await asyncio.sleep(1)
                return True

            logger.warning("Could not find mailing info dropdown")
            return False

        except Exception as e:
            logger.error(f"Error clicking mailing info dropdown: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def click_add_billing_info_button(self):
        """Click the add billing info button specifically"""
        logger.info("Attempting to click add billing info button")

        try:
            # Try multiple selectors for the add billing info button
            selectors = [
                "button:has-text('Add Billing Info')",
                ".p-button:has-text('Add Billing Info')",
                "button.p-button:has(.p-button-label:has-text('Add Billing Info'))",
                "button.vstate-button:has-text('Add Billing Info')",
                "button[aria-label='Add Billing Info']",
                ".p-button:has(.pi-plus):has-text('Add Billing Info')"
            ]

            # Try each selector
            for selector in selectors:
                logger.info(f"Trying selector: {selector}")
                try:
                    # Check if the element exists
                    element = await self.page.query_selector(selector)
                    if element:
                        logger.info(f"Found add billing info button with selector: {selector}")
                        # Click the element
                        await element.click()
                        logger.info("Clicked add billing info button")
                        # Wait a moment for any action to complete
                        await asyncio.sleep(1)
                        return True
                except Exception as e:
                    logger.warning(f"Error with selector {selector}: {e}")
                    continue

            # If none of the selectors worked, try JavaScript approach
            logger.info("Trying JavaScript approach to find and click add billing info button")
            js_result = await self.page.evaluate("""
            () => {
                // Try to find by text content
                const buttons = Array.from(document.querySelectorAll('button'));
                for (const button of buttons) {
                    if (button.textContent.includes('Add Billing Info')) {
                        console.log('Found by button text');
                        button.click();
                        return true;
                    }
                }

                // Try to find by aria-label
                const ariaButtons = Array.from(document.querySelectorAll('button[aria-label="Add Billing Info"]'));
                if (ariaButtons.length > 0) {
                    console.log('Found by aria-label');
                    ariaButtons[0].click();
                    return true;
                }

                // Try to find by class and icon
                const iconButtons = Array.from(document.querySelectorAll('.p-button'));
                for (const button of iconButtons) {
                    if (button.querySelector('.pi-plus') && button.textContent.toLowerCase().includes('billing')) {
                        console.log('Found by icon and text');
                        button.click();
                        return true;
                    }
                }

                return false;
            }
            """)

            if js_result:
                logger.info("Successfully clicked add billing info button using JavaScript")
                await asyncio.sleep(1)
                return True

            logger.warning("Could not find add billing info button")
            return False

        except Exception as e:
            logger.error(f"Error clicking add billing info button: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def click_organizer_dropdown(self):
        """Click the organizer dropdown

        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("Attempting to click organizer dropdown")

        try:
            # Try multiple selectors for the organizer dropdown
            selectors = [
                "#Organizer",  # ID from the provided HTML
                "div[id='Organizer']",
                ".p-dropdown:has-text('Select Organizer')",
                ".p-dropdown-label:has-text('Organizer')",
                "div.p-dropdown:has(.p-dropdown-label:has-text('Organizer'))",
                "span.p-float-label:has(div#Organizer)",
                "div.field:has(label:has-text('Select Organizer')) .p-dropdown",
                "div.field:has(label:has-text('Organizer')) .p-dropdown"
            ]

            # Try each selector
            for selector in selectors:
                logger.info(f"Trying selector: {selector}")
                try:
                    # Check if the element exists
                    element = await self.page.query_selector(selector)
                    if element:
                        logger.info(f"Found organizer dropdown with selector: {selector}")
                        # Click the element
                        await element.click()
                        logger.info("Clicked organizer dropdown")
                        # Wait a moment for the dropdown to open
                        await asyncio.sleep(1)
                        return True
                except Exception as e:
                    logger.warning(f"Error with selector {selector}: {e}")
                    continue

            # If none of the selectors worked, try JavaScript approach
            logger.info("Trying JavaScript approach to find and click organizer dropdown")
            js_result = await self.page.evaluate("""
            () => {
                // Try to find by ID
                const byId = document.getElementById('Organizer');
                if (byId) {
                    console.log('Found organizer dropdown by ID');
                    byId.click();
                    return true;
                }

                // Try to find by text content
                const labels = Array.from(document.querySelectorAll('label'));
                for (const label of labels) {
                    if (label.textContent.includes('Select Organizer')) {
                        const field = label.closest('.field');
                        if (field) {
                            const dropdown = field.querySelector('.p-dropdown');
                            if (dropdown) {
                                console.log('Found organizer dropdown by label text');
                                dropdown.click();
                                return true;
                            }
                        }
                    }
                }

                // Try to find any dropdown with organizer text
                const dropdowns = document.querySelectorAll('.p-dropdown');
                for (const dropdown of dropdowns) {
                    const label = dropdown.textContent.toLowerCase();
                    if (label.includes('organizer')) {
                        console.log('Found organizer dropdown by text content');
                        dropdown.click();
                        return true;
                    }
                }

                return false;
            }
            """)

            if js_result:
                logger.info("Successfully clicked organizer dropdown using JavaScript")
                await asyncio.sleep(1)
                return True

            logger.warning("Could not find organizer dropdown")
            return False

        except Exception as e:
            logger.error(f"Error clicking organizer dropdown: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def click_add_organizer_button(self):
        """Click the add organizer button

        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("Attempting to click add organizer button")

        try:
            # Try multiple selectors for the add organizer button
            selectors = [
                "button:has-text('Add Organizer')",
                ".p-button:has-text('Add Organizer')",
                "button.p-button:has(.p-button-label:has-text('Add Organizer'))",
                "button.vstate-button:has-text('Add Organizer')",
                "button[aria-label='Add Organizer']",
                ".p-button:has(.pi-plus):has-text('Add Organizer')"
            ]

            # Try each selector
            for selector in selectors:
                logger.info(f"Trying selector: {selector}")
                try:
                    # Check if the element exists
                    element = await self.page.query_selector(selector)
                    if element:
                        logger.info(f"Found add organizer button with selector: {selector}")
                        # Click the element
                        await element.click()
                        logger.info("Clicked add organizer button")
                        # Wait a moment for any action to complete
                        await asyncio.sleep(1)
                        return True
                except Exception as e:
                    logger.warning(f"Error with selector {selector}: {e}")
                    continue

            # If none of the selectors worked, try JavaScript approach
            logger.info("Trying JavaScript approach to find and click add organizer button")
            js_result = await self.page.evaluate("""
            () => {
                // Try to find by aria-label
                const buttons = document.querySelectorAll('button');
                for (const button of buttons) {
                    if (button.getAttribute('aria-label') === 'Add Organizer') {
                        console.log('Found add organizer button by aria-label');
                        button.click();
                        return true;
                    }
                }

                // Try to find by text content
                const addButtons = Array.from(document.querySelectorAll('button'));
                for (const button of addButtons) {
                    if (button.textContent.includes('Add Organizer')) {
                        console.log('Found add organizer button by text content');
                        button.click();
                        return true;
                    }
                }

                // Try to find by class and icon
                const plusButtons = document.querySelectorAll('.p-button');
                for (const button of plusButtons) {
                    if (button.querySelector('.pi-plus') &&
                        button.textContent.toLowerCase().includes('organizer')) {
                        console.log('Found add organizer button by class and icon');
                        button.click();
                        return true;
                    }
                }

                return false;
            }
            """)

            if js_result:
                logger.info("Successfully clicked add organizer button using JavaScript")
                await asyncio.sleep(1)
                return True

            logger.warning("Could not find add organizer button")
            return False

        except Exception as e:
            logger.error(f"Error clicking add organizer button: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def click_principal_address_dropdown(self):
        """Click the principal address dropdown specifically"""
        logger.info("Attempting to click principal address dropdown")

        try:
            # Try multiple selectors for the principal address dropdown
            selectors = [
                "#Principal_Address",  # ID from the provided HTML
                "div[id='Principal_Address']",
                ".p-dropdown:has-text('Select Principal Address')",
                ".p-dropdown-label:has-text('Principal Address')",
                "div.p-dropdown:has(.p-dropdown-label:has-text('Principal Address'))",
                "span.p-float-label:has(div#Principal_Address)",
                "div.field:has(label:has-text('Select Principal Address')) .p-dropdown",
                "div.field:has(label:has-text('Principal Address')) .p-dropdown"
            ]

            # Try each selector
            for selector in selectors:
                logger.info(f"Trying selector: {selector}")
                try:
                    # Check if the element exists
                    element = await self.page.query_selector(selector)
                    if element:
                        logger.info(f"Found principal address dropdown with selector: {selector}")
                        # Click the element
                        await element.click()
                        logger.info("Clicked principal address dropdown")
                        # Wait a moment for the dropdown to open
                        await asyncio.sleep(1)
                        return True
                except Exception as e:
                    logger.warning(f"Error with selector {selector}: {e}")
                    continue

            # If none of the selectors worked, try JavaScript approach
            logger.info("Trying JavaScript approach to find and click principal address dropdown")
            js_result = await self.page.evaluate("""
            () => {
                // Try to find by ID
                const byId = document.getElementById('Principal_Address');
                if (byId) {
                    console.log('Found by ID');
                    byId.click();
                    return true;
                }

                // Try to find by text content
                const labels = Array.from(document.querySelectorAll('label'));
                for (const label of labels) {
                    if (label.textContent.includes('Principal Address')) {
                        const field = label.closest('.field');
                        if (field) {
                            const dropdown = field.querySelector('.p-dropdown');
                            if (dropdown) {
                                console.log('Found by label text');
                                dropdown.click();
                                return true;
                            }
                        }
                    }
                }

                // Try to find any dropdown
                const dropdowns = document.querySelectorAll('.p-dropdown');
                for (const dropdown of dropdowns) {
                    const label = dropdown.textContent.toLowerCase();
                    if (label.includes('principal') || label.includes('address')) {
                        console.log('Found by dropdown text');
                        dropdown.click();
                        return true;
                    }
                }

                return false;
            }
            """)

            if js_result:
                logger.info("Successfully clicked principal address dropdown using JavaScript")
                await asyncio.sleep(1)
                return True

            logger.warning("Could not find principal address dropdown")
            return False

        except Exception as e:
            logger.error(f"Error clicking principal address dropdown: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def click_billing_info_dropdown(self):
        """Click the billing info dropdown specifically"""
        logger.info("Attempting to click billing info dropdown")

        try:
            # Try multiple selectors for the billing info dropdown
            selectors = [
                "#RA_Billing_Information",  # ID from the provided HTML
                "div[id='RA_Billing_Information']",
                ".p-dropdown:has-text('Select Billing Info')",
                ".p-dropdown-label:has-text('Billing Info')",
                "div.p-dropdown:has(.p-dropdown-label:has-text('Billing Info'))",
                "span.p-float-label:has(div#RA_Billing_Information)",
                "div.field:has(label:has-text('Select Billing Info')) .p-dropdown",
                "div.field:has(label:has-text('Billing Info')) .p-dropdown"
            ]

            # Try each selector
            for selector in selectors:
                logger.info(f"Trying selector: {selector}")
                try:
                    # Check if the element exists
                    element = await self.page.query_selector(selector)
                    if element:
                        logger.info(f"Found billing info dropdown with selector: {selector}")
                        # Click the element
                        await element.click()
                        logger.info("Clicked billing info dropdown")
                        # Wait a moment for the dropdown to open
                        await asyncio.sleep(1)
                        return True
                except Exception as e:
                    logger.warning(f"Error with selector {selector}: {e}")
                    continue

            # If none of the selectors worked, try JavaScript approach
            logger.info("Trying JavaScript approach to find and click billing info dropdown")
            js_result = await self.page.evaluate("""
            () => {
                // Try to find by ID
                const byId = document.getElementById('RA_Billing_Information');
                if (byId) {
                    console.log('Found by ID');
                    byId.click();
                    return true;
                }

                // Try to find by text content
                const labels = Array.from(document.querySelectorAll('label'));
                for (const label of labels) {
                    if (label.textContent.includes('Billing Info') || label.textContent.includes('Select Billing')) {
                        const field = label.closest('.field');
                        if (field) {
                            const dropdown = field.querySelector('.p-dropdown');
                            if (dropdown) {
                                console.log('Found by label text');
                                dropdown.click();
                                return true;
                            }
                        }
                    }
                }

                // Try to find any dropdown
                const dropdowns = document.querySelectorAll('.p-dropdown');
                for (const dropdown of dropdowns) {
                    const label = dropdown.textContent.toLowerCase();
                    if (label.includes('billing') || label.includes('bill')) {
                        console.log('Found by dropdown text');
                        dropdown.click();
                        return true;
                    }
                }

                return false;
            }
            """)

            if js_result:
                logger.info("Successfully clicked billing info dropdown using JavaScript")
                await asyncio.sleep(1)
                return True

            logger.warning("Could not find billing info dropdown")
            return False

        except Exception as e:
            logger.error(f"Error clicking billing info dropdown: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def click_add_billing_info_button(self):
        """Click the add billing info button specifically"""
        logger.info("Attempting to click add billing info button")

        try:
            # Try multiple selectors for the add billing info button
            selectors = [
                "button:has-text('Add Billing Info')",
                ".p-button:has-text('Add Billing Info')",
                "button.p-button:has(.p-button-label:has-text('Add Billing Info'))",
                "button.vstate-button:has-text('Add Billing Info')",
                "button[aria-label='Add Billing Info']",
                ".p-button:has(.pi-plus):has-text('Add Billing Info')"
            ]

            # Try each selector
            for selector in selectors:
                logger.info(f"Trying selector: {selector}")
                try:
                    # Check if the element exists
                    element = await self.page.query_selector(selector)
                    if element:
                        logger.info(f"Found add billing info button with selector: {selector}")
                        # Click the element
                        await element.click()
                        logger.info("Clicked add billing info button")
                        # Wait a moment for any action to complete
                        await asyncio.sleep(1)
                        return True
                except Exception as e:
                    logger.warning(f"Error with selector {selector}: {e}")
                    continue

            # If none of the selectors worked, try JavaScript approach
            logger.info("Trying JavaScript approach to find and click add billing info button")
            js_result = await self.page.evaluate("""
            () => {
                // Try to find by text content
                const buttons = Array.from(document.querySelectorAll('button'));
                for (const button of buttons) {
                    if (button.textContent.includes('Add Billing Info')) {
                        console.log('Found by button text');
                        button.click();
                        return true;
                    }
                }

                // Try to find by aria-label
                const ariaButtons = Array.from(document.querySelectorAll('button[aria-label="Add Billing Info"]'));
                if (ariaButtons.length > 0) {
                    console.log('Found by aria-label');
                    ariaButtons[0].click();
                    return true;
                }

                // Try to find by class and icon
                const iconButtons = Array.from(document.querySelectorAll('.p-button'));
                for (const button of iconButtons) {
                    if (button.querySelector('.pi-plus') && button.textContent.toLowerCase().includes('billing')) {
                        console.log('Found by icon and text');
                        button.click();
                        return true;
                    }
                }

                return false;
            }
            """)

            if js_result:
                logger.info("Successfully clicked add billing info button using JavaScript")
                await asyncio.sleep(1)
                return True

            logger.warning("Could not find add billing info button")
            return False

        except Exception as e:
            logger.error(f"Error clicking add billing info button: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def close(self, keep_browser_open=False):
        """Close the assistant and browser"""
        try:
            if self.browser and not keep_browser_open:
                await self.browser.close()
        except Exception as e:
            print(f"Error closing browser: {e}")

    async def run(self):
        """Main run method for the assistant"""
        global running, input_mode

        try:
            # Start the input threads
            print("\nStarting input threads...")
            text_thread = threading.Thread(target=text_input_thread, args=(self,))
            voice_thread = threading.Thread(target=voice_input_thread, args=(self,))

            text_thread.daemon = True
            voice_thread.daemon = True

            # Start both threads
            text_thread.start()
            voice_thread.start()

            print("\n✅ Input threads started successfully")
            print("=" * 80)
            print("🎤 Voice input thread is running")
            print("⌨️  Text input thread is running")
            print("=" * 80)

            # Signal that initialization is complete
            self.ready_event.set()

            # Main command processing loop
            while running:
                try:
                    # Get command from queue with timeout
                    try:
                        command = command_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue

                    if command.lower() == "exit":
                        print("\nExiting...")
                        running = False
                        break

                    # Process the command
                    await self.process_command(command)

                    # Force the recognizer to start listening immediately
                    if self.recognizer:
                        print("\n🎤 LISTENING NOW... (Speak your command)", flush=True)
                        try:
                            # Start listening in a non-blocking way
                            await self._listen_voice()
                        except Exception as e:
                            print(f"Error in voice recognition: {e}")
                            import traceback
                            traceback.print_exc()

                except Exception as e:
                    print(f"Error processing command: {e}")
                    import traceback
                    traceback.print_exc()

        except Exception as e:
            print(f"Error in run method: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Clean up
            await self.close()
            running = False

    async def _normalize_command_with_llm(self, text):
        """Use LLM to normalize and interpret the voice command"""
        if not hasattr(self, 'llm_utils') or not self.llm_utils:
            logger.warning("LLM utils not available for command normalization")
            return text

        try:
            logger.info(f"Normalizing command with LLM: {text}")

            # Create a prompt for the LLM to normalize the command
            prompt = f"""
            You are a voice command interpreter for a web assistant. Normalize the following voice command to make it more processable:

            "{text}"

            Apply these transformations based on command type:

            1. NAVIGATION COMMANDS:
               - Convert "go to", "navigate to", "open", "visit", "browse to", "load" to "goto " format
               - Convert spoken URL formats (e.g., "dot com", "dot in") to proper URL notation
               - IMPORTANT: For domain corrections, follow these rules:
                 * ONLY correct domains when the user is clearly trying to go to a specific site
                 * If the user says something like "red beryl test" or similar variations, they likely mean "redberyltest.in"
                 * Do NOT convert legitimate domains like "redbus.in" to other domains unless it's clear from context
                 * Respect the user's intent - don't change domains unless you're confident it's a speech recognition error

            2. CLICK COMMANDS:
               - Standardize "click on", "press", "tap", "select", "choose" to "click " format
               - Preserve the element name to be clicked (e.g., "click login button" → "click login button")

            3. FORM FILLING COMMANDS:
               - Standardize "enter", "input", "type", "fill", "put" to "enter " format
               - Preserve field names and values (e.g., "enter john@example.com as email" → "enter email john@example.com")
               - For login commands, format as "login with email [email] and password [password]"

            4. PAGE COMMANDS:
               - Standardize "refresh", "reload", "update" to "refresh" format
               - Standardize "back", "go back", "previous" to "back" format
               - Standardize "forward", "go forward", "next" to "forward" format
               - Standardize scroll commands to "scroll up/down/top/bottom" format

            5. GENERAL IMPROVEMENTS:
               - Fix spacing and formatting issues
               - Correct typos in command keywords
               - Preserve the original intent of the command
               - Make sure email addresses and passwords are properly formatted

            Return ONLY the normalized command text without any explanations or additional text.
            """

            # Get the normalized command from the LLM
            normalized_text = None

            # Try different LLM methods based on what's available
            if hasattr(self.llm_utils, 'get_llm_response'):
                logger.info("Using get_llm_response method for command normalization")
                normalized_text = await self.llm_utils.get_llm_response(prompt)
            elif hasattr(self.llm_utils.llm_provider, 'generate_content'):
                logger.info("Using generate_content method for command normalization")
                response = self.llm_utils.llm_provider.generate_content(prompt)
                normalized_text = response.text
            elif hasattr(self.llm_utils.llm_provider, 'generate'):
                logger.info("Using generate method for command normalization")
                normalized_text = await self.llm_utils.llm_provider.generate(prompt)

            # Clean up the normalized text
            if normalized_text:
                # Remove any quotes or extra whitespace
                normalized_text = normalized_text.strip().strip('"\'').strip()
                logger.info(f"LLM normalized command: '{text}' → '{normalized_text}'")
                return normalized_text
            else:
                logger.warning("LLM normalization failed, returning original text")
                return text

        except Exception as e:
            logger.error(f"Error normalizing command with LLM: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return text  # Return original text if normalization fails

    async def _listen_voice(self):
        """Listen for voice input and return the recognized text"""
        if not self.recognizer:
            logger.error("No speech recognizer available")
            return None

        try:
            logger.info("Starting voice recognition...")
            # Use the recognizer's listen method
            text = await self.recognizer.listen()

            if text:
                logger.info(f"Recognized text: {text}")

                # Use LLM to normalize the command if available
                normalized_text = await self._normalize_command_with_llm(text)

                return normalized_text
            else:
                logger.warning("No speech detected")
                return None
        except Exception as e:
            logger.error(f"Error in voice recognition: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

def text_input_thread(assistant):
    """Thread for handling text input"""
    global running, input_mode

    assistant.ready_event.wait()

    if input_mode == "text":
        display_prompt()

    while running:
        try:
            if input_mode == "text":
                command = input()

                if command.strip():
                    if command.lower() in ["voice", "voice mode", "switch to voice", "switch to voice mode"]:
                        input_mode = "voice"
                        print(f"\n{VOICE_MODE_SWITCH_MESSAGE}")
                        print("Say 'text' or 'switch to text mode' to switch back to text mode.")

                        # Switch recognizer mode if available
                        if assistant.recognizer:
                            asyncio.run(assistant.switch_recognizer_mode("voice"))

                        display_voice_prompt()
                        sys.stdout.flush()
                    else:
                        # Process the command directly without showing voice recognition messages
                        command_queue.put(command.strip())
                        print(f"Processing command: {command}")
                else:
                    display_prompt()
            else:
                time.sleep(0.5)

        except KeyboardInterrupt:
            print("\nKeyboard interrupt detected. Exiting...")
            command_queue.put("exit")
            running = False
            break
        except Exception as e:
            print(f"Error in text input thread: {e}")
            import traceback
            traceback.print_exc()
            display_prompt()

def voice_input_thread(assistant):
    """Thread for handling voice input"""
    global running, input_mode

    # Common domain name corrections - only for actual misrecognitions of redberyltest
    DOMAIN_CORRECTIONS = {
        "redberyl": "redberyltest",
        "red beryl": "redberyltest",
        "redberyl test": "redberyltest",
        "red beryl test": "redberyltest"
    }

    # Wait for initialization to complete
    assistant.ready_event.wait()

    # Initialize microphone at the start
    try:
        import speech_recognition as sr
        if not hasattr(assistant.recognizer, 'microphone'):
            print("🎤 Initializing microphone...")
            # Create a new recognizer instance for microphone handling
            mic_recognizer = sr.Recognizer()
            assistant.recognizer.microphone = sr.Microphone()
            with assistant.recognizer.microphone as source:
                mic_recognizer.adjust_for_ambient_noise(source, duration=1)
                print("✅ Microphone initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize microphone: {e}")
        print("⚠️ Switching to text mode...")
        input_mode = "text"
        display_prompt()
        return

    # Main voice input loop
    while running:
        try:
            if input_mode == "voice" and assistant.recognizer:
                # Display voice mode banner
                print("\n" + "=" * 80)
                print("🎤 VOICE MODE ACTIVE - READY FOR COMMANDS")
                print("=" * 80)
                print(f"\n{VOICE_PROMPT}")
                print("=" * 80)
                sys.stdout.flush()

                try:
                    # Create a new recognizer instance each time
                    import speech_recognition as sr
                    recognizer = sr.Recognizer()
                    microphone = sr.Microphone()

                    with microphone as source:
                        print("\n🎤 LISTENING NOW... (Speak your command clearly)")
                        print("-" * 80)
                        sys.stdout.flush()

                        # Optimize recognition settings for better responsiveness
                        recognizer.energy_threshold = 300  # Much lower threshold for better sensitivity
                        recognizer.dynamic_energy_threshold = True
                        recognizer.dynamic_energy_adjustment_damping = 0.15
                        recognizer.dynamic_energy_ratio = 1.5
                        recognizer.pause_threshold = 0.3  # Shorter pause threshold
                        recognizer.phrase_threshold = 0.1  # Shorter phrase threshold
                        recognizer.non_speaking_duration = 0.1  # Shorter non-speaking duration

                        # Quick ambient noise adjustment
                        recognizer.adjust_for_ambient_noise(source, duration=0.5)

                        # Listen for command with shorter timeouts
                        audio = recognizer.listen(
                            source,
                            timeout=3,  # Shorter timeout
                            phrase_time_limit=5  # Shorter phrase time limit
                        )

                        print("\n🔍 RECOGNIZING SPEECH...")
                        print("-" * 80)
                        sys.stdout.flush()

                        # Try Google's speech recognition service with optimized settings
                        text = recognizer.recognize_google(
                            audio,
                            language="en-US",
                            show_all=False
                        ).lower()

                        # Clean up and normalize the recognized text
                        text = text.strip()

                        # Handle common URL recognition issues
                        text = text.replace("dot com", ".com")
                        text = text.replace("dot in", ".in")
                        text = text.replace("dot org", ".org")
                        text = text.replace("dot net", ".net")
                        text = text.replace("dot co", ".co")
                        text = text.replace("dot", ".")

                        # Handle common command variations with proper spacing
                        if "go to" in text:
                            text = text.replace("go to", "goto ")
                        if "navigate to" in text:
                            text = text.replace("navigate to", "goto ")
                        if "open" in text:
                            text = text.replace("open", "goto ")
                        if "visit" in text:
                            text = text.replace("visit", "goto ")

                        # Apply domain name corrections only for actual misrecognitions of redberyltest
                        for wrong, correct in DOMAIN_CORRECTIONS.items():
                            if wrong in text:
                                text = text.replace(wrong, correct)
                                print(f"\nℹ️ Corrected domain name from '{wrong}' to '{correct}'")

                        # Ensure proper spacing in URLs
                        if "goto" in text:
                            # Split the command and URL
                            parts = text.split("goto")
                            if len(parts) == 2:
                                command = parts[0].strip()
                                url = parts[1].strip()
                                # Ensure there's a space after goto
                                text = f"{command}goto {url}"

                        # Display the recognized text
                        print("\n" + "*" * 60)
                        print("*" + " " * 58 + "*")
                        print("*" + f"🎯 RECOGNIZED COMMAND: \"{text}\"".center(58) + "*")
                        print("*" + " " * 58 + "*")
                        print("*" * 60)
                        sys.stdout.flush()

                        if text:
                            # Handle mode switching commands
                            if text.lower() in ["text", "switch to text", "switch to text mode"]:
                                input_mode = "text"
                                print(f"\n{TEXT_MODE_SWITCH_MESSAGE}")
                                display_prompt()
                                continue

                            # Add command to queue for processing
                            command_queue.put(text)
                            print(f"📥 Added to command queue: \"{text}\"")
                            print(f"⏱️ Command will be processed momentarily...")
                            sys.stdout.flush()

                except sr.UnknownValueError:
                    print("\n❌ SPEECH NOT RECOGNIZED. Please try again.")
                    print("\nTips for better recognition:")
                    print("- Speak clearly and directly into the microphone")
                    print("- Reduce background noise if possible")
                    print("- Try speaking at a moderate pace")
                    print("- Make sure you're speaking within 3 seconds of seeing 'LISTENING NOW...'")
                    print("- For URLs, say 'dot' instead of '.' (e.g., 'redberyltest dot in')")
                    print("- For 'redberyltest', say it slowly and clearly")
                    sys.stdout.flush()

                    # Try one more time with different settings
                    try:
                        print("\n🔄 Trying again with different settings...")
                        # Adjust settings for another attempt
                        recognizer.energy_threshold = 4000  # Higher threshold
                        recognizer.dynamic_energy_threshold = True

                        with microphone as source:
                            print("Please speak your command again...")
                            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                            text = recognizer.recognize_google(audio).lower()
                            print(f"🎯 Successfully recognized on retry: \"{text}\"")

                            # Process the retry command
                            if text:
                                command_queue.put(text)
                                print(f"📥 Added to command queue: \"{text}\"")
                                print(f"⏱️ Command will be processed momentarily...")
                                sys.stdout.flush()
                    except:
                        print("\nRetry failed. Please try again.")

                except sr.RequestError as e:
                    print(f"\n❌ SPEECH RECOGNITION SERVICE ERROR: {e}")
                    print("This could be due to network issues or problems with the Google Speech API.")
                    sys.stdout.flush()

                except Exception as e:
                    print(f"\n⚠️ Error in voice recognition: {e}")
                    import traceback
                    traceback.print_exc()
                    sys.stdout.flush()

                # Add a small delay to prevent CPU overload
                time.sleep(0.1)
            else:
                # If not in voice mode, just sleep a bit
                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\nKeyboard interrupt detected. Exiting...")
            command_queue.put("exit")
            running = False
            break
        except Exception as e:
            print(f"Error in voice input thread: {e}")
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            time.sleep(0.1)

async def process_commands(assistant):
    """Process commands from the queue"""
    global running, input_mode

    while running:
        try:
            # Get command from queue with timeout
            try:
                command = command_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if command.lower() == "exit":
                print("\nExiting...")
                running = False
                break

            # Process the command
            await assistant.process_command(command)

            # Force the recognizer to start listening immediately
            if assistant.recognizer:
                print("\n🎤 LISTENING NOW... (Speak your command)", flush=True)
                try:
                    # Start listening in a non-blocking way
                    await assistant._listen_voice()
                except Exception as e:
                    print(f"Error in voice recognition: {e}")
                    import traceback
                    traceback.print_exc()

        except Exception as e:
            print(f"Error processing command: {e}")
            import traceback
            traceback.print_exc()

async def main():
    """Main entry point"""
    global running, input_mode

    try:
        print("\n==== Starting Voice Assistant ====")
        print("Initializing components...")

        # Initialize the assistant
        assistant = SimpleVoiceAssistant()
        print("Assistant instance created")

        # Get input mode from user
        print("\n🔊 Select input mode:")
        print("1. Voice")
        print("2. Text")
        choice = input("Choice (1/2): ").strip()
        input_mode = "voice" if choice == "1" else "text"
        print(f"\n⌨️  Starting in {input_mode} mode")

        # Initialize the assistant first
        print("\n==== Initializing Browser and Components ====")
        print("This may take a moment...")
        logger.info("Initializing assistant...")

        try:
            init_success = await assistant.initialize()
            if not init_success:
                logger.error("Failed to initialize assistant")
                print("\n❌ Failed to initialize assistant. Check logs for details.")
                return
        except Exception as e:
            print(f"\n❌ Error during initialization: {e}")
            import traceback
            traceback.print_exc()
            return

        print("\n✅ Browser initialized successfully!")
        logger.info("Assistant initialized successfully, running main loop...")

        # Run the assistant
        print("\n==== Starting Main Loop ====")

        # Set the ready event
        assistant.ready_event.set()
        print("\n✅ Assistant ready event set")

        # Main loop for commands
        running = True
        while running:
            try:
                if input_mode == "voice":
                    # Initialize microphone for each attempt
                    try:
                        with assistant.microphone as source:
                            print("\n🎤 Initializing microphone...")
                            sys.stdout.flush()

                            # Adjust for ambient noise
                            print("Adjusting for ambient noise (2 seconds)...")
                            assistant.recognizer.adjust_for_ambient_noise(source, duration=2)
                            print(f"Energy threshold set to: {assistant.recognizer.energy_threshold}")
                            sys.stdout.flush()

                            # Clear visual prompt
                            print("\n" + "=" * 80)
                            print("🎤 READY FOR VOICE COMMAND...".center(80))
                            print("Speak clearly into your microphone".center(80))
                            print("=" * 80 + "\n")
                            sys.stdout.flush()

                            try:
                                # Listen for command with shorter timeouts
                                audio = assistant.recognizer.listen(
                                    source,
                                    timeout=5,
                                    phrase_time_limit=10
                                )

                                # Process the audio
                                try:
                                    command = assistant.recognizer.recognize_google(
                                        audio,
                                        language="en-US"
                                    )

                                    if command:
                                        print(f"\n🎤 Recognized: {command}")
                                        await assistant.process_command(command)

                                        # Show ready prompt
                                        print("\n" + "=" * 80)
                                        print("🎤 READY FOR NEXT COMMAND...".center(80))
                                        print("=" * 80 + "\n")
                                        sys.stdout.flush()

                                except sr.UnknownValueError:
                                    print("\n❌ Could not understand audio")
                                    print("Please try speaking more clearly")
                                    sys.stdout.flush()
                                except sr.RequestError as e:
                                    print(f"\n❌ Error with speech recognition service: {e}")
                                    sys.stdout.flush()

                            except sr.WaitTimeoutError:
                                print("\n⏱️ No speech detected")
                                print("Please try speaking again")
                                sys.stdout.flush()

                    except Exception as e:
                        print(f"\n❌ Error with microphone: {e}")
                        print("Trying to reinitialize...")
                        sys.stdout.flush()
                        await asyncio.sleep(1)

                else:
                    # Text mode
                    print("\nType your command (or 'help' for available commands):")
                    command = input("> ").strip()

                    if command.lower() == "exit":
                        print("\nExiting...")
                        running = False
                        break
                    elif command.lower() == "voice":
                        print("\nSwitching to voice mode...")
                        input_mode = "voice"
                        continue
                    elif command:
                        await assistant.process_command(command)

            except Exception as e:
                print(f"\n❌ Error in main loop: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(1)

    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
    finally:
        running = False
        print("\n🛑 Shutting down...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        import traceback

        logger.error(f"aFatal error: {e}")
        traceback.print_exc()