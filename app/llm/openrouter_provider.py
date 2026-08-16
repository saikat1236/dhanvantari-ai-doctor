import httpx
import logging
from typing import Any, List, Dict
from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)

OPENROUTER_FALLBACKS = [
    "deepseek/deepseek-r1",
    "qwen/qwen-2.5-72b-instruct",
    "meta-llama/llama-3.3-70b-instruct"
]

class OpenRouterProvider(LLMProvider):
    """Queries OpenRouter API for DeepSeek-R1 CoT reasoning and multimodal vision processing."""
    def __init__(self, api_key: str, model_name: str = "deepseek/deepseek-r1"):
        self.api_key = api_key
        self.model_name = model_name
        self.client = httpx.AsyncClient(timeout=20)

    async def generate(self, system_prompt: str, messages: List[Dict], **kwargs: Any) -> str:
        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
            
        for msg in messages:
            role = "assistant" if msg.get("role") == "assistant" else "user"
            payload_messages.append({"role": role, "content": msg.get("content", "")})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://dhanvantari-ai.org",
            "X-Title": "Dhanvantari AI Doctor",
            "Content-Type": "application/json"
        }
        url = "https://openrouter.ai/api/v1/chat/completions"

        target_model = kwargs.get("model", self.model_name)
        models_to_try = [target_model] + [m for m in OPENROUTER_FALLBACKS if m != target_model]
        last_error = None

        for model in models_to_try:
            payload = {
                "model": model,
                "messages": payload_messages,
                "temperature": kwargs.get("temperature", 0.3),
                "max_tokens": kwargs.get("max_tokens", 800)
            }
            try:
                resp = await self.client.post(url, json=payload, headers=headers, timeout=12.0)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.warning(f"OpenRouter model '{model}' returned {resp.status_code}: {resp.text}")
                    last_error = f"Status {resp.status_code}: {resp.text}"
            except Exception as e:
                logger.warning(f"OpenRouter model '{model}' failed: {str(e)}")
                last_error = str(e)

        raise RuntimeError(f"All OpenRouter attempts failed. Last error: {last_error}")

    async def analyze_image(self, base64_image: str, mime_type: str, prompt: str, **kwargs: Any) -> str:
        """Process multimodal image (CXR / Lab report) using OpenRouter vision models with fast timeout."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://dhanvantari-ai.org",
            "X-Title": "Dhanvantari AI Doctor",
            "Content-Type": "application/json"
        }
        url = "https://openrouter.ai/api/v1/chat/completions"
        data_url = f"data:{mime_type};base64,{base64_image}"

        # Test single high-compatibility vision model with quick timeout
        payload = {
            "model": "qwen/qwen-2.5-vl-72b-instruct",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}}
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 800
        }
        try:
            resp = await self.client.post(url, json=payload, headers=headers, timeout=6.0)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                logger.warning(f"Vision request returned {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"Vision analysis error: {str(e)}")

        raise RuntimeError("OpenRouter vision model unavailable.")
