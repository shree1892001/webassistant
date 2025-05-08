"""
Core assistant module for WebAssist
"""

import logging
from typing import Dict, Any, List

from webassist.core.config import AssistantConfig
from webassist.Common.constants import (
    DEFAULT_START_URL,
    EXIT_COMMANDS,
    HELP_COMMAND,
    VOICE_MODE,
    TEXT_MODE
)
from webassist.speech.recognizer import create_recognizer
from webassist.speech.synthesizer import create_synthesizer
from webassist.web.browser import WebBrowser
from webassist.web.navigator import WebNavigator
from webassist.web.interactor import WebInteractor
from webassist.llm.provider import LLMProviderFactory
from webassist.commands.command import CommandRegistry
from webassist.commands.navigation import (
    NavigationCommand,
    BackCommand,
    ForwardCommand,
    RefreshCommand
)
from webassist.commands.interaction import (
    SearchCommand,
    LoginCommand,
    MenuClickCommand,
    SubmenuCommand,
    CheckboxCommand,
    DropdownCommand,
    StateSelectionCommand
)


class Assistant:
    """Core assistant class"""

    def __init__(self, config: AssistantConfig):
        """Initialize the assistant"""
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.synthesizer = create_synthesizer(config)
        self.input_mode = self._get_initial_mode()
        self.recognizer = create_recognizer(config, self.input_mode)

        # Initialize browser
        self.browser = WebBrowser(config)
        self.page = None

        # Initialize LLM provider
        self.llm_provider = LLMProviderFactory.create_provider(
            "gemini",
            config.gemini_api_key,
            config.llm_model
        )

        # Initialize web components
        self.navigator = None
        self.interactor = None

        # Initialize command registry
        self.command_registry = CommandRegistry()

        print(f"🚀 Assistant initialized in {self.input_mode} mode")

    async def initialize(self):
        """Initialize async components"""
        # Start browser
        self.page = await self.browser.start()

        # Initialize web components
        self.navigator = WebNavigator(self.page, self.llm_provider, self.synthesizer)
        self.interactor = WebInteractor(self.page, self.llm_provider, self.synthesizer, self.config)

        # Register commands
        await self._register_commands()

    def _get_initial_mode(self) -> str:
        """Get the initial input mode"""
        print("\n🔊 Select input mode:")
        print("1. Voice\n2. Text")
        while True:
            choice = input("Choice (1/2): ").strip()
            return VOICE_MODE if choice == '1' else TEXT_MODE

    async def _register_commands(self) -> None:
        """Register commands"""
        # Navigation commands
        await self.command_registry.register(NavigationCommand(self.navigator))
        await self.command_registry.register(BackCommand(self.navigator))
        await self.command_registry.register(ForwardCommand(self.navigator))
        await self.command_registry.register(RefreshCommand(self.navigator))

        # Interaction commands
        await self.command_registry.register(SearchCommand(self.interactor, self.llm_provider, self.synthesizer))
        await self.command_registry.register(LoginCommand(self.interactor, self.llm_provider, self.synthesizer))
        await self.command_registry.register(MenuClickCommand(self.interactor, self.llm_provider, self.synthesizer))
        await self.command_registry.register(SubmenuCommand(self.interactor, self.llm_provider, self.synthesizer))
        await self.command_registry.register(CheckboxCommand(self.interactor, self.llm_provider, self.synthesizer))
        await self.command_registry.register(DropdownCommand(self.interactor, self.llm_provider, self.synthesizer))
        await self.command_registry.register(StateSelectionCommand(self.interactor))

    async def listen(self) -> str:
        """Listen for user input"""
        return await self.recognizer.listen()

    async def speak(self, text: str) -> None:
        """Speak to the user"""
        await self.synthesizer.speak(text)

    async def process_command(self, command: str) -> bool:
        """Process a command"""
        if not command:
            return True

        command_lower = command.lower()

        # Handle exit commands
        if command_lower in EXIT_COMMANDS:
            return False

        # Handle help command
        if command_lower == HELP_COMMAND:
            print("Showing help information...")
            await self._show_help()
            return True

        # Handle mode switching
        if command_lower in [VOICE_MODE, TEXT_MODE]:
            # Only switch if not already in that mode
            if self.input_mode != command_lower:
                self.input_mode = command_lower
                self.recognizer = create_recognizer(self.config, self.input_mode)
                await self.speak(f"Switched to {command_lower} mode")
                print(f"Switched to {command_lower} mode")
            return True

        # Process command using registry
        result = await self.command_registry.process(command)

        if not result.success:
            # If no command matched, try LLM-guided actions
            action_data = await self._get_actions(command)
            return await self._execute_actions(action_data)

        return result.success

    async def _get_actions(self, command: str) -> Dict[str, Any]:
        """Get actions from LLM"""
        page_context = await self.interactor._get_page_context()
        prompt = self._create_prompt(command, page_context)

        try:
            response = self.llm_provider.generate_content(prompt)
            print("🔍 Raw LLM response:\n", response.text)
            return self._parse_response(response.text)
        except Exception as e:
            print(f"LLM Error: {e}")
            return {"error": str(e)}

    def _create_prompt(self, command: str, context: Dict[str, Any]) -> str:
        """Create a prompt for the LLM"""
        input_fields_info = ""
        if "input_fields" in context and context["input_fields"]:
            input_fields_info = "Input Fields Found:\n"
            for idx, field in enumerate(context["input_fields"]):
                input_fields_info += f"{idx + 1}. {field['tag']} - type: {field['type']}, id: {field['id']}, name: {field['name']}, placeholder: {field['placeholder']}, aria-label: {field['aria-label']}\n"

        menu_items_info = ""
        if "menu_items" in context and context["menu_items"]:
            menu_items_info = "Menu Items Found:\n"
            for idx, item in enumerate(context["menu_items"]):
                submenu_indicator = " (has submenu)" if item.get("has_submenu") else ""
                menu_items_info += f"{idx + 1}. {item['text']}{submenu_indicator}\n"

        buttons_info = ""
        if "buttons" in context and context["buttons"]:
            buttons_info = "Buttons Found:\n"
            for idx, button in enumerate(context["buttons"]):
                buttons_info += f"{idx + 1}. {button['text']} - id: {button['id']}, class: {button['class']}, type: {button['type']}\n"

        return f"""Analyze the web page and generate precise Playwright selectors to complete: \"{command}\".

Selector Priority:
1. ID (
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

    def _parse_response(self, raw_response: str) -> Dict[str, Any]:
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

    async def _execute_actions(self, action_data: Dict[str, Any]) -> bool:
        """Execute actions"""
        if 'error' in action_data:
            await self.speak("⚠️ Action could not be completed. Switching to fallback...")
            return False

        for action in action_data.get('actions', []):
            try:
                await self._perform_action(action)
                await self.page.wait_for_timeout(1000)
            except Exception as e:
                await self.speak(f"❌ Failed to {action.get('purpose', 'complete action')}")
                print(f"Action Error: {str(e)}")
                return False
        return True

    async def _perform_action(self, action: Dict[str, Any]) -> None:
        """Perform an action"""
        action_type = action['action']

        if action_type == 'click':
            selector = action.get('selector', '')
            fallbacks = action.get('fallback_selectors', [])
            await self._try_selectors_for_click([selector] + fallbacks, action['purpose'])
        elif action_type == 'type':
            selector = action.get('selector', '')
            fallbacks = action.get('fallback_selectors', [])
            await self._try_selectors_for_type([selector] + fallbacks, action['text'], action['purpose'])
        elif action_type == 'navigate':
            url = action.get('url', '')
            if not url:
                purpose = action.get('purpose', '')
                nav_selectors = self._find_navigation_selectors(purpose)
                if nav_selectors:
                    for selector in nav_selectors:
                        try:
                            if await self.page.locator(selector).count() > 0:
                                await self._retry_click(selector, f"Navigate to {purpose}")
                                return
                        except:
                            continue
                await self.speak(f"Could not find a way to {purpose}.")
            else:
                await self.navigator.browse_website(url)
        elif action_type == 'hover':
            selector = action.get('selector', '')
            fallbacks = action.get('fallback_selectors', [])
            await self._try_selectors_for_hover([selector] + fallbacks, action['purpose'])
        elif action_type == 'select_option':
            selector = action.get('selector', '')
            option = action.get('option', '')
            fallbacks = action.get('fallback_selectors', [])
            await self._try_selectors_for_select([selector] + fallbacks, option, action['purpose'])
        elif action_type in ['check', 'uncheck', 'toggle']:
            selector = action.get('selector', '')
            fallbacks = action.get('fallback_selectors', [])
            await self._try_selectors_for_checkbox([selector] + fallbacks, action_type, action['purpose'])
        else:
            raise ValueError(f"Unknown action: {action_type}")

    async def _retry_click(self, selector: str, purpose: str) -> bool:
        """Retry clicking an element"""
        tries = 3
        for attempt in range(tries):
            try:
                await self.page.locator(selector).first.click(timeout=5000)
                await self.speak(f"👆 Clicked {purpose}")
                return True
            except Exception as e:
                if attempt == tries - 1:
                    raise e
                await self.page.wait_for_timeout(1000)
        return False

    async def _try_selectors_for_click(self, selectors: List[str], purpose: str) -> bool:
        """Try different selectors to click an element"""
        for selector in selectors:
            if not selector:
                continue

            try:
                if await self.page.locator(selector).count() > 0:
                    await self._retry_click(selector, purpose)
                    return True
            except Exception:
                continue

        page_context = await self.interactor._get_page_context()
        new_selectors = await self.llm_provider.get_selectors(f"find clickable element for {purpose}", page_context)

        for selector in new_selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    await self._retry_click(selector, purpose)
                    return True
            except:
                continue

        await self.speak(f"Could not find element to click for {purpose}")
        return False

    async def _try_selectors_for_hover(self, selectors: List[str], purpose: str) -> bool:
        """Try different selectors to hover over an element"""
        for selector in selectors:
            if not selector:
                continue

            try:
                if await self.page.locator(selector).count() > 0:
                    await self.page.locator(selector).first.hover()
                    await self.speak(f"🖱️ Hovering over {purpose}")
                    return True
            except Exception:
                continue

        page_context = await self.interactor._get_page_context()
        new_selectors = await self.llm_provider.get_selectors(f"find hoverable element for {purpose}", page_context)

        for selector in new_selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    await self.page.locator(selector).first.hover()
                    await self.speak(f"🖱️ Hovering over {purpose}")
                    return True
            except:
                continue

        await self.speak(f"Could not hover over {purpose}")
        return False

    async def _retry_type(self, selector: str, text: str, purpose: str) -> bool:
        """Retry typing text into an element"""
        tries = 3
        for attempt in range(tries):
            try:
                await self.page.locator(selector).first.fill(text)
                await self.speak(f"⌨️ Entered {purpose}")
                return True
            except Exception as e:
                if attempt == tries - 1:
                    raise e
                await self.page.wait_for_timeout(1000)
        return False

    async def _try_selectors_for_type(self, selectors: List[str], text: str, purpose: str) -> bool:
        """Try different selectors to type text into an element"""
        for selector in selectors:
            if not selector:
                continue

            try:
                if await self.page.locator(selector).count() > 0:
                    return await self._retry_type(selector, text, purpose)
            except Exception:
                continue

        page_context = await self.interactor._get_page_context()
        new_selectors = await self.llm_provider.get_selectors(f"find input field for {purpose}", page_context)

        for selector in new_selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    return await self._retry_type(selector, text, purpose)
            except:
                continue

        await self.speak(f"Could not find input field for {purpose}")
        return False

    async def _try_selectors_for_select(self, _: List[str], option: str, dropdown_name: str) -> bool:
        """Try different selectors to select an option from a dropdown"""
        # Delegate to interactor
        context = {
            "purpose": dropdown_name,
            "element_type": "dropdown",
            "action": "select",
            "value": option
        }
        return await self.interactor._handle_select(context)

    async def _try_selectors_for_checkbox(self, _: List[str], action: str, checkbox_label: str) -> bool:
        """Try different selectors to interact with a checkbox"""
        # Delegate to interactor
        context = {
            "purpose": checkbox_label,
            "element_type": "checkbox",
            "action": "checkbox",
            "value": action
        }
        return await self.interactor._handle_checkbox(context)

    def _find_navigation_selectors(self, target: str) -> List[str]:
        """Find navigation selectors based on target description"""
        selectors = []

        # Common navigation selectors
        selectors.append(f"a:has-text('{target}')")
        selectors.append(f"nav a:has-text('{target}')")
        selectors.append(f"header a:has-text('{target}')")
        selectors.append(f"[role='menuitem']:has-text('{target}')")
        selectors.append(f"button:has-text('{target}')")
        selectors.append(f".navlink:has-text('{target}')")
        selectors.append(f".menu-item:has-text('{target}')")

        return selectors

    async def _show_help(self) -> None:
        """Show available commands and usage examples"""
        help_text = """
    🔍 Voice Web Assistant Help:

    Basic Navigation:
    - "Go to [website]" - Navigate to a website
    - "Navigate to [section]" - Go to a specific section on the current site
    - "Click on [element]" - Click on a button, link, or other element
    - "Search for [query]" - Use the search function

    Forms:
    - "Type [text] in [field]" - Enter text in an input field
    - "Login with email [email] and password [password]" - Fill login forms
    - "Select [option] from [dropdown]" - Select from dropdown menus
    - "Check/uncheck [checkbox]" - Toggle checkboxes

    Menu Navigation:
    - "Click on menu item [name]" - Click on a menu item
    - "Navigate to [submenu] under [menu]" - Access submenu items

    Input Mode:
    - "Voice" - Switch to voice input mode
    - "Text" - Switch to text input mode

    General:
    - "Help" - Show this help message
    - "Exit" or "Quit" - Close the assistant
    """
        await self.speak("📋 Showing help")
        print(help_text)
        # Only speak the first part to avoid too much speech
        await self.synthesizer.speak("Here's the help information. You can see the full list on screen.")

    def _listen_text(self):
        """Listen for text input"""
        try:
            text = input("\n⌨️ Command: ").strip()
            if text.lower() in ["voice", "voice mode"]:
                self.input_mode = 'voice'
                # Just print a message since we can't await here
                print("Voice mode activated")
            return text
        except Exception as e:
            print(f"Input error: {e}")
            return ""

    async def run(self) -> None:
        """Run the assistant"""
        await self.speak("Web Assistant ready. Say 'help' for available commands.")

        # Start with Google
        print("Opening browser to Google...")
        await self.navigator.browse_website(DEFAULT_START_URL)
        print("Browser opened. Ready for commands.")
        print("Type 'help' for available commands or 'exit' to quit.")

        # Main command loop
        while True:
            try:
                # Handle input differently based on mode
                if self.input_mode == VOICE_MODE:
                    # For voice mode, use the async listen method
                    print("\n🎤 Listening...")
                    command = await self.listen()
                else:
                    # For text mode, use the _listen_text method
                    command = self._listen_text()

                # Handle empty command
                if not command:
                    print("Empty command received. Please try again.")
                    await self.speak("I didn't catch that. Please try again.")
                    continue

                # Echo the command for confirmation
                print(f"USER: '{command}'")

                # Process the command
                command_result = await self.process_command(command)
                print(f"Command processed: {'success' if command_result else 'failed'}")

                if not command_result:
                    if command.lower() in EXIT_COMMANDS:
                        await self.speak("Goodbye!")
                        print("Exiting assistant...")
                        break
                    else:
                        await self.speak("Something went wrong. Please try again.")

            except KeyboardInterrupt:
                print("\nKeyboard interrupt detected. Exiting...")
                await self.speak("Goodbye!")
                break
            except Exception as e:
                import traceback
                print(f"Error processing command: {e}")
                traceback.print_exc()
                await self.speak("Sorry, there was an error processing your command. Please try again.")

    async def close(self) -> None:
        """Close the assistant"""
        await self.browser.close()
