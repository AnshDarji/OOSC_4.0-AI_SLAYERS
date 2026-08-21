from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from app.schemas.kanoon import KanoonQueryRequest, KanoonQueryResponse
from app.services.kanoon_service import kanoon_service
from app.middleware.auth import verify_firebase_token
from app.core.rate_limit import limiter

from app.database.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/query", response_model=KanoonQueryResponse)
@limiter.limit("20/minute")
async def ask_kanoon(
    request: Request,
    payload: KanoonQueryRequest,
    background_tasks: BackgroundTasks,
    user_token: dict = Depends(verify_firebase_token),
    db: Session = Depends(get_db)
):
    return kanoon_service.query(payload, user_token.uid, db, background_tasks)

@router.post("/query-stream")
@limiter.limit("20/minute")
async def ask_kanoon_stream(
    request: Request,
    payload: KanoonQueryRequest,
    background_tasks: BackgroundTasks,
    user_token: dict = Depends(verify_firebase_token),
    db: Session = Depends(get_db)
):
    stream_gen = kanoon_service.query_stream(payload, user_token.uid, db, background_tasks)
    return StreamingResponse(stream_gen, media_type="text/event-stream")
