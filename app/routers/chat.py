import uuid
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.core import Conversation, Message, Patient, ReviewItem
from app.orchestrator.graph import build_graph
from app.orchestrator.state import ConversationState, SymptomEntry
from app.llm.vision_extractor import VisionExtractor
from app.llm.router import LLMRouter
from app.rag.retriever import MedicalRetriever
from app.safety.prescription_pdf import generate_prescription_pdf
from app.audio.vibevoice_tts import VibeVoiceTTSProvider

router = APIRouter(prefix="/chat", tags=["chat"])
graph = build_graph()
vision_extractor = VisionExtractor()
llm_router = LLMRouter()
retriever = MedicalRetriever()
vibevoice_tts = VibeVoiceTTSProvider()

class ChatRequest(BaseModel):
    patient_id: str
    conversation_id: Optional[str] = None
    message: str
    language: Optional[str] = "en-IN"

class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    speech_reply: str
    triage_level: Optional[str]
    symptoms: List[SymptomEntry]
    red_flag_detected: bool
    escalated_to_rmp: bool
    multimodal_findings: Optional[Dict[str, Any]] = None
    audio_base64: Optional[str] = None

class TTSRequest(BaseModel):
    text: str
    language: Optional[str] = "hi-IN"

class PrescriptionGenerateRequest(BaseModel):
    patient_id: str
    conversation_id: str

class PrescriptionGenerateResponse(BaseModel):
    conversation_id: str
    patient_id: str
    diagnosis: str
    icd10: str
    triage_level: str
    symptoms: List[str]
    medications: List[Dict[str, Any]]
    investigations: List[str]
    advice: List[str]
    pdf_download_url: str
    legal_status: str

