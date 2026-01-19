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
    duration_seconds: float | None = None  # Video duration from ffprobe

    @computed_field
    @property
    def stream_full(self) -> str:
        """Full stream identifier: 'Type.Stream' or just 'Type' if no stream."""
        if self.stream:
            return f"{self.event_type}.{self.stream}"
        return self.event_type


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
    model_name: str


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
    model_name: str

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


# ═══════════════════════════════════════════════════════════════════════════
# Map-Reduce Models for Large Transcript Processing
# ═══════════════════════════════════════════════════════════════════════════


class TextPart(BaseModel):
    """Part of transcript text with overlap information.

    Used by TextSplitter to split large transcripts into overlapping parts
    for parallel processing while maintaining context at boundaries.
    """

    index: int = Field(..., ge=1, description="Part number (1-based)")
    text: str = Field(..., min_length=1, description="Part content")
    start_char: int = Field(..., ge=0, description="Start position in original text")
    end_char: int = Field(..., ge=0, description="End position in original text")
    has_overlap_before: bool = Field(
        default=False, description="Has overlap with previous part"
    )
    has_overlap_after: bool = Field(
        default=False, description="Has overlap with next part"
    )

    @computed_field
    @property
    def char_count(self) -> int:
        """Number of characters in this part."""
        return len(self.text)

    @computed_field
    @property
    def word_count(self) -> int:
        """Number of words in this part."""
        return len(self.text.split())


class PartOutline(BaseModel):
    """Outline extracted from a single text part.

    Contains structured information about topics and key points
    extracted by LLM from one part of the transcript.
    """

    part_index: int = Field(..., ge=1, description="Part number (1-based)")
    topics: list[str] = Field(
        ...,
        min_length=1,
        max_length=4,
        description="Main topics in this part (2-4)",
    )
    key_points: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Key points from this part (3-5)",
    )
    summary: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Brief summary (1-2 sentences)",
    )


class TranscriptOutline(BaseModel):
    """Combined outline of the entire transcript.

    Created by reducing multiple PartOutlines into a unified structure
    with deduplicated topics. Used as context for chunking.
    """

    parts: list[PartOutline] = Field(
        default_factory=list, description="Outlines from all parts"
    )
    all_topics: list[str] = Field(
        default_factory=list, description="Deduplicated list of all topics"
    )

    @computed_field
    @property
    def total_parts(self) -> int:
        """Total number of parts processed."""
        return len(self.parts)

    def to_context(self) -> str:
        """Format outline as context string for chunking prompt.

        Returns:
            Formatted context for insertion into LLM prompt.
        """
        if not self.parts:
            return ""

        lines = ["## КОНТЕКСТ ВСЕГО ВИДЕО", ""]
        lines.append(f"Транскрипт состоит из {self.total_parts} частей.")
        lines.append("")

        if self.all_topics:
            lines.append("### Основные темы видео:")
            for topic in self.all_topics:
                lines.append(f"- {topic}")
            lines.append("")

        lines.append("### Структура по частям:")
        for part in self.parts:
            lines.append(f"\n**Часть {part.part_index}:**")
            lines.append(f"Темы: {', '.join(part.topics)}")
            lines.append(f"Содержание: {part.summary}")

        return "\n".join(lines)


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
    model_name: str


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
    whisper_model: str | None = Field(
        default=None,
        description="Override Whisper model (for transcribe step)",
    )


class StepCleanRequest(BaseModel):
    """Request for /step/clean endpoint."""

    raw_transcript: RawTranscript
    metadata: VideoMetadata
    model: str | None = Field(
        default=None,
        description="Override LLM model for cleaning",
    )


class StepChunkRequest(BaseModel):
    """Request for /step/chunk endpoint."""

    cleaned_transcript: CleanedTranscript
    metadata: VideoMetadata
    model: str | None = Field(
        default=None,
        description="Override LLM model for chunking",
    )


class StepSummarizeRequest(BaseModel):
    """Request for /step/summarize endpoint."""

    cleaned_transcript: CleanedTranscript
    metadata: VideoMetadata
    prompt_name: str = Field(
        default="summarizer",
        description="Prompt name from config/prompts/",
    )
    model: str | None = Field(
        default=None,
        description="Override LLM model for summarization",
    )


class StepSaveRequest(BaseModel):
    """Request for /step/save endpoint."""

    metadata: VideoMetadata
    raw_transcript: RawTranscript
    cleaned_transcript: CleanedTranscript
    chunks: TranscriptChunks
    summary: VideoSummary
    audio_path: str | None = Field(
        default=None,
        description="Path to extracted audio file (from transcribe step)",
    )
