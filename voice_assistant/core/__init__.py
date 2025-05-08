"""
Core package for the Voice Assistant
"""
from .assistant import VoiceAssistant
from .config import AssistantConfig, BrowserConfig, SpeechConfig, LLMConfig, ConfigManager
from .speech import SpeechEngine
from .navigator import WebNavigator
from .command_processor import CommandProcessor
from .voice_engine import VoiceEngine
from .browser_manager import BrowserManager
from .plugin import PluginManager, BasePlugin

__all__ = [
    'VoiceAssistant',
    'AssistantConfig',
    'BrowserConfig',
    'SpeechConfig',
    'LLMConfig',
    'ConfigManager',
    'SpeechEngine',
    'WebNavigator',
    'CommandProcessor',
    'VoiceEngine',
    'BrowserManager',
    'PluginManager',
    'BasePlugin'
] 