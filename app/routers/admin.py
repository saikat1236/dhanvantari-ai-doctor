from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.core import Conversation, ReviewItem, Message, Patient

router = APIRouter(prefix="/admin", tags=["admin"])

# Pydantic schemas for request/response
class ReviewQueueItem(BaseModel):
    id: str
    conversation_id: str
    patient_id: str
    patient_email: Optional[str]
    triage_level: Optional[str]
    created_at: datetime
    status: str
    draft_prescription: Optional[str]

class MessageItem(BaseModel):
    role: str
    content: str
    timestamp: datetime
    red_flag_detected: bool

class ConversationDetail(BaseModel):
    conversation_id: str
    patient_id: str
    patient_email: Optional[str]
    consent_scope: Optional[str]
    triage_level: Optional[str]
    status: str
    messages: List[MessageItem]

class PrescriptionSubmitRequest(BaseModel):
    review_item_id: str
    rmp_id: str
    prescription_text: str
    signature: str

class PrescriptionSubmitResponse(BaseModel):
    review_item_id: str
    status: str
    final_prescription: str
    rmp_signature: str
    message: str

@router.get("/queue", response_model=List[ReviewQueueItem])
async def get_review_queue(db: AsyncSession = Depends(get_db)):
    """
    Retrieve the queue of conversations escalated for RMP review.
    Displays patient metadata and current triage level.
    """
    stmt = (
        select(ReviewItem, Conversation, Patient)
        .join(Conversation, ReviewItem.conversation_id == Conversation.id)
        .join(Patient, Conversation.patient_id == Patient.id)
        .order_by(ReviewItem.created_at.desc())
    )
    result = await db.execute(stmt)
    records = result.all()
    
    queue = []
    for review_item, conversation, patient in records:
        queue.append(ReviewQueueItem(
            id=review_item.id,
            conversation_id=conversation.id,
            patient_id=patient.id,
            patient_email=patient.email,
            triage_level=conversation.triage_level,
            created_at=review_item.created_at,
            status=review_item.status,
            draft_prescription=review_item.draft_prescription
        ))
    return queue

@router.get("/conversation/{conversation_id}", response_model=ConversationDetail)
async def get_conversation_detail(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve the full chat history and DPDP consent logs for a specific escalated case.
    """
    con_stmt = (
        select(Conversation, Patient)
        .join(Patient, Conversation.patient_id == Patient.id)
        .where(Conversation.id == conversation_id)
    )
    con_result = await db.execute(con_stmt)
    record = con_result.first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
        
    conversation, patient = record
    
    msg_stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.timestamp.asc())
    msg_result = await db.execute(msg_stmt)
    messages = msg_result.scalars().all()
    
    message_items = [
        MessageItem(
            role=m.role,
            content=m.content,
            timestamp=m.timestamp,
            red_flag_detected=m.red_flag_detected
        ) for m in messages
    ]
    
    return ConversationDetail(
        conversation_id=conversation.id,
        patient_id=patient.id,
        patient_email=patient.email,
        consent_scope=patient.consent_scope,
        triage_level=conversation.triage_level,
        status=conversation.status,
        messages=message_items
    )

@router.post("/prescription/submit", response_model=PrescriptionSubmitResponse)
async def submit_prescription(data: PrescriptionSubmitRequest, db: AsyncSession = Depends(get_db)):
    """
    Approve and sign off on a prescription as a Registered Medical Practitioner (RMP).
    Resolves the escalated queue item and updates the consultation status.
    """
    try:
        # Load the review item
        stmt = select(ReviewItem).where(ReviewItem.id == data.review_item_id)
        result = await db.execute(stmt)
        review_item = result.scalar_one_or_none()
        
        if not review_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review queue item not found."
            )
            
        if review_item.status == "prescribed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This case has already been approved and prescribed."
            )

        # Update ReviewItem
        review_item.status = "prescribed"
        review_item.reviewing_rmp_id = data.rmp_id
        review_item.final_prescription = data.prescription_text
        review_item.rmp_signature = data.signature
        db.add(review_item)

        # Update Conversation status to resolved
        con_stmt = select(Conversation).where(Conversation.id == review_item.conversation_id)
        con_result = await db.execute(con_stmt)
        conversation = con_result.scalar_one_or_none()
        
        if conversation:
            conversation.status = "resolved"
            db.add(conversation)

        await db.commit()
        await db.refresh(review_item)

        return PrescriptionSubmitResponse(
            review_item_id=review_item.id,
            status=review_item.status,
            final_prescription=review_item.final_prescription,
            rmp_signature=review_item.rmp_signature,
            message="Prescription signed and issued successfully. Case resolved."
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prescription sign-off failed: {str(e)}"
        )
