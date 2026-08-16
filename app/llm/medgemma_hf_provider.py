import httpx
import logging
from typing import Any
from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)

class HuggingFaceMedGemmaProvider(LLMProvider):
    """Queries MedGemma models on Hugging Face Serverless Inference API (cloud execution)."""
    def __init__(self, token: str, model_id: str = "google/medgemma-1.5-4b-it"):
        self.token = token
        self.model_id = model_id
        self.client = httpx.AsyncClient(timeout=30)

    async def generate(self, system_prompt: str, messages: list[dict], **kwargs: Any) -> str:
        # Construct messages payload matching OpenAI spec on HF Inference API
        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
            
        for msg in messages:
            role = "assistant" if msg.get("role") == "assistant" else "user"
            payload_messages.append({"role": role, "content": msg.get("content", "")})

        payload = {
            "model": self.model_id,
            "messages": payload_messages,
            "temperature": kwargs.get("temperature", 0.3),
            "max_tokens": kwargs.get("max_tokens", 1000)
        }

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        # Hugging Face serverless OpenAI-compatible endpoint
        url = f"https://api-inference.huggingface.co/models/{self.model_id}/v1/chat/completions"
        
        try:
            resp = await self.client.post(url, json=payload, headers=headers)
            
            # Catch cold start (503 Service Unavailable)
            if resp.status_code == 503:
                data = resp.json()
                estimated = data.get("estimated_time", 20)
                logger.warning(f"HF MedGemma model is warming up/loading. Est load: {estimated}s. Failing over.")
                raise RuntimeError(f"HuggingFace model loading: estimated warm up {estimated} seconds.")
                
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"HuggingFace MedGemma provider error: {str(e)}") from e


