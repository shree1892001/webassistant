from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import logging

logger = logging.getLogger(__name__)

class BrowserManager:
    """Manages browser and page interactions"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        logger.info(f"BrowserManager initialized with config: {self.config}")

    async def initialize(self) -> None:
        """Initialize browser components"""
        try:
            logger.info("Starting browser initialization...")
            self.playwright = await async_playwright().start()
            logger.info("Playwright started")
            
            headless = self.config.get('headless', False)
            logger.info(f"Launching browser with headless={headless}")
            
            self.browser = await self.playwright.chromium.launch(
                headless=headless
            )
            logger.info("Browser launched")
            
            self.context = await self.browser.new_context(
                viewport={
                    'width': self.config.get('width', 1280),
                    'height': self.config.get('height', 800)
                }
            )
            logger.info("Browser context created")
            
            self.page = await self.context.new_page()
            logger.info("New page created")
            logger.info("Browser initialization completed successfully")
        except Exception as e:
            logger.error(f"Error during browser initialization: {e}")
            raise

    async def navigate(self, url: str) -> bool:
        """Navigate to a URL"""
        try:
            logger.info(f"Attempting to navigate to: {url}")
            if not self.page:
                logger.error("No page available for navigation")
                return False
                
            await self.page.goto(url, wait_until="networkidle")
            logger.info(f"Successfully navigated to: {url}")
            return True
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            return False

    async def close(self, keep_browser_open: bool = False) -> None:
        """Close browser components"""
        if not keep_browser_open:
            logger.info("Closing browser components...")
            if self.context:
                await self.context.close()
                logger.info("Context closed")
            if self.browser:
                await self.browser.close()
                logger.info("Browser closed")
            if self.playwright:
                await self.playwright.stop()
                logger.info("Playwright stopped")
            logger.info("All browser components closed")
        else:
            logger.info("Browser kept open for inspection")

    def get_page(self) -> Page:
        """Get the current page"""
        return self.page

    def get_context(self) -> BrowserContext:
        """Get the current browser context"""
        return self.context

    def get_browser(self) -> Browser:
        """Get the current browser instance"""
        return self.browser 