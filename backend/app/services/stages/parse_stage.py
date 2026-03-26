"""
Parse stage for media filename parsing.

Extracts metadata from media filename: date, event type, stream, title, speaker.
Supports both video and audio files.

v0.84+: MD file enrichment (duration, speaker_info, language) consolidated here.
"""

from pathlib import Path

from app.config import Settings
from app.models.schemas import ProcessingStatus, VideoMetadata
from app.services.parser import FilenameParseError, parse_filename
from app.services.stages.base import BaseStage, StageContext, StageError
from app.utils import (
    detect_language,
    estimate_duration_from_size,
    estimate_duration_from_text,
    get_media_duration,
    is_transcript_file,
)
from app.utils.speaker_utils import parse_speakers


class ParseStage(BaseStage):
    """Parse video filename to extract metadata.

    v0.84+: Consolidates MD file enrichment (duration, speaker_info, language)
    that was previously duplicated in orchestrator.process() and step_routes.py.

    Input (from context.metadata):
        - video_path: Path to video file

    Output:
        VideoMetadata with parsed information

    Example:
        stage = ParseStage(settings)
        context = StageContext().with_metadata("video_path", Path("inbox/video.mp4"))
        metadata = await stage.execute(context)
    """

    name = "parse"
    depends_on: list[str] = []
    status = ProcessingStatus.PARSING

    def __init__(self, settings: Settings):
        """Initialize parse stage.

        Args:
            settings: Application settings
        """
        self.settings = settings

    async def execute(self, context: StageContext) -> VideoMetadata:
        """Parse video filename and extract metadata.

        Args:
            context: Context with video_path in metadata

        Returns:
            VideoMetadata with parsed information

        Raises:
            StageError: If parsing fails
        """
        video_path = context.get_metadata("video_path")
        if video_path is None:
            raise StageError(self.name, "video_path not found in context metadata")

        video_path = Path(video_path)
        if not video_path.exists():
            raise StageError(self.name, f"Video file not found: {video_path}")

        try:
            metadata = parse_filename(video_path.name, video_path)
        except FilenameParseError as e:
            raise StageError(self.name, str(e), e)

        # v0.84+: Enrichment consolidated from orchestrator/step_routes
        if is_transcript_file(video_path):
            text = video_path.read_text(encoding="utf-8")
            metadata.duration_seconds = estimate_duration_from_text(text)
            metadata.speaker_info = parse_speakers(text)
            metadata.language = detect_language(text)
        else:
            metadata.duration_seconds = get_media_duration(video_path)
            if metadata.duration_seconds is None:
                metadata.duration_seconds = estimate_duration_from_size(video_path)

        return metadata

    def estimate_time(self, input_size: int) -> float:
        """Estimate execution time.

        Parsing is nearly instant, but ffprobe may take a second.
        """
        return 1.0
