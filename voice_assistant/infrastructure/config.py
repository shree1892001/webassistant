import json
import os
from typing import Dict, Any
from voice_assistant.utils.constants import DEFAULT_CONFIG

class ConfigManager:
    """Manages configuration settings for the voice assistant"""
    
    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file if it exists"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.config.update(json.load(f))
            except Exception as e:
                print(f"Error loading config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value"""
        self.config[key] = value
        self._save_config()
    
    def update(self, new_config: Dict[str, Any]) -> None:
        """Update multiple configuration values"""
        self.config.update(new_config)
        self._save_config()
    
    def _save_config(self) -> None:
        """Save configuration to file"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        try:
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """Get the entire configuration"""
        return self.config.copy() 