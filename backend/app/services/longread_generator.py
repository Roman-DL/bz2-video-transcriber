"""
Longread generator service.

Creates longread documents from cleaned transcript.
Auto-selects generation strategy based on model context window:
- Single-pass for large context models (Claude 200K)
- Map-reduce for small context models (Ollama 8-32K)

v0.23+: New prompt architecture (system + instructions + template).
v0.25+: Accepts CleanedTranscript directly (no chunks dependency).
v0.42+: Added tokens_used, cost, and processing_time_sec metrics.
v0.50+: Added slides_text parameter for slides integration.
v0.67+: Single-pass path for large context models, auto-selection.
"""

import asyncio
import logging
import time
from typing import Any

from app.config import Settings, load_prompt, get_model_config, load_model_config
from app.utils.json_utils import extract_and_parse_json
from app.utils import calculate_cost
from app.models.schemas import (
    CleanedTranscript,
    Longread,
    LongreadSection,
    PromptOverrides,
    TextPart,
    TokensUsed,
    TranscriptOutline,
    VideoMetadata,
)
from app.services.ai_clients import BaseAIClient
from app.services.outline_extractor import OutlineExtractor
from app.services.text_splitter import TextSplitter, PART_SIZE, OVERLAP_SIZE, MIN_PART_SIZE

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("app.perf")

# Valid topic_area values for classification
VALID_TOPIC_AREAS = [
    "продажи", "спонсорство", "лидерство",
    "мотивация", "инструменты", "маркетинг-план"
]

# Valid access_level values
VALID_ACCESS_LEVELS = ["consultant", "leader", "personal"]

# Russian month names for date formatting
RUSSIAN_MONTHS = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]

# Default configuration
DEFAULT_PARTS_PER_SECTION = 2  # Text parts per section (was chunks_per_section)
DEFAULT_MAX_PARALLEL_SECTIONS = 2
DEFAULT_LARGE_TEXT_THRESHOLD = 10000  # Extract outline for texts > 10K chars
DEFAULT_CONTEXT_TOKENS = 8192

# Context budget: Russian text ~2.0 tokens/char (calibrated for Claude tokenizer)
TOKENS_PER_CHAR = 2.0
# Reserve for system prompt, instructions, template (~15K tokens)
PROMPT_OVERHEAD_TOKENS = 15_000
# Reserve for output (~20K tokens, SINGLE_PASS_MAX_TOKENS=16K + margin)
OUTPUT_RESERVE_TOKENS = 20_000
# Use 90% of context window (prompt overhead already accounted separately)
CONTEXT_UTILIZATION = 0.90

# Single-pass needs more output tokens than default 4096
# Typical longread: 4000-8000 words ≈ 10K-20K tokens in Russian
SINGLE_PASS_MAX_TOKENS = 16384


