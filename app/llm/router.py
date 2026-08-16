import logging
from typing import Any
from app.config import settings
from app.llm.groq_provider import GroqProvider
from app.llm.openrouter_provider import OpenRouterProvider
from app.llm.medgemma_hf_provider import HuggingFaceMedGemmaProvider
from app.llm.medgemma_provider import MedGemmaProvider
from app.llm.gemma_provider import GemmaProvider
from app.llm.gemini_provider import GeminiProvider
from app.llm.mock_provider import MockProvider

logger = logging.getLogger(__name__)

class LLMRouter:
    def __init__(self):
        self.providers = []
        
        # 1. Groq Open-Weight Fast Reasoning Provider (DeepSeek-R1 / LLaMA 3.3)
        if settings.GROQ_API_KEY:
            logger.info(f"Initializing Groq Reasoning provider ({settings.GROQ_MODEL_NAME}).")
            self.providers.append(GroqProvider(
                api_key=settings.GROQ_API_KEY,
                model_name=settings.GROQ_MODEL_NAME
            ))

        # 2. OpenRouter Free Reasoning Provider (DeepSeek-R1 / Qwen)
        if settings.OPENROUTER_API_KEY:
            logger.info(f"Initializing OpenRouter provider ({settings.OPENROUTER_MODEL_NAME}).")
            self.providers.append(OpenRouterProvider(
                api_key=settings.OPENROUTER_API_KEY,
                model_name=settings.OPENROUTER_MODEL_NAME
            ))

        # 3. HuggingFace MedGemma Provider
        if settings.HF_TOKEN:
            logger.info(f"Initializing HuggingFace MedGemma provider ({settings.MEDGEMMA_HF_MODEL_ID}).")
            self.providers.append(HuggingFaceMedGemmaProvider(
                token=settings.HF_TOKEN,
                model_id=settings.MEDGEMMA_HF_MODEL_ID
            ))

        # 4. Self-hosted local/remote MedGemma vLLM endpoint
        if settings.MEDGEMMA_API_BASE:
            logger.info(f"Initializing self-hosted MedGemma provider ({settings.MEDGEMMA_API_BASE}).")
            self.providers.append(MedGemmaProvider(
                base_url=settings.MEDGEMMA_API_BASE
            ))
        
        # 5. Cloud Gemma provider
        if settings.GEMINI_API_KEY:
            logger.info(f"Initializing cloud Gemma provider ({settings.GEMMA_MODEL_NAME}).")
            self.providers.append(GemmaProvider(
                api_key=settings.GEMINI_API_KEY, 
                model_name=settings.GEMMA_MODEL_NAME
            ))
            
        # 6. Cloud Gemini provider
        if settings.GEMINI_API_KEY:
            logger.info(f"Initializing cloud Gemini provider ({settings.GEMINI_MODEL_NAME}).")
            self.providers.append(GeminiProvider(
                api_key=settings.GEMINI_API_KEY
            ))
            
        # 7. Add Clinical Decision Engine (MockProvider) as the robust zero-failure fallback
        logger.info("Initializing Clinical Decision Support Engine as failsafe provider.")
        self.providers.append(MockProvider())

    async def generate(self, system_prompt: str, messages: list[dict], **kwargs: Any) -> str:
        errors = []
        for provider in self.providers:
            try:
                provider_name = provider.__class__.__name__
                logger.info(f"Attempting response generation with {provider_name}")
                result = await provider.generate(system_prompt, messages, **kwargs)
                logger.info(f"Successfully generated response using {provider_name}")
                return result
            except Exception as e:
                provider_name = provider.__class__.__name__
                logger.warning(f"{provider_name} failed: {str(e)}")
                errors.append(f"{provider_name}: {str(e)}")
                
        raise RuntimeError(f"All LLM providers failed. Errors: {'; '.join(errors)}")
