from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class MessageCreate(BaseModel):
    receiver_id: UUID
    content: str

class MessageResponse(BaseModel):
    id: UUID
    sender_id: UUID
    receiver_id: UUID
    content: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class ConversationSummary(BaseModel):
    partner_id: UUID
    partner_name: str
    partner_role: str
    last_message: str
    last_message_at: datetime
    unread_count: int
