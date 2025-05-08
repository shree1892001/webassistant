class BrowserUtils:
    """Utility methods for browser interactions"""

    def __init__(self, page, speak_func):
        """Initialize browser utilities

        Args:
            page: Playwright page object
            speak_func: Function to speak text
        """
        self.page = page
        self.speak = speak_func

    async def retry_click(self, selector, purpose, max_retries=3, timeout=10000):
        """Retry clicking an element multiple times with increasing waits"""
        for attempt in range(max_retries):
            try:
                # Wait for the element to be visible
                await self.page.locator(selector).first.wait_for(state="visible", timeout=timeout)

                # Try to scroll the element into view using Playwright's built-in method
                try:
                    element = await self.page.locator(selector).first
                    await element.scroll_into_view_if_needed()
                    await self.page.wait_for_timeout(500)  # Wait for scroll to complete
                except Exception as scroll_error:
                    print(f"Scroll error (non-critical): {scroll_error}")

                # Click the element
                await self.page.locator(selector).first.click(timeout=timeout)
                print(f"Successfully clicked {purpose} on attempt {attempt + 1}")
                return True
            except Exception as e:
                print(f"Click attempt {attempt + 1} failed for {purpose}: {e}")
                if attempt < max_retries - 1:
                    # Increase wait time with each retry
                    wait_time = 1000 * (attempt + 1)
                    print(f"Waiting {wait_time}ms before retry...")
                    await self.page.wait_for_timeout(wait_time)

        # If we get here, all attempts failed
        print(f"All {max_retries} click attempts failed for {purpose}")
        raise Exception(f"Failed to click {purpose} after {max_retries} attempts")

    async def retry_type(self, selector, text, purpose, max_retries=3, timeout=10000):
        """Retry typing into an element multiple times with increasing waits"""
        for attempt in range(max_retries):
            try:
                # Wait for the element to be visible
                await self.page.locator(selector).first.wait_for(state="visible", timeout=timeout)

                # Try to scroll the element into view using Playwright's built-in method
                try:
                    element = await self.page.locator(selector).first
                    await element.scroll_into_view_if_needed()
                    await self.page.wait_for_timeout(500)  # Wait for scroll to complete
                except Exception as scroll_error:
                    print(f"Scroll error (non-critical): {scroll_error}")

                # Clear the field first
                await self.page.locator(selector).first.fill("")

                # Type the text
                await self.page.locator(selector).first.fill(text, timeout=timeout)

                # Dispatch events to ensure the value is registered
                await self.page.locator(selector).first.dispatch_event("input")
                await self.page.locator(selector).first.dispatch_event("change")

                print(f"Successfully entered {purpose} on attempt {attempt + 1}")
                return True
            except Exception as e:
                print(f"Type attempt {attempt + 1} failed for {purpose}: {e}")
                if attempt < max_retries - 1:
                    # Increase wait time with each retry
                    wait_time = 1000 * (attempt + 1)
                    print(f"Waiting {wait_time}ms before retry...")
                    await self.page.wait_for_timeout(wait_time)

        # If we get here, all attempts failed
        print(f"All {max_retries} type attempts failed for {purpose}")

        # Try JavaScript as a last resort
        try:
            print(f"Trying JavaScript injection for {purpose}...")
            js_result = await self.page.evaluate(f"""(selector, text) => {{
                try {{
                    const element = document.querySelector(selector);
                    if (element) {{
                        element.value = text;
                        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return true;
                    }}

                    // If selector didn't work, try to find input by purpose/placeholder
                    const inputs = Array.from(document.querySelectorAll('input, textarea'));
                    for (const input of inputs) {{
                        if (input.placeholder && input.placeholder.toLowerCase().includes('{purpose.lower()}') ||
                            input.name && input.name.toLowerCase().includes('{purpose.lower()}') ||
                            input.id && input.id.toLowerCase().includes('{purpose.lower()}')) {{

                            input.value = text;
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return true;
                        }}
                    }}

                    return false;
                }} catch (error) {{
                    console.error("JavaScript injection error:", error);
                    return false;
                }}
            }}""", selector, text)

            if js_result:
                print(f"Successfully filled {purpose} using JavaScript")
                return True
        except Exception as js_error:
            print(f"JavaScript injection failed: {js_error}")

        raise Exception(f"Failed to enter {purpose} after {max_retries} attempts")

    async def try_selectors_for_click(self, selectors, purpose):
        """Try multiple selectors to click an element"""
        for selector in selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    await self.retry_click(selector, purpose)
                    await self.speak(f"Clicked {purpose}")
                    return True
            except Exception as e:
                print(f"Error with selector {selector} for {purpose}: {e}")
                continue

        await self.speak(f"Could not find element to {purpose}")
        return False

    async def try_selectors_for_type(self, selectors, text, purpose):
        """Try multiple selectors to type into an element"""
        for selector in selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    await self.retry_type(selector, text, purpose)
                    await self.speak(f"Entered {purpose}")
                    return True
            except Exception as e:
                print(f"Error with selector {selector} for {purpose}: {e}")
                continue

        await self.speak(f"Could not find element to enter {purpose}")
        return False

    async def try_selectors_for_hover(self, selectors, purpose):
        """Try multiple selectors to hover over an element"""
        for selector in selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    await self.page.locator(selector).first.hover()
                    await self.speak(f"Hovered over {purpose}")
                    return True
            except Exception as e:
                print(f"Error with selector {selector} for hovering over {purpose}: {e}")
                continue

        await self.speak(f"Could not find element to hover over {purpose}")
        return False

    async def try_selectors_for_select(self, selectors, value, purpose):
        """Try multiple selectors to select an option from a dropdown"""
        for selector in selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    await self.page.locator(selector).select_option(value)
                    await self.speak(f"Selected {value} for {purpose}")
                    return True
            except Exception as e:
                print(f"Error with selector {selector} for selecting {value} in {purpose}: {e}")
                continue

        await self.speak(f"Could not find dropdown to select {value} for {purpose}")
        return False

    async def try_selectors_for_check(self, selectors, purpose):
        """Try multiple selectors to check a checkbox"""
        for selector in selectors:
            try:
                if await self.page.locator(selector).count() > 0:
                    await self.page.locator(selector).check()
                    await self.speak(f"Checked {purpose}")
                    return True
            except Exception as e:
                print(f"Error with selector {selector} for checking {purpose}: {e}")
                continue

        await self.speak(f"Could not find checkbox for {purpose}")
        return False
