"""
Interaction commands for WebAssist
"""

import re
from typing import Dict, Any, List

from webassist.commands.command import Command
from webassist.web.interactor import WebInteractor
from webassist.models.result import InteractionResult
from webassist.models.context import InteractionContext
from webassist.llm.provider import LLMProvider
from webassist.speech.synthesizer import SpeechSynthesizer
from webassist.core.constants import (
    SEARCH_PATTERN,
    LOGIN_PATTERN,
    MENU_CLICK_PATTERN,
    SUBMENU_PATTERN,
    CHECKBOX_PATTERN,
    DROPDOWN_PATTERN,
    STATE_SELECTION_PATTERN
)


class SearchCommand(Command):
    """Command for searching on a website"""
    
    def __init__(self, interactor: WebInteractor, llm_provider: LLMProvider, speaker: SpeechSynthesizer):
        """Initialize the command"""
        super().__init__(re.compile(SEARCH_PATTERN, re.IGNORECASE))
        self.interactor = interactor
        self.llm_provider = llm_provider
        self.speaker = speaker
    
    async def execute(self, command_text: str, **kwargs) -> InteractionResult:
        """Execute the command"""
        match = self.pattern.match(command_text)
        if match:
            query = match.group(1)
            
            # Get page context
            page_context = await self.interactor._get_page_context()
            
            # Get selectors for search input
            search_selectors = self.llm_provider.get_selectors("find search input field", page_context)
            
            for selector in search_selectors:
                try:
                    if await self.interactor.page.locator(selector).count() > 0:
                        await self.interactor._retry_action(
                            self.interactor._type_text,
                            selector,
                            query,
                            "search query"
                        )
                        await self.interactor.page.locator(selector).press("Enter")
                        await self.speaker.speak(f"🔍 Searching for '{query}'")
                        await self.interactor.page.wait_for_timeout(3000)
                        return InteractionResult(
                            success=True,
                            message=f"Searched for '{query}'"
                        )
                except Exception as e:
                    continue
            
            return InteractionResult(
                success=False,
                message="Could not find search field"
            )
        
        return InteractionResult(
            success=False,
            message="Invalid search command"
        )


class LoginCommand(Command):
    """Command for logging in to a website"""
    
    def __init__(self, interactor: WebInteractor, llm_provider: LLMProvider, speaker: SpeechSynthesizer):
        """Initialize the command"""
        super().__init__(re.compile(LOGIN_PATTERN, re.IGNORECASE))
        self.interactor = interactor
        self.llm_provider = llm_provider
        self.speaker = speaker
    
    async def execute(self, command_text: str, **kwargs) -> InteractionResult:
        """Execute the command"""
        match = self.pattern.match(command_text)
        if match:
            email, password = match.groups()
            
            # Get page context
            page_context = await self.interactor._get_page_context()
            
            # Get selectors for email input
            email_selectors = self.llm_provider.get_selectors("find email or username input field", page_context)
            email_found = False
            
            for selector in email_selectors:
                try:
                    if await self.interactor.page.locator(selector).count() > 0:
                        await self.interactor._retry_action(
                            self.interactor._type_text,
                            selector,
                            email,
                            "email address"
                        )
                        email_found = True
                        break
                except Exception:
                    continue
            
            # Get selectors for password input
            password_selectors = self.llm_provider.get_selectors("find password input field", page_context)
            password_found = False
            
            for selector in password_selectors:
                try:
                    if await self.interactor.page.locator(selector).count() > 0:
                        await self.interactor._retry_action(
                            self.interactor._type_text,
                            selector,
                            password,
                            "password"
                        )
                        password_found = True
                        break
                except Exception:
                    continue
            
            if email_found and password_found:
                # Get selectors for login button
                login_button_selectors = self.llm_provider.get_selectors("find login or sign in button", page_context)
                
                for selector in login_button_selectors:
                    try:
                        if await self.interactor.page.locator(selector).count() > 0:
                            await self.interactor._retry_action(
                                self.interactor._click_element,
                                selector,
                                "login button"
                            )
                            return InteractionResult(
                                success=True,
                                message="Logged in successfully"
                            )
                    except Exception:
                        continue
                
                return InteractionResult(
                    success=False,
                    message="Filled login details but couldn't find login button"
                )
            else:
                return InteractionResult(
                    success=False,
                    message="Could not find all required login fields"
                )
        
        return InteractionResult(
            success=False,
            message="Invalid login command"
        )


