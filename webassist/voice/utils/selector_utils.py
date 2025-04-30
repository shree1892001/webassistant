from typing import List, Dict, Any

class SelectorUtils:
    def __init__(self, assistant):
        self.assistant = assistant

    async def try_selectors_for_click(self, selectors: List[str], purpose: str) -> bool:
        """Try multiple selectors for clicking an element"""
        for selector in selectors:
            try:
                if await self.assistant.page.locator(selector).count() > 0:
                    await self.assistant.page.locator(selector).first.click()
                    self.assistant.speak(f"Successfully clicked {purpose}")
                    await self.assistant.page.wait_for_timeout(1000)
                    return True
            except Exception:
                continue
        return False

    async def try_selectors_for_type(self, selectors: List[str], text: str, purpose: str, max_retries: int = 3, timeout: int = 30000) -> bool:
        """Try multiple selectors for typing text into an element"""
        for selector in selectors:
            try:
                if await self.assistant.page.locator(selector).count() > 0:
                    await self.assistant.page.locator(selector).first.fill(text)
                    self.assistant.speak(f"Successfully entered {purpose}")
                    await self.assistant.page.wait_for_timeout(1000)
                    return True
            except Exception:
                continue
        return False

    async def try_selectors_for_hover(self, selectors: List[str], purpose: str) -> bool:
        """Try multiple selectors for hovering over an element"""
        for selector in selectors:
            try:
                if await self.assistant.page.locator(selector).count() > 0:
                    await self.assistant.page.locator(selector).first.hover()
                    self.assistant.speak(f"Successfully hovered over {purpose}")
                    await self.assistant.page.wait_for_timeout(1000)
                    return True
            except Exception:
                continue
        return False

    async def try_selectors_for_check(self, selectors: List[str], purpose: str) -> bool:
        """Try multiple selectors for checking/unchecking an element"""
        for selector in selectors:
            try:
                if await self.assistant.page.locator(selector).count() > 0:
                    checkbox = self.assistant.page.locator(selector).first
                    is_checked = await checkbox.is_checked()
                    if is_checked:
                        await checkbox.uncheck()
                    else:
                        await checkbox.check()
                    self.assistant.speak(f"Successfully toggled {purpose}")
                    await self.assistant.page.wait_for_timeout(1000)
                    return True
            except Exception:
                continue
        return False

    async def retry_click(self, selector: str, purpose: str) -> bool:
        """Retry clicking an element with exponential backoff"""
        max_retries = 3
        base_delay = 1000  # milliseconds

        for attempt in range(max_retries):
            try:
                if await self.assistant.page.locator(selector).count() > 0:
                    await self.assistant.page.locator(selector).first.click()
                    self.assistant.speak(f"Successfully clicked {purpose}")
                    return True
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    await self.assistant.page.wait_for_timeout(delay)
                else:
                    self.assistant.speak(f"Failed to click {purpose} after {max_retries} attempts: {str(e)}")
        return False

    async def retry_type(self, selector: str, text: str, purpose: str, max_retries: int = 3, timeout: int = 30000) -> bool:
        """Retry typing into an element with exponential backoff"""
        base_delay = 1000  # milliseconds

        for attempt in range(max_retries):
            try:
                if await self.assistant.page.locator(selector).count() > 0:
                    await self.assistant.page.locator(selector).first.fill(text)
                    self.assistant.speak(f"Successfully entered {purpose}")
                    return True
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    await self.assistant.page.wait_for_timeout(delay)
                else:
                    self.assistant.speak(f"Failed to enter {purpose} after {max_retries} attempts: {str(e)}")
        return False 