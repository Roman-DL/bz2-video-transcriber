"""
Pydantic models for the video transcription pipeline.
"""

import datetime as dt
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
    LONGREAD = "longread"
    SUMMARIZING = "summarizing"
    STORY = "story"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"


class ContentType(str, Enum):
    """Type of content for processing pipeline.

    Determines output documents and chunking source:
    - educational: longread.md + summary.md, chunks from longread
    - leadership: story.md (8 blocks), chunks from story
    """
    EDUCATIONAL = "educational"
    LEADERSHIP = "leadership"


class EventCategory(str, Enum):
    """Category of event for archive structure.

    - regular: weekly schools (ПШ) → archive/{year}/ПШ/{MM.DD}/{Title}/
    - offsite: events (выездные) → archive/{year}/Выездные/{Event}/{Title}/
    """
    REGULAR = "regular"
    OFFSITE = "offsite"


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
    content_type: ContentType = ContentType.EDUCATIONAL
    event_category: EventCategory = EventCategory.REGULAR
    event_name: str | None = None  # For offsite events: "Форум TABTeam (Москва)"

    @computed_field
    @property
    def stream_full(self) -> str:
        """Full stream identifier: 'Type.Stream' or just 'Type' if no stream."""
        if self.stream:
            return f"{self.event_type}.{self.stream}"
        return self.event_type

    @computed_field
    @property
    def is_offsite(self) -> bool:
        """True if this is an offsite event (not regular weekly school)."""
        return self.event_category == EventCategory.OFFSITE


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


# ═══════════════════════════════════════════════════════════════════════════
# Longread and Summary Models (two-stage generation)
# ═══════════════════════════════════════════════════════════════════════════


class LongreadSection(BaseModel):
    """Single section of a longread document.

    Each section is a self-contained piece of content for RAG retrieval.
    """

    index: int = Field(..., ge=1, description="Section number (1-based)")
    title: str = Field(..., min_length=1, description="Section title")
    content: str = Field(..., min_length=1, description="Section content in markdown")
    source_chunks: list[int] = Field(
        default_factory=list, description="Indices of source chunks used"
    )
    word_count: int = Field(..., ge=0, description="Word count in content")


# ═══════════════════════════════════════════════════════════════════════════
# Story Models for Leadership Content (v0.23+)
# ═══════════════════════════════════════════════════════════════════════════


class StoryBlock(BaseModel):
    """Single block of a leadership story (1 of 8 blocks).

    Each block represents a thematic section of a leader's story.
    """

    block_number: int = Field(..., ge=1, le=8, description="Block number (1-8)")
    block_name: str = Field(..., description="Block name (e.g., 'Кто они', 'Путь в бизнес')")
    content: str = Field(..., description="Block content in markdown")


