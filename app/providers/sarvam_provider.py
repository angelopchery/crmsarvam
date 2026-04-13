"""
Sarvam AI provider for speech-to-text transcription.
"""
import logging
import os
from typing import Optional, Dict, Any
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class SarvamAIProvider:
    """Provider for Sarvam AI Saaras v3 transcription API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize SarvamAIProvider.

        Args:
            api_key: Sarvam AI API key (defaults to SARVAMAI_API_KEY env var)

        Raises:
            ValueError: If API key is not provided
        """
        self.api_key = api_key or os.getenv("SARVAMAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Sarvam AI API key not provided. Set SARVAMAI_API_KEY environment variable."
            )

        self.base_url = "https://api.sarvam.ai"
        self.timeout = 300.0  # 5 minutes timeout for long transcriptions

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def transcribe(
        self,
        audio_path: str,
        model: str = "saaras:v3",
        language_code: str = "auto",
        enable_timestamps: bool = False,
    ) -> Dict[str, Any]:
        """
        Transcribe audio file using Sarvam AI Saaras v3 API.

        Args:
            audio_path: Path to the audio file
            model: Model to use (default: saaras:v3)
            language_code: Language code (default: auto for auto-detection)
            enable_timestamps: Whether to include timestamps in output

        Returns:
            Dictionary containing transcription results with keys:
                - transcript_text: Full transcribed text
                - language_code: Detected language code
                - confidence: Confidence score (if available)
                - segments: List of timestamped segments (if enabled)

        Raises:
            FileNotFoundError: If audio file doesn't exist
            httpx.HTTPError: If API request fails
            RuntimeError: If transcription fails
        """
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Starting transcription for {audio_path} using model {model}")

        # Prepare the file for upload
        if not audio_file.is_file():
            raise ValueError(f"Path is not a file: {audio_path}")

        # Determine content type based on file extension
        content_type = self._get_content_type(audio_file.suffix.lower())

        # Prepare request
        url = f"{self.base_url}/speech-to-text/transcribe"
        headers = {
            "api-subscription-key": self.api_key,
        }

        # Prepare form data
        files = {
            "file": (audio_file.name, open(audio_file, "rb"), content_type),
        }
        data = {
            "model": model,
            "mode": "transcribe",
        }

        # Add language code if not auto
        if language_code != "auto":
            data["language_code"] = language_code

        # Add timestamps option
        if enable_timestamps:
            data["enable_timestamps"] = "true"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    files=files,
                    data=data,
                )

            # Close the file
            files["file"][1].close()

            # Check response
            if response.status_code != 200:
                error_msg = f"Transcription API failed with status {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f": {error_detail}"
                except:
                    error_msg += f": {response.text}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            result = response.json()

            # Parse response
            transcript_result = {
                "transcript_text": "",
                "language_code": "",
                "confidence": None,
                "segments": [],
            }

            # Extract transcript text
            if "transcript" in result:
                transcript_result["transcript_text"] = result["transcript"]
            elif "transcription" in result:
                transcript_result["transcript_text"] = result["transcription"]

            # Extract language code
            if "language_code" in result:
                transcript_result["language_code"] = result["language_code"]
            elif "detected_language" in result:
                transcript_result["language_code"] = result["detected_language"]

            # Extract confidence
            if "confidence" in result:
                transcript_result["confidence"] = float(result["confidence"])

            # Extract segments if available
            if "segments" in result:
                transcript_result["segments"] = result["segments"]

            logger.info(f"Transcription completed for {audio_path}")
            logger.debug(f"Transcript length: {len(transcript_result['transcript_text'])} chars")

            return transcript_result

        except httpx.TimeoutException:
            logger.error(f"Transcription timeout for {audio_path}")
            raise RuntimeError("Transcription request timed out")
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during transcription: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during transcription: {e}")
            raise

    def _get_content_type(self, file_extension: str) -> str:
        """
        Get MIME content type for file extension.

        Args:
            file_extension: File extension (with dot)

        Returns:
            MIME content type
        """
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
        """
        Check if the Sarvam AI API is accessible.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            url = f"{self.base_url}/health"
            headers = {
                "api-subscription-key": self.api_key,
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)

            return response.status_code == 200

        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False


# Alternative implementation using sarvamai Python SDK
# Uncomment this if using the official SDK

# try:
#     from sarvamai import SarvamAI
#
#     class SarvamAISDKProvider:
#         """Provider using the official Sarvam AI Python SDK."""
#
#         def __init__(self, api_key: Optional[str] = None):
#             self.api_key = api_key or os.getenv("SARVAMAI_API_KEY")
#             if not self.api_key:
#                 raise ValueError("Sarvam AI API key not provided.")
#
#             self.client = SarvamAI(api_subscription_key=self.api_key)
#
#         async def transcribe(
#             self,
#             audio_path: str,
#             model: str = "saaras:v3",
#             language_code: str = "auto",
#         ) -> Dict[str, Any]:
#             """Transcribe using SDK."""
#             audio_file = Path(audio_path)
#             if not audio_file.exists():
#                 raise FileNotFoundError(f"Audio file not found: {audio_path}")
#
#             logger.info(f"Transcribing {audio_path} using SDK")
#
#             with open(audio_path, "rb") as f:
#                 response = self.client.speech_to_text.transcribe(
#                     file=f,
#                     model=model,
#                     mode="transcribe",
#                 )
#
#             return {
#                 "transcript_text": response.transcript,
#                 "language_code": response.language_code,
#                 "confidence": getattr(response, "confidence", None),
#                 "segments": getattr(response, "segments", []),
#             }
#
# except ImportError:
#     logger.info("sarvamai SDK not available, using HTTP implementation")
