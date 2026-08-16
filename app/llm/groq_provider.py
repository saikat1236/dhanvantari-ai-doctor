import httpx
import logging
from typing import Any
from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)

# Preferred model sequence with automatic fallback
GROQ_MODEL_FALLBACKS = [
    "llama-3.3-70b-versatile",
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-120b",
    "mixtral-8x7b-32768",
    "llama-3.1-8b-instant"
]

class GroqProvider(LLMProvider):
    """Queries Groq Cloud API for ultra-fast open-weight reasoning & triage with resilient model failover."""
    def __init__(self, api_key: str, model_name: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model_name = model_name
        self.client = httpx.AsyncClient(timeout=30)

    async def generate(self, system_prompt: str, messages: list[dict], **kwargs: Any) -> str:
        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
            
        for msg in messages:
            role = "assistant" if msg.get("role") == "assistant" else "user"
            payload_messages.append({"role": role, "content": msg.get("content", "")})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        url = "https://api.groq.com/openai/v1/chat/completions"

        # Try user configured model first, then fallback models
        models_to_try = [self.model_name] + [m for m in GROQ_MODEL_FALLBACKS if m != self.model_name]
        last_error = None

        for model in models_to_try:
            payload = {
                "model": model,
                "messages": payload_messages,
                "temperature": kwargs.get("temperature", 0.3),
                "max_tokens": kwargs.get("max_tokens", 1000)
            }
            try:
                resp = await self.client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.warning(f"Groq model '{model}' returned status {resp.status_code}: {resp.text}")
                    last_error = f"Status {resp.status_code}: {resp.text}"
            except Exception as e:
                logger.warning(f"Groq model '{model}' request failed: {str(e)}")
                last_error = str(e)

        raise RuntimeError(f"All Groq model attempts failed. Last error: {last_error}")
