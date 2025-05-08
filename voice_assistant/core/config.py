from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Type, List
import json
import os
from pathlib import Path

@dataclass
class BrowserConfig:
    headless: bool = True
    width: int = 1280
    height: int = 800
    timeout: int = 30000

@dataclass
class SpeechConfig:
    rate: int = 150
    volume: float = 1.0

@dataclass
class LLMConfig:
    provider: str = "gemini"
    model: str = "gemini-pro"
    api_key: Optional[str] = None

@dataclass
class AssistantConfig:
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    speech: SpeechConfig = field(default_factory=SpeechConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    
    @classmethod
    def from_env(cls) -> 'AssistantConfig':
        """Create configuration from environment variables"""
        import os
        return cls(
            browser=BrowserConfig(
                headless=os.getenv('BROWSER_HEADLESS', 'true').lower() == 'true',
                width=int(os.getenv('BROWSER_WIDTH', '1280')),
                height=int(os.getenv('BROWSER_HEIGHT', '800')),
                timeout=int(os.getenv('BROWSER_TIMEOUT', '30000'))
            ),
            speech=SpeechConfig(
                rate=int(os.getenv('SPEECH_RATE', '150')),
                volume=float(os.getenv('SPEECH_VOLUME', '1.0'))
            ),
            llm=LLMConfig(
                provider=os.getenv('LLM_PROVIDER', 'gemini'),
                model=os.getenv('LLM_MODEL', 'gemini-pro'),
                api_key=os.getenv('GEMINI_API_KEY')
            )
        )

class ConfigManager:
    """Manages dynamic configuration"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(os.getcwd(), 'config.json')
        self.config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            self.config = {}

    def save_config(self) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        self.config[key] = value
        self.save_config()

    def update(self, new_config: Dict[str, Any]) -> None:
        """Update multiple configuration values"""
        self.config.update(new_config)
        self.save_config()

    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Get configuration for a specific plugin"""
        return self.config.get('plugins', {}).get(plugin_name, {})

    def set_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> None:
        """Set configuration for a specific plugin"""
        if 'plugins' not in self.config:
            self.config['plugins'] = {}
        self.config['plugins'][plugin_name] = config
        self.save_config()

    def validate_config(self, schema: Dict[str, Type]) -> bool:
        """Validate configuration against a schema"""
        try:
            for key, expected_type in schema.items():
                if key in self.config and not isinstance(self.config[key], expected_type):
                    return False
            return True
        except Exception:
            return False

    def get_available_plugins(self) -> List[str]:
        """Get list of available plugins"""
        return list(self.config.get('plugins', {}).keys())

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """Check if a plugin is enabled"""
        return self.get_plugin_config(plugin_name).get('enabled', False) 