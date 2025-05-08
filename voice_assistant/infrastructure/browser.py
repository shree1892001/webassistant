from playwright.async_api import async_playwright
from typing import Dict, Any

class BrowserManager:
    """Manages browser automation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.browser = None
        self.context = None
        self.page = None
    
    async def initialize(self) -> None:
        """Initialize the browser"""
        playwright = await async_playwright().start()
        
        # Launch browser based on config
        browser_type = self.config.get('browser_type', 'chromium')
        if browser_type == 'chromium':
            self.browser = await playwright.chromium.launch(
                headless=self.config.get('headless', False)
            )
        elif browser_type == 'firefox':
            self.browser = await playwright.firefox.launch(
                headless=self.config.get('headless', False)
            )
        elif browser_type == 'webkit':
            self.browser = await playwright.webkit.launch(
                headless=self.config.get('headless', False)
            )
        
        # Create context and page
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
    
    async def navigate(self, url: str) -> bool:
        """Navigate to a URL"""
        try:
            await self.page.goto(url)
            return True
        except Exception as e:
            print(f"Error navigating to {url}: {e}")
            return False
    
    async def close(self, keep_browser_open: bool = False) -> None:
        """Close the browser"""
        if self.context:
            await self.context.close()
        if self.browser and not keep_browser_open:
            await self.browser.close() 