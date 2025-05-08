"""
Business Purpose interaction handlers for the Voice Assistant.

This module contains handlers for business purpose dropdown interactions.
"""

import re
import asyncio
from typing import Dict, List, Any, Optional, Tuple

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
            # Try to click the business purpose dropdown using its ID
            clicked = await self.page.evaluate("""
            () => {
                console.log("Looking for business purpose dropdown...");
                
                // Try to find by ID
                const purposeDropdown = document.getElementById('CD_Business_Purpose_Details');
                if (purposeDropdown) {
                    console.log("Found business purpose dropdown by ID");
                    purposeDropdown.click();
                    return true;
                }
                
                // Try to find by class and text content
                const dropdowns = document.querySelectorAll('.p-dropdown');
                for (const dropdown of dropdowns) {
                    const label = dropdown.querySelector('.p-dropdown-label');
                    if (label && (
                        label.textContent.toLowerCase().includes('purpose') || 
                        label.textContent.toLowerCase().includes('business')
                    )) {
                        console.log("Found business purpose dropdown by text content");
                        dropdown.click();
                        return true;
                    }
                }
                
                // Try to find by nearby label
                const labels = Array.from(document.querySelectorAll('label'));
                for (const label of labels) {
                    if (label.textContent.toLowerCase().includes('purpose') || 
                        label.textContent.toLowerCase().includes('business purpose')) {
                        
                        // Look for dropdown in the same container
                        const parent = label.closest('.field') || label.parentElement;
                        if (parent) {
                            const dropdown = parent.querySelector('.p-dropdown');
                            if (dropdown) {
                                console.log("Found business purpose dropdown by label");
                                dropdown.click();
                                return true;
                            }
                        }
                        
                        // Try next sibling
                        let current = label;
                        while (current.nextElementSibling) {
                            current = current.nextElementSibling;
                            if (current.classList.contains('p-dropdown')) {
                                console.log("Found business purpose dropdown by sibling");
                                current.click();
                                return true;
                            }
                        }
                    }
                }
                
                console.log("Could not find business purpose dropdown");
                return false;
            }
            """)
            
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
            
            # Select the business purpose
            selected = await self.page.evaluate("""
            (purposeName) => {
                console.log("Looking for business purpose:", purposeName);
                
                // Find all dropdown items
                const items = Array.from(document.querySelectorAll('.p-dropdown-item'));
                console.log(`Found ${items.length} dropdown items`);
                
                // Log all available options for debugging
                items.forEach(item => console.log(`Option: ${item.textContent.trim()}`));
                
                // Try to find an exact match first
                let match = items.find(item => 
                    item.textContent.trim().toLowerCase() === purposeName.toLowerCase()
                );
                
                // If no exact match, try partial match
                if (!match) {
                    match = items.find(item => 
                        item.textContent.trim().toLowerCase().includes(purposeName.toLowerCase())
                    );
                }
                
                if (match) {
                    console.log(`Clicking business purpose: ${match.textContent.trim()}`);
                    match.click();
                    return true;
                }
                
                return false;
            }
            """, purpose_name)
            
            if selected:
                await self.speak(f"Selected business purpose: {purpose_name}")
                return True
            else:
                await self.speak(f"Could not find business purpose: {purpose_name}")
                return False
                
        except Exception as e:
            await self.speak(f"Error selecting business purpose: {str(e)}")
            return False
