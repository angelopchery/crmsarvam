"""
Event and EventMedia models for meeting/call tracking.
"""
import datetime as dt

from sqlalchemy import String, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Event(Base):
    """
    Event model for tracking meetings, calls, and interactions.

    Attributes:
        id: Primary key
        client_id: Foreign key to clients table
        title: Event title/subject
        type: Event type (meeting, call, etc.)
        datetime: Scheduled event date and time
        notes: Additional notes about the event
        created_by: User ID who created the event
        created_at: Record creation timestamp
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="meeting", nullable=False)
    datetime: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    created_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow, nullable=False)

    # Relationships
    client: Mapped["Client"] = relationship(back_populates="events")
    created_by_user: Mapped["User"] = relationship(back_populates="events_created")
    media: Mapped[list["EventMedia"]] = relationship(
        back_populates="event", lazy="selectin", cascade="all, delete-orphan"
    )
    transcriptions: Mapped[list["Transcription"]] = relationship(
        back_populates="event", lazy="selectin", cascade="all, delete-orphan"
    )
    follow_ups: Mapped[list["FollowUp"]] = relationship(
        back_populates="event", lazy="selectin", cascade="all, delete-orphan"
    )
    deadlines: Mapped[list["Deadline"]] = relationship(
        back_populates="event", lazy="selectin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Event(id={self.id}, title='{self.title}', type='{self.type}')>"


class EventMedia(Base):
    """
    EventMedia model for storing uploaded media files.

    Attributes:
        id: Primary key
        event_id: Foreign key to events table
        file_path: Local file system path
        file_type: Media type (audio, video, document)
        uploaded_at: Upload timestamp
    """

    __tablename__ = "event_media"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    file_size: Mapped[int] = mapped_column(nullable=False)  # in bytes
    uploaded_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow, nullable=False)

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="media")

    def __repr__(self) -> str:
        return f"<EventMedia(id={self.id}, file_type='{self.file_type}', event_id={self.event_id})>"
