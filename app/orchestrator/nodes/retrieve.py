from app.rag.retriever import MedicalRetriever
from app.orchestrator.state import ConversationState

# Instantiate retriever once
retriever = MedicalRetriever()

async def run(state: ConversationState, db=None) -> ConversationState:
    """Retrieve Node: Searches the medical knowledge base to pull clinical reference guidelines,
    ICD-10 classifications, recommended investigations, and NLEM formulary dosage slots."""
    if not state.get("turns"):
        return state
        
    last_user_turn = next((turn for turn in reversed(state["turns"]) if turn["role"] == "user"), None)
    if not last_user_turn:
        return state
        
    query = last_user_turn["content"]
    
    # Retrieve top 2 documents
    matches = retriever.retrieve(query, limit=2)
    
    # Format matches into rich clinical grounding chunks
    context_chunks = []
    for match in matches:
        diff_text = "\n".join([
            f"  - {d.get('condition')} [Confidence: {d.get('confidence')}]: Key differentiator: {d.get('differentiator')}"
            for d in match.get("differential_candidates", [])
        ]) or "  - Standard clinical evaluation"

        tests_text = "\n".join([f"  - {t}" for t in match.get("recommended_investigations", [])]) or "  - None routinely required"

        formulary_text = "\n".join([
            f"  - {f.get('molecule')}: Standard Dose: {f.get('standard_dose')} | Contraindications: {f.get('contraindications')} | Status: {f.get('telemedicine_status')}"
            for f in match.get("formulary_guidelines", [])
        ]) or "  - Non-pharmacological self-care only"

        chunk = (
            f"--- CLINICAL GUIDELINE: {match['condition']} (ICD-10: {match['icd10']}) ---\n"
            f"Triage Level: {match['triage_level']}\n"
            f"Differential Candidates to Differentiate:\n{diff_text}\n"
            f"Recommended Diagnostic Investigations:\n{tests_text}\n"
            f"NLEM Standard Dosing Slots:\n{formulary_text}\n"
            f"Clinical Protocol:\n{match['action_plan']}"
        )
        context_chunks.append(chunk)
        
    state["retrieved_context"] = context_chunks
    return state