class Story(BaseModel):
    """Leadership story document (8 blocks structure).

    A story is a structured analysis of a leader's journey for those
    who didn't attend the event. It follows a fixed 8-block template.

    Blocks:
    1. Кто они — basic info about the leader(s)
    2. Путь в бизнес — how they started
    3. Рост и вызовы — growth timeline, stagnations
    4. Ключ к статусу — breakthrough to current status
    5. Как устроен бизнес — business structure
    6. Принципы и советы — philosophy, rules
    7. Итоги — summary, key metrics
    8. Заметки аналитика — analyst notes for RAG
    """

    video_id: str = Field(..., description="Video identifier")
    names: str = Field(..., description="Leader name(s)")
    current_status: str = Field(default="", description="Current Herbalife status")
    event_name: str = Field(default="", description="Event name")
    date: dt.date = Field(..., description="Event date")

    main_insight: str = Field(default="", description="Main insight (1 sentence)")
    blocks: list[StoryBlock] = Field(default_factory=list, description="8 content blocks")

    # Journey metadata
    time_in_business: str = Field(default="", description="Years in business")
    time_to_status: str = Field(default="", description="Years to current status")
    speed: str = Field(
        default="средне",
        description="Speed to status: быстро (<3) | средне (3-7) | долго (7-15) | очень долго (15+)",
    )

    # Business format
    business_format: str = Field(
        default="гибрид", description="Business format: клуб | онлайн | гибрид"
    )

    # Story characteristics
    is_family: bool = Field(default=False, description="Family business")
    had_stagnation: bool = Field(default=False, description="Had stagnation period")
    stagnation_years: int = Field(default=0, description="Years of stagnation")
    had_restart: bool = Field(default=False, description="Had to restart")
    key_pattern: str = Field(default="", description="Key pattern identifier")
    mentor: str = Field(default="", description="Mentor name")

    # Classification
    tags: list[str] = Field(default_factory=list, description="Tags for search")
    access_level: str = Field(
        default="consultant", description="Access level: consultant | leader | personal"
    )
    related: list[str] = Field(default_factory=list, description="Related stories")

    model_name: str = Field(default="", description="LLM model used")

    @computed_field
    @property
    def total_blocks(self) -> int:
        """Total number of filled blocks."""
        return len(self.blocks)

    def to_markdown(self) -> str:
        """Convert story to markdown format with YAML frontmatter.

        Returns:
            Full markdown document.
        """
        lines = [
            "---",
            'type: "leadership-story"',
            f'names: "{self.names}"',
            f'current_status: "{self.current_status}"',
            f'event: "{self.event_name}"',
            f'date: "{self.date.isoformat()}"',
            "",
            f'time_in_business: "{self.time_in_business}"',
            f'time_to_status: "{self.time_to_status}"',
            f"speed: {self.speed}",
            "",
            f"business_format: {self.business_format}",
            "",
            f"is_family: {str(self.is_family).lower()}",
            f"had_stagnation: {str(self.had_stagnation).lower()}",
            f"stagnation_years: {self.stagnation_years}",
            f"had_restart: {str(self.had_restart).lower()}",
            f'key_pattern: "{self.key_pattern}"',
            f'mentor: "{self.mentor}"',
            "",
            f"access_level: {self.access_level}",
            "tags:",
        ]
        for tag in self.tags:
            lines.append(f'  - "{tag}"')
        lines.append("related:")
        for rel in self.related:
            lines.append(f'  - "{rel}"')
        lines.append("---")
        lines.append("")
        lines.append(f"# История {self.current_status}: {self.names}")
        lines.append("")

        if self.main_insight:
            lines.append("> [!abstract] Главный инсайт")
            lines.append("> ")
            lines.append(f"> {self.main_insight}")
            lines.append("")
            lines.append("---")
            lines.append("")

        for block in self.blocks:
            lines.append(f"## {block.block_number}️⃣ {block.block_name}")
            lines.append("")
            lines.append(block.content)
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)


