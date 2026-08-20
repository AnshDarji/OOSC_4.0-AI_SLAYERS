from pydantic import BaseModel
from typing import List, Optional, Literal
from pydantic import Field
from datetime import datetime
from app.models.chat import FeatureType, MessageRole

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    created_at: datetime
    is_helpful: Optional[str] = None
    feedback_category: Optional[str] = None

    class Config:
        from_attributes = True

class FeedbackRequest(BaseModel):
    is_helpful: Literal["yes", "no"]
    category: Optional[str] = Field(default=None, max_length=50)

    class Config:
        from_attributes = True

class DocumentSummaryResponse(BaseModel):
    filename: str
    pages: int
    summary: Optional[str] = None

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    feature_type: FeatureType
    document_id: Optional[str] = None
    document: Optional[DocumentSummaryResponse] = None
    is_pinned: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ConversationRenameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)

class ConversationPinRequest(BaseModel):
    is_pinned: bool

class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]

class MessageListResponse(BaseModel):
    messages: List[MessageResponse]
