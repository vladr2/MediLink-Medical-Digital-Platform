from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Any


class ChatMessage(BaseModel):
    role: str  # "user" sau "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[UUID] = None


class ChatResponse(BaseModel):
    conversation_id: UUID
    message: str
    intent: Optional[str] = None
    suggested_doctor: Optional[dict] = None   # {name, specialization, department, user_id}


class ConversationResponse(BaseModel):
    id: UUID
    patient_id: UUID
    messages: List[Any]
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
