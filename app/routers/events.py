"""
Event management router for CRUD operations with file uploads.
"""
import logging
import os
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.routers.auth import get_current_user
from app.schemas.event import (
    EventCreate,
    EventUpdate,
    EventResponse,
    EventWithDetails,
    EventListResponse,
    EventMediaResponse,
)
from app.schemas.user import UserResponse
from app.services.event_service import EventService, EventMediaService
from app.providers.media_processor import MediaProcessor
from app.workers.transcription_worker import process_transcription

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])


# ============ Event Routes ============

@router.get("", response_model=EventListResponse)
async def get_events(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Number of records to return")] = 100,
    client_id: Annotated[int | None, Query(description="Filter by client ID")] = None,
    event_type: Annotated[str | None, Query(description="Filter by event type")] = None,
):
    """
    Get paginated list of events.

    Requires: Any authenticated user
    """
    event_service = EventService(db)
    return await event_service.get_events(
        skip=skip,
        limit=limit,
        client_id=client_id,
        event_type=event_type,
    )


@router.get("/{event_id}", response_model=EventWithDetails)
async def get_event(
    event_id: int,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific event with all related data (media, transcriptions, follow-ups, deadlines).

    Requires: Any authenticated user
    """
    event_service = EventService(db)
    event = await event_service.get_event_with_details(event_id)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    return event


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new event.

    Requires: Any authenticated user
    """
    event_service = EventService(db)

    try:
        event = await event_service.create_event(event_data, created_by=current_user.id)
        return event
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    event_data: EventUpdate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update an existing event.

    Requires: Any authenticated user
    """
    event_service = EventService(db)

    try:
        event = await event_service.update_event(event_id, event_data)
        return event
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete an event.

    Requires: Any authenticated user
    Note: This will cascade delete all related media, transcriptions, follow-ups, etc.
    """
    event_service = EventService(db)
    deleted = await event_service.delete_event(event_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )


# ============ Event Media Routes ============

@router.get("/{event_id}/media", response_model=list[EventMediaResponse])
async def get_event_media(
    event_id: int,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get all media files for an event.

    Requires: Any authenticated user
    """
    media_service = EventMediaService(db, upload_dir=settings.UPLOAD_DIR)
    media_list = await media_service.get_media_by_event(event_id)
    return media_list


@router.post("/{event_id}/media", response_model=EventMediaResponse, status_code=status.HTTP_201_CREATED)
async def upload_event_media(
    event_id: int,
    file: Annotated[UploadFile, File(description="Media file to upload")],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Upload a media file for an event.

    Supports: Audio (mp3, wav, m4a, ogg, flac), Video (mp4, avi, mov, mkv, webm), Documents (pdf, doc, docx, txt)

    For audio and video files, automatically triggers transcription processing.

    Requires: Any authenticated user
    """
    # Verify file extension is allowed
    media_processor = MediaProcessor()
    file_type = media_processor.get_file_type(file.filename)

    if file_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: {settings.allowed_extensions}",
        )

    # Check file size
    file_size = 0
    content = await file.read()
    file_size = len(content)

    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB",
        )

    # Generate unique filename
    file_ext = Path(file.filename).suffix.lower()
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = Path(settings.UPLOAD_DIR) / unique_filename

    # Save file
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"File saved: {file_path}")
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file",
        )

    # Create media record
    media_service = EventMediaService(db, upload_dir=settings.UPLOAD_DIR)

    try:
        media = await media_service.upload_media(
            event_id=event_id,
            file_path=str(file_path),
            file_type=file_type,
            original_filename=file.filename,
            file_size=file_size,
        )

        # Trigger transcription for audio/video files
        if file_type in ("audio", "video"):
            logger.info(f"Scheduling transcription for media_id={media.id}")
            process_transcription.delay(media.id)

        return media

    except ValueError as e:
        # Clean up file if media record creation failed
        try:
            file_path.unlink()
        except:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/media/{media_id}", response_model=EventMediaResponse)
async def get_media(
    media_id: int,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific media file by ID.

    Requires: Any authenticated user
    """
    media_service = EventMediaService(db, upload_dir=settings.UPLOAD_DIR)
    media = await media_service.get_media(media_id)

    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found",
        )

    return media


@router.delete("/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    media_id: int,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a media file.

    Requires: Any authenticated user
    """
    media_service = EventMediaService(db, upload_dir=settings.UPLOAD_DIR)
    deleted = await media_service.delete_media(media_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found",
        )


@router.get("/media/{media_id}/download")
async def download_media(
    media_id: int,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Download a media file.

    Requires: Any authenticated user
    """
    from fastapi.responses import FileResponse

    media_service = EventMediaService(db, upload_dir=settings.UPLOAD_DIR)
    media = await media_service.get_media(media_id)

    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found",
        )

    file_path = Path(media.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk",
        )

    return FileResponse(
        path=str(file_path),
        filename=media.original_filename,
        media_type="application/octet-stream",
    )
