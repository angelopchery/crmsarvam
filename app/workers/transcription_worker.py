"""
Background worker for processing media transcriptions.
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.workers.celery_app import celery_app
from app.core.config import settings
from app.providers.media_processor import MediaProcessor
from app.providers.sarvam_provider import SarvamAIProvider
from app.providers.intelligence_extractor import (
    IntelligenceExtractor,
    ExtractedFollowUp,
    ExtractedDeadline,
)
from app.models import (
    EventMedia,
    Transcription,
    Event,
    FollowUp,
    Deadline,
    Task,
)
from app.core.database import Base

logger = logging.getLogger(__name__)

# Create async engine for workers
worker_engine = create_async_engine(settings.DATABASE_URL, echo=False)
worker_session_maker = sessionmaker(
    worker_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_worker_db() -> AsyncSession:
    """Get database session for worker tasks."""
    async with worker_session_maker() as session:
        yield session


@celery_app.task(
    name="app.workers.transcription_worker.process_transcription",
    bind=True,
    max_retries=3,
)
def process_transcription(self, media_id: int) -> dict:
    """
    Process transcription for uploaded media.

    This task:
    1. Retrieves the media record from database
    2. Extracts audio if it's a video file
    3. Sends audio to Sarvam AI for transcription
    4. Stores the transcription
    5. Extracts and stores follow-ups and deadlines

    Args:
        media_id: ID of the EventMedia record

    Returns:
        Dictionary with processing results
    """
    logger.info(f"Starting transcription processing for media_id={media_id}")

    # Import asyncio and run async function
    import asyncio

    return asyncio.run(_process_transcription_async(self, media_id))


async def _process_transcription_async(task, media_id: int) -> dict:
    """Async implementation of transcription processing."""
    result = {
        "media_id": media_id,
        "status": "processing",
        "transcription_id": None,
        "follow_ups_count": 0,
        "deadlines_count": 0,
        "error": None,
    }

    async with worker_session_maker() as db:
        try:
            # 1. Get media record
            media = await db.get(EventMedia, media_id)
            if not media:
                result["status"] = "failed"
                result["error"] = f"Media not found: {media_id}"
                logger.error(result["error"])
                return result

            logger.info(f"Processing media: {media.file_path}")

            # 2. Initialize processors
            media_processor = MediaProcessor(ffmpeg_path=settings.FFMPEG_PATH)
            sarvam_provider = SarvamAIProvider()
            intelligence_extractor = IntelligenceExtractor()

            # 3. Process audio/video
            audio_path = media.file_path
            file_type = media.file_type

            # Extract audio from video if needed
            if file_type == "video":
                logger.info("Extracting audio from video...")
                audio_path = media_processor.extract_audio_from_video(
                    media.file_path,
                    audio_format="wav"
                )

            # 4. Validate audio file
            is_valid, error_msg = media_processor.validate_audio_file(audio_path)
            if not is_valid:
                result["status"] = "failed"
                result["error"] = f"Invalid audio file: {error_msg}"
                logger.error(result["error"])
                return result

            # 5. Transcribe audio
            logger.info("Starting transcription with Sarvam AI...")
            transcription_result = await sarvam_provider.transcribe(
                audio_path=audio_path,
                model="saaras:v3",
                language_code="auto",
            )

            # 6. Store transcription
            transcription = Transcription(
                event_id=media.event_id,
                transcript_text=transcription_result["transcript_text"],
                language_code=transcription_result["language_code"],
                confidence=transcription_result.get("confidence"),
            )
            db.add(transcription)
            await db.flush()
            await db.refresh(transcription)

            result["transcription_id"] = transcription.id
            logger.info(f"Transcription stored: {transcription.id}")

            # 7. Extract intelligence (follow-ups and deadlines)
            logger.info("Extracting intelligence from transcript...")
            follow_ups, deadlines = intelligence_extractor.extract_from_transcript(
                transcription_result["transcript_text"]
            )

            # 8. Store follow-ups
            for fu in follow_ups:
                follow_up = FollowUp(
                    event_id=media.event_id,
                    description=fu.description,
                    date=fu.date,
                )
                db.add(follow_up)

            result["follow_ups_count"] = len(follow_ups)
            logger.info(f"Stored {len(follow_ups)} follow-ups")

            # 9. Store deadlines and create tasks
            for dl in deadlines:
                deadline = Deadline(
                    event_id=media.event_id,
                    description=dl.description,
                    due_date=dl.due_date,
                )
                db.add(deadline)

                # Create a pending task for this deadline
                task = Task(deadline_id=deadline.id, status="pending")
                db.add(task)

            result["deadlines_count"] = len(deadlines)
            logger.info(f"Stored {len(deadlines)} deadlines")

            # Commit all changes
            await db.commit()

            result["status"] = "completed"
            logger.info(f"Transcription processing completed for media_id={media_id}")

            # Cleanup temp audio file if extracted from video
            if file_type == "video" and audio_path != media.file_path:
                media_processor.cleanup_temp_files(audio_path)

        except Exception as e:
            logger.exception(f"Error processing transcription for media_id={media_id}: {e}")
            await db.rollback()

            result["status"] = "failed"
            result["error"] = str(e)

            # Retry if it's a retryable error
            if isinstance(e, (ConnectionError, TimeoutError)):
                try:
                    raise task.retry(countdown=60, max_retries=3)
                except task.MaxRetriesExceededError:
                    logger.error(f"Max retries exceeded for media_id={media_id}")

    return result


@celery_app.task(
    name="app.workers.transcription_worker.retry_failed_transcription",
)
def retry_failed_transcription(media_id: int) -> dict:
    """
    Retry a failed transcription.

    Args:
        media_id: ID of the EventMedia record

    Returns:
        Dictionary with processing results
    """
    logger.info(f"Retrying transcription for media_id={media_id}")

    # Import asyncio and run async function
    import asyncio

    return asyncio.run(_retry_failed_transcription_async(media_id))


async def _retry_failed_transcription_async(media_id: int) -> dict:
    """Async implementation of retry transcription."""
    async with worker_session_maker() as db:
        # Get media record
        media = await db.get(EventMedia, media_id)
        if not media:
            return {"status": "failed", "error": "Media not found"}

        # Check if there's already a successful transcription
        existing_result = await db.execute(
            select(Transcription).where(Transcription.event_id == media.event_id)
        )
        if existing_result.scalar_one_or_none():
            return {"status": "skipped", "error": "Transcription already exists"}

    # Process the transcription
    task = process_transcription.s(media_id)
    return task.apply_async().get()
