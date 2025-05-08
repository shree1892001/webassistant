from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import re
from voice_assistant.utils.constants import COMMAND_PATTERNS

class BasePlugin(ABC):
    """Base class for all plugins"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.command_patterns = self._get_command_patterns()
        self.initialize()

    def initialize(self) -> None:
        """Initialize the plugin"""
        pass

    def _get_command_patterns(self) -> Dict[str, str]:
        """Get command patterns for this plugin"""
        return {}

    def _matches_pattern(self, command: str, pattern: str) -> bool:
        """Check if a command matches a pattern"""
        return bool(re.search(pattern, command, re.IGNORECASE))

    def _extract_pattern(self, command: str, pattern: str) -> str:
        """Extract matched text from a command using a pattern"""
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""

    @abstractmethod
    async def handle_command(self, command: str) -> bool:
        """Handle a command"""
        pass

    def get_help_text(self) -> List[str]:
        """Get help text for this plugin"""
        return []

    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for this plugin"""
        return {}

    def validate_config(self) -> bool:
        """Validate plugin configuration"""
        return True

class PluginManager:
    """Manages all plugins"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.plugins: Dict[str, BasePlugin] = {}
        self._load_plugins()

    def _load_plugins(self) -> None:
        """Load all available plugins"""
        # This would be populated dynamically based on installed plugins
        pass

    def register_plugin(self, name: str, plugin: BasePlugin) -> None:
        """Register a new plugin"""
        self.plugins[name] = plugin

    def unregister_plugin(self, name: str) -> None:
        """Unregister a plugin"""
        if name in self.plugins:
            del self.plugins[name]

    async def handle_command(self, command: str) -> bool:
        """Handle a command using appropriate plugin"""
        for plugin in self.plugins.values():
            if await plugin.handle_command(command):
                return True
        return False

    def get_help_text(self) -> List[str]:
        """Get help text from all plugins"""
        help_text = []
        for plugin in self.plugins.values():
            help_text.extend(plugin.get_help_text())
        return help_text 