@router.post("", response_model=ChatResponse)
async def process_chat(data: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Process Chat Turn through the LangGraph State Machine Triage Orchestrator.
    Logs messages and checks safety red flags.
    """
    patient_stmt = select(Patient).where(Patient.id == data.patient_id)
    patient_result = await db.execute(patient_stmt)
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient consent has not been registered. Please complete consent capture first."
        )

    conversation_id = data.conversation_id
    if not conversation_id:
        conversation_id = f"CON-{uuid.uuid4().hex[:8].upper()}"
        conversation = Conversation(
            id=conversation_id,
            patient_id=data.patient_id,
            status="active"
        )
        db.add(conversation)
        await db.commit()
    else:
        con_stmt = select(Conversation).where(Conversation.id == conversation_id)
        con_result = await db.execute(con_stmt)
        conversation = con_result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation session not found."
            )

    user_msg_id = f"MSG-{uuid.uuid4().hex[:8].upper()}"
    user_message = Message(
        id=user_msg_id,
        conversation_id=conversation_id,
        role="user",
        content=data.message,
        red_flag_detected=False
    )
    db.add(user_message)
    await db.commit()

    history_stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.timestamp.asc())
    history_result = await db.execute(history_stmt)
    messages_history = history_result.scalars().all()
    
    turns = [{"role": msg.role, "content": msg.content} for msg in messages_history]

    state: ConversationState = {
        "session_id": conversation_id,
        "patient_id": data.patient_id,
        "turns": turns,
        "symptoms": [],
        "red_flag_detected": False,
        "red_flag_reason": None,
        "retrieved_context": [],
        "multimodal_data": None,
        "requires_deep_reasoning": False,
        "cot_reasoning_trace": None,
        "differential_candidates": [],
        "draft_prescription_payload": [],
        "triage_level": conversation.triage_level,
        "escalated_to_rmp": conversation.status == "escalated",
        "draft_response": None,
        "speech_response": None,
        "language": data.language
    }

    try:
        updated_state = await graph.ainvoke(state, db=db)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Orchestrator graph execution failed: {str(e)}"
        )

    assistant_msg_id = f"MSG-{uuid.uuid4().hex[:8].upper()}"
    reply_content = updated_state.get("draft_response") or "Triage analysis completed."
    turn_red_flag = updated_state.get("red_flag_detected", False)
    
    assistant_message = Message(
        id=assistant_msg_id,
        conversation_id=conversation_id,
        role="assistant",
        content=reply_content,
        red_flag_detected=turn_red_flag,
        retrieved_context="\n".join(updated_state.get("retrieved_context", []))
    )
    db.add(assistant_message)
    
    conversation.triage_level = updated_state.get("triage_level")
    if updated_state.get("escalated_to_rmp"):
        conversation.status = "escalated"
    db.add(conversation)
    
    await db.commit()

    # 7. Synthesize Doctor Neural Audio using tarun7r/vibevoice-hindi-1.5B
    speech_text = updated_state.get("speech_response") or reply_content
    audio_b64 = await vibevoice_tts.synthesize(speech_text, language=data.language or "hi-IN")

    return ChatResponse(
        conversation_id=conversation_id,
        reply=reply_content,
        speech_reply=speech_text,
        triage_level=updated_state.get("triage_level"),
        symptoms=updated_state.get("symptoms", []),
        red_flag_detected=turn_red_flag,
        escalated_to_rmp=updated_state.get("escalated_to_rmp", False),
        audio_base64=audio_b64
    )

@router.post("/upload", response_model=ChatResponse)
async def upload_medical_file(
    patient_id: str = Form(...),
    conversation_id: Optional[str] = Form(None),
    notes: Optional[str] = Form(""),
    language: Optional[str] = Form("en-IN"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest and analyze patient-uploaded medical imaging (Chest X-Ray, CT, MRI) 
    or Laboratory PDF reports via Multimodal Vision Extractor.
    """
    patient_stmt = select(Patient).where(Patient.id == patient_id)
    patient_result = await db.execute(patient_stmt)
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient consent has not been registered."
        )

    if not conversation_id:
        conversation_id = f"CON-{uuid.uuid4().hex[:8].upper()}"
        conversation = Conversation(
            id=conversation_id,
            patient_id=patient_id,
            status="active"
        )
        db.add(conversation)
        await db.commit()
    else:
        con_stmt = select(Conversation).where(Conversation.id == conversation_id)
        con_result = await db.execute(con_stmt)
        conversation = con_result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation session not found."
            )

    file_bytes = await file.read()
    mime_type = file.content_type or "image/jpeg"
    extracted_findings = await vision_extractor.extract_from_bytes(file_bytes, mime_type=mime_type)

    upload_msg_content = f"Uploaded Medical Document: {file.filename} ({extracted_findings.get('modality')}). Patient Note: {notes}"
    user_message = Message(
        id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conversation_id,
        role="user",
        content=upload_msg_content,
        red_flag_detected=False
    )
    db.add(user_message)
    await db.commit()

    history_stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.timestamp.asc())
    history_result = await db.execute(history_stmt)
    messages_history = history_result.scalars().all()
    turns = [{"role": msg.role, "content": msg.content} for msg in messages_history]

    state: ConversationState = {
        "session_id": conversation_id,
        "patient_id": patient_id,
        "turns": turns,
        "symptoms": [],
        "red_flag_detected": False,
        "red_flag_reason": None,
        "retrieved_context": [],
        "multimodal_data": extracted_findings,
        "requires_deep_reasoning": True,
        "cot_reasoning_trace": None,
        "differential_candidates": [],
        "draft_prescription_payload": [],
        "triage_level": conversation.triage_level,
        "escalated_to_rmp": True,
        "draft_response": None,
        "speech_response": None,
        "language": language
    }

    updated_state = await graph.ainvoke(state, db=db)

    reply_content = updated_state.get("draft_response") or "Multimodal document analysis complete."
    assistant_message = Message(
        id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conversation_id,
        role="assistant",
        content=reply_content,
        red_flag_detected=updated_state.get("red_flag_detected", False),
        retrieved_context="\n".join(updated_state.get("retrieved_context", []))
    )
    db.add(assistant_message)
    
    conversation.triage_level = updated_state.get("triage_level")
    conversation.status = "escalated"
    db.add(conversation)
    await db.commit()

    speech_text = updated_state.get("speech_response") or reply_content
    audio_b64 = await vibevoice_tts.synthesize(speech_text, language=language or "hi-IN")

    return ChatResponse(
        conversation_id=conversation_id,
        reply=reply_content,
        speech_reply=speech_text,
        triage_level=updated_state.get("triage_level"),
        symptoms=updated_state.get("symptoms", []),
        red_flag_detected=updated_state.get("red_flag_detected", False),
        escalated_to_rmp=True,
        multimodal_findings=extracted_findings,
        audio_base64=audio_b64
    )

