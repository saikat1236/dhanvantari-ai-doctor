import httpx
from typing import Any
from app.llm.base import LLMProvider

class GeminiProvider(LLMProvider):
    """Talks to Google Gemini API using raw HTTP requests (zero-SDK approach for maximum portability)."""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30)

    async def generate(self, system_prompt: str, messages: list[dict], **kwargs: Any) -> str:
        # Map roles to Google API specifications (user -> user, assistant -> model)
        contents = []
        for msg in messages:
            role = "model" if msg.get("role") == "assistant" else "user"
            contents.append({
                "role": role,
                "parts": [{"text": msg.get("content", "")}]
            })

        # If system_prompt is provided, we set it as the system instruction
        payload = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.3),
                "maxOutputTokens": kwargs.get("max_tokens", 1000),
            }
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        try:
            resp = await self.client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            raise RuntimeError(f"Gemini API provider error: {str(e)}") from e


