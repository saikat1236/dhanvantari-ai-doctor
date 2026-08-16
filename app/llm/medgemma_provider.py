import httpx
from typing import Any
from app.llm.base import LLMProvider

class MedGemmaProvider(LLMProvider):
    """Talks to a self-hosted vLLM server running MedGemma 1.5."""
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30)

    async def generate(self, system_prompt: str, messages: list[dict], **kwargs: Any) -> str:
        payload = {
            "model": "medgemma-1.5-27b",
            "messages": [{"role": "system", "content": system_prompt}, *messages],
            "temperature": kwargs.get("temperature", 0.2),
            "max_tokens": kwargs.get("max_tokens", 800),
        }
        url = f"{self.base_url.rstrip('/')}/v1/chat/completions"
        try:
            resp = await self.client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"MedGemma provider error: {str(e)}") from e


