"""
Browser module for WebAssist
"""

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from webassist.core.config import AssistantConfig


class WebBrowser:
    """Web browser using Playwright"""

    def __init__(self, config: AssistantConfig):
        """Initialize the browser"""
        self.config = config
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def start(self) -> Page:
        """Start the browser and return the page"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.config.browser_headless,
            slow_mo=self.config.browser_slow_mo
        )
        self.context = await self.browser.new_context(
            viewport={
                'width': self.config.browser_width,
                'height': self.config.browser_height
            }
        )
        self.page = await self.context.new_page()
        return self.page

    async def close(self) -> None:
        """Close the browser"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            print("🛑 Browser closed")
        except Exception as e:
            print(f"Error closing browser: {e}")

    def get_page(self) -> Page:
        """Get the current page"""
        return self.page

    def get_browser(self) -> Browser:
        """Get the browser"""
        return self.browser

    def get_context(self) -> BrowserContext:
        """Get the browser context"""
        return self.context