class MenuClickCommand(Command):
    """Command for clicking on a menu item"""
    
    def __init__(self, interactor: WebInteractor, llm_provider: LLMProvider, speaker: SpeechSynthesizer):
        """Initialize the command"""
        super().__init__(re.compile(MENU_CLICK_PATTERN, re.IGNORECASE))
        self.interactor = interactor
        self.llm_provider = llm_provider
        self.speaker = speaker
    
    async def execute(self, command_text: str, **kwargs) -> InteractionResult:
        """Execute the command"""
        match = self.pattern.match(command_text)
        if match:
            menu_item = match.group(1)
            
            # Get page context
            page_context = await self.interactor._get_page_context()
            
            # Get selectors for menu item
            menu_selectors = self.llm_provider.get_selectors(f"find menu item '{menu_item}'", page_context)
            
            for selector in menu_selectors:
                try:
                    if await self.interactor.page.locator(selector).count() > 0:
                        await self.interactor._retry_action(
                            self.interactor._click_element,
                            selector,
                            f"menu item '{menu_item}'"
                        )
                        await self.interactor.page.wait_for_timeout(1000)
                        return InteractionResult(
                            success=True,
                            message=f"Clicked on menu item '{menu_item}'"
                        )
                except Exception:
                    continue
            
            return InteractionResult(
                success=False,
                message=f"Could not find menu item '{menu_item}'"
            )
        
        return InteractionResult(
            success=False,
            message="Invalid menu click command"
        )


class SubmenuCommand(Command):
    """Command for navigating to a submenu"""
    
    def __init__(self, interactor: WebInteractor, llm_provider: LLMProvider, speaker: SpeechSynthesizer):
        """Initialize the command"""
        super().__init__(re.compile(SUBMENU_PATTERN, re.IGNORECASE))
        self.interactor = interactor
        self.llm_provider = llm_provider
        self.speaker = speaker
    
    async def execute(self, command_text: str, **kwargs) -> InteractionResult:
        """Execute the command"""
        match = self.pattern.match(command_text)
        if match:
            target_item, parent_menu = match.groups()
            
            # Get page context
            page_context = await self.interactor._get_page_context()
            
            # Get selectors for parent menu
            parent_selectors = self.llm_provider.get_selectors(f"find menu item '{parent_menu}'", page_context)
            
            parent_found = False
            for selector in parent_selectors:
                try:
                    if await self.interactor.page.locator(selector).count() > 0:
                        await self.interactor.page.locator(selector).hover()
                        await self.speaker.speak(f"Hovering over '{parent_menu}' menu")
                        await self.interactor.page.wait_for_timeout(1000)
                        parent_found = True
                        break
                except Exception:
                    continue
            
            if not parent_found:
                return InteractionResult(
                    success=False,
                    message=f"Could not find parent menu '{parent_menu}'"
                )
            
            # Get updated page context after hovering
            updated_context = await self.interactor._get_page_context()
            
            # Get selectors for submenu item
            submenu_selectors = self.llm_provider.get_selectors(
                f"find submenu item '{target_item}' under '{parent_menu}'",
                updated_context
            )
            
            for selector in submenu_selectors:
                try:
                    if await self.interactor.page.locator(selector).count() > 0:
                        await self.interactor._retry_action(
                            self.interactor._click_element,
                            selector,
                            f"submenu item '{target_item}'"
                        )
                        await self.interactor.page.wait_for_timeout(1000)
                        return InteractionResult(
                            success=True,
                            message=f"Navigated to '{target_item}' under '{parent_menu}'"
                        )
                except Exception:
                    continue
            
            return InteractionResult(
                success=False,
                message=f"Could not find submenu item '{target_item}' under '{parent_menu}'"
            )
        
        return InteractionResult(
            success=False,
            message="Invalid submenu command"
        )