class LongreadGenerator:
    """
    Longread generation service with auto-selection of strategy.

    v0.67+: Auto-selects between two generation paths:
    - **Single-pass**: 1 LLM call for models with large context (Claude 200K)
    - **Map-reduce**: Split → Outline → Sections → Frame for small context models

    Selection is automatic based on model's context_tokens vs transcript size.

    Example:
        async with ClaudeClient.from_settings(settings) as client:
            generator = LongreadGenerator(client, settings)
            longread = await generator.generate(cleaned_transcript, metadata)
    """

    def __init__(
        self,
        ai_client: BaseAIClient,
        settings: Settings,
        prompt_overrides: PromptOverrides | None = None,
    ):
        """
        Initialize longread generator.

        Args:
            ai_client: AI client for LLM calls
            settings: Application settings
            prompt_overrides: Optional prompt file overrides (v0.32+)
        """
        self.ai_client = ai_client
        self.settings = settings

        # Load prompt architecture with optional overrides
        overrides = prompt_overrides or PromptOverrides()
        self.system_prompt = load_prompt("longread", overrides.system or "system", settings)
        self.instructions = load_prompt("longread", overrides.instructions or "instructions", settings)
        self.template = load_prompt("longread", overrides.template or "template", settings)

        # Map-reduce components (used only when text doesn't fit in context)
        # Read text_splitter config from model profile (large: min_part_size=20000)
        ts_config = load_model_config(settings.longread_model, "text_splitter", settings)
        self.text_splitter = TextSplitter(
            part_size=ts_config.get("part_size", PART_SIZE),
            overlap_size=ts_config.get("overlap_size", OVERLAP_SIZE),
            min_part_size=ts_config.get("min_part_size", MIN_PART_SIZE),
        )
        self.outline_extractor = OutlineExtractor(ai_client, settings)

        # Token tracking (v0.43+: unified interface)
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._tokens_lock = asyncio.Lock()

        # Get model-specific config (v0.67+: uses longread_model, not summarizer_model)
        model_config = get_model_config(settings.longread_model, settings)
        self.context_tokens = model_config.get("context_tokens", DEFAULT_CONTEXT_TOKENS)

        longread_config = model_config.get("longread", {})
        self.parts_per_section = longread_config.get(
            "parts_per_section",
            longread_config.get("chunks_per_section", DEFAULT_PARTS_PER_SECTION)
        )
        self.max_parallel = longread_config.get(
            "max_parallel_sections", DEFAULT_MAX_PARALLEL_SECTIONS
        )
        self.large_text_threshold = longread_config.get(
            "large_text_threshold", DEFAULT_LARGE_TEXT_THRESHOLD
        )
        self.max_input_chars = longread_config.get("max_input_chars", 0)

        logger.debug(
            f"LongreadGenerator config: context_tokens={self.context_tokens}, "
            f"parts_per_section={self.parts_per_section}, "
            f"max_parallel={self.max_parallel}"
        )

    async def generate(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
        slides_text: str | None = None,
    ) -> Longread:
        """
        Generate longread from cleaned transcript.

        v0.67+: Auto-selects single-pass or map-reduce based on context window.

        Args:
            cleaned_transcript: Cleaned transcript text
            metadata: Video metadata
            slides_text: Optional extracted text from slides (v0.50+)

        Returns:
            Longread with introduction, sections, and conclusion
        """
        start_time = time.time()

        # Reset token counters
        self._total_input_tokens = 0
        self._total_output_tokens = 0

        # Prepare full text with optional slides
        full_text = self._prepare_text(cleaned_transcript.text, slides_text)
        input_chars = len(full_text)

        # Auto-select generation path
        if self._fits_in_context(full_text):
            logger.info(
                f"Single-pass: {input_chars} chars fits in "
                f"{self.context_tokens} context tokens"
            )
            longread = await self._generate_single_pass(full_text, metadata)
        else:
            logger.info(
                f"Map-reduce: {input_chars} chars exceeds context, splitting"
            )
            longread = await self._generate_map_reduce(
                full_text, cleaned_transcript, metadata
            )

        elapsed = time.time() - start_time

        cost_str = f"cost=${longread.cost:.4f} | " if longread.cost else ""
        logger.info(
            f"Longread complete: {longread.total_sections} sections, "
            f"{longread.total_word_count} words, {elapsed:.1f}s"
        )

        perf_logger.info(
            f"PERF | longread | "
            f"chars={input_chars} | "
            f"sections={longread.total_sections} | "
            f"words={longread.total_word_count} | "
            f"tokens={self._total_input_tokens}+{self._total_output_tokens} | "
            f"{cost_str}time={elapsed:.1f}s"
        )

        return longread

    # -------------------------------------------------------------------------
    # Strategy selection
    # -------------------------------------------------------------------------

    def _fits_in_context(self, text: str) -> bool:
        """Check if text fits in model's context window for single-pass."""
        estimated_tokens = len(text) * TOKENS_PER_CHAR
        available = (
            self.context_tokens * CONTEXT_UTILIZATION
            - PROMPT_OVERHEAD_TOKENS
            - OUTPUT_RESERVE_TOKENS
        )
        return estimated_tokens < available

    def _prepare_text(self, transcript_text: str, slides_text: str | None) -> str:
        """Combine transcript with optional slides text."""
        if not slides_text:
            return transcript_text

        logger.info(f"Added slides context: {len(slides_text)} chars")
        return (
            f"{transcript_text}\n\n"
            "---\n\n"
            "## Дополнительная информация со слайдов презентации\n\n"
            f"{slides_text}"
        )

    # -------------------------------------------------------------------------
    # Single-pass path (v0.67+)
    # -------------------------------------------------------------------------

    async def _generate_single_pass(
        self,
        full_text: str,
        metadata: VideoMetadata,
    ) -> Longread:
        """
        Generate longread in a single LLM call.

        Used when full transcript fits in model's context window.

        Args:
            full_text: Full transcript (with optional slides)
            metadata: Video metadata

        Returns:
            Longread object
        """
        start_time = time.time()

        prompt = self._build_single_pass_prompt(full_text, metadata)

        response, usage = await self.ai_client.generate(
            prompt,
            model=self.settings.longread_model,
            num_predict=SINGLE_PASS_MAX_TOKENS,
        )
        self._total_input_tokens = usage.input_tokens
        self._total_output_tokens = usage.output_tokens

        data = self._parse_json_response(response)
        elapsed = time.time() - start_time

        return self._build_longread(
            data, metadata,
            tokens_input=self._total_input_tokens,
            tokens_output=self._total_output_tokens,
            elapsed=elapsed,
        )

    def _build_single_pass_prompt(
        self,
        full_text: str,
        metadata: VideoMetadata,
    ) -> str:
        """Build prompt for single-pass generation."""
        date_formatted = (
            f"{metadata.date.day} {RUSSIAN_MONTHS[metadata.date.month]} "
            f"{metadata.date.year}"
        )

        prompt_parts = [
            self.system_prompt,
            "",
            "---",
            "",
            self.instructions,
            "",
            "---",
            "",
            "## Задание",
            "",
            "Создай полный лонгрид по транскрипту выступления.",
            "",
            f"**Спикер:** {metadata.speaker}",
            f"**Тема:** {metadata.title}",
            f"**Дата:** {date_formatted}",
            f"**Событие:** {metadata.event_type}",
            "",
            "### Транскрипт",
            "",
            full_text,
            "",
            "### Формат ответа",
            "",
            self.template,
        ]
        return "\n".join(prompt_parts)

    # -------------------------------------------------------------------------
    # Map-reduce path (existing logic, refactored)
    # -------------------------------------------------------------------------

    async def _generate_map_reduce(
        self,
        full_text: str,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
    ) -> Longread:
        """
        Generate longread using map-reduce approach.

        Used when transcript doesn't fit in model's context window.
        Split → Outline → Parallel sections → Frame (intro + conclusion).

        Args:
            full_text: Full transcript (with optional slides)
            cleaned_transcript: Original CleanedTranscript
            metadata: Video metadata

        Returns:
            Longread object
        """
        start_time = time.time()

        # Split text into parts
        text_parts = self.text_splitter.split(full_text)

        logger.info(
            f"Generating longread (map-reduce): {len(full_text)} chars, "
            f"{len(text_parts)} parts, parts_per_section={self.parts_per_section}"
        )

        # Extract outline for large texts
        outline = await self._extract_outline_if_needed(
            cleaned_transcript, text_parts
        )
        outline_context = outline.to_context() if outline else "Контекст не предоставлен."

        # MAP: Generate sections in parallel
        sections = await self._generate_sections(text_parts, metadata, outline_context)

        # REDUCE: Generate intro and conclusion
        intro, conclusion, classification = await self._generate_frame(
            sections, metadata
        )

        elapsed = time.time() - start_time

        # Build data dict matching single-pass JSON format
        data = {
            "introduction": intro,
            "sections": [
                {"title": s.title, "content": s.content}
                for s in sections
            ],
            "conclusion": conclusion,
            "topic_area": classification.get("topic_area", []),
            "tags": classification.get("tags", []),
            "access_level": classification.get("access_level", "consultant"),
        }

        return self._build_longread(
            data, metadata,
            tokens_input=self._total_input_tokens,
            tokens_output=self._total_output_tokens,
            elapsed=elapsed,
        )

    async def _extract_outline_if_needed(
        self,
        cleaned: CleanedTranscript,
        text_parts: list[TextPart],
    ) -> TranscriptOutline | None:
        """Extract outline for large texts."""
        input_chars = len(cleaned.text)

        if input_chars <= self.large_text_threshold:
            logger.debug(f"Small text ({input_chars} chars), skipping outline extraction")
            return None

        logger.info(
            f"Large text detected ({input_chars} chars), "
            f"extracting outline from {len(text_parts)} parts"
        )

        outline = await self.outline_extractor.extract(text_parts)

        logger.info(
            f"Outline extracted: {outline.total_parts} parts, "
            f"{len(outline.all_topics)} unique topics"
        )

        return outline

    async def _generate_sections(
        self,
        text_parts: list[TextPart],
        metadata: VideoMetadata,
        outline_context: str,
    ) -> list[LongreadSection]:
        """Generate sections in parallel using semaphore for rate limiting."""
        part_groups = self._group_parts(text_parts)
        total_sections = len(part_groups)

        logger.info(
            f"Generating {total_sections} sections "
            f"(max {self.max_parallel} parallel)"
        )

        semaphore = asyncio.Semaphore(self.max_parallel)

        async def generate_with_semaphore(
            section_idx: int, part_group: list[TextPart]
        ) -> LongreadSection:
            async with semaphore:
                return await self._generate_section(
                    section_idx=section_idx + 1,
                    total_sections=total_sections,
                    parts=part_group,
                    metadata=metadata,
                    outline_context=outline_context,
                )

        tasks = [
            generate_with_semaphore(idx, group)
            for idx, group in enumerate(part_groups)
        ]
        sections = await asyncio.gather(*tasks)

        return list(sections)

    def _group_parts(self, text_parts: list[TextPart]) -> list[list[TextPart]]:
        """Group text parts into sections."""
        groups: list[list[TextPart]] = []
        current_group: list[TextPart] = []

        for part in text_parts:
            current_group.append(part)

            if len(current_group) >= self.parts_per_section:
                groups.append(current_group)
                current_group = []

        if current_group:
            groups.append(current_group)

        return groups

    async def _generate_section(
        self,
        section_idx: int,
        total_sections: int,
        parts: list[TextPart],
        metadata: VideoMetadata,
        outline_context: str,
    ) -> LongreadSection:
        """Generate a single section from a group of text parts."""
        logger.debug(f"Generating section {section_idx}/{total_sections}")

        parts_text = self._format_parts(parts)

        prompt = self._build_section_prompt(
            section_idx, total_sections, parts_text, metadata, outline_context
        )

        response, usage = await self.ai_client.generate(
            prompt, model=self.settings.longread_model
        )
        async with self._tokens_lock:
            self._total_input_tokens += usage.input_tokens
            self._total_output_tokens += usage.output_tokens

        section_data = self._parse_json_response(response)
        source_indices = [p.index for p in parts]

        return LongreadSection(
            index=section_idx,
            title=section_data.get("title", f"Раздел {section_idx}"),
            content=section_data.get("content", ""),
            source_chunks=source_indices,
            word_count=section_data.get("word_count", 0),
        )

    def _build_section_prompt(
        self,
        section_idx: int,
        total_sections: int,
        parts_text: str,
        metadata: VideoMetadata,
        outline_context: str,
    ) -> str:
        """Build section generation prompt with system + instructions + template."""
        prompt_parts = [
            self.system_prompt,
            "",
            "---",
            "",
            self.instructions,
            "",
            "---",
            "",
            "## Задание",
            "",
            f"Создай раздел {section_idx} из {total_sections} для лонгрида.",
            "",
            f"**Спикер:** {metadata.speaker}",
            f"**Тема:** {metadata.title}",
            "",
            "### Контекст (outline)",
            "",
            outline_context,
            "",
            "### Текст для обработки",
            "",
            parts_text,
            "",
            "### Формат ответа",
            "",
            "Верни JSON:",
            '```json',
            '{',
            '  "title": "Название раздела по содержанию",',
            '  "content": "Текст раздела от первого лица...",',
            '  "word_count": 150',
            '}',
            '```',
        ]
        return "\n".join(prompt_parts)

    def _format_parts(self, parts: list[TextPart]) -> str:
        """Format text parts for inclusion in prompt."""
        lines = []
        for part in parts:
            lines.append(f"### Часть {part.index}")
            lines.append("")
            lines.append(part.text)
            lines.append("")
        return "\n".join(lines)

    async def _generate_frame(
        self,
        sections: list[LongreadSection],
        metadata: VideoMetadata,
    ) -> tuple[str, str, dict[str, Any]]:
        """Generate introduction and conclusion from section summaries."""
        logger.debug("Generating introduction and conclusion")

        sections_summary = self._build_sections_summary(sections)
        date_formatted = f"{metadata.date.day} {RUSSIAN_MONTHS[metadata.date.month]} {metadata.date.year}"

        prompt = self._build_frame_prompt(sections_summary, metadata, date_formatted)

        response, usage = await self.ai_client.generate(
            prompt, model=self.settings.longread_model
        )
        async with self._tokens_lock:
            self._total_input_tokens += usage.input_tokens
            self._total_output_tokens += usage.output_tokens

        data = self._parse_json_response(response)

        classification = {
            "topic_area": data.get("topic_area", ["мотивация"]),
            "tags": data.get("tags", []),
            "access_level": data.get("access_level", "consultant"),
        }

        return (
            data.get("introduction", ""),
            data.get("conclusion", ""),
            classification,
        )

    def _build_frame_prompt(
        self,
        sections_summary: str,
        metadata: VideoMetadata,
        date_formatted: str,
    ) -> str:
        """Build frame generation prompt (intro + conclusion)."""
        prompt_parts = [
            self.system_prompt,
            "",
            "---",
            "",
            self.instructions,
            "",
            "---",
            "",
            "## Задание",
            "",
            "Создай вступление, заключение и классификацию для лонгрида.",
            "",
            f"**Спикер:** {metadata.speaker}",
            f"**Тема:** {metadata.title}",
            f"**Дата:** {date_formatted}",
            f"**Событие:** {metadata.event_type}",
            "",
            "### Разделы лонгрида",
            "",
            sections_summary,
            "",
            "### Формат ответа",
            "",
            self.template,
        ]
        return "\n".join(prompt_parts)

    def _build_sections_summary(self, sections: list[LongreadSection]) -> str:
        """Build summary of sections for intro/conclusion generation."""
        lines = []
        for section in sections:
            lines.append(f"### {section.index}. {section.title}")
            lines.append("")
            preview = section.content[:300].rsplit(" ", 1)[0] + "..."
            lines.append(preview)
            lines.append("")
        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # Shared: building Longread + validation
    # -------------------------------------------------------------------------

    def _build_longread(
        self,
        data: dict[str, Any],
        metadata: VideoMetadata,
        tokens_input: int,
        tokens_output: int,
        elapsed: float,
    ) -> Longread:
        """Build Longread object from parsed JSON data with validation."""
        # Parse sections
        sections_data = data.get("sections", [])
        sections = [
            LongreadSection(
                index=idx + 1,
                title=s.get("title", f"Раздел {idx + 1}"),
                content=s.get("content", ""),
                source_chunks=[],
                word_count=len(s.get("content", "").split()),
            )
            for idx, s in enumerate(sections_data)
        ]

        # Validate classification
        topic_area = self._validate_topic_area(data.get("topic_area", []))
        access_level = self._validate_access_level(data.get("access_level"))

        # Calculate cost
        tokens_used = None
        cost = None
        if tokens_input > 0 or tokens_output > 0:
            tokens_used = TokensUsed(input=tokens_input, output=tokens_output)
            cost = calculate_cost(
                self.settings.longread_model,
                tokens_input,
                tokens_output,
            )

        return Longread(
            video_id=metadata.video_id,
            title=metadata.title,
            speaker=metadata.speaker,
            speaker_status=getattr(metadata, 'speaker_status', ''),
            date=metadata.date,
            event_type=metadata.event_type,
            stream=metadata.stream,
            introduction=data.get("introduction", ""),
            sections=sections,
            conclusion=data.get("conclusion", ""),
            topic_area=topic_area,
            tags=data.get("tags", []),
            access_level=access_level,
            model_name=self.settings.longread_model,
            tokens_used=tokens_used,
            cost=cost,
            processing_time_sec=elapsed,
        )

    def _validate_topic_area(self, topic_area: Any) -> list[str]:
        """Validate and normalize topic_area from LLM response."""
        if isinstance(topic_area, str):
            topic_area = [topic_area]
        if not isinstance(topic_area, list):
            return ["мотивация"]
        valid = [t for t in topic_area if t in VALID_TOPIC_AREAS]
        return valid if valid else ["мотивация"]

    def _validate_access_level(self, access_level: Any) -> str:
        """Validate and normalize access_level from LLM response."""
        if access_level in VALID_ACCESS_LEVELS:
            return access_level
        return "consultant"

    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """Parse JSON from LLM response."""
        return extract_and_parse_json(response, json_type="object", default={})
