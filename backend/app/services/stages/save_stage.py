"""
Save stage for persisting all processing results to archive.

Saves transcripts, chunks, longread, summary, and audio to the archive directory.
"""

from pathlib import Path

from app.config import Settings
from app.models.schemas import (
    CleanedTranscript,
    Longread,
    ProcessingStatus,
    RawTranscript,
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
        - longread: Longread
        - summarize: Summary

    Output:
        List of created file names

    Example:
        stage = SaveStage(settings)
        files = await stage.execute(context)
    """

    name = "save"
    depends_on = ["parse", "transcribe", "clean", "chunk", "longread", "summarize"]
    status = ProcessingStatus.SAVING

    def __init__(self, settings: Settings):
        """Initialize save stage.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.saver = FileSaver(settings)

    async def execute(self, context: StageContext) -> list[str]:
        """Save all results to archive.

        Args:
            context: Context with all previous stage results

        Returns:
            List of created file names

        Raises:
            StageError: If saving fails
        """
        self.validate_context(context)

        metadata: VideoMetadata = context.get_result("parse")
        raw_transcript, audio_path = context.get_result("transcribe")
        cleaned: CleanedTranscript = context.get_result("clean")
        chunks, _, _ = context.get_result("chunk")
        longread: Longread = context.get_result("longread")
        summary: Summary = context.get_result("summarize")

        try:
            return await self.saver.save(
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
