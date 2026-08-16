from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=True)
    consent_given_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=True)
    consent_scope: Mapped[str] = mapped_column(Text, default="Symptom analysis and triage consulting under India Telemedicine Guidelines 2020 and DPDP Act 2023.")

    conversations = relationship("Conversation", back_populates="patient", cascade="all, delete-orphan")

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    triage_level: Mapped[str] = mapped_column(String, nullable=True)  # self_care, see_doctor_soon, urgent, emergency
    status: Mapped[str] = mapped_column(String, default="active")     # active, resolved, escalated

    patient = relationship("Patient", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    review_items = relationship("ReviewItem", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    conversation_id: Mapped[str] = mapped_column(String, ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    red_flag_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    retrieved_context: Mapped[str] = mapped_column(Text, nullable=True)  # JSON/string of RAG chunks

    conversation = relationship("Conversation", back_populates="messages")

class ReviewItem(Base):
    __tablename__ = "review_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    conversation_id: Mapped[str] = mapped_column(String, ForeignKey("conversations.id"), index=True)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending, reviewed, prescribed
    reviewing_rmp_id: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    draft_prescription: Mapped[str] = mapped_column(Text, nullable=True)  # AI-generated draft
    final_prescription: Mapped[str] = mapped_column(Text, nullable=True)  # Doctor-approved final copy
    rmp_signature: Mapped[str] = mapped_column(String, nullable=True)     # "Signed by Dr. X, Registration Num"

    conversation = relationship("Conversation", back_populates="review_items")
