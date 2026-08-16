from typing import TypedDict, Literal, List, Optional, Dict, Any
from pydantic import BaseModel

class SymptomEntry(BaseModel):
    description: str
    onset: Optional[str] = None
    severity: Optional[int] = None  # 1-10
    organ_system: Optional[str] = None

class DifferentialCandidate(BaseModel):
    condition: str
    icd10: str
    probability: float
    differentiator: str

class SuggestedMedication(BaseModel):
    molecule: str
    strength: str
    standard_dose: str
    frequency: str
    duration: str
    nlem_listed: bool
    schedule_category: str
    contraindication_check: str

class ConversationState(TypedDict):
    session_id: str
    patient_id: str
    turns: List[dict]              # list of {"role": "user"|"assistant", "content": str}
    symptoms: List[SymptomEntry]
    red_flag_detected: bool
    red_flag_reason: Optional[str]
    retrieved_context: List[str]   # RAG chunks used to ground the response
    
    # Multimodal Imaging / Lab Ingestion
    multimodal_data: Optional[Dict[str, Any]]
    
    # Deep Reasoning & Escalation
    requires_deep_reasoning: bool
    cot_reasoning_trace: Optional[str]
    differential_candidates: List[DifferentialCandidate]
    
    # CDS & Prescriptions
    draft_prescription_payload: List[SuggestedMedication]
    
    triage_level: Optional[Literal["self_care", "see_doctor_soon", "urgent", "emergency"]]
    escalated_to_rmp: bool
    draft_response: Optional[str]
    speech_response: Optional[str]
    language: Optional[str]
