from .base import AIProvider
from .mock_adapter import MockAIAdapter
from .live_adapter import GeminiLiveAdapter

def get_ai_provider(provider_type: str = "mock") -> AIProvider:
    if provider_type.lower() == "gemini":
        return GeminiLiveAdapter()
    return MockAIAdapter()

__all__ = ["AIProvider", "MockAIAdapter", "GeminiLiveAdapter", "get_ai_provider"]
