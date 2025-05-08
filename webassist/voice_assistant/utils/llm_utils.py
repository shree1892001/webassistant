from webassist.models.result import InteractionResult

class LLMUtils:
    """Utility methods for LLM interactions"""

    def __init__(self, llm_provider, page, speak_func, browser_utils=None, navigation_handler=None):
        """Initialize LLM utilities

        Args:
            llm_provider: LLM provider instance
            page: Playwright page object
            speak_func: Function to speak text
            browser_utils: Browser utilities for common operations
            navigation_handler: Navigation handler for browsing websites
        """
        self.llm_provider = llm_provider
        self.page = page
        self.speak = speak_func
        self.browser_utils = browser_utils
        self.navigation_handler = navigation_handler

    async def get_page_context(self):
        """Get the current page context for LLM prompts"""
        try:
            # Get page title
            title = await self.page.title()

            # Get page URL
            url = self.page.url

            # Get visible text (limited to avoid token limits)
            visible_text = await self.page.evaluate("""() => {
                // Get all visible text nodes
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    {
                        acceptNode: function(node) {
                            // Check if the node's parent is visible
                            const style = window.getComputedStyle(node.parentElement);
                            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
                                return NodeFilter.FILTER_REJECT;
                            }
                            // Only accept non-empty text nodes
                            return node.textContent.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
                        }
                    }
                );

                // Collect text nodes
                const textNodes = [];
                let currentNode;
                while (currentNode = walker.nextNode()) {
                    textNodes.push(currentNode.textContent.trim());
                }

                // Join and limit to avoid token limits
                return textNodes.join(' ').substring(0, 5000);
            }""")

            # Get form elements
            form_elements = await self.page.evaluate("""() => {
                const result = {
                    inputs: [],
                    buttons: [],
                    dropdowns: [],
                    checkboxes: []
                };

                // Get inputs
                document.querySelectorAll('input, textarea').forEach(input => {
                    result.inputs.push({
                        type: input.type || 'text',
                        id: input.id,
                        name: input.name,
                        placeholder: input.placeholder,
                        value: input.value,
                        class: input.className
                    });
                });

                // Get buttons
                document.querySelectorAll('button, input[type="button"], input[type="submit"], a.btn, .button, [role="button"]').forEach(button => {
                    result.buttons.push({
                        text: button.textContent.trim(),
                        id: button.id,
                        class: button.className,
                        type: button.type
                    });
                });

                // Get dropdowns
                document.querySelectorAll('select, .p-dropdown').forEach(dropdown => {
                    result.dropdowns.push({
                        id: dropdown.id,
                        class: dropdown.className,
                        options: dropdown.tagName === 'SELECT' ?
                            Array.from(dropdown.options).map(opt => opt.textContent.trim()) :
                            []
                    });
                });

                // Get checkboxes
                document.querySelectorAll('input[type="checkbox"], .p-checkbox').forEach(checkbox => {
                    result.checkboxes.push({
                        id: checkbox.id,
                        class: checkbox.className,
                        checked: checkbox.checked || checkbox.classList.contains('p-checkbox-checked')
                    });
                });

                return result;
            }""")

            # Format buttons for better context
            formatted_buttons = self._format_buttons(form_elements.get('buttons', []))

            # Create context dictionary
            context_dict = {
                "title": title,
                "url": url,
                "visible_text": visible_text,
                "form_elements": form_elements,
                "formatted_buttons": formatted_buttons
            }

            return context_dict
        except Exception as e:
            print(f"Error getting page context: {e}")
            return {
                "title": "Error getting page context",
                "url": self.page.url,
                "error": str(e)
            }

    def _format_buttons(self, buttons):
        """Format buttons for LLM prompt"""
        result = ""
        for idx, button in enumerate(buttons):
            result += f"{idx + 1}. {button.get('text', '')} - "
            result += f"id: {button.get('id', '')}, "
            result += f"class: {button.get('class', '')}, "
            result += f"type: {button.get('type', '')}\n"
        return result

    async def get_selectors(self, task, context_dict):
        """Use LLM to generate selectors for a task based on page context"""
        try:
            # Use the LLM provider to get selectors
            selectors = await self.llm_provider.get_selectors(task, context_dict)
            print(f"🔍 Selector generation response:\n", selectors)

            # Sanitize selectors
            sanitized_selectors = []
            for selector in selectors:
                # Replace :contains() with :has-text() for Playwright
                if ":contains(" in selector:
                    selector = selector.replace(":contains(", ":has-text(")
                sanitized_selectors.append(selector)

            return sanitized_selectors
        except Exception as e:
            print(f"Error generating selectors: {e}")
            # Return some basic fallback selectors based on the task
            if "email" in task.lower():
                return ['input[type="email"]', 'input[name="email"]', 'input[id*="email"]']
            elif "password" in task.lower():
                return ['input[type="password"]', 'input[name="password"]', '#password']
            elif "button" in task.lower() or "submit" in task.lower():
                return ['button[type="submit"]', 'input[type="submit"]', 'button', '.btn', '.button']
            else:
                return []

    async def get_llm_response(self, prompt):
        """Get a response from the LLM provider

        This method handles different LLM provider interfaces

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            str: The LLM response text
        """
        try:
            # Try different methods based on what's available in the LLM provider
            if hasattr(self.llm_provider, 'get_llm_response'):
                return await self.llm_provider.get_llm_response(prompt)
            elif hasattr(self.llm_provider, 'generate_content'):
                response = self.llm_provider.generate_content(prompt)
                return response.text
            elif hasattr(self.llm_provider, 'generate'):
                return await self.llm_provider.generate(prompt)
            elif hasattr(self.llm_provider, 'generate_text'):
                return await self.llm_provider.generate_text(prompt)
            else:
                print("No suitable LLM method found")
                return '{"approach": "combined", "selectors": ["input", "textarea"], "explanation": "Fallback response - no LLM method found"}'
        except Exception as e:
            print(f"Error getting LLM response: {e}")
            import traceback
            traceback.print_exc()
            return '{"approach": "combined", "selectors": ["input", "textarea"], "explanation": "Error response"}'

    async def get_actions(self, command):
        """Use LLM to generate actions for a command"""
        try:
            # Get page context
            context = await self.get_page_context()

            # Use the LLM provider to get actions
            actions = await self.llm_provider.get_actions(command, context)
            return actions
        except Exception as e:
            print(f"Error generating actions: {e}")
            return {"error": str(e)}

    async def execute_actions(self, action_data):
        """Execute actions"""
        if 'error' in action_data:
            self.speak("⚠️ Action could not be completed. Switching to fallback...")
            return False

        result = InteractionResult(success=True, message="Actions executed successfully")

        for action in action_data.get('actions', []):
            try:
                await self._perform_action(action)
                await self.page.wait_for_timeout(1000)
            except Exception as e:
                error_message = f"❌ Failed to {action.get('purpose', 'complete action')}"
                self.speak(error_message)
                print(f"Action Error: {str(e)}")
                result = InteractionResult(success=False, message=error_message, details={"error": str(e)})
                return result.success

        return result.success

    async def _perform_action(self, action):
        """Perform a single action"""
        # Check for both 'type' and 'action' fields since LLM might use either
        action_type = action.get('type', action.get('action', '')).lower()
        print(f"Performing action: {action_type} - {action.get('purpose', '')}")

        if action_type == 'click':
            selector = action.get('selector', '')
            fallbacks = action.get('fallback_selectors', [])
            await self.browser_utils.try_selectors_for_click([selector] + fallbacks, action.get('purpose', 'click element'))
        elif action_type == 'type':
            selector = action.get('selector', '')
            fallbacks = action.get('fallback_selectors', [])
            await self.browser_utils.try_selectors_for_type([selector] + fallbacks, action.get('text', ''),
                                               action.get('purpose', 'enter text'))
        elif action_type == 'navigate':
            url = action.get('url', '')
            if url:
                # Use the navigation handler's browse_website method if available
                if hasattr(self, 'navigation_handler') and self.navigation_handler:
                    await self.navigation_handler.browse_website(url)
                else:
                    # Fallback to direct navigation
                    try:
                        await self.page.goto(url, wait_until="networkidle", timeout=20000)
                        self.speak(f"Navigated to: {url}")
                    except Exception as e:
                        self.speak(f"Navigation failed: {str(e)}")
            else:
                self.speak("No URL provided for navigation")
        elif action_type == 'hover':
            selector = action.get('selector', '')
            fallbacks = action.get('fallback_selectors', [])
            await self.browser_utils.try_selectors_for_hover([selector] + fallbacks, action.get('purpose', 'hover over element'))
        elif action_type == 'select':
            selector = action.get('selector', '')
            fallbacks = action.get('fallback_selectors', [])
            value = action.get('value', '')
            await self.browser_utils.try_selectors_for_select([selector] + fallbacks, value, action.get('purpose', 'select option'))
        elif action_type == 'check':
            selector = action.get('selector', '')
            fallbacks = action.get('fallback_selectors', [])
            await self.browser_utils.try_selectors_for_check([selector] + fallbacks, action.get('purpose', 'check checkbox'))
        elif action_type == 'wait':
            timeout = action.get('timeout', 1000)
            await self.page.wait_for_timeout(timeout)
        else:
            self.speak(f"Unknown action type: {action_type}")
