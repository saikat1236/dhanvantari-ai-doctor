import re
from typing import List
from app.orchestrator.state import ConversationState, SymptomEntry

# Simple list of known symptoms to extract via regex fallback
COMMON_SYMPTOMS = ["fever", "cough", "chest pain", "stomach pain", "headache", "sore throat", "vomiting", "diarrhea", "breathlessness", "dizziness"]

def parse_symptoms_regex(text: str) -> List[SymptomEntry]:
    """Parse symptoms, onset, and severity from text using regular expressions."""
    extracted = []
    text_lower = text.lower()
    
    # 1. Detect common symptoms
    found_symptoms = []
    for symptom in COMMON_SYMPTOMS:
        if symptom in text_lower:
            found_symptoms.append(symptom)
            
    if not found_symptoms:
        # Generic match for "pain" or "hurt" or generic symptoms
        pain_matches = re.findall(r"(\w+\s+pain|pain\s+in\s+\w+)", text_lower)
        found_symptoms.extend(pain_matches)
        
    # If still nothing, default to the query itself if it's short
    if not found_symptoms and len(text.split()) < 5:
        found_symptoms.append(text_lower)

    # 2. Estimate onset (e.g., "3 days", "since yesterday", "2 hours")
    onset_match = re.search(
        r"(\d+\s*(?:day|hour|week|month)s?|since\s+\w+|yesterday|today)", 
        text_lower
    )
    onset = onset_match.group(1) if onset_match else None

    # 3. Estimate severity (e.g., "7/10", "severity 8", "pain of 5")
    severity = None
    severity_match = re.search(r"(?:pain|severity|scale|rating)\s*(?:is|of)?\s*(\d+)", text_lower)
    if severity_match:
        try:
            val = int(severity_match.group(1))
            if 1 <= val <= 10:
                severity = val
        except ValueError:
            pass
            
    # Check for direct fraction notation like "8/10" or "6 out of 10"
    fraction_match = re.search(r"(\d+)\s*(?:/|out\s*of)\s*10", text_lower)
    if fraction_match:
        try:
            val = int(fraction_match.group(1))
            if 1 <= val <= 10:
                severity = val
        except ValueError:
            pass

    for s in found_symptoms:
        extracted.append(SymptomEntry(description=s, onset=onset, severity=severity))
        
    return extracted

async def run(state: ConversationState, db=None) -> ConversationState:
    """Symptom Collector Node: Extracts structured symptom details from the conversation history."""
    if not state.get("turns"):
        return state
        
    # Focus on the last user turn
    last_user_turn = next((turn for turn in reversed(state["turns"]) if turn["role"] == "user"), None)
    if not last_user_turn:
        return state
        
    text = last_user_turn["content"]
    
    # Extract symptoms using our robust regex parser
    extracted_symptoms = parse_symptoms_regex(text)
    
    # Merge/add to state symptoms list if they are new
    existing_descriptions = {s.description.lower() for s in state["symptoms"]}
    for new_sym in extracted_symptoms:
        if new_sym.description.lower() not in existing_descriptions:
            state["symptoms"].append(new_sym)
            
    return state