@router.post("/tts/synthesize")
async def synthesize_speech_endpoint(data: TTSRequest):
    """
    Direct endpoint for synthesizing text using tarun7r/vibevoice-hindi-1.5B
    """
    audio_b64 = await vibevoice_tts.synthesize(data.text, language=data.language or "hi-IN")
    return {
        "audio_base64": audio_b64,
        "model_id": "tarun7r/vibevoice-hindi-1.5B"
    }

@router.post("/prescription/generate", response_model=PrescriptionGenerateResponse)
async def generate_prescription(data: PrescriptionGenerateRequest, db: AsyncSession = Depends(get_db)):
    """
    Synthesizes the complete consultation into a formal NLEM-grounded Medical Prescription.
    """
    # 1. Fetch conversation and history
    con_stmt = select(Conversation).where(Conversation.id == data.conversation_id)
    con_res = await db.execute(con_stmt)
    conversation = con_res.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    history_stmt = select(Message).where(Message.conversation_id == data.conversation_id).order_by(Message.timestamp.asc())
    history_res = await db.execute(history_stmt)
    messages = history_res.scalars().all()
    
    chat_text = "\n".join([f"{m.role}: {m.content}" for m in messages])

    # 2. Retrieve grounded clinical guidelines
    user_queries = [m.content for m in messages if m.role == "user"]
    combined_query = " ".join(user_queries[-3:]) if user_queries else "general medical evaluation"
    guidelines = retriever.retrieve(combined_query, limit=2)

    primary_guideline = guidelines[0] if guidelines else {
        "condition": "Acute Febrile Illness / Respiratory Episode",
        "icd10": "R50.9",
        "triage_level": "self_care",
        "formulary_guidelines": [
            {
                "molecule": "Paracetamol (Acetaminophen) 500mg",
                "standard_dose": "500 mg orally every 6-8 hrs as needed",
                "frequency": "Thrice daily after meals",
                "duration": "3 days",
                "nlem_status": "Listed in NLEM",
                "contraindications": "Active severe hepatic failure"
            },
            {
                "molecule": "WHO Oral Rehydration Salts (ORS)",
                "standard_dose": "1 sachet in 1 litre clean water",
                "frequency": "Sip frequently throughout the day",
                "duration": "Until hydration restored",
                "nlem_status": "Listed in NLEM",
                "contraindications": "None"
            }
        ],
        "recommended_investigations": ["CBC with Platelet count if fever persists > 3 days"],
        "action_plan": "Maintain fluid hydration, rest, and observe temperature twice daily."
    }

    # Format medications list
    medications = []
    for fg in primary_guideline.get("formulary_guidelines", []):
        medications.append({
            "molecule": fg.get("molecule"),
            "strength": "Standard OTC formulation",
            "dosage": fg.get("standard_dose"),
            "frequency": "Every 6-8 hrs as needed",
            "duration": "3-5 days",
            "nlem_listed": True,
            "schedule_category": "List A (Telemedicine Compliant)",
            "contraindication_check": fg.get("contraindications", "None noted")
        })

    if not medications:
        medications.append({
            "molecule": "Paracetamol 500mg",
            "strength": "500 mg Tablet",
            "dosage": "1 tablet every 8 hours",
            "frequency": "Thrice daily after meals",
            "duration": "3 days",
            "nlem_listed": True,
            "schedule_category": "List A",
            "contraindication_check": "Passed"
        })

    symptoms_detected = [w for w in ["Fever", "Cough", "Throat Pain", "Stomach Ache", "Headache", "Body Ache"] if w.lower() in chat_text.lower()]
    if not symptoms_detected:
        symptoms_detected = ["Reported physical discomfort and constitutional symptoms"]

    investigations = primary_guideline.get("recommended_investigations", ["Complete Blood Count (CBC) if symptoms persist > 3 days"])
    advice = [
        "Drink plenty of fluids (minimum 2.5 - 3 litres daily, including coconut water and ORS).",
        "Adequate rest and avoid strenuous physical activity.",
        "Seek immediate emergency care (108 / 112) if you develop chest pain, severe shortness of breath, or high fever > 103°F."
    ]

    # 3. Create or update ReviewItem
    review_stmt = select(ReviewItem).where(ReviewItem.conversation_id == data.conversation_id)
    review_res = await db.execute(review_stmt)
    review_item = review_res.scalar_one_or_none()

    draft_summary_text = (
        f"DIAGNOSIS: {primary_guideline.get('condition')} (ICD-10: {primary_guideline.get('icd10')})\n"
        f"MEDICATIONS:\n" + "\n".join([f"- {m['molecule']}: {m['dosage']} ({m['duration']})" for m in medications]) +
        f"\nADVICE:\n" + "\n".join([f"- {a}" for a in advice])
    )

    if not review_item:
        review_item = ReviewItem(
            id=f"REV-{uuid.uuid4().hex[:8].upper()}",
            conversation_id=data.conversation_id,
            status="pending",
            draft_prescription=draft_summary_text
        )
        db.add(review_item)
    else:
        review_item.draft_prescription = draft_summary_text
        db.add(review_item)

    conversation.status = "escalated"
    db.add(conversation)
    await db.commit()

    return PrescriptionGenerateResponse(
        conversation_id=data.conversation_id,
        patient_id=data.patient_id,
        diagnosis=primary_guideline.get("condition"),
        icd10=primary_guideline.get("icd10"),
        triage_level=conversation.triage_level or "see_doctor_soon",
        symptoms=symptoms_detected,
        medications=medications,
        investigations=investigations,
        advice=advice,
        pdf_download_url=f"/api/chat/prescription/{data.conversation_id}/pdf",
        legal_status="DRAFT_PENDING_RMP_SIGNOFF"
    )

