"""
Pydantic models for the video transcription pipeline.
"""

from datetime import date, datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, computed_field


class ProcessingStatus(str, Enum):
    """Status of a processing job."""
    PENDING = "pending"
    PARSING = "parsing"
    TRANSCRIBING = "transcribing"
    CLEANING = "cleaning"
    CHUNKING = "chunking"
    SUMMARIZING = "summarizing"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoMetadata(BaseModel):
    """Metadata extracted from video filename."""

    date: date
    event_type: str
    stream: str
    title: str
    speaker: str
    original_filename: str
    video_id: str
    source_path: Path
    archive_path: Path

    @computed_field
    @property
    def stream_full(self) -> str:
        """Full stream name (to be resolved from events.yaml)."""
        return f"{self.event_type}.{self.stream}"


class TranscriptSegment(BaseModel):
    """Single segment from Whisper transcription."""

    start: float
    end: float
    text: str

    @computed_field
    @property
    def start_time(self) -> str:
        """Formatted start time (HH:MM:SS)."""
        return self._format_time(self.start)

    @computed_field
    @property
    def end_time(self) -> str:
        """Formatted end time (HH:MM:SS)."""
        return self._format_time(self.end)

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds as HH:MM:SS."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"


class RawTranscript(BaseModel):
    """Raw transcript from Whisper."""

    segments: list[TranscriptSegment]
    language: str
    duration_seconds: float
    whisper_model: str

    @computed_field
    @property
    def full_text(self) -> str:
        """Full text without timestamps."""
        return " ".join(seg.text for seg in self.segments)

    @computed_field
    @property
    def text_with_timestamps(self) -> str:
        """Text with timestamps for LLM processing."""
        lines = [f"[{seg.start_time}] {seg.text}" for seg in self.segments]
        return "\n".join(lines)


class CleanedTranscript(BaseModel):
    """Cleaned transcript after LLM processing."""

    text: str
    original_length: int
    cleaned_length: int
    corrections_made: list[str] = Field(default_factory=list)


class TranscriptChunk(BaseModel):
    """Single semantic chunk of transcript."""

    id: str
    index: int
    topic: str
    text: str
    word_count: int


class TranscriptChunks(BaseModel):
    """Collection of transcript chunks."""

    chunks: list[TranscriptChunk]

    @computed_field
    @property
    def total_chunks(self) -> int:
        """Total number of chunks."""
        return len(self.chunks)

    @computed_field
    @property
    def avg_chunk_size(self) -> int:
        """Average chunk size in words."""
        if not self.chunks:
            return 0
        return sum(c.word_count for c in self.chunks) // len(self.chunks)


class VideoSummary(BaseModel):
    """Video summary for BZ 2.0."""

    summary: str
    key_points: list[str]
    recommendations: list[str]
    target_audience: str
    questions_answered: list[str]
    section: str
    subsection: str
    tags: list[str]
    access_level: int = Field(ge=1, le=4, default=1)


class ProcessingResult(BaseModel):
    """Result of successful video processing."""

    video_id: str
    archive_path: Path
    chunks_count: int
    duration_seconds: float
    files_created: list[str]


class ProcessingJob(BaseModel):
    """Processing job state."""

    job_id: str
    video_path: Path
    status: ProcessingStatus = ProcessingStatus.PENDING
    progress: float = Field(ge=0, le=100, default=0)
    current_stage: str = ""
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
    result: ProcessingResult | None = None


# ═══════════════════════════════════════════════════════════════════════════
# API Request/Response Models
# ═══════════════════════════════════════════════════════════════════════════


class ProcessRequest(BaseModel):
    """Request to start video processing."""

    video_filename: str = Field(
        ...,
        description="Video filename in inbox directory",
        examples=["2025.01.09 ПШ.SV Title (Speaker).mp4"],
    )


class ProgressMessage(BaseModel):
    """WebSocket progress message."""

    status: ProcessingStatus
    progress: float = Field(ge=0, le=100)
    message: str
    timestamp: datetime
    result: ProcessingResult | None = None
    error: str | None = None


class StepParseRequest(BaseModel):
    """Request for /step/parse endpoint."""

    video_filename: str


class StepCleanRequest(BaseModel):
    """Request for /step/clean endpoint."""

    raw_transcript: RawTranscript
    metadata: VideoMetadata


class StepChunkRequest(BaseModel):
    """Request for /step/chunk endpoint."""

    cleaned_transcript: CleanedTranscript
    metadata: VideoMetadata


class StepSummarizeRequest(BaseModel):
    """Request for /step/summarize endpoint."""

    cleaned_transcript: CleanedTranscript
    metadata: VideoMetadata
    prompt_name: str = Field(
        default="summarizer",
        description="Prompt name from config/prompts/",
    )


class StepSaveRequest(BaseModel):
    """Request for /step/save endpoint."""

    metadata: VideoMetadata
    raw_transcript: RawTranscript
    chunks: TranscriptChunks
    summary: VideoSummary
