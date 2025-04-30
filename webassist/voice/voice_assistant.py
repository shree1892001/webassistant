import os
import re
import asyncio
import pyttsx3
from playwright.async_api import async_playwright
from webassist.Common.constants import *
from webassist.llm.provider import LLMProviderFactory
from webassist.core.config import AssistantConfig
from webassist.models.context import PageContext, InteractionContext
from webassist.models.result import InteractionResult
from typing import Dict, Any, List

# Import handlers and utilities
from webassist.voice.commands.login_handler import LoginHandler
from webassist.voice.commands.navigation_handler import NavigationHandler
from webassist.voice.commands.state_handler import StateHandler
from webassist.voice.commands.form_handler import FormHandler
from webassist.voice.utils.selector_utils import SelectorUtils
from webassist.voice.utils.context_utils import ContextUtils

class VoiceAssistant:
    def __init__(self, config=None):
        self.engine = None
        self.llm_provider = None
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        # Use provided config or create default
        self.config = config or AssistantConfig.from_env()

        # Initialize handlers and utilities
        self.login_handler = LoginHandler(self)
        self.navigation_handler = NavigationHandler(self)
        self.state_handler = StateHandler(self)
        self.form_handler = FormHandler(self)
        self.selector_utils = SelectorUtils(self)
        self.context_utils = ContextUtils(self)

    async def initialize(self):
        """Initialize components"""
        # Initialize text-to-speech
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', self.config.speech_rate)
        self.engine.setProperty('volume', self.config.speech_volume)

        # Initialize LLM provider
        api_key = self.config.gemini_api_key or os.environ.get("GEMINI_API_KEY", DEFAULT_API_KEY)
        self.llm_provider = LLMProviderFactory.create_provider("gemini", api_key, self.config.llm_model)

        # Initialize browser
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.config.browser_headless)
        self.context = await self.browser.new_context(
            viewport={'width': self.config.browser_width, 'height': self.config.browser_height}
        )
        self.page = await self.context.new_page()

        # Navigate to start URL
        await self.navigation_handler.browse_website(DEFAULT_START_URL)

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

    async def process_command(self, command):
        """Process a command"""
        print(f"DEBUG: Processing command: '{command}'")

        if command.lower() in EXIT_COMMANDS:
            self.speak("Goodbye! Browser will remain open for inspection.")
            return False

        if command.lower() == HELP_COMMAND:
            self.show_help()
            return True

        # Try navigation commands first
        if await self.navigation_handler.handle_navigation(command):
            return True

        # Try login commands
        if await self.login_handler.handle_login(command):
            return True

        # Try state selection commands
        if await self.state_handler.handle_state_selection(command):
            return True

        # Try form commands
        if await self.form_handler.handle_form_command(command):
            return True

        # For other commands, use LLM to generate actions
        action_data = await self._get_actions(command)
        return await self._execute_actions(action_data)

    def show_help(self):
        """Show help information"""
        help_text = """
        Available Commands:
        - Navigation:
          * "go to [URL]" or "navigate to [URL]" or "open [URL]"
          * "search for [query]"
        
        - Login:
          * "login with email [email] and password [password]"
        
        - Form Interaction:
          * "select [option] from [dropdown]"
          * "check [checkbox]"
          * "uncheck [checkbox]"
          * "toggle [checkbox]"
        
        - State Selection:
          * "select state [state name]"
          * "choose state [state name]"
          * "pick state [state name]"
        
        - Other:
          * "help" - Show this help message
          * "exit" or "quit" - Exit the assistant
        """
        self.speak(help_text)

    async def _get_actions(self, command: str) -> List[Dict[str, Any]]:
        """Get actions from LLM for a command"""
        try:
            # Get page context
            context = await self._get_page_context()

            # Prepare prompt for LLM
            prompt = f"""
            Command: {command}
            Page Context:
            - Title: {context.get('title', '')}
            - URL: {context.get('url', '')}
            - Visible Text: {context.get('visible_text', '')[:500]}...
            - Input Fields: {context.get('input_fields', {})}
            - Buttons: {context.get('buttons', [])}
            - Links: {context.get('links', [])}

            Please provide a list of actions to execute this command. Each action should be a dictionary with:
            - type: click, type, select, check, uncheck, etc.
            - selector: CSS selector to find the element
            - value: value to enter (for type actions)
            - description: what this action does
            Example: {{'type': 'click', 'selector': 'button[type="submit"]', 'description': 'Click submit button'}}
            """

            # Get response from LLM
            response = await self.llm_provider.generate_content(prompt)
            
            # Get the text content from the response
            response_text = response.text
            
            # Parse response into actions
            actions = []
            for line in response_text.split('\n'):
                if line.strip():
                    try:
                        # Try to parse the line as a dictionary
                        action = eval(line)  # Convert string to dict
                        if isinstance(action, dict) and 'type' in action and 'selector' in action:
                            actions.append(action)
                    except:
                        # If the line isn't a valid dictionary, try to extract an action
                        if 'type' in line and 'selector' in line:
                            try:
                                # Extract the action details using regex
                                import re
                                type_match = re.search(r"type':\s*'([^']*)'", line)
                                selector_match = re.search(r"selector':\s*'([^']*)'", line)
                                value_match = re.search(r"value':\s*'([^']*)'", line)
                                desc_match = re.search(r"description':\s*'([^']*)'", line)
                                
                                if type_match and selector_match:
                                    action = {
                                        'type': type_match.group(1),
                                        'selector': selector_match.group(1)
                                    }
                                    if value_match:
                                        action['value'] = value_match.group(1)
                                    if desc_match:
                                        action['description'] = desc_match.group(1)
                                    actions.append(action)
                            except:
                                continue

            return actions
        except Exception as e:
            print(f"Error getting actions: {e}")
            return []

    async def _execute_actions(self, actions):
        """Execute a list of actions"""
        for action in actions:
            try:
                action_type = action.get('type', '').lower()
                selector = action.get('selector', '')
                value = action.get('value', '')
                description = action.get('description', '')

                if not selector:
                    continue

                self.speak(f"Executing: {description}")

                if action_type == 'click':
                    await self.selector_utils.retry_click(selector, description)
                elif action_type == 'type':
                    await self.selector_utils.retry_type(selector, value, description)
                elif action_type == 'check':
                    await self.page.locator(selector).first.check()
                elif action_type == 'uncheck':
                    await self.page.locator(selector).first.uncheck()
                elif action_type == 'select':
                    await self.page.locator(selector).first.select_option(value)
                elif action_type == 'hover':
                    await self.page.locator(selector).first.hover()

                await self.page.wait_for_timeout(1000)
            except Exception as e:
                self.speak(f"Error executing action: {str(e)}")
                continue

        return True

    async def _get_llm_selectors(self, task: str, context_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get selectors for elements using LLM"""
        try:
            # Prepare prompt for LLM
            prompt = f"""
            Task: {task}
            Page Context:
            - Title: {context_dict.get('title', '')}
            - URL: {context_dict.get('url', '')}
            - Visible Text: {context_dict.get('visible_text', '')[:500]}...
            - Input Fields: {context_dict.get('input_fields', {})}
            - Buttons: {context_dict.get('buttons', [])}
            - Links: {context_dict.get('links', [])}

            Please provide a list of CSS selectors that would help identify the elements needed for this task.
            The selectors should be ordered by priority (most specific first).
            Format each selector as a dictionary with 'selector' and 'description' keys.
            Example: {{'selector': 'input[type="email"]', 'description': 'Email input field'}}
            """

            # Get response from LLM
            response = await self.llm_provider.generate_content(prompt)
            
            # Get the text content from the response
            response_text = response.text
            
            # Parse response into selectors
            selectors = []
            for line in response_text.split('\n'):
                if line.strip():
                    try:
                        # Try to parse the line as a dictionary
                        selector = eval(line)  # Convert string to dict
                        if isinstance(selector, dict) and 'selector' in selector:
                            selectors.append(selector)
                    except:
                        # If the line isn't a valid dictionary, try to extract a selector
                        if 'selector' in line:
                            try:
                                # Extract the selector and description using regex
                                import re
                                match = re.search(r"selector':\s*'([^']*)'.*description':\s*'([^']*)'", line)
                                if match:
                                    selector, description = match.groups()
                                    selectors.append({
                                        'selector': selector,
                                        'description': description
                                    })
                            except:
                                continue

            return selectors
        except Exception as e:
            print(f"Error getting LLM selectors: {e}")
            return []

    async def _get_page_context(self) -> Dict[str, Any]:
        """Get current page context including title, URL, and visible elements"""
        try:
            # Get basic page information
            title = await self.page.title()
            url = self.page.url
            
            # Get visible text content
            visible_text = await self.page.evaluate("""
                () => {
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    let text = '';
                    let node;
                    while (node = walker.nextNode()) {
                        if (node.parentElement && 
                            window.getComputedStyle(node.parentElement).display !== 'none' &&
                            node.parentElement.offsetParent !== null) {
                            text += node.textContent + ' ';
                        }
                    }
                    return text.trim();
                }
            """)
            
            # Get input fields
            input_fields = await self.page.evaluate("""
                () => {
                    const inputs = Array.from(document.querySelectorAll('input, textarea, select'));
                    return inputs.map(input => ({
                        type: input.type || input.tagName.toLowerCase(),
                        name: input.name || '',
                        id: input.id || '',
                        placeholder: input.placeholder || '',
                        value: input.value || ''
                    }));
                }
            """)
            
            # Get buttons
            buttons = await self.page.evaluate("""
                () => {
                    const buttons = Array.from(document.querySelectorAll('button, [role="button"], input[type="button"], input[type="submit"]'));
                    return buttons.map(button => ({
                        text: button.textContent.trim(),
                        type: button.type || button.tagName.toLowerCase(),
                        name: button.name || '',
                        id: button.id || ''
                    }));
                }
            """)
            
            # Get links
            links = await self.page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a'));
                    return links.map(link => ({
                        text: link.textContent.trim(),
                        href: link.href,
                        id: link.id || ''
                    }));
                }
            """)
            
            return {
                "title": title,
                "url": url,
                "visible_text": visible_text,
                "input_fields": input_fields,
                "buttons": buttons,
                "links": links
            }
        except Exception as e:
            print(f"Error getting page context: {e}")
            return {
                "title": "",
                "url": "",
                "visible_text": "",
                "input_fields": [],
                "buttons": [],
                "links": []
            }

    async def _check_for_input_fields(self) -> Dict[str, Any]:
        """Check for input fields on the current page"""
        try:
            # Get all input elements
            input_elements = await self.page.evaluate("""
                () => {
                    const inputs = Array.from(document.querySelectorAll('input, textarea, select'));
                    return inputs.map(input => ({
                        type: input.type || input.tagName.toLowerCase(),
                        name: input.name || '',
                        id: input.id || '',
                        placeholder: input.placeholder || '',
                        value: input.value || '',
                        label: (() => {
                            // Try to find associated label
                            if (input.id) {
                                const label = document.querySelector(`label[for="${input.id}"]`);
                                if (label) return label.textContent.trim();
                            }
                            // Try to find parent label
                            const parentLabel = input.closest('label');
                            if (parentLabel) return parentLabel.textContent.trim();
                            // Try to find preceding label
                            const prevLabel = input.previousElementSibling;
                            if (prevLabel && prevLabel.tagName.toLowerCase() === 'label') {
                                return prevLabel.textContent.trim();
                            }
                            return '';
                        })()
                    }));
                }
            """)
            
            # Group inputs by type
            input_fields = {
                'text': [],
                'email': [],
                'password': [],
                'select': [],
                'checkbox': [],
                'radio': [],
                'other': []
            }
            
            for input_elem in input_elements:
                input_type = input_elem['type'].lower()
                if input_type in input_fields:
                    input_fields[input_type].append(input_elem)
                else:
                    input_fields['other'].append(input_elem)
            
            return input_fields
        except Exception as e:
            print(f"Error checking for input fields: {e}")
            return {
                'text': [],
                'email': [],
                'password': [],
                'select': [],
                'checkbox': [],
                'radio': [],
                'other': []
            }

async def main():
    """Main entry point"""
    assistant = VoiceAssistant()
    await assistant.initialize()
    
    try:
        while True:
            command = input("Enter command (or 'exit' to quit): ")
            if not await assistant.process_command(command):
                break
    finally:
        await assistant.close(keep_browser_open=True)

if __name__ == "__main__":
    asyncio.run(main()) 