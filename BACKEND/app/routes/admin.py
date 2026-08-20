from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.database import get_db
from app.models.chat import Conversation, Message
from app.core.metrics import global_metrics
from app.core.config import settings
from app.middleware.auth import VerifiedToken, verify_firebase_token

router = APIRouter()

@router.get("/metrics")
def get_operational_metrics(
    db: Session = Depends(get_db),
    token: VerifiedToken = Depends(verify_firebase_token),
):
    if token.uid not in settings.ADMIN_UIDS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access is required.")
    # Fetch active users (unique users who have a conversation)
    active_users = db.query(func.count(func.distinct(Conversation.user_id))).scalar()
    
    # Fetch feedback stats
    total_feedback = db.query(Message).filter(Message.is_helpful != None).count()
    helpful_feedback = db.query(Message).filter(Message.is_helpful == "yes").count()
    
    snapshot = global_metrics.get_snapshot()
    snapshot["active_users"] = active_users
    
    snapshot["feedback"] = {
        "total_responses_rated": total_feedback,
        "helpful_responses": helpful_feedback,
        "approval_rating_percent": (helpful_feedback / total_feedback * 100) if total_feedback > 0 else 0.0
    }
    
    return snapshot
