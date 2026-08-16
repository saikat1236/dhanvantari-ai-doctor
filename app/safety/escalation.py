import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.core import Conversation, ReviewItem, Message

async def escalate_conversation(
    db: AsyncSession, 
    conversation_id: str, 
    symptoms_summary: str,
    triage_level: str
) -> ReviewItem:
    """
    Escalates a patient conversation to the Registered Medical Practitioner (RMP) queue.
    Updates conversation status and drafts an initial prescription template.
    """
    # 1. Update Conversation status to 'escalated' and set triage level
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()
    
    if conversation:
        conversation.status = "escalated"
        conversation.triage_level = triage_level
        db.add(conversation)

    # 2. Draft an AI-generated prescription template for the RMP to sign
    draft_template = f"""PATIENT CONSULTATION TRIAGE RECORD & PRESCRIPTION DRAFT
===========================================================
Triage Level: {triage_level.upper()}
Extracted Symptoms: {symptoms_summary}

--- THE FOLLOWING SECTION IS TO BE COMPLETED AND APPROVED BY AN RMP ONLY ---

Rx:
1. [Medication Name] - [Dosage, e.g. 500mg] - [Frequency, e.g. Twice Daily] - [Duration, e.g. 5 days]
2. [Medication Name] - [Dosage] - [Frequency] - [Duration]

Clinical Advice & Lifestyle Modifications:
- Maintain complete bed rest and stay hydrated.
- Follow up if symptoms worsen or persist beyond 48 hours.

RMP Electronic Authorization:
Name: Dr. [Name]
Registration No: [Reg No]
Digital Signature: [Signed / Unsigned]
"""

    # 3. Create or update ReviewItem
    review_stmt = select(ReviewItem).where(ReviewItem.conversation_id == conversation_id)
    review_result = await db.execute(review_stmt)
    existing_item = review_result.scalar_one_or_none()
    
    if existing_item:
        existing_item.status = "pending"
        existing_item.draft_prescription = draft_template
        db.add(existing_item)
        return existing_item
    else:
        new_review = ReviewItem(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            status="pending",
            draft_prescription=draft_template
        )
        db.add(new_review)
        return new_review
