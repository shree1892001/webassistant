"""
Configuration module for WebAssist
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from webassist.Common.constants import (
    DEFAULT_BROWSER_WIDTH,
    DEFAULT_BROWSER_HEIGHT,
    DEFAULT_SPEECH_RATE,
    DEFAULT_SPEECH_VOLUME,
    DEFAULT_TIMEOUT,
    DEFAULT_RETRY_DELAY,
    DEFAULT_MAX_RETRIES,
    GEMINI_MODEL
)


@dataclass
class AssistantConfig:
    """Configuration for the assistant"""
    # API Keys
    gemini_api_key: str = ""

    # Browser settings
    browser_width: int = DEFAULT_BROWSER_WIDTH
    browser_height: int = DEFAULT_BROWSER_HEIGHT
    browser_headless: bool = False
    browser_slow_mo: int = 500

    # Speech settings
    speech_rate: int = DEFAULT_SPEECH_RATE
    speech_volume: float = DEFAULT_SPEECH_VOLUME
    speech_voice_id: Optional[int] = 1  # Default to female voice (index 1)

    # Interaction settings
    timeout: int = DEFAULT_TIMEOUT
    retry_delay: int = DEFAULT_RETRY_DELAY
    max_retries: int = DEFAULT_MAX_RETRIES

    # LLM settings
    llm_model: str = GEMINI_MODEL

    # Additional settings
    additional_settings: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls):
        """Create configuration from environment variables"""
        config = cls()

        # Load API keys from environment
        config.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")

        # Load other settings from environment if available
        if "BROWSER_WIDTH" in os.environ:
            config.browser_width = int(os.environ["BROWSER_WIDTH"])
        if "BROWSER_HEIGHT" in os.environ:
            config.browser_height = int(os.environ["BROWSER_HEIGHT"])
        if "BROWSER_HEADLESS" in os.environ:
            config.browser_headless = os.environ["BROWSER_HEADLESS"].lower() == "true"
        if "SPEECH_RATE" in os.environ:
            config.speech_rate = int(os.environ["SPEECH_RATE"])
        if "SPEECH_VOLUME" in os.environ:
            config.speech_volume = float(os.environ["SPEECH_VOLUME"])
        if "LLM_MODEL" in os.environ:
            config.llm_model = os.environ["LLM_MODEL"]

        return config

    @classmethod
    def from_file(cls, file_path: str):
        """Create configuration from a file"""
        # Implementation depends on file format (JSON, YAML, etc.)
        # For simplicity, not implemented here
        raise NotImplementedError("Loading from file not implemented yet")
