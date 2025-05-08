"""Voice Assistant package for web automation and voice control"""
from .core.assistant import VoiceAssistant
from .core.config import AssistantConfig, BrowserConfig, SpeechConfig, LLMConfig

__all__ = [
    'VoiceAssistant',
    'AssistantConfig',
    'BrowserConfig',
    'SpeechConfig',
    'LLMConfig'
] 