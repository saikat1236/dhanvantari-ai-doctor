import httpx
from typing import Any
from app.llm.base import LLMProvider

class GemmaProvider(LLMProvider):
    """Talks to Google AI Developer API for Gemma hosted models (zero-SDK approach for maximum portability)."""
    def __init__(self, api_key: str, model_name: str = "gemma-2-9b-it"):
        self.api_key = api_key
        self.model_name = model_name
        self.client = httpx.AsyncClient(timeout=30)

    async def generate(self, system_prompt: str, messages: list[dict], **kwargs: Any) -> str:
        # Prepend system instructions to the first turn to ensure absolute compatibility 
        # with Gemma model endpoints (which do not support the systemInstruction block).
        contents = []
        
        if system_prompt and messages:
            # Format the first user message with system instructions prepended
            first_msg = messages[0]
            role = "model" if first_msg.get("role") == "assistant" else "user"
            combined_text = f"System Instructions:\n{system_prompt}\n\nUser Message:\n{first_msg.get('content', '')}"
            
            contents.append({
                "role": role,
                "parts": [{"text": combined_text}]
            })
            
            # Add subsequent turns
            for msg in messages[1:]:
                role = "model" if msg.get("role") == "assistant" else "user"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.get("content", "")}]
                })
        else:
            # Fallback if messages list is empty
            if system_prompt:
                contents.append({
                    "role": "user",
                    "parts": [{"text": f"System Instructions:\n{system_prompt}\n\nUser: Hello"}]
                })
            else:
                contents.append({
                    "role": "user",
                    "parts": [{"text": "Hello"}]
                })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.3),
                "maxOutputTokens": kwargs.get("max_tokens", 1000),
            }
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        try:
            resp = await self.client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            raise RuntimeError(f"Gemma API provider error: {str(e)}") from e


