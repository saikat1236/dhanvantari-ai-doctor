import asyncio
import uuid
from datetime import datetime
from app.db.session import engine, Base, AsyncSessionLocal
from app.models.core import Patient, Conversation, Message, ReviewItem

async def seed():
    print("Initializing database and seeding mock data...")
    
    # 1. Drop & Recreate Tables to start fresh
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as session:
        # 2. Seed Patients (DPDP compliant consent)
        p1 = Patient(
            id="PAT-SEED001",
            email="aravind.sharma@example.com",
            consent_given_at=datetime.utcnow(),
            consent_scope="Symptom analysis and triage consulting under India Telemedicine Guidelines 2020 and DPDP Act 2023."
        )
        p2 = Patient(
            id="PAT-SEED002",
            email="riya.sen@example.com",
            consent_given_at=datetime.utcnow(),
            consent_scope="Symptom analysis and triage consulting under India Telemedicine Guidelines 2020 and DPDP Act 2023."
        )
        session.add_all([p1, p2])
        await session.commit()
        
        # 3. Seed Conversation 1 (Mild Cough - Self Care)
        c1_id = "CON-SEED001"
        c1 = Conversation(
            id=c1_id,
            patient_id=p1.id,
            started_at=datetime.utcnow(),
            triage_level="self_care",
            status="active"
        )
        session.add(c1)
        
        m1_user = Message(
            id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
            conversation_id=c1_id,
            role="user",
            content="Hello, I have a mild dry cough and a slight throat irritation. No fever.",
            timestamp=datetime.utcnow()
        )
        m1_assistant = Message(
            id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
            conversation_id=c1_id,
            role="assistant",
            content="Hello! Based on a mild dry cough and slight throat irritation without fever: Triage level is Self-care. We recommend resting, steam inhalation, and warm saline gargles. Please consult a doctor if you develop a fever or breathing difficulty.",
            timestamp=datetime.utcnow()
        )
        session.add_all([m1_user, m1_assistant])
        
        # 4. Seed Conversation 2 (Severe Stomach Ache - Escalated/Pending review)
        c2_id = "CON-SEED002"
        c2 = Conversation(
            id=c2_id,
            patient_id=p2.id,
            started_at=datetime.utcnow(),
            triage_level="see_doctor_soon",
            status="escalated"
        )
        session.add(c2)
        
        m2_user = Message(
            id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
            conversation_id=c2_id,
            role="user",
            content="I am having severe stomach pain in the lower abdomen and I threw up once this morning.",
            timestamp=datetime.utcnow()
        )
        m2_assistant = Message(
            id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
            conversation_id=c2_id,
            role="assistant",
            content="This abdominal pain accompanied by vomiting suggests a see_doctor_soon triage. You are being escalated to the Doctor Review queue for RMP evaluation and prescription drafting. Please rest and stay hydrated.",
            timestamp=datetime.utcnow()
        )
        session.add_all([m2_user, m2_assistant])
        
        # Create Review Item in doctor queue
        r2 = ReviewItem(
            id="REV-SEED002",
            conversation_id=c2_id,
            status="pending",
            created_at=datetime.utcnow(),
            draft_prescription="""PATIENT CONSULTATION TRIAGE RECORD & PRESCRIPTION DRAFT
===========================================================
Triage Level: SEE_DOCTOR_SOON
Extracted Symptoms: severe stomach pain, vomiting (onset: this morning)

--- THE FOLLOWING SECTION IS TO BE COMPLETED AND APPROVED BY AN RMP ONLY ---

Rx:
1. ORS Rehydration Salts - 1 sachet - Dissolve in 1L water, sip throughout day - 2 days
2. Pantoprazole 40mg - 1 tablet - Once daily before breakfast - 3 days

Clinical Advice & Lifestyle Modifications:
- Avoid spicy, solid foods; take light diet (coconut water, rice gruel).
- If severe localized lower right quadrant pain develops, proceed to emergency room.

RMP Electronic Authorization:
Name: Dr. Vikram R. Iyer
Registration No: RMP-MCI-983120
Digital Signature: Dr. Vikram Iyer
"""
        )
        session.add(r2)
        await session.commit()
        
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    asyncio.run(seed())
