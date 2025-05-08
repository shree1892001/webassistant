import re

class NavigationHandler:
    """Handles navigation-related commands"""

    def __init__(self, page, speak_func, llm_utils, browser_utils):

        self.page = page
        self.speak = speak_func
        self.llm_utils = llm_utils
        self.browser_utils = browser_utils

    async def handle_command(self, command):
        """Handle navigation-related commands

        Args:
            command: User command string

        Returns:
            bool: True if command was handled, False otherwise
        """
        # Handle search command
        search_match = re.search(r'search(?:\s+for)?\s+(.+)', command, re.IGNORECASE)
        if search_match:
            query = search_match.group(1)
            return await self._handle_search(query)

        # Handle click command
        click_match = re.search(r'cl[ci]?[ck]k?(?:\s+on)?\s+(?:the\s+)?(.+)', command, re.IGNORECASE)
        if click_match:
            element_name = click_match.group(1).strip()
            return await self._handle_click(element_name)

        return False

    async def browse_website(self, url):
        """Navigate to URL"""
        try:
            # Clean up the URL
            url = url.strip()

            # Check if it's a valid URL format
            if not url.startswith(('http://', 'https://')):
                # Special handling for signin URLs
                if url.startswith('#/signin') or url.startswith('/#/signin') or 'signin' in url:
                    self.speak("Trying alternative approach for signin page...")
                    try:
                        # Try the known working URL
                        await self.page.goto("https://www.redberyltest.in/#/signin", wait_until="networkidle", timeout=40000)
                        self.speak("Successfully navigated to signin page")
                        return True
                    except Exception as alt_err:
                        self.speak(f"Alternative navigation also failed: {str(alt_err)}")

                        # As a last resort, try to find and click login button
                        self.speak("Trying to find login option...")
                        login_selectors = await self.llm_utils.get_selectors("find login or sign in link or button",
                                                                  await self.llm_utils.get_page_context())
                        for selector in login_selectors:
                            try:
                                if await self.page.locator(selector).count() > 0:
                                    await self.page.locator(selector).first.click()
                                    await self.page.wait_for_timeout(10000)
                                    self.speak("Found and clicked login option")
                                    return True
                            except Exception:
                                continue
                    return False

                # Add https:// prefix for regular domains
                url = f"https://{url}"

            # Ensure there's a domain name
            domain_part = url.split('//')[1].split('/')[0]
            if not domain_part or domain_part == '':
                await self.speak("Invalid URL: Missing domain name")
                return False

            print(f"Navigating to: {url}")
            await self.page.goto(url, wait_until="networkidle", timeout=20000)
            await self.speak(f"Loaded: {await self.page.title()}")
            return True
        except Exception as e:
            await self.speak(f"Navigation failed: {str(e)}")

            # Handle special case for login URLs
            if url.startswith('#/signin') or url.startswith('/#/signin') or 'signin' in url:
                await self.speak("Trying alternative approach for signin page...")
                try:
                    # Try the known working URL
                    await self.page.goto("https://www.redberyltest.in/#/signin", wait_until="networkidle", timeout=30000)
                    await self.speak("Successfully navigated to signin page")
                    return True
                except Exception as alt_err:
                    await self.speak(f"Alternative navigation also failed: {str(alt_err)}")

                    # As a last resort, try to find and click login button
                    await self.speak("Trying to find login option...")
                    login_selectors = await self.llm_utils.get_selectors("find login or sign in link or button",
                                                              await self.llm_utils.get_page_context())
                    for selector in login_selectors:
                        try:
                            if await self.page.locator(selector).count() > 0:
                                await self.page.locator(selector).first.click()
                                await self.page.wait_for_timeout(10000)
                                await self.speak("Found and clicked login option")
                                return True
                        except Exception:
                            continue
            return False

    async def _handle_search(self, query):
        """Handle search command"""
        await self.speak(f"Searching for '{query}'...")

        # First try using the LLM to generate actions
        context = await self.llm_utils.get_page_context()

        # Create a specific command for the LLM
        action_data = await self.llm_utils.get_actions(f"search for {query}")

        if 'actions' in action_data and len(action_data['actions']) > 0:
            # Try to execute the LLM-generated actions
            success = await self.llm_utils.execute_actions(action_data)
            if success:
                return True
            else:
                await self.speak("LLM-generated actions failed, trying fallback methods...")

        # If LLM actions failed, try with JavaScript injection first
        await self.speak("Trying JavaScript injection for search query...")
        try:
            # Use JavaScript to find and fill the search input
            search_result = await self.page.evaluate("""(searchQuery) => {
                console.log("Searching for search input field...");

                // Try common search input selectors
                const searchSelectors = [
                    'input[type="search"]',
                    'input[name="search"]',
                    'input[placeholder*="search" i]',
                    'input[aria-label*="search" i]',
                    '.search-input',
                    '#search',
                    'input.form-control',
                    'input[type="text"]',
                    '.App input[type="text"]'
                ];

                // Try each selector
                for (const selector of searchSelectors) {
                    const searchInputs = document.querySelectorAll(selector);
                    console.log(`Found ${searchInputs.length} elements matching selector: ${selector}`);

                    if (searchInputs.length > 0) {
                        // Use the first matching input
                        const searchInput = searchInputs[0];
                        console.log(`Using search input: ${selector}`);

                        // Fill the input
                        searchInput.value = searchQuery;
                        searchInput.dispatchEvent(new Event('input', { bubbles: true }));
                        searchInput.dispatchEvent(new Event('change', { bubbles: true }));

                        // Try to submit the form if the input is in a form
                        const form = searchInput.closest('form');
                        if (form) {
                            console.log("Found parent form, submitting it");
                            form.dispatchEvent(new Event('submit', { bubbles: true }));
                            return { success: true, message: "Submitted search form" };
                        }

                        // If no form, try to press Enter
                        console.log("No parent form found, simulating Enter key");
                        searchInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', bubbles: true }));
                        searchInput.dispatchEvent(new KeyboardEvent('keypress', { key: 'Enter', code: 'Enter', bubbles: true }));
                        searchInput.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', bubbles: true }));

                        return { success: true, message: "Filled search input and simulated Enter key" };
                    }
                }

                // If we get here, we couldn't find a search input
                return { success: false, message: "Could not find search input" };
            }""", query)

            print(f"JavaScript search result: {search_result}")

            if search_result and search_result.get('success'):
                await self.speak(f"🔍 Searching for '{query}'")
                await self.page.wait_for_timeout(3000)
                return True
            else:
                print("JavaScript injection failed:", search_result.get('message', 'Unknown error'))
        except Exception as e:
            print(f"JavaScript injection failed: {e}")

        # If JavaScript injection failed, try with selectors
        search_selectors = await self.llm_utils.get_selectors("find search input field", context)

        # Add some common fallback selectors
        fallback_selectors = [
            'input[type="search"]',
            'input[name="search"]',
            'input[placeholder*="search" i]',
            'input[aria-label*="search" i]',
            '.search-input',
            '#search',
            'input.form-control',
            'input[type="text"]',
            '.App input[type="text"]'
        ]

        # Try all selectors
        for selector in search_selectors + fallback_selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    # Increase timeout for typing
                    await self.browser_utils.retry_type(selector, query, "search query", max_retries=5, timeout=60000)
                    await self.page.locator(selector).press("Enter")
                    await self.speak(f"🔍 Searching for '{query}'")
                    await self.page.wait_for_timeout(3000)
                    return True
            except Exception as e:
                print(f"Error with search selector {selector}: {e}")
                continue

        await self.speak("Could not find search field")
        return False

    async def _handle_click(self, element_name):
        """Handle click command"""
        await self.speak(f"Looking for {element_name}...")

        # First try using the LLM to generate actions
        context = await self.llm_utils.get_page_context()

        # Create a specific command for the LLM
        action_data = await self.llm_utils.get_actions(f"click on {element_name}")

        if 'actions' in action_data and len(action_data['actions']) > 0:
            # Try to execute the LLM-generated actions
            success = await self.llm_utils.execute_actions(action_data)
            if success:
                return True
            else:
                await self.speak("LLM-generated actions failed, trying fallback methods...")

        # If LLM actions failed, try with selectors
        element_selectors = await self.llm_utils.get_selectors(f"find {element_name}", context)

        for selector in element_selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    await self.browser_utils.retry_click(selector, element_name)
                    await self.speak(f"Clicked on {element_name}")
                    await self.page.wait_for_timeout(2000)
                    return True
            except Exception as e:
                print(f"Error with selector {selector} for {element_name}: {e}")
                continue

        # Try with more specific selectors
        specific_selectors = await self.llm_utils.get_selectors(f"find {element_name} button, link, or menu item", context)

        for selector in specific_selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    await self.browser_utils.retry_click(selector, element_name)
                    await self.speak(f"Clicked on {element_name}")
                    await self.page.wait_for_timeout(2000)
                    return True
            except Exception as e:
                print(f"Error with specific selector {selector} for {element_name}: {e}")
                continue

        await self.speak(f"Could not find {element_name}")
        return False