class Longread(BaseModel):
    """Full longread document generated from transcript chunks.

    A longread is an edited version of the transcript for those who
    didn't watch the video. It preserves the speaker's voice and logic.
    """

    video_id: str = Field(..., description="Video identifier")
    title: str = Field(..., description="Video title")
    speaker: str = Field(..., description="Speaker name")
    speaker_status: str = Field(default="", description="Speaker status (v0.23+)")
    date: dt.date = Field(..., description="Video date")
    event_type: str = Field(..., description="Event type code")
    stream: str = Field(default="", description="Stream code")

    introduction: str = Field(default="", description="Introduction text")
    sections: list[LongreadSection] = Field(
        default_factory=list, description="Main content sections"
    )
    conclusion: str = Field(default="", description="Conclusion text")

    # Classification (v0.23+: topic_area replaces section)
    topic_area: list[str] = Field(
        default_factory=list,
        description="Topic areas: продажи | спонсорство | лидерство | мотивация | инструменты | маркетинг-план",
    )
    tags: list[str] = Field(default_factory=list, description="Tags for search")
    access_level: str = Field(
        default="consultant", description="Access level: consultant | leader | personal"
    )

    # Publication metadata (v0.23+)
    publish_gdocs: bool = Field(default=False, description="Publish to Google Docs")
    gdocs_url: str = Field(default="", description="Google Docs URL if published")
    related: list[str] = Field(default_factory=list, description="Related longreads")

    model_name: str = Field(default="", description="LLM model used")

    @computed_field
    @property
    def total_sections(self) -> int:
        """Total number of sections."""
        return len(self.sections)

    @computed_field
    @property
    def total_word_count(self) -> int:
        """Total word count across all sections."""
        intro_words = len(self.introduction.split()) if self.introduction else 0
        section_words = sum(s.word_count for s in self.sections)
        conclusion_words = len(self.conclusion.split()) if self.conclusion else 0
        return intro_words + section_words + conclusion_words

    def to_markdown(self) -> str:
        """Convert longread to markdown format.

        Returns:
            Full markdown document with YAML frontmatter.
        """
        lines = [
            "---",
            'type: "лонгрид"',
            f'video_id: "{self.video_id}"',
            f'title: "{self.title}"',
            f'speaker: "{self.speaker}"',
            f'speaker_status: "{self.speaker_status}"',
            f'event: "{self.event_type}"',
            f'date: "{self.date.isoformat()}"',
            "",
            "topic_area:",
        ]
        for area in self.topic_area:
            lines.append(f"  - {area}")
        lines.append("")
        lines.append(f"access_level: {self.access_level}")
        lines.append(f"publish_gdocs: {str(self.publish_gdocs).lower()}")
        lines.append(f'gdocs_url: "{self.gdocs_url}"')
        lines.append("")
        lines.append("tags:")
        for tag in self.tags:
            lines.append(f'  - "{tag}"')
        lines.append("related:")
        for rel in self.related:
            lines.append(f'  - "{rel}"')
        lines.append("---")
        lines.append("")
        lines.append(f"# {self.title}")
        lines.append("")

        if self.introduction:
            lines.append("## Вступление")
            lines.append("")
            lines.append(self.introduction)
            lines.append("")

        for section in self.sections:
            lines.append(f"## {section.title}")
            lines.append("")
            lines.append(section.content)
            lines.append("")

        if self.conclusion:
            lines.append("## Заключение")
            lines.append("")
            lines.append(self.conclusion)
            lines.append("")

        return "\n".join(lines)


