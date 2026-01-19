"""
Longread generator service.

Creates longread documents from transcript chunks using Map-Reduce approach.
Each section is generated in parallel with outline as shared context.
"""

import asyncio
import json
import logging
import re
import time
from typing import Any

from app.config import Settings, get_settings, load_prompt, get_model_config
from app.models.schemas import (
    Longread,
    LongreadSection,
    TranscriptChunks,
    TranscriptOutline,
    VideoMetadata,
)
from app.services.ai_client import AIClient

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("app.perf")

# Valid section values for classification
VALID_SECTIONS = ["Обучение", "Продукты", "Бизнес", "Мотивация"]

# Russian month names for date formatting
RUSSIAN_MONTHS = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]

# Default configuration
DEFAULT_CHUNKS_PER_SECTION = 4
DEFAULT_MAX_PARALLEL_SECTIONS = 2


class LongreadGenerator:
    """
    Longread generation service using Map-Reduce approach.

    For large transcripts:
    1. MAP: Groups chunks into sections and generates each section in parallel
    2. REDUCE: Generates introduction and conclusion from section summaries

    Each section receives the full outline as context, making it aware of
    the overall structure while processing only its assigned chunks.

    Example:
        async with AIClient(settings) as client:
            generator = LongreadGenerator(client, settings)
            longread = await generator.generate(chunks, metadata, outline)
            markdown = longread.to_markdown()
    """

    def __init__(self, ai_client: AIClient, settings: Settings):
        """
        Initialize longread generator.

        Args:
            ai_client: AI client for LLM calls
            settings: Application settings
        """
        self.ai_client = ai_client
        self.settings = settings
        self.section_prompt = load_prompt(
            "longread_section", settings.summarizer_model, settings
        )
        self.combine_prompt = load_prompt(
            "longread_combine", settings.summarizer_model, settings
        )

        # Get model-specific config
        model_config = get_model_config(settings.summarizer_model, settings)
        longread_config = model_config.get("longread", {})
        self.chunks_per_section = longread_config.get(
            "chunks_per_section", DEFAULT_CHUNKS_PER_SECTION
        )
        self.max_parallel = longread_config.get(
            "max_parallel_sections", DEFAULT_MAX_PARALLEL_SECTIONS
        )

        logger.debug(
            f"LongreadGenerator config: chunks_per_section={self.chunks_per_section}, "
            f"max_parallel={self.max_parallel}"
        )

    async def generate(
        self,
        chunks: TranscriptChunks,
        metadata: VideoMetadata,
        outline: TranscriptOutline | None,
    ) -> Longread:
        """
        Generate longread from transcript chunks.

        Args:
            chunks: Transcript chunks from SemanticChunker
            metadata: Video metadata
            outline: TranscriptOutline for context (may be None for small texts)

        Returns:
            Longread with introduction, sections, and conclusion
        """
        start_time = time.time()

        # Format outline for prompts
        outline_context = outline.to_context() if outline else "Контекст не предоставлен."

        logger.info(
            f"Generating longread: {chunks.total_chunks} chunks, "
            f"chunks_per_section={self.chunks_per_section}"
        )

        # Phase 1: MAP - Generate sections in parallel
        sections = await self._generate_sections(chunks, metadata, outline_context)

        # Phase 2: REDUCE - Generate intro and conclusion
        intro, conclusion, classification = await self._generate_frame(
            sections, metadata
        )

        elapsed = time.time() - start_time

        longread = Longread(
            video_id=metadata.video_id,
            title=metadata.title,
            speaker=metadata.speaker,
            date=metadata.date,
            event_type=metadata.event_type,
            stream=metadata.stream,
            introduction=intro,
            sections=sections,
            conclusion=conclusion,
            section=classification.get("section", "Обучение"),
            subsection=classification.get("subsection", ""),
            tags=classification.get("tags", []),
            access_level=classification.get("access_level", 1),
            model_name=self.settings.summarizer_model,
        )

        logger.info(
            f"Longread complete: {longread.total_sections} sections, "
            f"{longread.total_word_count} words, {elapsed:.1f}s"
        )

        perf_logger.info(
            f"PERF | longread | "
            f"chunks={chunks.total_chunks} | "
            f"sections={longread.total_sections} | "
            f"words={longread.total_word_count} | "
            f"time={elapsed:.1f}s"
        )

        return longread

    async def _generate_sections(
        self,
        chunks: TranscriptChunks,
        metadata: VideoMetadata,
        outline_context: str,
    ) -> list[LongreadSection]:
        """
        Generate sections in parallel using semaphore for rate limiting.

        Args:
            chunks: All transcript chunks
            metadata: Video metadata
            outline_context: Formatted outline for context

        Returns:
            List of LongreadSection in order
        """
        # Group chunks into sections
        chunk_groups = self._group_chunks(chunks)
        total_sections = len(chunk_groups)

        logger.info(
            f"Generating {total_sections} sections "
            f"(max {self.max_parallel} parallel)"
        )

        # Create semaphore for parallel execution limit
        semaphore = asyncio.Semaphore(self.max_parallel)

        async def generate_with_semaphore(
            section_idx: int, chunk_group: list
        ) -> LongreadSection:
            async with semaphore:
                return await self._generate_section(
                    section_idx=section_idx + 1,
                    total_sections=total_sections,
                    chunks=chunk_group,
                    metadata=metadata,
                    outline_context=outline_context,
                )

        # Run all sections in parallel with semaphore
        tasks = [
            generate_with_semaphore(idx, group)
            for idx, group in enumerate(chunk_groups)
        ]
        sections = await asyncio.gather(*tasks)

        return list(sections)

    def _group_chunks(self, chunks: TranscriptChunks) -> list[list[dict]]:
        """
        Group chunks into sections of N chunks each.

        Args:
            chunks: All transcript chunks

        Returns:
            List of chunk groups (each group is a list of chunk dicts)
        """
        groups = []
        current_group = []

        for chunk in chunks.chunks:
            current_group.append({
                "index": chunk.index,
                "topic": chunk.topic,
                "text": chunk.text,
                "word_count": chunk.word_count,
            })

            if len(current_group) >= self.chunks_per_section:
                groups.append(current_group)
                current_group = []

        # Add remaining chunks
        if current_group:
            groups.append(current_group)

        return groups

    async def _generate_section(
        self,
        section_idx: int,
        total_sections: int,
        chunks: list[dict],
        metadata: VideoMetadata,
        outline_context: str,
    ) -> LongreadSection:
        """
        Generate a single section from a group of chunks.

        Args:
            section_idx: Section number (1-based)
            total_sections: Total number of sections
            chunks: Chunks for this section
            metadata: Video metadata
            outline_context: Formatted outline for context

        Returns:
            LongreadSection with title and content
        """
        logger.debug(f"Generating section {section_idx}/{total_sections}")

        # Format chunks for prompt
        chunks_text = self._format_chunks(chunks)

        # Build prompt
        prompt = self.section_prompt
        prompt = prompt.replace("{speaker}", metadata.speaker)
        prompt = prompt.replace("{title}", metadata.title)
        prompt = prompt.replace("{section_index}", str(section_idx))
        prompt = prompt.replace("{total_sections}", str(total_sections))
        prompt = prompt.replace("{outline}", outline_context)
        prompt = prompt.replace("{chunks}", chunks_text)

        # Call LLM
        response = await self.ai_client.generate(
            prompt, model=self.settings.summarizer_model
        )

        # Parse response
        section_data = self._parse_json_response(response)

        source_indices = [c["index"] for c in chunks]

        return LongreadSection(
            index=section_idx,
            title=section_data.get("title", f"Раздел {section_idx}"),
            content=section_data.get("content", ""),
            source_chunks=source_indices,
            word_count=section_data.get("word_count", 0),
        )

    def _format_chunks(self, chunks: list[dict]) -> str:
        """
        Format chunks for inclusion in prompt.

        Args:
            chunks: List of chunk dicts

        Returns:
            Formatted string with chunk contents
        """
        lines = []
        for chunk in chunks:
            lines.append(f"### Чанк {chunk['index']}: {chunk['topic']}")
            lines.append("")
            lines.append(chunk["text"])
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

        # Build prompt
        prompt = self.combine_prompt
        prompt = prompt.replace("{speaker}", metadata.speaker)
        prompt = prompt.replace("{title}", metadata.title)
        prompt = prompt.replace("{date}", date_formatted)
        prompt = prompt.replace("{event_type}", metadata.event_type)
        prompt = prompt.replace("{sections_summary}", sections_summary)

        # Call LLM
        response = await self.ai_client.generate(
            prompt, model=self.settings.summarizer_model
        )

        # Parse response
        data = self._parse_json_response(response)

        # Validate section
        section = data.get("section", "")
        if section not in VALID_SECTIONS:
            logger.warning(f"Invalid section '{section}', using default 'Обучение'")
            section = "Обучение"

        classification = {
            "section": section,
            "subsection": data.get("subsection", ""),
            "tags": data.get("tags", []),
            "access_level": data.get("access_level", 1),
        }

        return (
            data.get("introduction", ""),
            data.get("conclusion", ""),
            classification,
        )

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
            # Take first 200 chars of content as preview
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
        json_str = self._extract_json(response)

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.debug(f"Response was: {response[:500]}...")
            return {}

    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from LLM response.

        Handles markdown code blocks and finds JSON object.

        Args:
            text: Raw LLM response

        Returns:
            Clean JSON string
        """
        cleaned = text.strip()

        # Try to extract from markdown code block
        code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
        if code_block_match:
            cleaned = code_block_match.group(1).strip()

        # Find JSON object
        if not cleaned.startswith("{"):
            start_idx = cleaned.find("{")
            if start_idx != -1:
                brace_count = 0
                end_idx = start_idx
                for i, char in enumerate(cleaned[start_idx:], start_idx):
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i
                            break
                cleaned = cleaned[start_idx : end_idx + 1]

        return cleaned.strip()


if __name__ == "__main__":
    """Run tests when executed directly."""
    import sys
    from datetime import date
    from pathlib import Path

    from app.models.schemas import TranscriptChunk

    logging.basicConfig(level=logging.INFO)

    async def run_tests():
        """Run all longread generator tests."""
        print("\nRunning longread generator tests...\n")

        settings = get_settings()

        # Test 1: Load prompts
        print("Test 1: Load prompts...", end=" ")
        try:
            section_prompt = load_prompt("longread_section", settings.summarizer_model, settings)
            combine_prompt = load_prompt("longread_combine", settings.summarizer_model, settings)
            assert "{speaker}" in section_prompt
            assert "{chunks}" in section_prompt
            assert "{sections_summary}" in combine_prompt
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 2: Chunk grouping
        print("\nTest 2: Chunk grouping...", end=" ")
        try:
            # Create mock generator (no AI client needed for this test)
            generator = LongreadGenerator(None, settings)  # type: ignore
            generator.chunks_per_section = 3

            mock_chunks = TranscriptChunks(
                chunks=[
                    TranscriptChunk(
                        id=f"test_{i}",
                        index=i,
                        topic=f"Topic {i}",
                        text=f"Text for chunk {i}",
                        word_count=50,
                    )
                    for i in range(1, 8)  # 7 chunks
                ],
                model_name="test",
            )

            groups = generator._group_chunks(mock_chunks)
            assert len(groups) == 3, f"Expected 3 groups, got {len(groups)}"
            assert len(groups[0]) == 3
            assert len(groups[1]) == 3
            assert len(groups[2]) == 1  # Remaining chunk
            print("OK")
            print(f"  Groups: {[len(g) for g in groups]}")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 3: JSON extraction
        print("\nTest 3: JSON extraction...", end=" ")
        try:
            test_responses = [
                '{"title": "Test", "content": "Content"}',
                '```json\n{"title": "Test"}\n```',
                'Some text before {"title": "Test"} and after',
            ]
            for resp in test_responses:
                result = generator._extract_json(resp)
                assert "{" in result and "}" in result
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 4: Full generation (requires Ollama)
        print("\nTest 4: Full generation...", end=" ")
        async with AIClient(settings) as client:
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

                    mock_chunks = TranscriptChunks(
                        chunks=[
                            TranscriptChunk(
                                id="test_1",
                                index=1,
                                topic="Введение",
                                text="Сегодня мы поговорим о работе с клиентами. "
                                     "Это важная тема для каждого консультанта.",
                                word_count=15,
                            ),
                            TranscriptChunk(
                                id="test_2",
                                index=2,
                                topic="Первые шаги",
                                text="Первое, что нужно сделать - это понять потребности клиента. "
                                     "Задавайте вопросы, слушайте внимательно.",
                                word_count=18,
                            ),
                        ],
                        model_name="test",
                    )

                    longread = await generator.generate(mock_chunks, mock_metadata, None)

                    assert longread.total_sections > 0
                    assert longread.total_word_count > 0
                    assert longread.section in VALID_SECTIONS

                    print("OK")
                    print(f"  Sections: {longread.total_sections}")
                    print(f"  Words: {longread.total_word_count}")
                    print(f"  Classification: {longread.section}/{longread.subsection}")

                except Exception as e:
                    print(f"FAILED: {e}")
                    import traceback
                    traceback.print_exc()
                    return 1

        print("\n" + "=" * 40)
        print("All tests passed!")
        return 0

    sys.exit(asyncio.run(run_tests()))
