"""
Summary generator service.

Creates condensed summaries (конспект) from longread documents.
A summary is a navigation document for those who already watched/read the content.
"""

import json
import logging
import time
from typing import Any

from app.config import Settings, get_settings, load_prompt, get_model_config
from app.utils.json_utils import extract_json
from app.models.schemas import (
    Longread,
    Summary,
    VideoMetadata,
)
from app.services.ai_clients import BaseAIClient, OllamaClient

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("app.perf")

# Russian month names for date formatting
RUSSIAN_MONTHS = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]

# Default max input chars (for truncation if needed)
DEFAULT_MAX_INPUT_CHARS = 8000


class SummaryGenerator:
    """
    Summary generation service.

    Creates a condensed summary (конспект) from a longread document.
    The summary helps those who already watched/read the content to
    quickly recall key points.

    Example:
        async with OllamaClient.from_settings(settings) as client:
            generator = SummaryGenerator(client, settings)
            summary = await generator.generate(longread, metadata)
            markdown = summary.to_markdown()
    """

    def __init__(self, ai_client: BaseAIClient, settings: Settings):
        """
        Initialize summary generator.

        Args:
            ai_client: AI client for LLM calls
            settings: Application settings
        """
        self.ai_client = ai_client
        self.settings = settings
        self.prompt_template = load_prompt(
            "summary", settings.summarizer_model, settings
        )

        # Get model-specific config
        model_config = get_model_config(settings.summarizer_model, settings)
        summary_config = model_config.get("summary", {})
        self.max_input_chars = summary_config.get(
            "max_input_chars", DEFAULT_MAX_INPUT_CHARS
        )

        logger.debug(f"SummaryGenerator config: max_input_chars={self.max_input_chars}")

    async def generate(
        self,
        longread: Longread,
        metadata: VideoMetadata,
    ) -> Summary:
        """
        Generate summary from longread document.

        Args:
            longread: Longread document to summarize
            metadata: Video metadata

        Returns:
            Summary with essence, concepts, tools, quotes, insight, actions
        """
        start_time = time.time()

        # Convert longread to text for prompt
        longread_text = self._prepare_longread_text(longread)
        input_chars = len(longread_text)

        logger.info(
            f"Generating summary from longread: {input_chars} chars, "
            f"{longread.total_sections} sections"
        )

        # Build prompt
        prompt = self._build_prompt(longread_text, metadata)

        # Call LLM
        response = await self.ai_client.generate(
            prompt, model=self.settings.summarizer_model
        )

        # Parse response
        summary_data = self._parse_response(response)

        elapsed = time.time() - start_time

        summary = Summary(
            video_id=metadata.video_id,
            title=metadata.title,
            speaker=metadata.speaker,
            date=metadata.date,
            essence=summary_data.get("essence", ""),
            key_concepts=summary_data.get("key_concepts", []),
            practical_tools=summary_data.get("practical_tools", []),
            quotes=summary_data.get("quotes", []),
            insight=summary_data.get("insight", ""),
            actions=summary_data.get("actions", []),
            # Copy classification from longread
            section=longread.section,
            subsection=longread.subsection,
            tags=longread.tags,
            access_level=longread.access_level,
            model_name=self.settings.summarizer_model,
        )

        logger.info(
            f"Summary complete: {len(summary.key_concepts)} concepts, "
            f"{len(summary.quotes)} quotes, {elapsed:.1f}s"
        )

        perf_logger.info(
            f"PERF | summary | "
            f"input_chars={input_chars} | "
            f"concepts={len(summary.key_concepts)} | "
            f"quotes={len(summary.quotes)} | "
            f"time={elapsed:.1f}s"
        )

        return summary

    def _prepare_longread_text(self, longread: Longread) -> str:
        """
        Prepare longread text for prompt.

        If the longread is too large, truncate it intelligently.

        Args:
            longread: Longread document

        Returns:
            Text ready for prompt insertion
        """
        # Build full text
        lines = []

        if longread.introduction:
            lines.append("## Вступление")
            lines.append(longread.introduction)
            lines.append("")

        for section in longread.sections:
            lines.append(f"## {section.title}")
            lines.append(section.content)
            lines.append("")

        if longread.conclusion:
            lines.append("## Заключение")
            lines.append(longread.conclusion)

        full_text = "\n".join(lines)

        # Truncate if needed
        if len(full_text) > self.max_input_chars:
            logger.warning(
                f"Longread too large ({len(full_text)} chars), "
                f"truncating to {self.max_input_chars}"
            )
            full_text = self._truncate_text(full_text, self.max_input_chars)

        return full_text

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """
        Truncate text intelligently, preserving structure.

        Tries to cut at section boundaries rather than mid-sentence.

        Args:
            text: Full text
            max_chars: Maximum characters

        Returns:
            Truncated text with indication that it was cut
        """
        if len(text) <= max_chars:
            return text

        # Find a good cut point (at a section header or paragraph)
        cut_point = max_chars - 100  # Leave room for truncation notice

        # Try to find last section header before cut point
        section_pattern = r"\n## "
        last_section = None
        for match in re.finditer(section_pattern, text[:cut_point]):
            last_section = match.start()

        if last_section and last_section > max_chars // 2:
            # Cut at section boundary
            return text[:last_section] + "\n\n[... сокращено для обработки ...]"

        # Otherwise, cut at paragraph boundary
        last_para = text.rfind("\n\n", 0, cut_point)
        if last_para > max_chars // 2:
            return text[:last_para] + "\n\n[... сокращено для обработки ...]"

        # Fall back to hard cut
        return text[:cut_point] + "...\n\n[... сокращено для обработки ...]"

    def _build_prompt(self, longread_text: str, metadata: VideoMetadata) -> str:
        """
        Build summary prompt from template.

        Args:
            longread_text: Prepared longread text
            metadata: Video metadata

        Returns:
            Complete prompt for LLM
        """
        date_formatted = f"{metadata.date.day} {RUSSIAN_MONTHS[metadata.date.month]} {metadata.date.year}"

        prompt = self.prompt_template
        prompt = prompt.replace("{speaker}", metadata.speaker)
        prompt = prompt.replace("{title}", metadata.title)
        prompt = prompt.replace("{date}", date_formatted)
        prompt = prompt.replace("{longread}", longread_text)

        return prompt

    def _parse_response(self, response: str) -> dict[str, Any]:
        """
        Parse LLM response into summary data.

        Args:
            response: Raw LLM response

        Returns:
            Dict with summary fields
        """
        json_str = extract_json(response, json_type="object")

        try:
            data = json.loads(json_str)
            if not isinstance(data, dict):
                logger.error(f"Expected dict, got {type(data).__name__}")
                return {}
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.debug(f"Response was: {response[:500]}...")
            return {}


