"""
Transcription model for storing AI-generated transcripts.
"""
from datetime import datetime

from sqlalchemy import String, Text, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Transcription(Base):
    """
    Transcription model for storing AI-generated transcripts from media.

    Attributes:
        id: Primary key
        event_id: Foreign key to events table
        transcript_text: Full transcribed text
        language_code: Detected language (e.g., 'en-IN', 'hi-IN')
        confidence: Transcription confidence score (0-1)
        created_at: Record creation timestamp
    """

    __tablename__ = "transcriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False
    )
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    language_code: Mapped[str] = mapped_column(String(10), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="transcriptions")

    def __repr__(self) -> str:
        return f"<Transcription(id={self.id}, lang='{self.language_code}', event_id={self.event_id})>"
