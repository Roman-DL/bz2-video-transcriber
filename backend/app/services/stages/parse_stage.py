"""
Parse stage for video filename parsing.

Extracts metadata from video filename: date, event type, stream, title, speaker.
"""

import subprocess
from pathlib import Path

from app.config import Settings
from app.models.schemas import ProcessingStatus, VideoMetadata
from app.services.parser import FilenameParseError, parse_filename
from app.services.stages.base import BaseStage, StageContext, StageError


def get_video_duration(video_path: Path) -> float | None:
    """Get video duration using ffprobe.

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds, or None if ffprobe fails
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception:
        pass
    return None


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

        # Get video duration
        metadata.duration_seconds = get_video_duration(video_path)
        if metadata.duration_seconds is None:
            # Fallback: estimate from file size (~5MB per minute)
            metadata.duration_seconds = video_path.stat().st_size / 83333

        return metadata

    def estimate_time(self, input_size: int) -> float:
        """Estimate execution time.

        Parsing is nearly instant, but ffprobe may take a second.
        """
        return 1.0
