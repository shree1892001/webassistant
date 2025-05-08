import asyncio
import logging
from typing import Optional, Dict, Any, Callable
import json
import google.generativeai as genai
from playwright.async_api import Page
from  webassist.Common.constants import *
import re
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from voice_assistant.core.config import ConfigManager
from voice_assistant.core.speech import SpeechEngine
from voice_assistant.core.voice_engine import VoiceEngine
from voice_assistant.core.browser_manager import BrowserManager
from voice_assistant.core.plugin import PluginManager, BasePlugin
from  voice_assistant.utils.constants import DEFAULT_CONFIG

class CommandProcessor:
    """LLM-based command processor for natural language understanding"""
    
    def __init__(self):
        # Initialize Gemini
        genai.configure(api_key=DEFAULT_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.base_prompt = """
        You are a command analyzer that understands natural language commands for a web assistant.
        Your task is to analyze user commands and determine:
        1. The intent of the command
        2. The action to take
        3. The parameters needed for the action
        
        Common command patterns include:
        - Navigation: "go to", "visit", "open", "navigate to" followed by a URL
        - Text Input: "enter", "type", "input", "fill" followed by text and optionally a field type
        - Button Actions: "click", "press", "select", "tap" followed by button identifier
        - Mode Switching: "switch to", "change to", "use" followed by mode type
        
        Return a JSON object with:
        {
            "intent": "The main purpose of the command",
            "action": "The specific action to take",
            "target": "The element to interact with",
            "parameters": {
                "text": "Text to enter if applicable",
                "url": "URL to navigate to if applicable",
                "selector": "CSS selector to find the element if applicable"
            },
            "confidence": "A score between 0 and 1 indicating confidence in the analysis"
        }
        """

    async def detect_command(self, command: str) -> Dict[str, Any]:
        """Detect command type and extract parameters"""
        try:
            # Configure generation parameters
            generation_config = {
                "temperature": 0.1,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 200,
            }
            
            # Create prompt for Gemini
            prompt = f"""
            {self.base_prompt}
            
            Analyze this command: "{command}"
            
            Consider:
            1. The context of web interactions
            2. Common web actions (navigation, form filling, button clicking)
            3. Natural language variations
            4. Implicit meanings and context
            5. Common typos and variations in command words
            """
            
            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Extract JSON from response
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            try:
                result = json.loads(response_text)
                logger.info(f"Command analysis result: {result}")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response: {response_text}")
                return {
                    "intent": "unknown",
                    "action": "unknown",
                    "target": "unknown",
                    "parameters": {},
                    "confidence": 0.0
                }
                
        except Exception as e:
            logger.error(f"Error in command detection: {e}")
            return {
                "intent": "unknown",
                "action": "unknown",
                "target": "unknown",
                "parameters": {},
                "confidence": 0.0
            }

    async def suggest_action(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest how to execute a command"""
        try:
            # For login form fields, use specific selectors
            if analysis["target"].lower() in ["email", "email field", "email address", "email address field", "email input field"]:
                return {
                    "action": "fill",
                    "selector": "#floating_outlined3",
                    "parameters": {
                        "text": analysis["parameters"]["text"]
                    },
                    "confidence": 0.9
                }
            elif analysis["target"].lower() in ["password", "password field"]:
                return {
                    "action": "fill",
                    "selector": "#floating_outlined15",
                    "parameters": {
                        "text": analysis["parameters"]["text"]
                    },
                    "confidence": 0.9
                }
            elif analysis["target"].lower() in ["login", "login button", "sign in", "sign in button"]:
                return {
                    "action": "click",
                    "selector": "#signInButton, .signup-btn, button[type='submit'], button.blue-btnnn:has-text('Login/Register'), a:has-text('Login/Register'), button:has-text('Login'), button:has-text('Sign in'), a:has-text('Login'), a:has-text('Sign in'), .login-button, .signin-button, button[type='button']:has-text('Login'), button[type='button']:has-text('Sign in')",
                    "parameters": {},
                    "confidence": 0.9
                }
            
            # For other commands, use Gemini's suggestion
            action_prompt = f"""
            Given this command analysis:
            Action: {analysis['action']}
            Target: {analysis['target']}
            Parameters: {analysis['parameters']}
            
            Suggest how to execute this command using Playwright.
            Consider:
            1. The type of action needed
            2. How to find the target element
            3. What parameters to use
            
            Return a JSON object with:
            {{
                "action": "The Playwright action to take (click, fill, goto, etc.)",
                "selector": "The CSS selector to find the element",
                "parameters": {{
                    "text": "Text to enter if applicable",
                    "url": "URL to navigate to if applicable"
                }},
                "confidence": "Confidence score (0-1)"
            }}
            
            IMPORTANT: Do not include any comments in the JSON response.
            """
            
            response = self.model.generate_content(
                action_prompt,
                generation_config={"temperature": 0.1}
            )
            
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Remove any comments from the JSON
            response_text = re.sub(r'//.*$', '', response_text, flags=re.MULTILINE)
            
            try:
                result = json.loads(response_text)
                logger.info(f"Action suggestion result: {result}")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response: {response_text}")
                # Return a default action for email fields if parsing fails
                if analysis["target"].lower() in ["email", "email field", "email address", "email address field", "email input field"]:
                    return {
                        "action": "fill",
                        "selector": "#floating_outlined3",
                        "parameters": {
                            "text": analysis["parameters"]["text"]
                        },
                        "confidence": 0.9
                    }
                return {
                    "action": "unknown",
                    "selector": "",
                    "parameters": {},
                    "confidence": 0.0
                }
                
        except Exception as e:
            logger.error(f"Error in action suggestion: {e}")
            # Return a default action for email fields if an error occurs
            if analysis["target"].lower() in ["email", "email field", "email address", "email address field", "email input field"]:
                return {
                    "action": "fill",
                    "selector": "#floating_outlined3",
                    "parameters": {
                        "text": analysis["parameters"]["text"]
                    },
                    "confidence": 0.9
                }
            return {
                "action": "unknown",
                "selector": "",
                "parameters": {},
                "confidence": 0.0
            }

class ActionExecutor:
    """Executes actions on the browser page"""
    
    def __init__(self, page: Page, browser_manager: BrowserManager, config_manager: ConfigManager, speak_callback: Optional[Callable[[str], None]] = None):
        """Initialize the action executor"""
        self.page = page
        self.browser_manager = browser_manager
        self.config_manager = config_manager
        self.speak = speak_callback or (lambda _: None)  # Default to no-op if no callback provided
        logger.info("ActionExecutor initialized")

    async def execute_goto(self, url: str) -> bool:
        """Execute navigation action"""
        if not url:
            return False
        
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        try:
            success = await self.browser_manager.navigate(url)
            return success
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            return False
    
    async def execute_click(self, selector: str, target: str) -> bool:
        """Execute click action"""
        try:
            # Split the selector string into individual selectors
            selectors = [s.strip() for s in selector.split(',')]
            
            # Try each selector until one works
            for sel in selectors:
                try:
                    element = await self.page.wait_for_selector(sel, timeout=5000)
                    if element:
                        await element.click()
                        return True
                except Exception:
                    continue
            
            return False
        except Exception as e:
            logger.error(f"Error clicking element: {e}")
            return False
    
    async def execute_fill(self, selector: str, text: str) -> bool:
        """Execute fill action"""
        try:
            # First check if we're dealing with the email field
            if selector == "#floating_outlined3":
                # First try to find the email field
                try:
                    element = await self.page.wait_for_selector(selector, timeout=5000)
                    if not element or not await element.is_visible():
                        # If email field is not visible, try to find and click the login button
                        self.speak("Email field not found. Looking for login button...")
                        login_button = await self.page.wait_for_selector("#signInButton, .signup-btn, button[type='submit'], button.blue-btnnn:has-text('Login/Register'), a:has-text('Login/Register'), button:has-text('Login'), button:has-text('Sign in'), a:has-text('Login'), a:has-text('Sign in'), .login-button, .signin-button, button[type='button']:has-text('Login'), button[type='button']:has-text('Sign in')", timeout=5000)
                        if login_button:
                            self.speak("Found login button. Clicking it...")
                            await login_button.click()
                            # Wait for the form to appear with a longer timeout
                            try:
                                await self.page.wait_for_selector(selector, timeout=10000)
                            except Exception as e:
                                self.speak("Form is taking longer to appear. Please wait...")
                                # Try one more time with an even longer timeout
                                await self.page.wait_for_selector(selector, timeout=15000)
                except Exception as e:
                    # If we can't find the email field, try to find and click the login button
                    self.speak("Email field not found. Looking for login button...")
                    login_button = await self.page.wait_for_selector("#signInButton, .signup-btn, button[type='submit'], button.blue-btnnn:has-text('Login/Register'), a:has-text('Login/Register'), button:has-text('Login'), button:has-text('Sign in'), a:has-text('Login'), a:has-text('Sign in'), .login-button, .signin-button, button[type='button']:has-text('Login'), button[type='button']:has-text('Sign in')", timeout=5000)
                    if login_button:
                        self.speak("Found login button. Clicking it...")
                        await login_button.click()
                        # Wait for the form to appear with a longer timeout
                        try:
                            await self.page.wait_for_selector(selector, timeout=10000)
                        except Exception as e:
                            self.speak("Form is taking longer to appear. Please wait...")
                            # Try one more time with an even longer timeout
                            await self.page.wait_for_selector(selector, timeout=15000)
            
            # Now try to find and fill the element
            element = await self.page.wait_for_selector(selector, timeout=5000)
            if element:
                # Clear the field first
                await element.fill("")
                # Fill with the new text
                await element.fill(text)
                # Trigger input and change events
                await element.evaluate("el => el.dispatchEvent(new Event('input', { bubbles: true }))")
                await element.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
                return True
            return False
        except Exception as e:
            logger.error(f"Error filling element: {e}")
            self.speak("Could not find the input field. Please try again.")
            return False
    
    async def execute_switch_mode(self, mode: str) -> bool:
        """Execute mode switch action"""
        if mode in ["voice", "text"]:
            self.config_manager.set('input_mode', mode)
            return True
        return False

class VoiceAssistant:
    """Main voice assistant class that coordinates all components"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the voice assistant"""
        try:
            logger.info("Initializing VoiceAssistant...")
            # Initialize configuration
            self.config_manager = ConfigManager()
            self.config = {**DEFAULT_CONFIG, **(config or {})}

            # Set browser to non-headless mode
            if 'browser' not in self.config:
                self.config['browser'] = {}
            self.config['browser']['headless'] = False
            self.config_manager.update(self.config)

            # Initialize components
            self.voice_engine = VoiceEngine(self.config_manager.get('voice'))
            self.browser_manager = BrowserManager(self.config_manager.get('browser'))
            self.plugin_manager = PluginManager(self.config_manager.get('plugins'))
            self.input_mode = self.config_manager.get('input_mode', 'text')
            self.command_processor = CommandProcessor()
            self.action_executor = None  # Will be initialized after browser setup

            logger.info("VoiceAssistant initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing VoiceAssistant: {e}")
            raise

    async def initialize(self) -> None:
        """Initialize all components"""
        try:
            logger.info("Starting initialization...")
        # Initialize browser
        await self.browser_manager.initialize()
            self.page = self.browser_manager.page
            
            # Initialize speech engine
            self.speech = SpeechEngine(self.config_manager.get('speech'))
            
            # Initialize voice engine and speak method
            self.voice_engine = VoiceEngine(self.config_manager.get('voice'))
            self.speak = self.voice_engine.speak
            
            # Initialize action executor with speak callback
            self.action_executor = ActionExecutor(
                page=self.page,
                browser_manager=self.browser_manager,
                config_manager=self.config_manager,
                speak_callback=self.speak
            )
        
        # Initialize plugins
        self._initialize_plugins()
        
            logger.info(f"🚀 Assistant initialized in {self.input_mode} mode")
        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            raise

    def _initialize_plugins(self) -> None:
        """Initialize and register all plugins"""
        from voice_assistant.plugins.dropdown_plugin import DropdownPlugin
        from voice_assistant.plugins.state_plugin import StatePlugin
        from voice_assistant.plugins.entity_plugin import EntityPlugin
        from voice_assistant.plugins.product_plugin import ProductPlugin
        from voice_assistant.plugins.address_plugin import AddressPlugin

        # Register all plugins
        self.plugin_manager.register_plugin('dropdown', DropdownPlugin(self.page, self.speech))
        self.plugin_manager.register_plugin('state', StatePlugin(self.page, self.speech))
        self.plugin_manager.register_plugin('entity', EntityPlugin(self.page, self.speech))
        self.plugin_manager.register_plugin('product', ProductPlugin(self.page, self.speech))
        self.plugin_manager.register_plugin('address', AddressPlugin(self.page, self.speech))

    async def close(self, keep_browser_open: bool = False) -> None:
        """Close all components"""
        self.voice_engine.close()
        await self.browser_manager.close(keep_browser_open)

    def speak(self, text: str) -> None:
        """Speak text using voice engine"""
        self.voice_engine.speak(text)

    async def listen(self) -> str:
        """Listen for input based on current mode"""
        if self.input_mode == "voice":
            return self.voice_engine.listen()
        else:
            return self._listen_text()

    def _listen_text(self) -> str:
        """Listen for text input"""
        try:
            text = input("\n⌨️ Command: ").strip()
            if text.lower() in ["voice", "voice mode"]:
                self.input_mode = 'voice'
                self.config_manager.set('input_mode', 'voice')
                print("Voice mode activated")
            return text
        except Exception as e:
            print(f"Input error: {e}")
            return ""

    async def process_command(self, command: str) -> bool:
        """Process a command using LLM-based detection"""
        try:
            # Use Gemini to detect command type and parameters
            analysis = await self.command_processor.detect_command(command)
            
            if analysis["confidence"] < 0.5:
                self.speak("I'm not sure what you want me to do. Please try again or say 'help' for available commands.")
                return False
            
            # Get action suggestion from Gemini
            action_suggestion = await self.command_processor.suggest_action(analysis)
            
            if action_suggestion["confidence"] < 0.5:
                self.speak("I'm not sure how to execute that command. Please try again or say 'help' for available commands.")
                return False
            
            action_type = action_suggestion["action"].lower()
            selector = action_suggestion["selector"]
            action_params = action_suggestion["parameters"]
            
            # Execute the suggested action
            success = False
            if action_type == "goto":
                url = action_params.get("url", "")
                if not url:
                    self.speak("Please specify a website to navigate to")
                    return False
                success = await self.action_executor.execute_goto(url)
                if success:
                    self.speak(f"Navigating to {url}")
                else:
                    self.speak("Sorry, I couldn't navigate to that website")
                    
            elif action_type == "click":
                success = await self.action_executor.execute_click(selector, analysis["target"])
                if success:
                    self.speak(f"Clicked the {analysis['target']} button")
                else:
                    self.speak(f"Could not find the {analysis['target']} button")
                    
            elif action_type == "fill":
                text = action_params.get("text", "")
                if not text:
                    self.speak("Please specify what text to enter")
                    return False
                success = await self.action_executor.execute_fill(selector, text)
                if success:
                    self.speak(f"Entered {text}")
                else:
                    self.speak("Could not find the input field")
                    
            elif action_type == "fill and submit" and analysis["intent"] == "User Authentication":
                # First try to find and click the login button to show the form
                login_button = await self.page.wait_for_selector("#signInButton, .signup-btn, button[type='submit']", timeout=5000)
                if login_button:
                    await login_button.click()
                    # Wait for the form to appear
                    await self.page.wait_for_selector("#floating_outlined3", timeout=5000)
                
                # Fill email
                email_success = await self.action_executor.execute_fill("#floating_outlined3", "shreyas.deodhare@redberyltech.com")
                if not email_success:
                    self.speak("Could not find the email field")
                    return False
                
                # Fill password
                password_success = await self.action_executor.execute_fill("#floating_outlined15", "Shreyas@123")
                if not password_success:
                    self.speak("Could not find the password field")
                    return False
                
                # Click login button
                submit_success = await self.action_executor.execute_click("#signInButton, .signup-btn, button[type='submit']", "login")
                if submit_success:
                    self.speak("Login successful")
                    return True
                else:
                    self.speak("Could not find the login button")
                    return False
            elif action_type == "switch_mode":
                mode = action_params.get("mode", "")
                success = await self.action_executor.execute_switch_mode(mode)
                if success:
                    self.speak(f"Switched to {mode} mode")
                else:
                    self.speak("Invalid mode specified")
                    
            else:
                self.speak("I don't know how to execute that action")
                return False
                
            return success
                
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            self.speak("Sorry, I couldn't process that command")
            return False

    def _show_help(self) -> None:
        """Show available commands"""
        help_text = [
            "I can help you with:",
            "1. Navigation:",
            "   - 'go to [website]' or 'open [website]'",
            "   - 'visit [website]' or 'navigate to [website]'",
            "2. Text Input:",
            "   - 'enter [text]' or 'type [text]'",
            "   - 'input [text]' or 'fill [text]'",
            "   - 'enter email [email]' or 'type username [username]'",
            "3. Button Actions:",
            "   - 'click [button]' or 'press [button]'",
            "   - 'select [button]' or 'tap [button]'",
            "4. Mode Switching:",
            "   - 'switch to voice' or 'voice mode'",
            "   - 'switch to text' or 'text mode'",
            "5. Other Commands:",
            "   - 'help' or 'what can you do'",
            "   - 'exit' or 'quit'"
        ]
        
        if self.input_mode == "voice":
            for line in help_text:
                self.speak(line)
        else:
            print("\n".join(help_text))

    def register_plugin(self, name: str, plugin: BasePlugin) -> None:
        """Register a new plugin"""
        self.plugin_manager.register_plugin(name, plugin)

    def unregister_plugin(self, name: str) -> None:
        """Unregister a plugin"""
        self.plugin_manager.unregister_plugin(name)

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update configuration"""
        self.config_manager.update(new_config)
        self.config = self.config_manager.config

async def main():
    try:
        logger.info("Starting Voice Assistant...")
        assistant = VoiceAssistant()
        await assistant.initialize()
        
        print("Welcome to the Voice Assistant!")
        print("Choose your input mode:")
        print("1. Voice Mode")
        print("2. Text Mode")
        
        while True:
            try:
                mode_choice = input("Enter your choice (1 or 2): ").strip()
                if mode_choice == "1":
                    assistant.input_mode = "voice"
                    print("Voice mode activated. Speak your commands.")
                    break
                elif mode_choice == "2":
                    assistant.input_mode = "text"
                    print("Text mode activated. Type your commands.")
                    break
                else:
                    print("Invalid choice. Please enter 1 or 2.")
            except KeyboardInterrupt:
                print("\nGoodbye!")
                return
            except Exception as e:
                logger.error(f"Error selecting mode: {e}")
                print("Error selecting mode. Please try again.")
        
        while True:
            try:
                if assistant.input_mode == "voice":
                    print("\nListening... (Press Ctrl+C to stop)")
                    command = await assistant.voice_engine.listen()
                    print(f"You said: {command}")
                else:
                    command = input("\nEnter command: ").strip()
                
                if not command:
                    continue
                
                if command.lower() in ["exit", "quit", "bye"]:
                    print("Goodbye!")
                    break
                
                if command.lower() in ["help", "what can you do"]:
                    assistant._show_help()
                    continue
                
                if command.lower() in ["voice", "voice mode"]:
                    assistant.input_mode = "voice"
                    print("Switched to voice mode")
                    continue
                
                if command.lower() in ["text", "text mode"]:
                    assistant.input_mode = "text"
                    print("Switched to text mode")
                    continue
                
            if not await assistant.process_command(command):
                    print("Command processing failed. Type 'help' for available commands.")

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                logger.error(f"Error processing command: {e}")
                print("An error occurred. Please try again.")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        try:
        await assistant.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    try:
    asyncio.run(main()) 
    except Exception as e:
        logger.error(f"Fatal error in main: {e}") 