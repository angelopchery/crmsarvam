"""
Media processing service for handling audio/video file operations.
"""
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class MediaProcessor:
    """Service for processing media files (audio extraction, conversion, etc.)."""

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        """
        Initialize MediaProcessor.

        Args:
            ffmpeg_path: Path to ffmpeg executable (default: 'ffmpeg' assumes in PATH)
        """
        self.ffmpeg_path = ffmpeg_path

    def get_file_type(self, filename: str) -> Optional[str]:
        """
        Determine the media type from file extension.

        Args:
            filename: Filename to check

        Returns:
            Media type ('audio', 'video', 'document', or None)
        """
        ext = Path(filename).suffix.lower()

        audio_extensions = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".wma"}
        video_extensions = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".wmv", ".flv"}
        document_extensions = {".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx"}

        if ext in audio_extensions:
            return "audio"
        elif ext in video_extensions:
            return "video"
        elif ext in document_extensions:
            return "document"
        else:
            return None

    def extract_audio_from_video(
        self,
        video_path: str,
        output_audio_path: Optional[str] = None,
        audio_format: str = "wav",
    ) -> str:
        """
        Extract audio from video file using ffmpeg.

        Args:
            video_path: Path to the video file
            output_audio_path: Optional output path for audio file
            audio_format: Audio format (default: wav)

        Returns:
            Path to the extracted audio file

        Raises:
            subprocess.SubprocessError: If ffmpeg extraction fails
            FileNotFoundError: If video file doesn't exist
        """
        video_file = Path(video_path)
        if not video_file.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Generate output path if not provided
        if output_audio_path is None:
            output_audio_path = str(video_file.with_suffix(f".{audio_format}"))

        logger.info(f"Extracting audio from {video_path} to {output_audio_path}")

        # Build ffmpeg command
        cmd = [
            self.ffmpeg_path,
            "-i", str(video_path),
            "-vn",  # No video
            "-acodec", "pcm_s16le",  # PCM 16-bit little-endian
            "-ar", "16000",  # 16kHz sample rate (common for ASR)
            "-ac", "1",  # Mono audio
            "-y",  # Overwrite output file if exists
            str(output_audio_path),
        ]

        try:
            # Run ffmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300,  # 5 minute timeout
            )

            # Verify output file was created
            if not Path(output_audio_path).exists():
                raise RuntimeError("Audio extraction failed - no output file created")

            logger.info(f"Audio extracted successfully: {output_audio_path}")
            return output_audio_path

        except subprocess.TimeoutExpired:
            logger.error(f"Audio extraction timed out for {video_path}")
            raise RuntimeError("Audio extraction timed out")
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg failed: {e.stderr}")
            raise RuntimeError(f"Audio extraction failed: {e.stderr}")

    def get_audio_duration(self, audio_path: str) -> float:
        """
        Get the duration of an audio file in seconds using ffprobe.

        Args:
            audio_path: Path to the audio file

        Returns:
            Duration in seconds

        Raises:
            RuntimeError: If ffprobe fails
            FileNotFoundError: If audio file doesn't exist
        """
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Build ffprobe command
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )

            duration = float(result.stdout.strip())
            logger.info(f"Audio duration: {duration:.2f} seconds")
            return duration

        except subprocess.CalledProcessError as e:
            logger.error(f"ffprobe failed: {e.stderr}")
            raise RuntimeError(f"Failed to get audio duration: {e.stderr}")

    def validate_audio_file(self, audio_path: str) -> Tuple[bool, str]:
        """
        Validate an audio file is usable for transcription.

        Args:
            audio_path: Path to the audio file

        Returns:
            Tuple of (is_valid, error_message)
        """
        audio_file = Path(audio_path)

        if not audio_file.exists():
            return False, f"File not found: {audio_path}"

        # Check file size
        file_size = audio_file.stat().st_size
        if file_size == 0:
            return False, "File is empty"

        # Try to get duration
        try:
            duration = self.get_audio_duration(audio_path)
            if duration < 0.1:
                return False, f"Audio too short: {duration:.2f} seconds"

            if duration > 3600:  # 1 hour max
                return False, f"Audio too long: {duration:.2f} seconds (max 1 hour)"

        except Exception as e:
            return False, f"Failed to validate audio: {str(e)}"

        return True, ""

    def convert_audio_format(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        target_format: str = "wav",
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> str:
        """
        Convert audio to a specific format and sample rate.

        Args:
            input_path: Path to input audio file
            output_path: Optional output path
            target_format: Target audio format (default: wav)
            sample_rate: Target sample rate (default: 16000)
            channels: Number of audio channels (default: 1 for mono)

        Returns:
            Path to the converted audio file

        Raises:
            RuntimeError: If conversion fails
        """
        input_file = Path(input_path)
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Generate output path if not provided
        if output_path is None:
            output_path = str(input_file.with_suffix(f".{target_format}"))

        logger.info(f"Converting {input_path} to {output_path}")

        # Build ffmpeg command
        cmd = [
            self.ffmpeg_path,
            "-i", str(input_path),
            "-acodec", "pcm_s16le",  # PCM 16-bit little-endian
            "-ar", str(sample_rate),
            "-ac", str(channels),
            "-y",
            str(output_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300,
            )

            if not Path(output_path).exists():
                raise RuntimeError("Audio conversion failed - no output file created")

            logger.info(f"Audio converted successfully: {output_path}")
            return output_path

        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg conversion failed: {e.stderr}")
            raise RuntimeError(f"Audio conversion failed: {e.stderr}")

    def cleanup_temp_files(self, file_path: str) -> None:
        """
        Clean up temporary files.

        Args:
            file_path: Path to the file to delete
        """
        try:
            file = Path(file_path)
            if file.exists():
                file.unlink()
                logger.info(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {file_path}: {e}")
