"""
Background worker for processing media transcriptions.

Task signature: process_transcription(transcription_id, file_path, file_type)
  - transcription_id: the pre-created Transcription row to update
  - file_path: absolute path to the uploaded audio/video file
  - file_type: "audio" or "video" (video triggers ffmpeg audio extraction)
"""
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.workers.celery_app import celery_app
from app.core.config import settings
from app.providers.media_processor import MediaProcessor
from app.providers.sarvam_provider import SarvamAIProvider
from app.providers.intelligence_extractor import IntelligenceExtractor
from app.models import Transcription, FollowUp, Deadline, Task
from app.models.transcription import TranscriptionStatus

logger = logging.getLogger(__name__)

worker_engine = create_async_engine(settings.DATABASE_URL, echo=False)
worker_session_maker = sessionmaker(
    worker_engine, class_=AsyncSession, expire_on_commit=False
)


@celery_app.task(
    name="app.workers.transcription_worker.process_transcription",
    bind=True,
    max_retries=3,
)
def process_transcription(self, transcription_id: int, file_path: str, file_type: str = "audio") -> dict:
    """Process transcription for a pre-created Transcription row."""
    logger.info(f"Starting transcription {transcription_id} (file={file_path}, type={file_type})")
    import asyncio
    return asyncio.run(_process_transcription_async(self, transcription_id, file_path, file_type))


async def _set_status(
    transcription_id: int,
    status: str,
    *,
    error: str | None = None,
    transcript_text: str | None = None,
    language_code: str | None = None,
    confidence: float | None = None,
) -> None:
    """Update a Transcription row in its own session and commit."""
    async with worker_session_maker() as db:
        transcription = await db.get(Transcription, transcription_id)
        if not transcription:
            logger.error(f"Transcription not found: {transcription_id}")
            return
        transcription.status = status
        if error is not None:
            transcription.error_message = error[:2000]
        if status == TranscriptionStatus.COMPLETED.value:
            transcription.error_message = None
        if transcript_text is not None:
            transcription.transcript_text = transcript_text
        if language_code is not None:
            transcription.language_code = language_code
        if confidence is not None:
            transcription.confidence = confidence
        transcription.updated_at = datetime.utcnow()
        await db.commit()


async def _get_event_id(transcription_id: int) -> int | None:
    async with worker_session_maker() as db:
        t = await db.get(Transcription, transcription_id)
        return t.event_id if t else None


async def _persist_intelligence(event_id: int, follow_ups, deadlines) -> tuple[int, int]:
    async with worker_session_maker() as db:
        for fu in follow_ups:
            db.add(FollowUp(event_id=event_id, description=fu.description, date=fu.date))
        for dl in deadlines:
            deadline = Deadline(event_id=event_id, description=dl.description, due_date=dl.due_date)
            db.add(deadline)
            await db.flush()
            db.add(Task(deadline_id=deadline.id, status="pending"))
        await db.commit()
    return len(follow_ups), len(deadlines)


async def _process_transcription_async(task, transcription_id: int, file_path: str, file_type: str) -> dict:
    result = {
        "transcription_id": transcription_id,
        "status": TranscriptionStatus.PROCESSING.value,
        "follow_ups_count": 0,
        "deadlines_count": 0,
        "error": None,
    }

    # Stage 1: mark processing so the UI poll flips immediately.
    await _set_status(transcription_id, TranscriptionStatus.PROCESSING.value)
    logger.info(f"Transcription {transcription_id} → processing")

    event_id = await _get_event_id(transcription_id)
    if event_id is None:
        logger.error(f"Transcription {transcription_id} has no event — aborting")
        await _set_status(transcription_id, TranscriptionStatus.FAILED.value, error="Transcription row missing")
        result["status"] = TranscriptionStatus.FAILED.value
        result["error"] = "Transcription row missing"
        return result

    # Stage 2: actual work (outside any DB session).
    media_processor = MediaProcessor(ffmpeg_path=settings.FFMPEG_PATH)
    sarvam_provider = SarvamAIProvider()
    intelligence_extractor = IntelligenceExtractor()
    audio_path = file_path
    cleanup_audio = False

    try:
        if file_type == "video":
            logger.info(f"Extracting audio from video for transcription {transcription_id}")
            audio_path = media_processor.extract_audio_from_video(file_path, audio_format="wav")
            cleanup_audio = True

        is_valid, error_msg = media_processor.validate_audio_file(audio_path)
        if not is_valid:
            raise ValueError(f"Invalid audio file: {error_msg}")

        logger.info(f"Sending transcription {transcription_id} to Sarvam AI")
        transcription_result = await sarvam_provider.transcribe(
            audio_path=audio_path,
            model="saaras:v3",
            language_code="auto",
        )

        follow_ups, deadlines = intelligence_extractor.extract_from_transcript(
            transcription_result["transcript_text"]
        )
    except Exception as e:
        logger.exception(f"Transcription {transcription_id} failed: {e}")
        await _set_status(transcription_id, TranscriptionStatus.FAILED.value, error=str(e))
        result["status"] = TranscriptionStatus.FAILED.value
        result["error"] = str(e)

        if isinstance(e, (ConnectionError, TimeoutError)):
            try:
                raise task.retry(countdown=60, max_retries=3)
            except task.MaxRetriesExceededError:
                logger.error(f"Max retries exceeded for transcription {transcription_id}")
        return result
    finally:
        if cleanup_audio and audio_path != file_path:
            try:
                media_processor.cleanup_temp_files(audio_path)
            except Exception:
                pass

    # Stage 3: mark completed + store intelligence.
    try:
        await _set_status(
            transcription_id,
            TranscriptionStatus.COMPLETED.value,
            transcript_text=transcription_result["transcript_text"],
            language_code=transcription_result["language_code"],
            confidence=transcription_result.get("confidence"),
        )
        fu_count, dl_count = await _persist_intelligence(event_id, follow_ups, deadlines)
        result["follow_ups_count"] = fu_count
        result["deadlines_count"] = dl_count
        result["status"] = TranscriptionStatus.COMPLETED.value
        logger.info(f"Transcription {transcription_id} completed (fu={fu_count}, dl={dl_count})")
    except Exception as e:
        logger.exception(f"Persisting transcription {transcription_id} failed: {e}")
        await _set_status(transcription_id, TranscriptionStatus.FAILED.value, error=str(e))
        result["status"] = TranscriptionStatus.FAILED.value
        result["error"] = str(e)

    return result


@celery_app.task(name="app.workers.transcription_worker.retry_failed_transcription")
def retry_failed_transcription(transcription_id: int, file_path: str, file_type: str = "audio") -> dict:
    """Retry a failed transcription by id."""
    logger.info(f"Retrying transcription {transcription_id}")
    return process_transcription(transcription_id, file_path, file_type)