class Summary(BaseModel):
    """Condensed summary (конспект) generated from longread.

    A summary is a navigation document for those who ALREADY watched/read
    the content. It helps recall key points quickly.
    """

    video_id: str = Field(..., description="Video identifier")
    title: str = Field(..., description="Video title")
    speaker: str = Field(..., description="Speaker name")
    date: dt.date = Field(..., description="Video date")

    essence: str = Field(..., description="2-3 paragraphs about the main idea")
    key_concepts: list[str] = Field(
        default_factory=list, description="Key concepts and distinctions"
    )
    practical_tools: list[str] = Field(
        default_factory=list, description="Tools and methods mentioned"
    )
    quotes: list[str] = Field(
        default_factory=list, description="2-4 direct quotes from speaker"
    )
    insight: str = Field(default="", description="Main takeaway (one sentence)")
    actions: list[str] = Field(
        default_factory=list, description="Concrete actions to take"
    )

    # Classification (v0.23+: topic_area replaces section)
    topic_area: list[str] = Field(
        default_factory=list,
        description="Topic areas: продажи | спонсорство | лидерство | мотивация | инструменты | маркетинг-план",
    )
    tags: list[str] = Field(default_factory=list, description="Tags for search")
    access_level: str = Field(
        default="consultant", description="Access level: consultant | leader | personal"
    )
    related: list[str] = Field(default_factory=list, description="Related documents")

    model_name: str = Field(default="", description="LLM model used")

    def to_markdown(self) -> str:
        """Convert summary to markdown format with Obsidian callouts.

        Returns:
            Full markdown document with YAML frontmatter.
        """
        lines = [
            "---",
            'type: "конспект"',
            f'video_id: "{self.video_id}"',
            f'title: "{self.title}"',
            f'speaker: "{self.speaker}"',
            f'date: "{self.date.isoformat()}"',
            "",
            "topic_area:",
        ]
        for area in self.topic_area:
            lines.append(f"  - {area}")
        lines.append("")
        lines.append(f"access_level: {self.access_level}")
        lines.append("")
        lines.append("tags:")
        for tag in self.tags:
            lines.append(f'  - "{tag}"')
        lines.append("related:")
        for rel in self.related:
            lines.append(f'  - "{rel}"')
        # Link to longread
        lines.append(f'  - "[[{self.speaker} — {self.title}]]"')
        lines.append("---")
        lines.append("")
        lines.append(f"# {self.title}")
        lines.append("")

        # Essence
        lines.append("## Суть темы")
        lines.append("")
        lines.append("> [!abstract] Главная идея")
        lines.append("> ")
        for para in self.essence.split("\n\n"):
            lines.append(f"> {para}")
        lines.append("")

        # Key concepts
        if self.key_concepts:
            lines.append("## Ключевые концепции")
            lines.append("")
            lines.append("> [!info] Основные понятия")
            lines.append("> ")
            for concept in self.key_concepts:
                lines.append(f"> - {concept}")
            lines.append("")

        # Practical tools
        if self.practical_tools:
            lines.append("## Инструменты и методы")
            lines.append("")
            for tool in self.practical_tools:
                lines.append(f"> [!tip] {tool.split(':')[0] if ':' in tool else tool}")
                lines.append("> ")
                if ":" in tool:
                    lines.append(f"> {tool.split(':', 1)[1].strip()}")
                lines.append("")

        # Quotes
        if self.quotes:
            lines.append("## Ключевые цитаты")
            lines.append("")
            for quote in self.quotes:
                lines.append("> [!quote]")
                lines.append("> ")
                lines.append(f"> {quote}")
                lines.append("")

        # Insight
        if self.insight:
            lines.append("## Главный инсайт")
            lines.append("")
            lines.append("> [!success] Запомнить")
            lines.append("> ")
            lines.append(f"> {self.insight}")
            lines.append("")

        # Actions
        if self.actions:
            lines.append("## Применение")
            lines.append("")
            lines.append("> [!todo] Что сделать после изучения")
            lines.append("> ")
            for action in self.actions:
                lines.append(f"> - [ ] {action}")
            lines.append("")

        return "\n".join(lines)


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


class StepLongreadRequest(BaseModel):
    """Request for /step/longread endpoint."""

    chunks: TranscriptChunks
    metadata: VideoMetadata
    outline: TranscriptOutline | None = Field(
        default=None,
        description="Transcript outline for context (optional)",
    )
    model: str | None = Field(
        default=None,
        description="Override LLM model for longread generation",
    )


class StepSummarizeRequest(BaseModel):
    """Request for /step/summarize endpoint.

    Updated in v0.24: Now takes CleanedTranscript instead of Longread.
    Summary is generated directly from the cleaned transcript, allowing
    it to see all original details.
    """

    cleaned_transcript: CleanedTranscript
    metadata: VideoMetadata
    model: str | None = Field(
        default=None,
        description="Override LLM model for summary generation",
    )


class StepStoryRequest(BaseModel):
    """Request for /step/story endpoint.

    For content_type=LEADERSHIP only. Generates 8-block story.
    """

    cleaned_transcript: CleanedTranscript
    metadata: VideoMetadata
    model: str | None = Field(
        default=None,
        description="Override LLM model for story generation",
    )


class StepSaveRequest(BaseModel):
    """Request for /step/save endpoint.

    Updated in v0.23: Supports both educational (longread+summary) and leadership (story).
    """

    metadata: VideoMetadata
    raw_transcript: RawTranscript
    cleaned_transcript: CleanedTranscript
    chunks: TranscriptChunks
    # Educational content
    longread: Longread | None = Field(
        default=None,
        description="Longread document (for educational content)",
    )
    summary: Summary | None = Field(
        default=None,
        description="Summary document (for educational content)",
    )
    # Leadership content
    story: Story | None = Field(
        default=None,
        description="Story document (for leadership content)",
    )
    audio_path: str | None = Field(
        default=None,
        description="Path to extracted audio file (from transcribe step)",
    )
