import logging
from app.orchestrator.state import ConversationState
from app.safety.escalation import escalate_conversation
from app.rag.retriever import MedicalRetriever

logger = logging.getLogger(__name__)
retriever = MedicalRetriever()

async def run(state: ConversationState, db=None) -> ConversationState:
    """
    Triage Router Node: Determines the triage urgency level and escalates 
    non-self-care cases to the RMP review queue.
    """
    # 1. Determine triage level if not already locked (e.g. by emergency safety check)
    if not state.get("triage_level"):
        triage_level = "self_care"
        
        # Check symptom severity first
        max_severity = 0
        symptoms_list = state.get("symptoms", [])
        for s in symptoms_list:
            if s.severity and s.severity > max_severity:
                max_severity = s.severity
                
        if max_severity >= 8:
            triage_level = "urgent"
        elif max_severity >= 5:
            triage_level = "see_doctor_soon"
        else:
            # Check retrieved guidelines to see if they recommend higher triage levels
            # We can parse context contents
            context_text = "".join(state.get("retrieved_context", [])).lower()
            if "emergency" in context_text or "myocardial infarction" in context_text:
                triage_level = "urgent"
            elif "see_doctor_soon" in context_text or "genteritis" in context_text or "stomach pain" in context_text:
                triage_level = "see_doctor_soon"
                
        state["triage_level"] = triage_level

    # 2. Perform RMP escalation if level is higher than self_care
    current_triage = state.get("triage_level")
    if current_triage in ["see_doctor_soon", "urgent", "emergency"]:
        # Assemble symptoms summary
        symptoms = state.get("symptoms", [])
        if symptoms:
            sym_strings = []
            for s in symptoms:
                onset_str = f" (Onset: {s.onset})" if s.onset else ""
                sev_str = f" (Severity: {s.severity}/10)" if s.severity else ""
                sym_strings.append(f"{s.description}{onset_str}{sev_str}")
            symptoms_summary = ", ".join(sym_strings)
        else:
            symptoms_summary = "Not structured yet"

        # Escalate to RMP if DB session is present
        if db is not None:
            conversation_id = state.get("session_id")
            try:
                await escalate_conversation(
                    db=db,
                    conversation_id=conversation_id,
                    symptoms_summary=symptoms_summary,
                    triage_level=current_triage
                )
                state["escalated_to_rmp"] = True
                logger.info(f"Successfully escalated conversation {conversation_id} to RMP review queue.")
            except Exception as e:
                logger.error(f"Failed to escalate conversation {conversation_id}: {str(e)}")
        else:
            logger.warning("No DB session provided. Escalation skipped.")
            
    return state
