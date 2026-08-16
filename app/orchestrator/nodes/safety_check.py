from app.safety.red_flags import detect_red_flag
from app.orchestrator.state import ConversationState

EMERGENCY_RESPONSES = {
    "Venomous Bite Emergency": (
        "⚠️ CRITICAL EMERGENCY: This sounds like a venomous bite (e.g., snake bite). "
        "Please dial emergency services (108 or 112 in India, 911 in the US) immediately, or proceed to the nearest emergency room. "
        "\n\nFirst Aid Directions:\n"
        "1. Keep the bitten limb completely immobilized and at or below heart level to slow the spread of venom.\n"
        "2. Do NOT apply a tight tourniquet, do NOT cut the wound, and do NOT try to suck out the venom.\n"
        "3. Remove any tight rings, bracelets, or clothing near the bite area, as swelling may occur.\n"
        "4. Go to a hospital immediately that has Anti-Snake Venom (ASV) available. Do not wait for symptoms to develop."
    ),
    "Suicide Risk": (
        "⚠️ CRITICAL CRISIS ALERT: If you are experiencing thoughts of self-harm or suicide, please know you are not alone. "
        "Contact the national mental health helpline (KIRAN helpline 1800-599-0019 in India, or 988 in the US/Canada) immediately. "
        "Please connect with a trusted person or seek emergency professional care right now."
    ),
    "Cardiovascular Emergency": (
        "⚠️ CRITICAL EMERGENCY: These symptoms indicate potential cardiovascular stress (heart attack symptoms). "
        "Please dial emergency services (108 or 112 in India, 911 in the US) immediately, or visit the nearest emergency room. "
        "Sit comfortably, stay calm, and avoid any physical exertion."
    )
}

DEFAULT_EMERGENCY_RESPONSE = (
    "⚠️ CRITICAL EMERGENCY: This sounds like a potential medical emergency. Please dial emergency services "
    "(108 or 112 in India, 911 in the US) immediately, or visit the nearest emergency room. "
    "I am an AI assistant and am not authorized to triage emergencies. Please seek immediate human medical care."
)

# Hinglish (Romanized Hindi) emergency responses
HINGLISH_EMERGENCY_RESPONSES = {
    "Venomous Bite Emergency": (
        "⚠️ CRITICAL EMERGENCY: Yeh ek venomous bite (jaise saap kaatna) lag raha hai. "
        "Kripya turant emergency services (108 / 112) ko call karein aur hospital jayein.\n\n"
        "First Aid Directions:\n"
        "1. Jis limb pe kaata hai use bilkul mat hilayein aur use heart level se neeche rakhein taaki venom pure body me na faile.\n"
        "2. Wound pe tight tourniquet mat bandhein, aur wound ko cut karne ya venom suck out karne ki koshish bilkul na karein.\n"
        "3. Bite area ke paas se tight rings, bracelets ya kapde nikal dein kyuki wahan sujan (swelling) ho sakti hai.\n"
        "4. Turant aise hospital jayein jahan Anti-Snake Venom (ASV) available ho. Symptoms aane ka wait na karein."
    ),
    "Suicide Risk": (
        "⚠️ CRITICAL CRISIS ALERT: Agar aap self-harm ya suicide ke thoughts face kar rahe hain, toh please national helpline KIRAN (1800-599-0019) ko call karein. "
        "Kripya kisi trusted insaan se baat karein ya turant emergency medical help lein."
    ),
    "Cardiovascular Emergency": (
        "⚠️ CRITICAL EMERGENCY: Yeh symptoms potential heart attack ya cardiovascular stress ke ho sakte hain. "
        "Kripya turant emergency services (108 / 112) ko call karein aur hospital jayein. Aaram se baith jayein aur physical pressure se bachein."
    )
}

HINGLISH_DEFAULT_EMERGENCY_RESPONSE = (
    "⚠️ CRITICAL EMERGENCY: Yeh ek medical emergency ho sakti hai. Kripya turant emergency services "
    "(108 / 112) ko call karein ya nearest emergency room jayein. Main ek AI assistant hoon aur emergency triage ke liye authorized nahi hoon."
)

async def run(state: ConversationState, db=None) -> ConversationState:
    """Safety Check Node: Detours immediately to EMERGENCY state on positive red-flag matches."""
    if not state.get("turns"):
        return state
        
    last_user_turn = next((turn for turn in reversed(state["turns"]) if turn["role"] == "user"), None)
    if not last_user_turn:
        return state
        
    text = last_user_turn["content"]
    is_red_flag, reason = detect_red_flag(text)
    
    if is_red_flag:
        state["red_flag_detected"] = True
        state["red_flag_reason"] = reason
        state["triage_level"] = "emergency"
        
        # Pull specific response based on language selection and reason
        if state.get("language") == "hi-IN":
            emergency_msg = HINGLISH_EMERGENCY_RESPONSES.get(reason, HINGLISH_DEFAULT_EMERGENCY_RESPONSE)
        else:
            emergency_msg = EMERGENCY_RESPONSES.get(reason, DEFAULT_EMERGENCY_RESPONSE)
            
        state["draft_response"] = emergency_msg
        state["speech_response"] = emergency_msg
    else:
        state["red_flag_detected"] = False
        state["red_flag_reason"] = None
        
    return state
