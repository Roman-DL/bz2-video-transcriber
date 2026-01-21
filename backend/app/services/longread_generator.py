"""
Longread generator service.

Creates longread documents from cleaned transcript using Map-Reduce approach.
Each section is generated in parallel with outline as shared context.

v0.23+: New prompt architecture (system + instructions + template).
v0.25+: Accepts CleanedTranscript directly (no chunks dependency).
"""

import asyncio
import json
import logging
import time
from typing import Any

from app.config import Settings, get_settings, load_prompt, get_model_config
from app.utils.json_utils import extract_json
from app.models.schemas import (
    CleanedTranscript,
    Longread,
    LongreadSection,
    TextPart,
    TranscriptOutline,
    VideoMetadata,
)
from app.services.ai_clients import BaseAIClient, OllamaClient
from app.services.outline_extractor import OutlineExtractor
from app.services.text_splitter import TextSplitter

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


class LongreadGenerator:
    """
    Longread generation service using Map-Reduce approach.

    For large transcripts:
    1. SPLIT: Split text into parts using TextSplitter
    2. OUTLINE: Extract outline if text > threshold (optional)
    3. MAP: Generate sections from text parts in parallel
    4. REDUCE: Generate introduction and conclusion from section summaries

    Each section receives the full outline as context, making it aware of
    the overall structure while processing only its assigned text parts.

    v0.23+: Uses new prompt architecture with system + instructions + template.
    v0.25+: Accepts CleanedTranscript directly instead of chunks.

    Example:
        async with OllamaClient.from_settings(settings) as client:
            generator = LongreadGenerator(client, settings)
            longread = await generator.generate(cleaned_transcript, metadata)
            markdown = longread.to_markdown()
    """

    def __init__(self, ai_client: BaseAIClient, settings: Settings):
        """
        Initialize longread generator.

        Args:
            ai_client: AI client for LLM calls
            settings: Application settings
        """
        self.ai_client = ai_client
        self.settings = settings

        # Load new prompt architecture
        self.system_prompt = load_prompt(
            "longread_system", settings.summarizer_model, settings
        )
        self.instructions = load_prompt(
            "longread_instructions", settings.summarizer_model, settings
        )
        self.template = load_prompt(
            "longread_template", settings.summarizer_model, settings
        )

        # Initialize text processing components
        self.text_splitter = TextSplitter()
        self.outline_extractor = OutlineExtractor(ai_client, settings)

        # Get model-specific config
        model_config = get_model_config(settings.summarizer_model, settings)
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

        logger.debug(
            f"LongreadGenerator config: parts_per_section={self.parts_per_section}, "
            f"max_parallel={self.max_parallel}, threshold={self.large_text_threshold}"
        )

    async def generate(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
    ) -> Longread:
        """
        Generate longread from cleaned transcript.

        v0.25+: Accepts CleanedTranscript directly instead of chunks.
        Internally splits text and extracts outline if needed.

        Args:
            cleaned_transcript: Cleaned transcript text
            metadata: Video metadata

        Returns:
            Longread with introduction, sections, and conclusion
        """
        start_time = time.time()

        # Phase 0: Split text into parts
        text_parts = self.text_splitter.split(cleaned_transcript.text)
        input_chars = len(cleaned_transcript.text)

        logger.info(
            f"Generating longread: {input_chars} chars, "
            f"{len(text_parts)} parts, parts_per_section={self.parts_per_section}"
        )

        # Phase 0.5: Extract outline for large texts
        outline = await self._extract_outline_if_needed(
            cleaned_transcript, text_parts
        )
        outline_context = outline.to_context() if outline else "Контекст не предоставлен."

        # Phase 1: MAP - Generate sections in parallel
        sections = await self._generate_sections(text_parts, metadata, outline_context)

        # Phase 2: REDUCE - Generate intro and conclusion
        intro, conclusion, classification = await self._generate_frame(
            sections, metadata
        )

        elapsed = time.time() - start_time

        # Validate and normalize classification
        topic_area = classification.get("topic_area", [])
        if isinstance(topic_area, str):
            topic_area = [topic_area]
        topic_area = [t for t in topic_area if t in VALID_TOPIC_AREAS]
        if not topic_area:
            topic_area = ["мотивация"]  # Default

        access_level = classification.get("access_level", "consultant")
        if access_level not in VALID_ACCESS_LEVELS:
            access_level = "consultant"

        longread = Longread(
            video_id=metadata.video_id,
            title=metadata.title,
            speaker=metadata.speaker,
            speaker_status=getattr(metadata, 'speaker_status', ''),
            date=metadata.date,
            event_type=metadata.event_type,
            stream=metadata.stream,
            introduction=intro,
            sections=sections,
            conclusion=conclusion,
            topic_area=topic_area,
            tags=classification.get("tags", []),
            access_level=access_level,
            model_name=self.settings.summarizer_model,
        )

        logger.info(
            f"Longread complete: {longread.total_sections} sections, "
            f"{longread.total_word_count} words, {elapsed:.1f}s"
        )

        perf_logger.info(
            f"PERF | longread | "
            f"chars={input_chars} | "
            f"parts={len(text_parts)} | "
            f"sections={longread.total_sections} | "
            f"words={longread.total_word_count} | "
            f"time={elapsed:.1f}s"
        )

        return longread

    async def _extract_outline_if_needed(
        self,
        cleaned: CleanedTranscript,
        text_parts: list[TextPart],
    ) -> TranscriptOutline | None:
        """
        Extract outline for large texts.

        Args:
            cleaned: Cleaned transcript
            text_parts: Text parts from splitter

        Returns:
            Outline if text is large enough, None otherwise
        """
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
        """
        Generate sections in parallel using semaphore for rate limiting.

        Args:
            text_parts: Text parts from TextSplitter
            metadata: Video metadata
            outline_context: Formatted outline for context

        Returns:
            List of LongreadSection in order
        """
        # Group text parts into sections
        part_groups = self._group_parts(text_parts)
        total_sections = len(part_groups)

        logger.info(
            f"Generating {total_sections} sections "
            f"(max {self.max_parallel} parallel)"
        )

        # Create semaphore for parallel execution limit
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

        # Run all sections in parallel with semaphore
        tasks = [
            generate_with_semaphore(idx, group)
            for idx, group in enumerate(part_groups)
        ]
        sections = await asyncio.gather(*tasks)

        return list(sections)

    def _group_parts(self, text_parts: list[TextPart]) -> list[list[TextPart]]:
        """
        Group text parts into sections.

        Args:
            text_parts: All text parts from TextSplitter

        Returns:
            List of part groups (each group is a list of TextPart)
        """
        groups: list[list[TextPart]] = []
        current_group: list[TextPart] = []

        for part in text_parts:
            current_group.append(part)

            if len(current_group) >= self.parts_per_section:
                groups.append(current_group)
                current_group = []

        # Add remaining parts
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
        """
        Generate a single section from a group of text parts.

        Args:
            section_idx: Section number (1-based)
            total_sections: Total number of sections
            parts: Text parts for this section
            metadata: Video metadata
            outline_context: Formatted outline for context

        Returns:
            LongreadSection with title and content
        """
        logger.debug(f"Generating section {section_idx}/{total_sections}")

        # Format parts for prompt
        parts_text = self._format_parts(parts)

        # Build prompt with new architecture
        prompt = self._build_section_prompt(
            section_idx, total_sections, parts_text, metadata, outline_context
        )

        # Call LLM
        response = await self.ai_client.generate(
            prompt, model=self.settings.summarizer_model
        )

        # Parse response
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
        """
        Build section generation prompt with system + instructions + template.

        Args:
            section_idx: Section number
            total_sections: Total sections count
            parts_text: Formatted text parts content
            metadata: Video metadata
            outline_context: Outline for context

        Returns:
            Combined prompt string
        """
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
        """
        Format text parts for inclusion in prompt.

        Args:
            parts: List of TextPart objects

        Returns:
            Formatted string with part contents
        """
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
        """
        Generate introduction and conclusion from section summaries.

        Args:
            sections: Generated sections
            metadata: Video metadata

        Returns:
            Tuple of (introduction, conclusion, classification_dict)
        """
        logger.debug("Generating introduction and conclusion")

        # Build sections summary
        sections_summary = self._build_sections_summary(sections)

        # Format date
        date_formatted = f"{metadata.date.day} {RUSSIAN_MONTHS[metadata.date.month]} {metadata.date.year}"

        # Build prompt with new architecture
        prompt = self._build_frame_prompt(sections_summary, metadata, date_formatted)

        # Call LLM
        response = await self.ai_client.generate(
            prompt, model=self.settings.summarizer_model
        )

        # Parse response
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
        """
        Build frame generation prompt (intro + conclusion).

        Args:
            sections_summary: Summary of all sections
            metadata: Video metadata
            date_formatted: Formatted date string

        Returns:
            Combined prompt string
        """
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
        """
        Build summary of sections for intro/conclusion generation.

        Args:
            sections: All generated sections

        Returns:
            Formatted summary string
        """
        lines = []
        for section in sections:
            lines.append(f"### {section.index}. {section.title}")
            lines.append("")
            # Take first 300 chars of content as preview
            preview = section.content[:300].rsplit(" ", 1)[0] + "..."
            lines.append(preview)
            lines.append("")
        return "\n".join(lines)

    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """
        Parse JSON from LLM response.

        Args:
            response: Raw LLM response

        Returns:
            Parsed dict
        """
        json_str = extract_json(response, json_type="object")

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.debug(f"Response was: {response[:500]}...")
            return {}


