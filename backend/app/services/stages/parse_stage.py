"""
Parse stage for media filename parsing.

Extracts metadata from media filename: date, event type, stream, title, speaker.
Supports both video and audio files.
"""

from pathlib import Path

from app.config import Settings
from app.models.schemas import ProcessingStatus, VideoMetadata
from app.services.parser import FilenameParseError, parse_filename
from app.services.stages.base import BaseStage, StageContext, StageError
from app.utils import estimate_duration_from_size, get_media_duration


class ParseStage(BaseStage):
    """Parse video filename to extract metadata.

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

        # Get media duration
        metadata.duration_seconds = get_media_duration(video_path)
        if metadata.duration_seconds is None:
            # Fallback: estimate from file size (different rates for audio/video)
            metadata.duration_seconds = estimate_duration_from_size(video_path)

        return metadata

    def estimate_time(self, input_size: int) -> float:
        """Estimate execution time.

        Parsing is nearly instant, but ffprobe may take a second.
        """
        return 1.0
