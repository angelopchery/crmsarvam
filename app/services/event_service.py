"""
Event management service for CRUD operations.
"""
import logging
import os
from typing import Optional
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.event import Event, EventMedia
from app.models.client import Client
from app.models.user import User
from app.schemas.event import (
    EventCreate,
    EventUpdate,
    EventResponse,
    EventWithDetails,
    EventListResponse,
    EventMediaResponse,
)

logger = logging.getLogger(__name__)


class EventService:
    """Service for handling Event CRUD operations."""

    def __init__(self, db: AsyncSession):
        """
        Initialize EventService with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def get_event(self, event_id: int) -> Optional[EventResponse]:
        """
        Get event by ID.

        Args:
            event_id: Event ID

        Returns:
            Event response or None
        """
        result = await self.db.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()
        return EventResponse.model_validate(event) if event else None

    async def get_event_with_details(self, event_id: int) -> Optional[EventWithDetails]:
        """
        Get event with all related data.

        Args:
            event_id: Event ID

        Returns:
            Event with details response or None
        """
        result = await self.db.execute(
            select(Event)
            .options(
                selectinload(Event.media),
                selectinload(Event.transcriptions),
                selectinload(Event.follow_ups),
                selectinload(Event.deadlines),
                selectinload(Event.client),
                selectinload(Event.created_by_user),
            )
            .where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            return None

        return EventWithDetails(
            id=event.id,
            client_id=event.client_id,
            title=event.title,
            type=event.type,
            datetime=event.datetime,
            notes=event.notes,
            created_by=event.created_by,
            created_at=event.created_at,
            client_name=event.client.name if event.client else None,
            created_by_username=event.created_by_user.username if event.created_by_user else None,
            media=[EventMediaResponse.model_validate(m) for m in event.media],
            transcriptions=[
                {
                    "id": t.id,
                    "event_id": t.event_id,
                    "transcript_text": t.transcript_text,
                    "language_code": t.language_code,
                    "confidence": t.confidence,
                    "created_at": t.created_at,
                }
                for t in event.transcriptions
            ],
            follow_ups=[
                {
                    "id": f.id,
                    "event_id": f.event_id,
                    "description": f.description,
                    "date": f.date,
                    "created_at": f.created_at,
                }
                for f in event.follow_ups
            ],
            deadlines=[
                {
                    "id": d.id,
                    "event_id": d.event_id,
                    "description": d.description,
                    "due_date": d.due_date,
                    "created_at": d.created_at,
                }
                for d in event.deadlines
            ],
        )

    async def get_events(
        self,
        skip: int = 0,
        limit: int = 100,
        client_id: Optional[int] = None,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> EventListResponse:
        """
        Get paginated list of events.

        Args:
            skip: Number of records to skip
            limit: Number of records to return
            client_id: Optional client filter
            event_type: Optional event type filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Paginated event list response
        """
        # Build query
        query = select(Event)

        if client_id:
            query = query.where(Event.client_id == client_id)
        if event_type:
            query = query.where(Event.type == event_type)
        if start_date:
            query = query.where(Event.datetime >= start_date)
        if end_date:
            query = query.where(Event.datetime <= end_date)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Get events with pagination
        query = query.offset(skip).limit(limit).order_by(Event.datetime.desc())
        result = await self.db.execute(query)
        events = result.scalars().all()

        return EventListResponse(
            events=[EventResponse.model_validate(event) for event in events],
            total=total,
            page=skip // limit + 1,
            page_size=limit,
        )

    async def create_event(
        self, event_data: EventCreate, created_by: int
    ) -> EventResponse:
        """
        Create a new event.

        Args:
            event_data: Event creation data
            created_by: User ID creating the event

        Returns:
            Created event response

        Raises:
            ValueError: If client not found
        """
        # Verify client exists
        client_result = await self.db.execute(
            select(Client).where(Client.id == event_data.client_id)
        )
        if not client_result.scalar_one_or_none():
            raise ValueError("Client not found")

        event = Event(
            **event_data.model_dump(exclude={"client_id"}),
            client_id=event_data.client_id,
            created_by=created_by,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)

        logger.info(f"Event created: {event.title}")
        return EventResponse.model_validate(event)

    async def update_event(
        self, event_id: int, event_data: EventUpdate
    ) -> Optional[EventResponse]:
        """
        Update an existing event.

        Args:
            event_id: Event ID
            event_data: Event update data

        Returns:
            Updated event response or None

        Raises:
            ValueError: If event not found
        """
        # Get event
        result = await self.db.execute(select(Event).where(Event.id == event_id))
        event = result.scalar_one_or_none()

        if not event:
            raise ValueError("Event not found")

        # Update fields
        update_data = event_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(event, field, value)

        await self.db.commit()
        await self.db.refresh(event)

        logger.info(f"Event updated: {event.title}")
        return EventResponse.model_validate(event)

    async def delete_event(self, event_id: int) -> bool:
        """
        Delete an event.

        Args:
            event_id: Event ID

        Returns:
            True if deleted, False otherwise
        """
        result = await self.db.execute(delete(Event).where(Event.id == event_id))
        await self.db.commit()
        deleted = result.rowcount > 0

        if deleted:
            logger.info(f"Event deleted: {event_id}")

        return deleted


class EventMediaService:
    """Service for handling EventMedia operations."""

    def __init__(self, db: AsyncSession, upload_dir: str = "uploads"):
        """
        Initialize EventMediaService with database session and upload directory.

        Args:
            db: Async database session
            upload_dir: Directory for storing uploaded files
        """
        self.db = db
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def get_media(self, media_id: int) -> Optional[EventMediaResponse]:
        """
        Get media by ID.

        Args:
            media_id: Media ID

        Returns:
            Event media response or None
        """
        result = await self.db.execute(
            select(EventMedia).where(EventMedia.id == media_id)
        )
        media = result.scalar_one_or_none()
        return EventMediaResponse.model_validate(media) if media else None

    async def get_media_by_event(
        self, event_id: int
    ) -> list[EventMediaResponse]:
        """
        Get all media for an event.

        Args:
            event_id: Event ID

        Returns:
            List of event media responses
        """
        result = await self.db.execute(
            select(EventMedia)
            .where(EventMedia.event_id == event_id)
            .order_by(EventMedia.uploaded_at.desc())
        )
        media = result.scalars().all()
        return [EventMediaResponse.model_validate(m) for m in media]

    async def upload_media(
        self,
        event_id: int,
        file_path: str,
        file_type: str,
        original_filename: str,
        file_size: int,
    ) -> EventMediaResponse:
        """
        Create a media record for an uploaded file.

        Args:
            event_id: Event ID
            file_path: Path to the stored file
            file_type: Type of media (audio, video, document)
            original_filename: Original filename
            file_size: File size in bytes

        Returns:
            Created event media response

        Raises:
            ValueError: If event not found
        """
        # Verify event exists
        event_result = await self.db.execute(
            select(Event).where(Event.id == event_id)
        )
        if not event_result.scalar_one_or_none():
            raise ValueError("Event not found")

        media = EventMedia(
            event_id=event_id,
            file_path=file_path,
            file_type=file_type,
            original_filename=original_filename,
            file_size=file_size,
        )
        self.db.add(media)
        await self.db.commit()
        await self.db.refresh(media)

        logger.info(f"Media uploaded: {original_filename} for event {event_id}")
        return EventMediaResponse.model_validate(media)

    async def delete_media(self, media_id: int) -> bool:
        """
        Delete a media record and its file.

        Args:
            media_id: Media ID

        Returns:
            True if deleted, False otherwise
        """
        # Get media
        result = await self.db.execute(
            select(EventMedia).where(EventMedia.id == media_id)
        )
        media = result.scalar_one_or_none()

        if not media:
            return False

        # Delete file from disk
        try:
            file_path = Path(media.file_path)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"File deleted: {file_path}")
        except Exception as e:
            logger.error(f"Error deleting file {media.file_path}: {e}")

        # Delete from database
        result = await self.db.execute(
            delete(EventMedia).where(EventMedia.id == media_id)
        )
        await self.db.commit()
        deleted = result.rowcount > 0

        if deleted:
            logger.info(f"Media record deleted: {media_id}")

        return deleted
