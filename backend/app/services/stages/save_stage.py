"""
Save stage for persisting all processing results to archive.

Saves transcripts, chunks, longread/story, summary, and audio to the archive directory.
v0.23+: Supports conditional saving based on content_type.
"""

from pathlib import Path

from app.config import Settings
from app.models.schemas import (
    CleanedTranscript,
    ContentType,
    Longread,
    ProcessingStatus,
    RawTranscript,
    SaveResult,
    Story,
    Summary,
    TranscriptChunks,
    VideoMetadata,
)
from app.services.saver import FileSaver
from app.services.stages.base import BaseStage, StageContext, StageError


class SaveStage(BaseStage):
    """Save all processing results to archive.

    Input (from context):
        - parse: VideoMetadata
        - transcribe: Tuple of (RawTranscript, audio_path)
        - clean: CleanedTranscript
        - chunk: Tuple of (TranscriptChunks, outline, text_parts)

        For EDUCATIONAL content:
        - longread: Longread
        - summarize: Summary

        For LEADERSHIP content:
        - story: Story

    Output:
        List of created file names

    Example:
        stage = SaveStage(settings)
        files = await stage.execute(context)
    """

    name = "save"
    # Dependencies include all possible sources - actual required deps checked in execute
    depends_on = ["parse", "transcribe", "clean", "chunk"]
    status = ProcessingStatus.SAVING

    def __init__(self, settings: Settings):
        """Initialize save stage.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.saver = FileSaver(settings)

    async def execute(self, context: StageContext) -> SaveResult:
        """Save all results to archive.

        Args:
            context: Context with all previous stage results

        Returns:
            SaveResult with created files and description metrics

        Raises:
            StageError: If saving fails
        """
        metadata: VideoMetadata = context.get_result("parse")
        raw_transcript, audio_path = context.get_result("transcribe")
        cleaned: CleanedTranscript = context.get_result("clean")
        chunks, _, _ = context.get_result("chunk")

        try:
            if metadata.content_type == ContentType.LEADERSHIP:
                # Leadership: story instead of longread + summary
                story: Story = context.get_result("story")
                return await self.saver.save_leadership(
                    metadata,
                    raw_transcript,
                    cleaned,
                    chunks,
                    story,
                    audio_path,
                )
            else:
                # Educational: longread + summary
                longread: Longread = context.get_result("longread")
                summary: Summary = context.get_result("summarize")
                return await self.saver.save_educational(
                    metadata,
                    raw_transcript,
                    cleaned,
                    chunks,
                    longread,
                    summary,
                    audio_path,
                )
        except Exception as e:
            raise StageError(self.name, f"Save failed: {e}", e)

    def estimate_time(self, input_size: int) -> float:
        """Estimate save time.

        Saving is quick - mostly file I/O.
        """
        return 2.0