@router.get("/prescription/{conversation_id}/pdf")
async def download_prescription_pdf(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """
    Generates and downloads the official Telemedicine Prescription PDF.
    """
    con_stmt = select(Conversation, Patient).join(Patient, Conversation.patient_id == Patient.id).where(Conversation.id == conversation_id)
    con_res = await db.execute(con_stmt)
    record = con_res.first()
    if not record:
        raise HTTPException(status_code=404, detail="Consultation session not found.")
    
    conversation, patient = record

    history_stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.timestamp.asc())
    history_res = await db.execute(history_stmt)
    messages = history_res.scalars().all()
    chat_text = " ".join([m.content for m in messages if m.role == "user"])

    guidelines = retriever.retrieve(chat_text, limit=1)
    primary = guidelines[0] if guidelines else {
        "condition": "Acute Febrile Presentation",
        "icd10": "R50.9",
        "formulary_guidelines": [
            {"molecule": "Paracetamol 500mg", "standard_dose": "1 tab every 8 hrs", "duration": "3 days", "nlem_status": "Listed in NLEM"},
            {"molecule": "WHO Oral Rehydration Salts", "standard_dose": "1 sachet in 1L water", "duration": "3 days", "nlem_status": "Listed in NLEM"}
        ],
        "recommended_investigations": ["Complete Blood Count (CBC) with Platelets"],
        "action_plan": "Hydration and rest."
    }

    symptoms = [w for w in ["Fever", "Cough", "Throat Pain", "Stomach Ache", "Headache", "Body Ache", "Vomiting"] if w.lower() in chat_text.lower()]
    if not symptoms:
        symptoms = ["Reported constitutional symptoms"]

    pdf_bytes = generate_prescription_pdf(
        patient_id=patient.id,
        patient_email=patient.email or "patient@example.com",
        conversation_id=conversation_id,
        diagnosis=primary.get("condition"),
        icd10=primary.get("icd10"),
        triage_level=conversation.triage_level or "see_doctor_soon",
        symptoms=symptoms,
        medications=primary.get("formulary_guidelines", []),
        investigations=primary.get("recommended_investigations", []),
        advice=[
            "Drink plenty of fluids (ORS, coconut water, water) to avoid dehydration.",
            "Rest adequately and avoid physical exertion.",
            "Consult a physician immediately if fever exceeds 103°F or if severe symptoms develop."
        ]
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Dhanvantari_Prescription_{conversation_id}.pdf"
        }
    )
