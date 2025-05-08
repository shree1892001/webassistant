"""
Member and Manager interaction handlers for the Voice Assistant.

This module contains handlers for member and manager interactions, including
selecting members, changing member types, and adding new members.
"""

import re
import asyncio
from typing import Dict, List, Any, Optional, Tuple

from webassist.voice_assistant.constants import (
    MEMBER_CHECKBOX_SELECTORS, MEMBER_MANAGER_DROPDOWN_SELECTORS,
    ADD_MEMBER_MANAGER_BUTTON_SELECTORS, JS_FIND_MEMBER_BY_NAME,
    JS_FIND_MEMBER_CHECKBOX, JS_SET_MEMBER_MANAGER_TYPE,
    JS_FIND_ADD_MEMBER_MANAGER_BUTTON
)


class MemberManagerHandler:
    """Handler for member and manager interactions"""

    def __init__(self, page, speak_func, llm_utils, browser_utils):
        """Initialize the member manager handler"""
        self.page = page
        self.speak = speak_func
        self.llm_utils = llm_utils
        self.browser_utils = browser_utils

    async def handle_command(self, command: str) -> bool:
        """Handle member/manager related commands"""
        # Handle member/manager selection
        member_match = re.search(r'(?:click|check|select|toggle|mark)\s+(?:on\s+)?(?:the\s+)?(?:member|manager)\s+(?:named|called|with\s+name)\s+(.+)', command.lower())
        if member_match:
            # Get the member name
            member_name = member_match.group(1)
            
            if member_name:
                return await self.handle_member_selection(member_name)
            else:
                await self.speak("Please specify which member or manager you want to select")
                return True
            
        # Handle member/manager type setting
        type_match = re.search(r'(?:set|make|change)\s+(?:row|member|person|entry)\s+(\d+)\s+(?:to|as)\s+(member|manager)', command.lower())
        if type_match:
            try:
                row_index = int(type_match.group(1)) - 1  # Convert to 0-based index
                type_value = type_match.group(2).capitalize()
                return await self.handle_type_change(row_index, type_value)
            except ValueError:
                await self.speak(f"Invalid row index: {type_match.group(1)}")
                return True
            
        # Handle add member/manager button
        add_member_match = re.search(r'(?:click|press|add|create)\s+(?:new\s+)?(?:member|manager|member\s+or\s+manager)', command.lower())
        if add_member_match:
            return await self.handle_add_member()
            
        return False

    async def handle_member_selection(self, member_name: str) -> bool:
        """Handle selecting a member by name"""
        await self.speak(f"Looking for {member_name}...")
        
        try:
            # Use the JavaScript from constants to find the member by name
            js_result = await self.page.evaluate(JS_FIND_MEMBER_BY_NAME, member_name)
            
            if js_result and js_result.get('success'):
                reason = js_result.get('reason', '')
                row_index = js_result.get('rowIndex', 0)
                
                if reason == 'already_checked':
                    await self.speak(f"Member {member_name} is already selected")
                else:
                    await self.speak(f"Selected member {member_name}")
                
                return True
            else:
                await self.speak(f"Could not find member with name {member_name}")
                return False
                
        except Exception as e:
            await self.speak(f"Error finding member: {str(e)}")
            return False

    async def handle_type_change(self, row_index: int, type_value: str) -> bool:
        """Handle changing a member's type"""
        await self.speak(f"Setting row {row_index + 1} to {type_value}...")
        
        try:
            # Validate the type value
            if type_value not in ["Member", "Manager"]:
                await self.speak(f"Invalid type value: {type_value}. Must be Member or Manager")
                return False
            
            # Use the JavaScript from constants to set the member/manager type
            js_result = await self.page.evaluate(JS_SET_MEMBER_MANAGER_TYPE, row_index, type_value)
            
            if js_result and js_result.get('success'):
                reason = js_result.get('reason', '')
                
                if reason == 'already_set':
                    await self.speak(f"Already set to {type_value}")
                elif reason == 'pending':
                    # Wait for the dropdown to be clicked and option to be selected
                    await asyncio.sleep(1)
                    await self.speak(f"Set to {type_value}")
                else:
                    await self.speak(f"Set to {type_value}")
                
                return True
            else:
                reason = js_result.get('reason', '') if js_result else 'unknown'
                await self.speak(f"Could not set type to {type_value}")
                return False
                
        except Exception as e:
            await self.speak(f"Error setting member type: {str(e)}")
            return False

    async def handle_add_member(self) -> bool:
        """Handle adding a new member"""
        await self.speak("Adding new member or manager...")
        
        try:
            # Try each selector from the constants
            for selector in ADD_MEMBER_MANAGER_BUTTON_SELECTORS:
                try:
                    # Check if the element exists
                    element = await self.page.query_selector(selector)
                    if element:
                        # Click the element
                        await element.click()
                        # Wait a moment for the form to open
                        await asyncio.sleep(1)
                        return True
                except Exception:
                    continue
            
            # If none of the selectors worked, try JavaScript approach
            js_result = await self.page.evaluate(JS_FIND_ADD_MEMBER_MANAGER_BUTTON)
            
            if js_result:
                await asyncio.sleep(1)
                return True
            
            await self.speak("Could not find the add member or manager button")
            return False
            
        except Exception as e:
            await self.speak(f"Error adding member: {str(e)}")
            return False

    async def click_member_checkbox(self, row_index: int = 0) -> bool:
        """Click a checkbox in the member/manager table"""
        try:
            # Use the JavaScript from constants to find and click the member checkbox
            js_result = await self.page.evaluate(JS_FIND_MEMBER_CHECKBOX, row_index)
            
            if js_result and js_result.get('success'):
                return True
            else:
                return False
                
        except Exception as e:
            await self.speak(f"Error clicking member checkbox: {str(e)}")
            return False