class CheckboxCommand(Command):
    """Command for interacting with checkboxes"""
    
    def __init__(self, interactor: WebInteractor, llm_provider: LLMProvider, speaker: SpeechSynthesizer):
        """Initialize the command"""
        super().__init__(re.compile(CHECKBOX_PATTERN, re.IGNORECASE))
        self.interactor = interactor
        self.llm_provider = llm_provider
        self.speaker = speaker
    
    async def execute(self, command_text: str, **kwargs) -> InteractionResult:
        """Execute the command"""
        match = self.pattern.match(command_text)
        if match:
            action, checkbox_label = match.groups()
            
            # Get page context
            page_context = await self.interactor._get_page_context()
            
            # Get selectors for checkbox
            checkbox_selectors = self.llm_provider.get_selectors(
                f"find checkbox with label '{checkbox_label}'",
                page_context
            )
            
            context = InteractionContext(
                purpose=checkbox_label,
                element_type="checkbox",
                action="checkbox",
                value=action
            )
            
            success = await self._try_selectors_for_checkbox(checkbox_selectors, action.lower(), checkbox_label)
            
            if success:
                return InteractionResult(
                    success=True,
                    message=f"{action.capitalize()}ed checkbox '{checkbox_label}'"
                )
            else:
                return InteractionResult(
                    success=False,
                    message=f"Could not find checkbox '{checkbox_label}'"
                )
        
        return InteractionResult(
            success=False,
            message="Invalid checkbox command"
        )
    
    async def _try_selectors_for_checkbox(self, selectors: List[str], action: str, checkbox_label: str) -> bool:
        """Try different selectors to find and interact with a checkbox"""
        for selector in selectors:
            if not selector:
                continue
            
            try:
                if await self.interactor.page.locator(selector).count() > 0:
                    checkbox = await self.interactor.page.locator(selector).first
                    is_checked = await checkbox.is_checked()
                    
                    if (action == "check" and not is_checked) or (
                            action == "uncheck" and is_checked) or action == "toggle":
                        await checkbox.click()
                        new_state = "checked" if action == "check" or (
                                action == "toggle" and not is_checked) else "unchecked"
                        await self.speaker.speak(f"✓ {new_state.capitalize()} {checkbox_label}")
                        return True
                    elif (action == "check" and is_checked) or (action == "uncheck" and not is_checked):
                        # Already in desired state
                        state = "already checked" if action == "check" else "already unchecked"
                        await self.speaker.speak(f"✓ {checkbox_label} is {state}")
                        return True
            except Exception:
                continue
        
        # If all selectors fail, ask LLM for better selectors
        page_context = await self.interactor._get_page_context()
        new_selectors = self.llm_provider.get_selectors(f"find checkbox for {checkbox_label}", page_context)
        
        for selector in new_selectors:
            try:
                if await self.interactor.page.locator(selector).count() > 0:
                    checkbox = await self.interactor.page.locator(selector).first
                    is_checked = await checkbox.is_checked()
                    
                    if (action == "check" and not is_checked) or (
                            action == "uncheck" and is_checked) or action == "toggle":
                        await checkbox.click()
                        new_state = "checked" if action == "check" or (
                                action == "toggle" and not is_checked) else "unchecked"
                        await self.speaker.speak(f"✓ {new_state.capitalize()} {checkbox_label}")
                        return True
                    elif (action == "check" and is_checked) or (action == "uncheck" and not is_checked):
                        # Already in desired state
                        state = "already checked" if action == "check" else "already unchecked"
                        await self.speaker.speak(f"✓ {checkbox_label} is {state}")
                        return True
            except Exception:
                continue
        
        await self.speaker.speak(f"Could not find checkbox for {checkbox_label}")
        return False


class DropdownCommand(Command):
    """Command for interacting with dropdowns"""
    
    def __init__(self, interactor: WebInteractor, llm_provider: LLMProvider, speaker: SpeechSynthesizer):
        """Initialize the command"""
        super().__init__(re.compile(DROPDOWN_PATTERN, re.IGNORECASE))
        self.interactor = interactor
        self.llm_provider = llm_provider
        self.speaker = speaker
    
    async def execute(self, command_text: str, **kwargs) -> InteractionResult:
        """Execute the command"""
        match = self.pattern.match(command_text)
        if match:
            option, dropdown_name = match.groups()
            
            # Create interaction context
            context = InteractionContext(
                purpose=f"select {option} from {dropdown_name}",
                element_type="dropdown",
                action="select",
                value=option
            )
            
            # Get page context
            page_context = await self.interactor._get_page_context()
            
            # Get selectors for dropdown
            dropdown_selectors = self.llm_provider.get_selectors(
                f"find dropdown with name '{dropdown_name}'",
                page_context
            )
            
            success = await self.interactor._handle_select(context)
            
            if success:
                return InteractionResult(
                    success=True,
                    message=f"Selected '{option}' from '{dropdown_name}' dropdown"
                )
            else:
                return InteractionResult(
                    success=False,
                    message=f"Could not select '{option}' from '{dropdown_name}' dropdown"
                )
        
        return InteractionResult(
            success=False,
            message="Invalid dropdown command"
        )


class StateSelectionCommand(Command):
    """Command for selecting a state from a dropdown"""
    
    def __init__(self, interactor: WebInteractor):
        """Initialize the command"""
        super().__init__(re.compile(STATE_SELECTION_PATTERN, re.IGNORECASE))
        self.interactor = interactor
    
    async def execute(self, command_text: str, **kwargs) -> InteractionResult:
        """Execute the command"""
        match = self.pattern.match(command_text)
        if match:
            state_name = match.group(1).strip()
            return await self.interactor.select_state(state_name)
        
        return InteractionResult(
            success=False,
            message=f"Could not parse state from command: {command_text}"
        )
