"""
Web interactor module for WebAssist
"""

import logging
import re
from typing import List, Dict, Any, Optional, Callable, Awaitable

from playwright.sync_api import Page

from webassist.models.context import InteractionContext, PageContext
from webassist.models.result import InteractionResult
from webassist.llm.provider import LLMProvider
from webassist.speech.synthesizer import SpeechSynthesizer
from webassist.core.config import AssistantConfig


class WebInteractor:
    """Reusable web interaction class"""

    def __init__(self, page: Page, llm_provider: LLMProvider, speaker: SpeechSynthesizer, config: AssistantConfig):
        """Initialize the interactor"""
        self.page = page
        self.llm_provider = llm_provider
        self.speaker = speaker
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.max_retries = config.max_retries
        self.retry_delay = config.retry_delay

    async def interact(self, context: InteractionContext) -> bool:
        """Enhanced interaction method with specific support for dialog form dropdowns"""
        if context.action == "select" and "dialog-form-input-field-wizard" in (context.element_classes or []):
            return await self._handle_dropdown(context)
        
        # Interaction methods using Strategy pattern
        interaction_methods = {
            "click": self._handle_click,
            "type": self._handle_type,
            "select": self._handle_select,
            "hover": self._handle_hover,
            "checkbox": self._handle_checkbox
        }

        handler = interaction_methods.get(context.action)
        if not handler:
            self.logger.error(f"Unsupported action: {context.action}")
            return False

        return await handler(context)

    async def _retry_action(self, action_func: Callable[..., Awaitable[bool]], *args) -> bool:
        """Generic retry mechanism"""
        for attempt in range(self.max_retries):
            try:
                result = await action_func(*args)
                if result:
                    return True
            except Exception as e:
                self.logger.debug(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    self.logger.error(f"Action failed after {self.max_retries} attempts: {str(e)}")
                    return False
                await self.page.wait_for_timeout(self.retry_delay)
        return False

    async def _get_llm_guidance(self, context: InteractionContext) -> dict:
        """Get LLM guidance for dialog form interactions"""
        prompt = f"""
        Analyze the following dropdown interaction:
        Element ID: {context.element_id}
        Classes: dialog-form-input-field-wizard, p-dropdown
        Action: {context.action}
        Value: {context.value}

        Generate selectors and steps for PrimeNG dropdown in a dialog form wizard.
        Consider:
        1. Dialog form specific structure
        2. PrimeNG dropdown components
        3. Hidden accessibility elements
        4. Dropdown trigger and panel
        """
        
        return await self.llm_provider.get_structured_guidance(prompt)

    async def _handle_click(self, context: InteractionContext) -> bool:
        """Handle click action"""
        guidance = await self._get_llm_guidance(context)

        for selector in guidance.get("selectors", []):
            if await self._retry_action(self._click_element, selector, context.purpose):
                return True

        return False

    async def _handle_type(self, context: InteractionContext) -> bool:
        """Handle type action"""
        guidance = await self._get_llm_guidance(context)

        for selector in guidance.get("selectors", []):
            if await self._retry_action(self._type_text, selector, context.value, context.purpose):
                return True

        return False

    async def _handle_select(self, context: InteractionContext) -> bool:
        """Handle select action"""
        guidance = await self._get_llm_guidance(context)

        # Let LLM handle the dropdown logic
        if "special_handling" in guidance:
            for step in guidance.get("special_handling", []):
                await self._execute_step(step)

        for selector in guidance.get("selectors", []):
            if await self._retry_action(self._select_option, selector, context.value, context.purpose):
                if "verification" in guidance:
                    if await self._verify_selection(guidance.get("verification", {}), context):
                        return True
                else:
                    return True

        return False

    async def _handle_hover(self, context: InteractionContext) -> bool:
        """Handle hover action"""
        guidance = await self._get_llm_guidance(context)

        for selector in guidance.get("selectors", []):
            if await self._retry_action(self._hover_element, selector, context.purpose):
                return True

        return False

    async def _handle_checkbox(self, context: InteractionContext) -> bool:
        """Handle checkbox action"""
        guidance = await self._get_llm_guidance(context)
        
        if context.product_name:
            # Handle product selection specifically
            return await self._select_product(context.product_name, context.value == 'true')
        
        # Default checkbox handling
        for selector in guidance.get("selectors", []):
            if await self._retry_action(self._toggle_checkbox, selector, context.value, context.purpose):
                return True
        
        return False

    async def _select_product(self, product_name: str, should_check: bool) -> bool:
        """Handle product selection from the product list"""
        try:
            # Find the product container by its name
            product_selector = f"//div[contains(@class, 'wizard-card-checkbox-text1')]//div[contains(text(), '{product_name}')]/ancestor::div[contains(@class, 'wizard-card-checkbox-container')]"
            
            # Find the checkbox within the product container
            checkbox_selector = f"{product_selector}//div[contains(@class, 'p-checkbox')]"
            
            # Get the checkbox element
            checkbox = await self.page.locator(checkbox_selector).first
            
            # Check if checkbox is already in desired state
            is_checked = await checkbox.evaluate("""el => {
                return el.classList.contains('p-checkbox-checked')
            }""")
            
            # Only click if the current state doesn't match desired state
            if is_checked != should_check:
                await checkbox.click()
                await self.page.wait_for_timeout(500)  # Wait for any animations/updates
                
                # Verify the change
                new_state = await checkbox.evaluate("""el => {
                    return el.classList.contains('p-checkbox-checked')
                }""")
                
                if new_state == should_check:
                    await self.speaker.speak(f"{'Selected' if should_check else 'Deselected'} {product_name}")
                    return True
            else:
                # Already in desired state
                await self.speaker.speak(f"{product_name} is already {'selected' if should_check else 'deselected'}")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to select product {product_name}: {str(e)}")
            return False

    async def select_product_by_name(self, product_name: str, should_check: bool = True) -> bool:
        """Public method to select a product by its name"""
        context = InteractionContext(
            purpose=f"{'Select' if should_check else 'Deselect'} {product_name}",
            element_type="checkbox",
            action="checkbox",
            value="true" if should_check else "false",
            product_name=product_name
        )
        
        return await self._handle_checkbox(context)

    async def _click_element(self, selector: str, purpose: str) -> bool:
        """Click an element"""
        element = await self.page.locator(selector).first
        await element.click()
        await self.speaker.speak(f"👆 Clicked {purpose}")
        return True

    async def _type_text(self, selector: str, text: str, purpose: str) -> bool:
        """Type text into an element"""
        element = await self.page.locator(selector).first
        await element.fill(text)
        await self.speaker.speak(f"⌨️ Entered {purpose}")
        return True

    async def _select_option(self, selector: str, option: str, purpose: str) -> bool:
        """Select an option from a dropdown"""
        element = await self.page.locator(selector).first

        # Handle different types of dropdowns
        is_select = await element.evaluate("el => el.tagName.toLowerCase() === 'select'")
        is_primeng = await self._is_primeng_dropdown(selector)

        if is_select:
            # Handle standard HTML select
            await element.select_option(label=option)
        elif is_primeng:
            # Handle PrimeNG dropdown
            await self._handle_primeng_dropdown(selector, option)
        else:
            # Handle custom dropdown
            await element.click()
            await self.page.wait_for_timeout(500)
            option_selector = await self._find_option_selector(option)
            if option_selector:
                await self.page.locator(option_selector).click()

        await self.speaker.speak(f"📝 Selected {option} from {purpose}")
        return True

    async def _is_primeng_dropdown(self, selector: str) -> bool:
        """Check if the element is a PrimeNG dropdown"""
        try:
            # Check for PrimeNG specific classes or attributes
            has_primeng_class = await self.page.locator(selector).evaluate("""
                el => {
                    return el.classList.contains('p-dropdown') || 
                           el.classList.contains('p-dropdown-trigger') ||
                           el.closest('.p-dropdown') !== null;
                }
            """)
            return has_primeng_class
        except:
            return False

    async def _handle_primeng_dropdown(self, selector: str, option: str) -> bool:
        """Handle PrimeNG dropdown selection"""
        try:
            # Click to open dropdown
            dropdown_element = await self.page.locator(selector).first
            await dropdown_element.click()

            # Wait for dropdown panel to appear
            await self.page.wait_for_selector('.p-dropdown-panel.p-component', state='visible', timeout=3000)

            # First check for filter in the dropdown panel
            filter_selector = '.p-dropdown-panel .p-dropdown-filter'
            has_filter = await self.page.locator(filter_selector).count() > 0

            if has_filter:
                # Use filter to find option
                await self.page.fill(filter_selector, option)
                await self.page.wait_for_timeout(500)

            # Try to find and click the option
            option_selectors = [
                f".p-dropdown-panel .p-dropdown-item:text-is('{option}')",
                f".p-dropdown-panel .p-dropdown-item:text-contains('{option}')",
                f".p-dropdown-panel li:text-contains('{option}')"
            ]

            for option_selector in option_selectors:
                if await self.page.locator(option_selector).count() > 0:
                    await self.page.locator(option_selector).first.click()
                    return True

            return False
        except Exception as e:
            self.logger.error(f"PrimeNG dropdown error: {str(e)}")
            return False

    async def _hover_element(self, selector: str, purpose: str) -> bool:
        """Hover over an element"""
        element = await self.page.locator(selector).first
        await element.hover()
        await self.speaker.speak(f"🖱️ Hovering over {purpose}")
        return True

    async def _toggle_checkbox(self, selector: str, action: str, purpose: str) -> bool:
        """Toggle a checkbox"""
        element = await self.page.locator(selector).first
        current_state = await element.is_checked()

        if action == "check" and not current_state:
            await element.click()
        elif action == "uncheck" and current_state:
            await element.click()

        await self.speaker.speak(f"✓ {action.capitalize()}ed {purpose}")
        return True

    async def _verify_selection(self, verification_steps: Dict, context: InteractionContext) -> bool:
        """Verify the selection was successful"""
        for step in verification_steps.get("steps", []):
            try:
                if not await self._execute_verification_step(step, context):
                    return False
            except Exception as e:
                self.logger.error(f"Verification failed: {str(e)}")
                return False
        return True

    async def _execute_verification_step(self, step: Dict, context: InteractionContext) -> bool:
        """Execute a single verification step"""
        step_type = step.get("type")
        if step_type == "check_text":
            return await self._verify_text(step.get("selector", ""), step.get("expected", ""))
        elif step_type == "check_value":
            return await self._verify_value(step.get("selector", ""), step.get("expected", ""))
        elif step_type == "check_state":
            return await self._verify_state(step.get("selector", ""), step.get("expected", ""))
        return False

    async def _get_page_context(self) -> Dict[str, Any]:
        """Get current page context"""
        return {
            "url": await self.page.url,
            "title": await self.page.title(),
            "content": await self.page.content(),
            "visible_text": await self.page.evaluate("() => document.body.innerText"),
        }

    async def _find_option_selector(self, option: str) -> Optional[str]:
        """Find selector for dropdown option"""
        guidance = await self._get_llm_guidance(InteractionContext(
            purpose=f"find option {option}",
            element_type="option",
            action="find",
            value=option
        ))

        for selector in guidance.get("selectors", []):
            if await self.page.locator(selector).count() > 0:
                return selector
        return None

    async def _handle_dropdown(self, context: InteractionContext) -> bool:
        """Handle dropdown selection with specific support for dialog form wizard"""
        guidance = await self._get_llm_guidance(context)
        
        # Primary selectors for the dialog form dropdown
        primary_selectors = [
            f"#{context.element_id}",
            f".dialog-form-input-field-wizard#{context.element_id}",
            f".p-dropdown.dialog-form-input-field-wizard#{context.element_id}",
            f"div[id='{context.element_id}']"
        ]

        for selector in primary_selectors:
            try:
                # Check if dropdown exists and is visible
                dropdown = await self.page.locator(selector).first
                if not await dropdown.is_visible():
                    continue

                # Click to open dropdown
                await dropdown.click()
                await self.page.wait_for_timeout(500)  # Wait for animation

                # Wait for dropdown panel to be visible
                panel_selector = '.p-dropdown-panel'
                await self.page.wait_for_selector(panel_selector, state='visible', timeout=3000)

                # Try to find and select the option
                option_selectors = [
                    f"{panel_selector} .p-dropdown-item:text-is('{context.value}')",
                    f"{panel_selector} .p-dropdown-item:text-contains('{context.value}')",
                    f"{panel_selector} li:text-contains('{context.value}')"
                ]

                for option_selector in option_selectors:
                    option_elements = await self.page.locator(option_selector).all()
                    if len(option_elements) > 0:
                        # Ensure option is in view and click it
                        await option_elements[0].scroll_into_view_if_needed()
                        await option_elements[0].click()
                        
                        # Verify selection
                        await self.page.wait_for_timeout(500)
                        selected_text = await dropdown.locator('.p-dropdown-label').text_content()
                        if context.value.lower() in selected_text.lower():
                            await self.speaker.speak(f"Selected {context.value}")
                            return True

                # If we get here, the option wasn't found
                self.logger.warning(f"Option '{context.value}' not found in dropdown {context.element_id}")
                
            except Exception as e:
                self.logger.error(f"Error handling dropdown {context.element_id}: {str(e)}")
                continue

        return False

    async def _verify_text(self, selector: str, expected: str) -> bool:
        """Verify text content of an element"""
        try:
            element = await self.page.locator(selector).first
            text = await element.text_content()
            return expected.lower() in text.lower()
        except Exception as e:
            self.logger.error(f"Text verification error: {str(e)}")
            return False

    async def _verify_value(self, selector: str, expected: str) -> bool:
        """Verify value of an input element"""
        try:
            element = await self.page.locator(selector).first
            value = await element.input_value()
            return expected.lower() in value.lower()
        except Exception as e:
            self.logger.error(f"Value verification error: {str(e)}")
            return False

    async def _verify_state(self, selector: str, expected: str) -> bool:
        """Verify state of an element"""
        try:
            element = await self.page.locator(selector).first
            if expected.lower() == "checked":
                return await element.is_checked()
            elif expected.lower() == "unchecked":
                return not await element.is_checked()
            elif expected.lower() == "visible":
                return await element.is_visible()
            elif expected.lower() == "hidden":
                return not await element.is_visible()
            elif expected.lower() == "enabled":
                return await element.is_enabled()
            elif expected.lower() == "disabled":
                return not await element.is_enabled()
            return False
        except Exception as e:
            self.logger.error(f"State verification error: {str(e)}")
            return False

    async def _execute_step(self, step: Dict) -> bool:
        """Execute a step from LLM guidance"""
        try:
            action = step.get("action")
            selector = step.get("selector")
            value = step.get("value")
            
            if action == "wait":
                await self.page.wait_for_selector(selector, state="visible", timeout=5000)
                return True
            
            elif action == "click":
                element = await self.page.locator(selector).first
                await element.click()
                await self.page.wait_for_timeout(500)
                return True
            
            elif action == "type":
                element = await self.page.locator(selector).first
                await element.fill(value)
                await self.page.wait_for_timeout(500)
                return True
            
            elif action == "select":
                return await self._select_option(selector, value, "dropdown")
            
            return False
        except Exception as e:
            self.logger.error(f"Step execution error: {str(e)}")
            return False

    # State selection methods
    async def _handle_state_selection(self, context: InteractionContext) -> InteractionResult:
        """Handle state selection from PrimeNG dropdown"""
        try:
            # Get LLM guidance for state dropdown interaction
            prompt = f"""
            Analyze this PrimeNG state dropdown interaction:
            Target State: {context.value}
            
            HTML Structure:
            <div class="p-dropdown-panel p-component p-connected-overlay-enter-done">
                <div class="p-dropdown-header">
                    <div class="p-dropdown-filter-container">
                        <input class="p-dropdown-filter p-inputtext p-component">
                    </div>
                </div>
                <div class="p-dropdown-items-wrapper">
                    <ul class="p-dropdown-items" role="listbox">
                        <li class="p-dropdown-item" aria-label="State">

            Generate interaction steps considering:
            1. Filter functionality
            2. Dropdown panel visibility
            3. State option selection
            4. Verification steps

            Return structured guidance for:
            - Opening dropdown
            - Using filter
            - Selecting state
            - Verifying selection
            """

            guidance = await self.llm_provider.get_structured_guidance(prompt)
            
            # Execute dropdown interaction steps
            for step in guidance.get("steps", []):
                action = step.get("action")
                selector = step.get("selector")
                value = step.get("value")
                
                if action == "wait":
                    await self.page.wait_for_selector(selector, state="visible", timeout=5000)
                
                elif action == "filter":
                    filter_input = await self.page.locator(selector).first
                    await filter_input.fill(value)
                    await self.page.wait_for_timeout(500)  # Wait for filter
                
                elif action == "click":
                    element = await self.page.locator(selector).first
                    await element.click()
                    await self.page.wait_for_timeout(500)  # Wait for animation
                
                elif action == "verify":
                    selected_text = await self.page.locator(selector).text_content()
                    if context.value.lower() not in selected_text.lower():
                        return InteractionResult(
                            success=False,
                            message=f"Failed to verify state selection: {context.value}"
                        )

            # Verify final selection
            verification_selectors = [
                '.p-dropdown-label',
                f'.p-dropdown-item[aria-selected="true"]'
            ]

            for selector in verification_selectors:
                try:
                    element = await self.page.locator(selector).first
                    if element:
                        selected_text = await element.text_content()
                        if context.value.lower() in selected_text.lower():
                            await self.speaker.speak(f"Selected state: {context.value}")
                            return InteractionResult(
                                success=True,
                                message=f"Successfully selected state: {context.value}"
                            )
                except Exception:
                    continue

            return InteractionResult(
                success=False,
                message=f"Failed to verify state selection: {context.value}"
            )

        except Exception as e:
            self.logger.error(f"State selection failed: {str(e)}")
            await self.speaker.speak(f"Failed to select state {context.value}")
            return InteractionResult(
                success=False,
                message=f"State selection failed: {str(e)}",
                details={"error": str(e)}
            )

    async def select_state(self, state_name: str) -> InteractionResult:
        """Public method to select state from dropdown"""
        context = InteractionContext(
            purpose="state selection",
            element_type="dropdown",
            action="select",
            value=state_name
        )
        
        return await self._handle_state_selection(context)

    # Voice command handler
    async def handle_state_command(self, command: str) -> InteractionResult:
        """Handle voice command for state selection"""
        # Match pattern like "select Alabama" or "choose state Alabama"
        state_match = re.search(r'(?:select|choose|pick)\s+(?:state\s+)?(.+)', command, re.IGNORECASE)
        
        if state_match:
            state_name = state_match.group(1).strip()
            return await self.select_state(state_name)
        
        return InteractionResult(
            success=False,
            message=f"Could not parse state from command: {command}"
        )