if __name__ == "__main__":
    """Run tests when executed directly."""
    import asyncio
    import sys
    from datetime import date
    from pathlib import Path

    from app.models.schemas import LongreadSection

    logging.basicConfig(level=logging.INFO)

    async def run_tests():
        """Run all summary generator tests."""
        print("\nRunning summary generator tests...\n")

        settings = get_settings()

        # Test 1: Load prompt
        print("Test 1: Load prompt...", end=" ")
        try:
            prompt = load_prompt("summary", settings.summarizer_model, settings)
            assert "{speaker}" in prompt
            assert "{longread}" in prompt
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 2: Text truncation
        print("\nTest 2: Text truncation...", end=" ")
        try:
            generator = SummaryGenerator(None, settings)  # type: ignore
            generator.max_input_chars = 100

            long_text = "A" * 200
            truncated = generator._truncate_text(long_text, 100)
            assert len(truncated) <= 100 + 50  # Some room for truncation notice
            assert "сокращено" in truncated
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 3: JSON extraction using shared utils
        print("\nTest 3: JSON extraction (shared utils)...", end=" ")
        try:
            test_json = '```json\n{"essence": "Test", "quotes": []}\n```'
            result = extract_json(test_json, json_type="object")
            parsed = json.loads(result)
            assert "essence" in parsed
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
                    generator = SummaryGenerator(client, settings)

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

                    mock_longread = Longread(
                        video_id="test-video",
                        title="Работа с клиентами",
                        speaker="Тест Спикер",
                        date=date(2025, 1, 20),
                        event_type="ПШ",
                        stream="SV",
                        introduction="Сегодня мы поговорим о важной теме.",
                        sections=[
                            LongreadSection(
                                index=1,
                                title="Первый контакт",
                                content="Первое впечатление очень важно. "
                                        "Всегда улыбайтесь и будьте дружелюбны.",
                                source_chunks=[1],
                                word_count=15,
                            ),
                            LongreadSection(
                                index=2,
                                title="Работа с возражениями",
                                content="Возражения - это возможность. "
                                        "Слушайте клиента и предлагайте решения.",
                                source_chunks=[2],
                                word_count=12,
                            ),
                        ],
                        conclusion="Помните: клиент всегда прав!",
                        section="Бизнес",
                        subsection="Продажи",
                        tags=["клиенты", "продажи"],
                        access_level=1,
                        model_name="test",
                    )

                    summary = await generator.generate(mock_longread, mock_metadata)

                    assert summary.essence, "Essence is empty"
                    assert summary.section == "Бизнес"  # Copied from longread

                    print("OK")
                    print(f"  Essence: {summary.essence[:100]}...")
                    print(f"  Concepts: {len(summary.key_concepts)}")
                    print(f"  Quotes: {len(summary.quotes)}")
                    print(f"  Insight: {summary.insight[:50]}..." if summary.insight else "  No insight")

                except Exception as e:
                    print(f"FAILED: {e}")
                    import traceback
                    traceback.print_exc()
                    return 1

        print("\n" + "=" * 40)
        print("All tests passed!")
        return 0

    sys.exit(asyncio.run(run_tests()))
