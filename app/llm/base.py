from abc import ABC, abstractmethod
from typing import Any

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, system_prompt: str, messages: list[dict], **kwargs: Any) -> str:
        """Generate response given a system prompt and conversation messages."""
        pass
