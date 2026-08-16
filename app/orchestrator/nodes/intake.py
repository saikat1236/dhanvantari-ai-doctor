from app.orchestrator.state import ConversationState

async def run(state: ConversationState, db=None) -> ConversationState:
    """Intake node: Initializes session records and default parameters if missing."""
    if "session_id" not in state:
        state["session_id"] = "default_session"
    if "patient_id" not in state:
        state["patient_id"] = "anonymous_patient"
    if "symptoms" not in state:
        state["symptoms"] = []
    if "red_flag_detected" not in state:
        state["red_flag_detected"] = False
    if "red_flag_reason" not in state:
        state["red_flag_reason"] = None
    if "retrieved_context" not in state:
        state["retrieved_context"] = []
    if "triage_level" not in state:
        state["triage_level"] = None
    if "escalated_to_rmp" not in state:
        state["escalated_to_rmp"] = False
    if "draft_response" not in state:
        state["draft_response"] = None
        
    return state
