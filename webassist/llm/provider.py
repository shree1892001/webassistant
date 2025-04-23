"""
LLM provider interface for WebAssist
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    async def generate_content(self, prompt: str) -> Any:
        """Generate content using the LLM"""
        pass

    @abstractmethod
    async def get_structured_guidance(self, prompt: str) -> Dict[str, Any]:
        """Get structured guidance from the LLM"""
        pass

    @abstractmethod
    async def get_selectors(self, prompt: str, context: Dict[str, Any]) -> List[str]:
        """Get selectors from the LLM"""
        pass


class LLMProviderFactory:
    """Factory for creating LLM providers"""

    @staticmethod
    def create_provider(provider_type: str, api_key: str, model: Optional[str] = None) -> LLMProvider:
        """Create an LLM provider"""
        if provider_type.lower() == "gemini":
            from webassist.llm.gemini import GeminiProvider
            return GeminiProvider(api_key, model)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider_type}")
