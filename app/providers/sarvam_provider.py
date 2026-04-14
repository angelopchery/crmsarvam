"""
Sarvam AI provider for speech-to-text transcription.

Endpoint: POST https://api.sarvam.ai/speech-to-text
Auth:     header `api-subscription-key`
Body:     multipart/form-data with `file` + `model` + `mode`
"""
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


SARVAM_BASE_URL = "https://api.sarvam.ai"
SARVAM_TRANSCRIBE_PATH = "/speech-to-text"


class SarvamAIProvider:
    """Provider for Sarvam AI Saaras speech-to-text API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SARVAMAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Sarvam AI API key not provided. Set SARVAMAI_API_KEY environment variable."
            )
        self.base_url = SARVAM_BASE_URL
        self.timeout = 300.0

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def transcribe(
        self,
        audio_path: str,
        model: str = "saaras:v3",
        language_code: str = "auto",
        enable_timestamps: bool = False,
    ) -> Dict[str, Any]:
        """
        Transcribe audio via POST /speech-to-text (multipart).

        Returns:
            {
                "transcript_text": str,
                "language_code": str,
                "confidence": float | None,
                "segments": list,
            }
        """
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        if not audio_file.is_file():
            raise ValueError(f"Path is not a file: {audio_path}")

        url = f"{self.base_url}{SARVAM_TRANSCRIBE_PATH}"
        headers = {"api-subscription-key": self.api_key}
        data = {"model": model, "mode": "transcribe"}
        if language_code and language_code != "auto":
            data["language_code"] = language_code
        if enable_timestamps:
            data["with_timestamps"] = "true"

        content_type = self._get_content_type(audio_file.suffix.lower())

        logger.info(f"Sending file to Sarvam: {audio_path}")

        with open(audio_file, "rb") as fh:
            files = {"file": (audio_file.name, fh, content_type)}
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, headers=headers, files=files, data=data)
            except httpx.TimeoutException as e:
                logger.error(f"Sarvam request timed out for {audio_path}: {e}")
                raise RuntimeError("Sarvam API request timed out") from e
            except httpx.HTTPError as e:
                logger.error(f"Sarvam HTTP error for {audio_path}: {e}")
                raise

        if response.status_code != 200:
            logger.error(
                "Sarvam API failed status=%s body=%s",
                response.status_code,
                response.text,
            )
            raise RuntimeError(
                f"Sarvam API failed: {response.status_code} {response.text}"
            )

        try:
            result = response.json()
        except ValueError as e:
            logger.error(f"Sarvam returned non-JSON body: {response.text!r}")
            raise RuntimeError("Sarvam API returned a non-JSON response") from e

        transcript_text = result.get("transcript") or result.get("transcription") or ""
        language = result.get("language_code") or result.get("detected_language") or ""
        confidence = result.get("language_probability")
        if confidence is None:
            confidence = result.get("confidence")
        if confidence is not None:
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                confidence = None
        segments = result.get("segments") or []

        preview = (transcript_text or "")[:100]
        logger.info(f"Transcription successful: {preview}")

        return {
            "transcript_text": transcript_text,
            "language_code": language,
            "confidence": confidence,
            "segments": segments,
        }

    def _get_content_type(self, file_extension: str) -> str:
        content_types = {
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".m4a": "audio/mp4",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
            ".aac": "audio/aac",
            ".wma": "audio/x-ms-wma",
        }
        return content_types.get(file_extension, "audio/wav")

    async def health_check(self) -> bool:
        """Best-effort reachability probe."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/", headers={"api-subscription-key": self.api_key}
                )
            return response.status_code < 500
        except Exception as e:
            logger.warning(f"Sarvam health check failed: {e}")
            return False
