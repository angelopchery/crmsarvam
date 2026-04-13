"""
Pydantic schemas for Event and EventMedia models.
"""
from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field, ConfigDict


class EventBase(BaseModel):
    """Base schema for Event."""

    title: str = Field(..., min_length=1, max_length=300)
    type: Literal["meeting", "call", "email", "other"] = "meeting"
    notes: Optional[str] = None


class EventCreate(EventBase):
    """Schema for creating a new event."""

    client_id: int
    datetime: datetime


class EventUpdate(BaseModel):
    """Schema for updating an event."""

    title: Optional[str] = Field(None, min_length=1, max_length=300)
    type: Optional[Literal["meeting", "call", "email", "other"]] = None
    datetime: Optional[datetime] = None
    notes: Optional[str] = None


class EventResponse(EventBase):
    """Schema for event response."""

    id: int
    client_id: int
    datetime: datetime
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventMediaBase(BaseModel):
    """Base schema for EventMedia."""

    file_type: Literal["audio", "video", "document"]


class EventMediaResponse(EventMediaBase):
    """Schema for event media response."""

    id: int
    event_id: int
    file_path: str
    original_filename: str
    file_size: int
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TranscriptionResponse(BaseModel):
    """Schema for transcription response."""

    id: int
    event_id: int
    transcript_text: str
    language_code: str
    confidence: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FollowUpResponse(BaseModel):
    """Schema for follow-up response."""

    id: int
    event_id: int
    description: str
    date: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeadlineResponse(BaseModel):
    """Schema for deadline response."""

    id: int
    event_id: int
    description: str
    due_date: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventWithDetails(EventResponse):
    """Schema for event response with all related data."""

    client_name: Optional[str] = None
    created_by_username: Optional[str] = None
    media: list[EventMediaResponse] = []
    transcriptions: list[TranscriptionResponse] = []
    follow_ups: list[FollowUpResponse] = []
    deadlines: list[DeadlineResponse] = []


class EventListResponse(BaseModel):
    """Schema for paginated event list response."""

    events: list[EventResponse]
    total: int
    page: int
    page_size: int
