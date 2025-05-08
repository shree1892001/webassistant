"""
Business Purpose interaction handlers for the Voice Assistant.

This module contains handlers for business purpose dropdown interactions.
"""

import re
import asyncio
from typing import Dict, List, Any, Optional, Tuple

from webassist.voice_assistant.constants import (
    BUSINESS_PURPOSE_DROPDOWN_SELECTORS,
    JS_FIND_BUSINESS_PURPOSE_DROPDOWN,
    JS_SELECT_BUSINESS_PURPOSE
)

class BusinessPurposeHandler:
    """Handler for business purpose dropdown interactions"""

    def __init__(self, page, speak_func, llm_utils, browser_utils):
        """Initialize the business purpose handler

        Args:
            page: Playwright page object
            speak_func: Function to speak text
            llm_utils: LLM utilities for generating selectors and actions
            browser_utils: Browser utilities for common operations
        """
        self.page = page
        self.speak = speak_func
        self.llm_utils = llm_utils
        self.browser_utils = browser_utils

    async def handle_command(self, command: str) -> bool:
        """Handle business purpose related commands

        Args:
            command: User command string

        Returns:
            bool: True if command was handled, False otherwise
        """
        # Handle business purpose dropdown command
        purpose_dropdown_match = re.search(r'(?:click|select|open)(?:\s+(?:on|the))?\s+(?:business\s+purpose|purpose)(?:\s+dropdown)?', command.lower())
        if purpose_dropdown_match:
            return await self.handle_business_purpose_dropdown()

        # Handle business purpose selection command
        purpose_selection_match = re.search(r'(?:select|choose|pick)\s+(?:business\s+purpose\s+)?([A-Za-z\s]+)(?:\s+(?:as|for)?\s+(?:business\s+purpose|purpose))?', command.lower())
        if purpose_selection_match:
            purpose_name = purpose_selection_match.group(1).strip()
            return await self.handle_business_purpose_selection(purpose_name)

        return False

    async def handle_business_purpose_dropdown(self) -> bool:
        """Handle clicking the business purpose dropdown

        Returns:
            bool: True if successful, False otherwise
        """
        await self.speak("Looking for business purpose dropdown...")

        try:
            # Try each selector from the constants
            for selector in BUSINESS_PURPOSE_DROPDOWN_SELECTORS:
                try:
                    # Check if the element exists
                    element = await self.page.query_selector(selector)
                    if element:
                        # Click the element
                        await element.click()
                        await self.speak("Clicked the business purpose dropdown")
                        # Wait for dropdown to open
                        await asyncio.sleep(1)
                        return True
                except Exception as e:
                    # Continue trying other selectors
                    continue

            # If none of the selectors worked, try JavaScript approach
            clicked = await self.page.evaluate(JS_FIND_BUSINESS_PURPOSE_DROPDOWN)

            if clicked:
                await self.speak("Clicked the business purpose dropdown")
                # Wait for dropdown to open
                await asyncio.sleep(1)
                return True
            else:
                await self.speak("Could not find business purpose dropdown")
                return False

        except Exception as e:
            await self.speak(f"Error clicking business purpose dropdown: {str(e)}")
            return False

    async def handle_business_purpose_selection(self, purpose_name: str) -> bool:
        """Handle selecting a business purpose from the dropdown

        Args:
            purpose_name: The business purpose to select

        Returns:
            bool: True if successful, False otherwise
        """
        await self.speak(f"Looking for business purpose: {purpose_name}")

        try:
            # First click the dropdown to open it
            dropdown_clicked = await self.handle_business_purpose_dropdown()
            if not dropdown_clicked:
                return False

            # Wait for dropdown items to appear
            await asyncio.sleep(1)

            # Select the business purpose using the JavaScript from constants
            result = await self.page.evaluate(JS_SELECT_BUSINESS_PURPOSE, purpose_name)

            if result and result.get('success'):
                selected_text = result.get('selected', purpose_name)
                await self.speak(f"Selected business purpose: {selected_text}")
                return True
            else:
                await self.speak(f"Could not find business purpose: {purpose_name}")
                return False

        except Exception as e:
            await self.speak(f"Error selecting business purpose: {str(e)}")
            return False
