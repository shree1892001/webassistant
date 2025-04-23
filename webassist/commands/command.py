"""
Command interface for WebAssist
"""

from abc import ABC, abstractmethod
import re
from typing import Dict, Any, List, Optional, Pattern

from webassist.models.result import InteractionResult


class Command(ABC):
    """Abstract base class for commands"""

    def __init__(self, pattern: Optional[Pattern] = None):
        """Initialize the command"""
        self.pattern = pattern

    def matches(self, command_text: str) -> bool:
        """Check if the command matches the pattern"""
        if self.pattern:
            return bool(self.pattern.match(command_text.lower()))
        return False

    @abstractmethod
    async def execute(self, command_text: str, **kwargs) -> InteractionResult:
        """Execute the command"""
        pass


class CommandRegistry:
    """Registry for commands"""

    def __init__(self):
        """Initialize the registry"""
        self.commands: List[Command] = []

    async def register(self, command: Command) -> None:
        """Register a command"""
        self.commands.append(command)

    async def register_all(self, commands: List[Command]) -> None:
        """Register multiple commands"""
        self.commands.extend(commands)

    async def process(self, command_text: str, **kwargs) -> InteractionResult:
        """Process a command"""
        for command in self.commands:
            if command.matches(command_text):
                return await command.execute(command_text, **kwargs)

        return InteractionResult(
            success=False,
            message=f"No command found for: {command_text}"
        )
