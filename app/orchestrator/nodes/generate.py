import json
import logging
import re
from app.llm.router import LLMRouter
from app.orchestrator.state import ConversationState

logger = logging.getLogger(__name__)
llm_router = LLMRouter()

SYSTEM_PROMPT_TEMPLATE = """You are Dr. Dhanvantari, a senior Clinical Physician and expert AI medical consultant.
Your goal is to consult with patients empathetically, evaluate symptoms thoroughly, formulate comprehensive grounded diagnoses based on medical science and NLEM guidelines, and deliver full, informative clinical guidance.

Clinical & Regulatory Guidelines:
1. Ground all recommendations in standard medical science and India NLEM 2022 guidelines.
2. If multimodal imaging (CXR) or lab report data is present, directly integrate the radiological observations into your clinical advice.
3. Keep the tone empathetic, reassuring, authoritative, warm, and highly professional.
4. In India, under the Telemedicine Practice Guidelines 2020, all prescriptions are drafts until verified and digitally signed by an RMP doctor.
5. Strictly adhere to the DPDP Act 2023 by protecting personal health information.
6. HINDI / HINGLISH: If the patient writes or speaks in Hindi or Hinglish, output your clinical guidance in natural Romanized Hinglish (e.g., "Aapko do din se tez bukhar aur khansi hai. Yeh viral ya seasonal sankraman ka sanket ho sakta hai. Aapko aaraam karna chahiye aur paracetamol le sakte hain.").

CRITICAL FORMAT REQUIREMENT:
You MUST respond with a valid JSON object ONLY containing two comprehensive fields:
{{
  "display_text": "Detailed clinical triage advice formatted with clean Markdown headings, findings, differential causes, precautions, NLEM medicine guidance, and follow-up advice.",
  "speech_text": "The FULL, complete, spoken clinical consultation matching the exact same informative depth as display_text, written in natural spoken paragraphs without markdown symbols (*, #, _, -). Speaks like a caring physician directly talking to the patient."
}}
Both display_text and speech_text MUST contain the FULL, rich clinical information so the patient hears every medical detail and recommendation out loud.
Do NOT output anything before or after the JSON.

Clinical Context & Grounding Guidelines:
---
{context}
---
"""

def extract_clean_responses(raw_text: str):
    """Robustly extracts display_text and speech_text from raw LLM output, ensuring full clinical depth."""
    if not raw_text:
        return "Triage analysis completed.", "Triage analysis completed."

    text = raw_text.strip()
    
    # Strip markdown codeblocks
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    # Try standard JSON parsing
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            disp = data.get("display_text") or data.get("reply") or ""
            sp = data.get("speech_text") or data.get("speech_reply") or ""
            if disp and not sp:
                sp = convert_markdown_to_speech(disp)
            elif sp and not disp:
                disp = sp
            if disp or sp:
                return disp, sp
    except Exception:
        pass

    # Try regex JSON extraction
    json_match = re.search(r'\{[\s\S]*"display_text"[\s\S]*"speech_text"[\s\S]*\}', text)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            disp = data.get("display_text", text)
            sp = data.get("speech_text", convert_markdown_to_speech(disp))
            return disp, sp
        except Exception:
            pass

    # Regex extraction of individual keys
    disp_match = re.search(r'"display_text"\s*:\s*"((?:\\.|[^"\\])*)"', text, re.DOTALL)
    speech_match = re.search(r'"speech_text"\s*:\s*"((?:\\.|[^"\\])*)"', text, re.DOTALL)

    if disp_match or speech_match:
        disp = disp_match.group(1).encode().decode('unicode_escape') if disp_match else ""
        sp = speech_match.group(1).encode().decode('unicode_escape') if speech_match else ""
        if disp and not sp:
            sp = convert_markdown_to_speech(disp)
        if disp or sp:
            return disp or sp, sp or disp

    # Clean raw text from JSON artifacts
    clean = re.sub(r'\{?\s*"(?:display_text|speech_text|clinical_advice)"\s*:\s*', '', text)
    clean = re.sub(r'["\}]\s*$', '', clean)
    clean = clean.strip()
    
    return clean, convert_markdown_to_speech(clean)

def convert_markdown_to_speech(md_text: str) -> str:
    """Converts structured markdown into natural, fluent spoken text preserving all clinical guidance."""
    if not md_text:
        return ""
    # Remove headers but keep title text
    text = re.sub(r'#+\s*', '', md_text)
    # Remove bold, italics, code marks
    text = re.sub(r'[*_`~]', '', text)
    # Remove bullet dashes and replace with smooth pauses
    text = re.sub(r'^\s*[-*•]\s*', '. ', text, flags=re.MULTILINE)
    # Remove excessive newlines
    text = re.sub(r'\n+', ' ', text)
    # Clean multiple spaces
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()

async def run(state: ConversationState, db=None) -> ConversationState:
    """Generate Node: Assembles system prompt, formats context, and calls LLMRouter to generate full clinical response."""
    if state.get("red_flag_detected"):
        logger.info("Red flag detected earlier. Skipping LLM generation.")
        state["speech_response"] = convert_markdown_to_speech(state["draft_response"])
        return state

    context_parts = []
    
    if state.get("retrieved_context"):
        context_parts.append("\n".join(state["retrieved_context"]))
        
    if state.get("multimodal_data"):
        mm = state["multimodal_data"]
        context_parts.append(
            f"--- MULTIMODAL DIAGNOSTIC REPORT ---\n"
            f"Modality: {mm.get('modality')}\n"
            f"Key Observations: {mm.get('key_findings')}\n"
            f"Preliminary Impression: {mm.get('preliminary_impression')}\n"
            f"Urgency: {mm.get('clinical_urgency')}"
        )

    if state.get("cot_reasoning_trace"):
        context_parts.append(
            f"--- DEEP CLINICAL REASONING TRACE (DeepSeek-R1) ---\n"
            f"{state['cot_reasoning_trace']}"
        )

    context_str = "\n\n".join(context_parts) if context_parts else "Standard safe clinical triage guidelines."
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context_str)
    messages = state.get("turns", [])
    
    try:
        response = await llm_router.generate(system_prompt, messages)
        disp_text, speech_text = extract_clean_responses(response)
        state["draft_response"] = disp_text
        state["speech_response"] = speech_text
    except Exception as e:
        logger.error(f"Error in LLM Generation node: {str(e)}")
        fallback_msg = (
            "I apologize, but I am experiencing temporary difficulty generating a response. "
            "Please rest, drink plenty of fluids, and consult a doctor if your symptoms do not improve."
        )
        state["draft_response"] = fallback_msg
        state["speech_response"] = fallback_msg
        
    return state
