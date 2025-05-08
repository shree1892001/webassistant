from typing import Dict, Any
from voice_assistant.domain.entities.command import Command

class ActionExecutor:
    """Service for executing different types of actions"""
    
    def __init__(self, page, browser_manager, config_manager):
        self.page = page
        self.browser_manager = browser_manager
        self.config_manager = config_manager
    
    async def execute_goto(self, url: str) -> bool:
        """Execute navigation action"""
        if not url:
            return False
        
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        try:
            success = await self.browser_manager.navigate(url)
            return success
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            return False
    
    async def execute_click(self, selector: str, target: str) -> bool:
        """Execute click action"""
        try:
            # For login button, try multiple selectors
            if target.lower() in ["login", "login button", "sign in", "sign in button"]:
                selectors = [
                    "button.signup-btn",
                    "button.vstate-button",
                    "button[type='submit']",
                    "#signInButton",
                    ".signup-btn",
                    "button.p-button"
                ]
                
                for sel in selectors:
                    try:
                        element = await self.page.wait_for_selector(sel, timeout=2000)
                        if element:
                            await element.click()
                            return True
                    except Exception:
                        continue
                return False
            
            # For other elements, use the provided selector
            element = await self.page.wait_for_selector(selector, timeout=5000)
            if element:
                await element.click()
                return True
            return False
        except Exception as e:
            logger.error(f"Error clicking element: {e}")
            return False
    
    async def execute_fill(self, selector: str, text: str) -> bool:
        """Execute fill action"""
        try:
            # First try to find the element
            element = await self.page.wait_for_selector(selector, timeout=5000)
            
            if not element:
                # If element not found and it's a login form field, try to find and click the login button
                if selector in ["#floating_outlined3", "#floating_outlined15"]:
                    try:
                        login_button = await self.page.wait_for_selector(
                            "button.signup-btn, button.vstate-button, button[type='submit']",
                            timeout=5000
                        )
                        if login_button:
                            await login_button.click()
                            # Wait for the form to appear
                            await self.page.wait_for_selector(selector, timeout=5000)
                            # Try to find the element again
                            element = await self.page.wait_for_selector(selector, timeout=5000)
                    except Exception as e:
                        logger.error(f"Error finding login button: {e}")
            
            if element:
                await element.fill("")
                await element.fill(text)
                return True
            return False
        except Exception as e:
            logger.error(f"Error filling element: {e}")
            return False
    
    async def execute_switch_mode(self, mode: str) -> bool:
        """Execute mode switch action"""
        if mode in ["voice", "text"]:
            self.config_manager.set('input_mode', mode)
            return True
        return False 