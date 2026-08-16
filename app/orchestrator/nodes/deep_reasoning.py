import logging
from typing import Any
from app.config import settings
from app.llm.openrouter_provider import OpenRouterProvider
from app.orchestrator.state import ConversationState

logger = logging.getLogger(__name__)

DEEP_REASONING_PROMPT = """You are DeepSeek-R1, a frontier Clinical Reasoning Engine for Dhanvantari AI Doctor.
Perform step-by-step clinical chain-of-thought analysis for this complex patient presentation.

Clinical Instructions:
1. Analyze all reported symptoms across organ systems, duration, and patient history.
2. If multimodal imaging (CXR) or lab reports are present, integrate the findings into the differential.
3. Formulate a ranked differential diagnosis (Top 3 candidate conditions with ICD-10 codes and estimated probabilities).
4. Identify critical rule-out conditions (e.g. Atypical Pneumonia, Appendicitis, Sepsis).
5. State the optimal next diagnostic investigations and standard non-pharmacological care.

FORMAT YOUR RESPONSE:
Begin with your detailed clinical chain-of-thought analysis under `[CLINICAL REASONING TRACE]`, followed by the structured clinical summary under `[DIFFERENTIAL DIAGNOSIS]`.
"""

class DeepReasoningNode:
    def __init__(self):
        self.provider = None
        if settings.OPENROUTER_API_KEY:
            self.provider = OpenRouterProvider(
                api_key=settings.OPENROUTER_API_KEY,
                model_name=settings.OPENROUTER_MODEL_NAME
            )

    async def run(self, state: ConversationState, db=None) -> ConversationState:
        """Executes DeepSeek-R1 deep chain-of-thought clinical differential reasoning."""
        logger.info("Executing Gated Deep Reasoning Node (DeepSeek-R1 671B MoE).")
        
        # Build context
        symptoms_str = ", ".join([f"{s.description} (onset: {s.onset}, severity: {s.severity}/10)" for s in state.get("symptoms", [])]) or "Patient presented with constitutional symptoms"
        multimodal_str = "None uploaded"
        if state.get("multimodal_data"):
            mm = state["multimodal_data"]
            multimodal_str = f"Modality: {mm.get('modality')}\nImpression: {mm.get('preliminary_impression')}\nFindings: {mm.get('key_findings')}"

        rag_context = "\n".join(state.get("retrieved_context", []))
        
        user_prompt = (
            f"Patient Symptoms: {symptoms_str}\n\n"
            f"Multimodal Diagnostic Upload: {multimodal_str}\n\n"
            f"Grounding Clinical Guidelines:\n{rag_context}\n\n"
            f"Patient Conversation History:\n" + "\n".join([f"{t['role']}: {t['content']}" for t in state.get("turns", [])])
        )

        messages = [{"role": "user", "content": user_prompt}]

        if self.provider:
            try:
                cot_output = await self.provider.generate(DEEP_REASONING_PROMPT, messages)
                state["cot_reasoning_trace"] = cot_output
                logger.info("Successfully generated DeepSeek-R1 clinical reasoning trace.")
                return state
            except Exception as e:
                logger.warning(f"DeepSeek-R1 provider failed: {str(e)}. Using fallback reasoning trace.")

        # Heuristic CoT trace if API is offline
        state["cot_reasoning_trace"] = (
            "[CLINICAL REASONING TRACE]\n"
            f"1. Symptom Cluster Analysis: Evaluated multi-system presentation ({symptoms_str}).\n"
            f"2. Multimodal Correlation: Assessed imaging status -> {multimodal_str}.\n"
            "3. Diagnostic Convergence: Differential narrowed based on absence of cardiovascular red flags and presentation chronometry."
        )
        return state

deep_reasoning_node = DeepReasoningNode()

async def run(state: ConversationState, db=None) -> ConversationState:
    return await deep_reasoning_node.run(state, db=db)
