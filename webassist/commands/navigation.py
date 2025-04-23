"""
Navigation commands for WebAssist
"""

import re
from typing import Dict, Any

from webassist.commands.command import Command
from webassist.web.navigator import WebNavigator
from webassist.models.result import InteractionResult
from webassist.core.constants import NAVIGATION_PATTERN


class NavigationCommand(Command):
    """Command for navigating to a website"""
    
    def __init__(self, navigator: WebNavigator):
        """Initialize the command"""
        super().__init__(re.compile(NAVIGATION_PATTERN, re.IGNORECASE))
        self.navigator = navigator
    
    async def execute(self, command_text: str, **kwargs) -> InteractionResult:
        """Execute the command"""
        match = self.pattern.match(command_text)
        if match:
            url = match.group(2)
            success = self.navigator.browse_website(url)
            if success:
                return InteractionResult(
                    success=True,
                    message=f"Navigated to {url}"
                )
            else:
                return InteractionResult(
                    success=False,
                    message=f"Failed to navigate to {url}"
                )
        
        return InteractionResult(
            success=False,
            message="Invalid navigation command"
        )


class BackCommand(Command):
    """Command for going back to the previous page"""
    
    def __init__(self, navigator: WebNavigator):
        """Initialize the command"""
        super().__init__(re.compile(r'^(go back|back)$', re.IGNORECASE))
        self.navigator = navigator
    
    async def execute(self, command_text: str, **kwargs) -> InteractionResult:
        """Execute the command"""
        success = self.navigator.go_back()
        if success:
            return InteractionResult(
                success=True,
                message="Went back to the previous page"
            )
        else:
            return InteractionResult(
                success=False,
                message="Failed to go back"
            )


class ForwardCommand(Command):
    """Command for going forward to the next page"""
    
    def __init__(self, navigator: WebNavigator):
        """Initialize the command"""
        super().__init__(re.compile(r'^(go forward|forward)$', re.IGNORECASE))
        self.navigator = navigator
    
    async def execute(self, command_text: str, **kwargs) -> InteractionResult:
        """Execute the command"""
        success = self.navigator.go_forward()
        if success:
            return InteractionResult(
                success=True,
                message="Went forward to the next page"
            )
        else:
            return InteractionResult(
                success=False,
                message="Failed to go forward"
            )


class RefreshCommand(Command):
    """Command for refreshing the current page"""
    
    def __init__(self, navigator: WebNavigator):
        """Initialize the command"""
        super().__init__(re.compile(r'^(refresh|reload)$', re.IGNORECASE))
        self.navigator = navigator
    
    async def execute(self, command_text: str, **kwargs) -> InteractionResult:
        """Execute the command"""
        success = self.navigator.refresh()
        if success:
            return InteractionResult(
                success=True,
                message="Refreshed the current page"
            )
        else:
            return InteractionResult(
                success=False,
                message="Failed to refresh"
            )
