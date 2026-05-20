from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User, UserRole
from app.models.patient import Patient
from app.models.ai_conversation import AIConversation
from app.schemas.chat import ChatRequest, ChatResponse, ConversationResponse
from app.services.ai_chat import chat_with_patient, generate_suggested_questions

router = APIRouter(prefix="/chat", tags=["AI chat"])


@router.get("/suggested-questions")
def get_suggested_questions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Feature 10 — Returnează 3 întrebări AI personalizate bazate pe istoricul pacientului."""
    if current_user.role != UserRole.patient:
        return {"questions": [
            "Cum pot vizualiza programările mele?",
            "Cum adaug o recenzie pentru un doctor?",
            "Cum exportez fișa medicală?",
        ]}
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        return {"questions": []}
    questions = generate_suggested_questions(patient.id, db)
    return {"questions": questions}


@router.post("/", response_model=ChatResponse)
def send_message(
    data: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.patient:
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient profile not found")
        patient_id = patient.id
    else:
        raise HTTPException(status_code=403, detail="Only patients can use the chat")

    result = chat_with_patient(
        patient_id=patient_id,
        message=data.message,
        conversation_id=data.conversation_id,
        db=db,
    )
    return result


@router.get("/conversations", response_model=List[ConversationResponse])
def get_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.patient:
        raise HTTPException(
            status_code=403, detail="Only patients can access conversations"
        )

    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        return []

    return (
        db.query(AIConversation)
        .filter(AIConversation.patient_id == patient.id)
        .order_by(AIConversation.created_at.desc())
        .all()
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.patient:
        raise HTTPException(
            status_code=403, detail="Only patients can access conversations"
        )

    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    conversation = (
        db.query(AIConversation)
        .filter(
            AIConversation.id == conversation_id,
            AIConversation.patient_id == patient.id,
        )
        .first()
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation
