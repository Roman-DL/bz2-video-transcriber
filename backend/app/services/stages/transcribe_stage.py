"""
Transcribe stage for video transcription via Whisper.

Extracts audio from video and sends to Whisper API for transcription.
"""

from pathlib import Path

from app.config import Settings
from app.models.schemas import ProcessingStatus, RawTranscript, TranscriptSegment
from app.services.ai_clients import WhisperClient
from app.services.stages.base import BaseStage, StageContext, StageError
from app.services.transcriber import WhisperTranscriber
from app.utils import estimate_duration_from_text, is_transcript_file


class TranscribeStage(BaseStage):
    """Transcribe video via Whisper API.

    Input (from context):
        - parse: VideoMetadata (for duration estimate)
        - video_path in metadata: Path to video file

    Output:
        Tuple of (RawTranscript, audio_path)

    Example:
        stage = TranscribeStage(whisper_client, settings)
        context = context.with_result("parse", metadata)
        raw_transcript, audio_path = await stage.execute(context)
    """

    name = "transcribe"
    depends_on = ["parse"]
    status = ProcessingStatus.TRANSCRIBING

    def __init__(self, whisper_client: WhisperClient, settings: Settings):
        """Initialize transcribe stage.

        Args:
            whisper_client: Whisper client for transcription API calls
            settings: Application settings
        """
        self.whisper_client = whisper_client
        self.settings = settings
        self.transcriber = WhisperTranscriber(whisper_client, settings)

    async def execute(self, context: StageContext) -> tuple[RawTranscript, Path | None]:
        """Transcribe video file or load MD transcript.

        v0.64+: For .md files, loads text directly instead of calling Whisper.

        Args:
            context: Context with parse result and video_path metadata

        Returns:
            Tuple of (RawTranscript, audio_path or None for MD)

        Raises:
            StageError: If transcription fails
        """
        self.validate_context(context)

        video_path = context.get_metadata("video_path")
        if video_path is None:
            raise StageError(self.name, "video_path not found in context metadata")

        video_path = Path(video_path)

        # v0.64+: MD transcript — load text directly
        if is_transcript_file(video_path):
            text = video_path.read_text(encoding="utf-8")
            estimated_duration = estimate_duration_from_text(text)
            transcript = RawTranscript(
                segments=[TranscriptSegment(start=0, end=estimated_duration, text=text)],
                language="ru",
                duration_seconds=estimated_duration,
                whisper_model="macwhisper-large-v2",
                processing_time_sec=0,
            )
            return transcript, None

        try:
            transcript, audio_path = await self.transcriber.transcribe(video_path)
            return transcript, audio_path
        except Exception as e:
            raise StageError(self.name, f"Transcription failed: {e}", e)

    def estimate_time(self, input_size: int) -> float:
        """Estimate transcription time.

        Args:
            input_size: Video duration in seconds

        Returns:
            Estimated time in seconds (roughly 1:1 ratio with video duration)
        """
        # Whisper transcription takes roughly 1x video duration on GPU
        # Add buffer for audio extraction
        return input_size * 1.2 + 5.0
