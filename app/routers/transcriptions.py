"""
Transcription status router — live polling endpoint for the UI.
"""
import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.routers.auth import get_current_user
from app.models.transcription import Transcription
from app.schemas.user import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/transcriptions", tags=["transcriptions"])


class TranscriptionPollResponse(BaseModel):
    status: str
    transcript: str = ""
    language_code: Optional[str] = None
    confidence: Optional[float] = None
    error: Optional[str] = None
    transcription_id: Optional[int] = None


@router.get("/{event_id}", response_model=TranscriptionPollResponse)
async def get_transcription_for_event(
    event_id: int,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Return the latest transcription state for an event (for UI polling)."""
    result = await db.execute(
        select(Transcription)
        .where(Transcription.event_id == event_id)
        .order_by(Transcription.created_at.desc())
        .limit(1)
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        return TranscriptionPollResponse(status="none")

    return TranscriptionPollResponse(
        status=transcription.status,
        transcript=transcription.transcript_text or "",
        language_code=transcription.language_code,
        confidence=transcription.confidence,
        error=transcription.error_message,
        transcription_id=transcription.id,
    )
