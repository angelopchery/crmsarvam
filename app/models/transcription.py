"""
Transcription model for storing AI-generated transcripts.
"""
import enum
from datetime import datetime

from sqlalchemy import String, Text, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TranscriptionStatus(str, enum.Enum):
    """Transcription processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Transcription(Base):
    """
    Transcription model for storing AI-generated transcripts from media.

    Attributes:
        id: Primary key
        event_id: Foreign key to events table
        transcript_text: Full transcribed text
        language_code: Detected language (e.g., 'en-IN', 'hi-IN')
        confidence: Transcription confidence score (0-1)
        status: Processing status (pending, processing, completed, failed)
        error_message: Error message if transcription failed
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "transcriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False
    )
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    language_code: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=TranscriptionStatus.PENDING.value, nullable=False, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    event: Mapped["Event"] = relationship(back_populates="transcriptions")

    def __repr__(self) -> str:
        return f"<Transcription(id={self.id}, lang='{self.language_code}', event_id={self.event_id}, status='{self.status}')>"
