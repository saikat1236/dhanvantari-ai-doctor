import re
from typing import Tuple, Optional

# Strict emergency medical keywords
RED_FLAG_PATTERNS = {
    "cardiovascular_emergency": [
        r"chest\s*pain", r"crushing\s*pain", r"pain\s*radiating\s*to\s*arm", 
        r"heart\s*attack", r"cardiac\s*arrest", r"left\s*arm\s*pain", r"tightness\s*in\s*chest",
        r"chhati\s*me\s*dard", r"dil\s*ka\s*daura", r"chhati\s*me\s*jalan"
    ],
    "respiratory_emergency": [
        r"can't\s*breathe", r"shortness\s*of\s*breath", r"gasping\s*for\s*air", 
        r"difficulty\s*breathing", r"suffocating", r"unable\s*to\s*breathe", r"dyspnea",
        r"saans\s*lene\s*me\s*takleef", r"saans\s*nahi\s*aa\s*rahi", r"saans\s*phool"
    ],
    "neurological_emergency": [
        r"face\s*drooping", r"slurred\s*speech", r"sudden\s*weakness", 
        r"numbness\s*one\s*side", r"stroke\s*symptoms", r"loss\s*of\s*vision", r"paralysis",
        r"bolne\s*me\s*takleef", r"muh\s*terha", r"falij"
    ],
    "severe_bleeding": [
        r"heavy\s*bleeding", r"gushing\s*blood", r"won't\s*stop\s*bleeding", 
        r"arterial\s*bleed", r"uncontrolled\s*bleeding",
        r"khoon\s*beh\s*raha", r"khoon\s*nahi\s*ruk"
    ],
    "suicide_risk": [
        r"want\s*to\s*die", r"end\s*my\s*life", r"suicide", r"kill\s*myself", r"self\s*harm",
        r"jaan\s*de\s*dung", r"marne\s*ka\s*man", r"zindagi\s*khatam"
    ],
    "severe_pediatric_fever": [
        r"baby\s*fever", r"infant\s*fever", r"newborn\s*temperature", 
        r"baby\s*temperature\s*high", r"newborn\s*fever"
    ],
    "toxic_ingestion": [
        r"swallowed\s*poison", r"drank\s*bleach", r"ingested\s*chemical", r"overdose",
        r"zeher", r"acid\s*pee"
    ],
    "venomous_bite_emergency": [
        r"snake\s*bite", r"cobra", r"viper", r"scorpion\s*sting", r"venomous\s*bite", r"dog\s*bite",
        r"saap\s*kaat", r"saap\s*ne\s*kata", r"bichhu\s*ne\s*kata", r"bichhu\s*dank"
    ]
}

def detect_red_flag(text: str) -> Tuple[bool, Optional[str]]:
    """
    Check if the user input contains any emergency medical red flags.
    Returns (is_red_flag, classification_reason)
    """
    if not text:
        return False, None
        
    lowered = text.lower()
    for category, patterns in RED_FLAG_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, lowered):
                # Format category name for readability
                reason = category.replace("_", " ").title()
                return True, reason
                
    return False, None