if __name__ == "__main__":
    """Run tests when executed directly."""
    import sys
    from datetime import date
    from pathlib import Path

    logging.basicConfig(level=logging.INFO)

    async def run_tests():
        """Run all longread generator tests."""
        print("\nRunning longread generator tests...\n")

        settings = get_settings()

        # Test 1: Load prompts (new architecture)
        print("Test 1: Load prompts (new architecture)...", end=" ")
        try:
            system_prompt = load_prompt("longread_system", settings.summarizer_model, settings)
            instructions = load_prompt("longread_instructions", settings.summarizer_model, settings)
            template = load_prompt("longread_template", settings.summarizer_model, settings)
            assert "Longread Generator" in system_prompt
            assert "Принципы" in instructions
            assert "JSON" in template
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 2: Part grouping (v0.25+)
        print("\nTest 2: Part grouping...", end=" ")
        try:
            # Create mock generator (no AI client needed for this test)
            generator = LongreadGenerator(None, settings)  # type: ignore
            generator.parts_per_section = 3

            mock_parts = [
                TextPart(
                    index=i,
                    text=f"Text for part {i}",
                    start_char=0,
                    end_char=100,
                    has_overlap_before=i > 1,
                    has_overlap_after=i < 7,
                )
                for i in range(1, 8)  # 7 parts
            ]

            groups = generator._group_parts(mock_parts)
            assert len(groups) == 3, f"Expected 3 groups, got {len(groups)}"
            assert len(groups[0]) == 3
            assert len(groups[1]) == 3
            assert len(groups[2]) == 1  # Remaining part
            print("OK")
            print(f"  Groups: {[len(g) for g in groups]}")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 3: JSON extraction using shared utils
        print("\nTest 3: JSON extraction (shared utils)...", end=" ")
        try:
            test_responses = [
                '{"title": "Test", "content": "Content"}',
                '```json\n{"title": "Test"}\n```',
                'Some text before {"title": "Test"} and after',
            ]
            for resp in test_responses:
                result = extract_json(resp, json_type="object")
                assert "{" in result and "}" in result
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 4: Full generation (requires Ollama)
        print("\nTest 4: Full generation...", end=" ")
        async with OllamaClient.from_settings(settings) as client:
            status = await client.check_services()

            if not status["ollama"]:
                print("SKIPPED (Ollama unavailable)")
            else:
                try:
                    generator = LongreadGenerator(client, settings)

                    mock_metadata = VideoMetadata(
                        date=date(2025, 1, 20),
                        event_type="ПШ",
                        stream="SV",
                        title="Работа с клиентами",
                        speaker="Тест Спикер",
                        original_filename="test.mp4",
                        video_id="test-video",
                        source_path=Path("/test/test.mp4"),
                        archive_path=Path("/archive/test"),
                    )

                    # v0.25+: Use CleanedTranscript instead of chunks
                    mock_cleaned = CleanedTranscript(
                        text=(
                            "Сегодня мы поговорим о работе с клиентами. "
                            "Это важная тема для каждого консультанта. "
                            "Первое, что нужно сделать - это понять потребности клиента. "
                            "Задавайте вопросы, слушайте внимательно."
                        ),
                        word_count=33,
                        model_name="test",
                    )

                    longread = await generator.generate(mock_cleaned, mock_metadata)

                    assert longread.total_sections > 0
                    assert longread.total_word_count > 0
                    assert isinstance(longread.topic_area, list)
                    assert longread.access_level in VALID_ACCESS_LEVELS

                    print("OK")
                    print(f"  Sections: {longread.total_sections}")
                    print(f"  Words: {longread.total_word_count}")
                    print(f"  Topic areas: {longread.topic_area}")
                    print(f"  Access level: {longread.access_level}")

                except Exception as e:
                    print(f"FAILED: {e}")
                    import traceback
                    traceback.print_exc()
                    return 1

        print("\n" + "=" * 40)
        print("All tests passed!")
        return 0

    sys.exit(asyncio.run(run_tests()))
