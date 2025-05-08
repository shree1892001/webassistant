from typing import Dict, Any
from voice_assistant.core.plugin import BasePlugin

class PluginManager:
    """Manages plugins for the voice assistant"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.plugins: Dict[str, BasePlugin] = {}
    
    def register_plugin(self, name: str, plugin: BasePlugin) -> None:
        """Register a new plugin"""
        self.plugins[name] = plugin
    
    def unregister_plugin(self, name: str) -> None:
        """Unregister a plugin"""
        if name in self.plugins:
            del self.plugins[name]
    
    def get_plugin(self, name: str) -> BasePlugin:
        """Get a plugin by name"""
        return self.plugins.get(name)
    
    def get_all_plugins(self) -> Dict[str, BasePlugin]:
        """Get all registered plugins"""
        return self.plugins.copy() 