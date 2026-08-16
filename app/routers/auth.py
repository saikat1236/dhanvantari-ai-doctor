import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.core import Patient

router = APIRouter(prefix="/auth", tags=["auth"])

class ConsentRequest(BaseModel):
    email: EmailStr
    consent_scope: str

class ConsentResponse(BaseModel):
    patient_id: str
    email: str
    consent_given_at: datetime
    message: str

@router.post("/consent", response_model=ConsentResponse)
async def capture_consent(data: ConsentRequest, db: AsyncSession = Depends(get_db)):
    """
    DPDP Act 2023 Compliant Consent Capture.
    Registers a new patient and logs their explicit consent.
    """
    try:
        # Check if patient already exists
        stmt = select(Patient).where(Patient.email == data.email)
        result = await db.execute(stmt)
        patient = result.scalar_one_or_none()
        
        if not patient:
            # Create a new patient
            patient_id = f"PAT-{uuid.uuid4().hex[:8].upper()}"
            patient = Patient(
                id=patient_id,
                email=data.email,
                consent_given_at=datetime.utcnow(),
                consent_scope=data.consent_scope
            )
            db.add(patient)
            await db.commit()
            await db.refresh(patient)
            msg = "Consent captured and new patient profile registered."
        else:
            # Update consent timestamp and scope
            patient.consent_given_at = datetime.utcnow()
            patient.consent_scope = data.consent_scope
            db.add(patient)
            await db.commit()
            await db.refresh(patient)
            msg = "Consent records updated successfully."
            
        return ConsentResponse(
            patient_id=patient.id,
            email=patient.email,
            consent_given_at=patient.consent_given_at,
            message=msg
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process consent: {str(e)}"
        )
