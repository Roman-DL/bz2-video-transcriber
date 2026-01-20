"""
Video summarizer service.

Creates structured summaries from cleaned transcripts using Ollama LLM.
"""

import json
import logging
import time
from typing import Any

from app.config import Settings, get_settings, load_prompt
from app.utils.json_utils import extract_json
from app.models.schemas import (
    CleanedTranscript,
    TranscriptOutline,
    VideoMetadata,
    VideoSummary,
)
from app.services.ai_clients import OllamaClient

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("app.perf")

# Valid section values for classification
VALID_SECTIONS = ["Обучение", "Продукты", "Бизнес", "Мотивация"]

# Russian month names for date formatting
RUSSIAN_MONTHS = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]


class VideoSummarizer:
    """
    Video summarization service using Ollama LLM.

    Creates structured summaries with key points, recommendations,
    target audience, and classification for BZ 2.0 knowledge base.

    For large texts (>10K chars), uses TranscriptOutline (~1K tokens)
    instead of full transcript (~50K tokens) for more stable LLM processing.

    Supports dynamic prompt selection for iterative format tuning.

    Example:
        async with OllamaClient.from_settings(settings) as client:
            summarizer = VideoSummarizer(client, settings)

            # With outline (large texts):
            summary = await summarizer.summarize(outline, metadata)

            # With full transcript (small texts or fallback):
            summary = await summarizer.summarize(None, metadata, cleaned_transcript)

        # With custom prompt:
        summarizer = VideoSummarizer(client, settings, prompt_name="summarizer_v2")
    """

    def __init__(
        self,
        ai_client: OllamaClient,
        settings: Settings,
        prompt_name: str = "summarizer",
    ):
        """
        Initialize summarizer.

        Args:
            ai_client: AI client for LLM calls
            settings: Application settings
            prompt_name: Name of prompt template file (without .md extension)
        """
        self.ai_client = ai_client
        self.settings = settings
        self.prompt_name = prompt_name
        self.prompt_template = load_prompt(prompt_name, settings.summarizer_model, settings)

    def set_prompt(self, prompt_name: str) -> None:
        """
        Change prompt template on the fly.

        Args:
            prompt_name: Name of prompt template file (without .md extension)
        """
        self.prompt_name = prompt_name
        self.prompt_template = load_prompt(prompt_name, self.settings.summarizer_model, self.settings)
        logger.info(f"Prompt changed to: {prompt_name}")

    async def summarize(
        self,
        outline: TranscriptOutline | None,
        metadata: VideoMetadata,
        cleaned_transcript: CleanedTranscript | None = None,
    ) -> VideoSummary:
        """
        Create structured summary from transcript outline or full text.

        For large texts (outline provided): uses outline context (~1K tokens)
        For small texts (no outline): uses full transcript text

        Args:
            outline: TranscriptOutline from OutlineExtractor (None for small texts)
            metadata: Video metadata
            cleaned_transcript: Full transcript (used when outline is None)

        Returns:
            VideoSummary with structured content and classification

        Raises:
            ValueError: If neither outline nor cleaned_transcript provided
        """
        if outline is None and cleaned_transcript is None:
            raise ValueError("Either outline or cleaned_transcript must be provided")

        # Determine input source
        if outline is not None and outline.total_parts > 0:
            # Large text: use outline context
            context_text = outline.to_context()
            input_chars = len(context_text)
            logger.info(
                f"Summarizing from outline: {outline.total_parts} parts, "
                f"{len(outline.all_topics)} topics, {input_chars} context chars, "
                f"prompt={self.prompt_name}"
            )
        else:
            # Small text: use full transcript
            if cleaned_transcript is None:
                raise ValueError("cleaned_transcript required when outline is empty")
            context_text = cleaned_transcript.text
            input_chars = len(context_text)
            logger.info(
                f"Summarizing full transcript: {input_chars} chars, "
                f"prompt={self.prompt_name}"
            )

        start_time = time.time()

        # Build prompt and call LLM
        prompt = self._build_prompt(context_text, metadata)
        response = await self.ai_client.generate(prompt)

        elapsed = time.time() - start_time

        # Parse LLM response into VideoSummary
        summary = self._parse_summary(response)

        logger.info(
            f"Summarization complete: section={summary.section}, "
            f"tags={len(summary.tags)}, access_level={summary.access_level}"
        )

        # Performance metrics for progress estimation
        perf_logger.info(
            f"PERF | summarize | "
            f"input_chars={input_chars} | "
            f"time={elapsed:.1f}s"
        )

        return summary

    def _build_prompt(self, text: str, metadata: VideoMetadata) -> str:
        """
        Build summarization prompt from template.

        Args:
            text: Context text (outline.to_context() or full transcript)
            metadata: Video metadata

        Returns:
            Complete prompt for LLM
        """
        # Format date in Russian (e.g., "8 января 2025")
        date_formatted = f"{metadata.date.day} {RUSSIAN_MONTHS[metadata.date.month]} {metadata.date.year}"

        # Use replace() because the prompt contains JSON examples with curly braces
        prompt = self.prompt_template
        prompt = prompt.replace("{title}", metadata.title)
        prompt = prompt.replace("{speaker}", metadata.speaker)
        prompt = prompt.replace("{date}", date_formatted)
        prompt = prompt.replace("{event_type}", metadata.event_type)
        prompt = prompt.replace("{stream_name}", metadata.stream_full)
        prompt = prompt.replace("{transcript}", text)

        return prompt

    def _parse_summary(self, response: str) -> VideoSummary:
        """
        Parse LLM response into VideoSummary.

        Handles nested classification structure and validates fields.

        Args:
            response: Raw LLM response (JSON or markdown-wrapped JSON)

        Returns:
            VideoSummary instance

        Raises:
            ValueError: If JSON parsing fails
        """
        # Extract JSON from response (handles markdown code blocks)
        json_str = extract_json(response, json_type="object")

        # Parse JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.debug(f"Response was: {response[:500]}...")
            raise ValueError(f"Invalid JSON in LLM response: {e}")

        # Validate it's a dict
        if not isinstance(data, dict):
            raise ValueError(f"Expected JSON object, got {type(data).__name__}")

        # Extract and flatten fields
        summary_data = self._flatten_response(data)

        # Validate section
        section = summary_data.get("section", "")
        if section not in VALID_SECTIONS:
            logger.warning(f"Invalid section value: '{section}', using default 'Обучение'")
            summary_data["section"] = "Обучение"

        # Add model name from settings
        summary_data["model_name"] = self.settings.summarizer_model

        return VideoSummary(**summary_data)

    def _flatten_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Flatten nested classification into top-level fields.

        Args:
            data: Parsed JSON data from LLM

        Returns:
            Flattened dict ready for VideoSummary
        """
        result = {
            "summary": data.get("summary", ""),
            "key_points": data.get("key_points", []),
            "recommendations": data.get("recommendations", []),
            "target_audience": data.get("target_audience", ""),
            "questions_answered": data.get("questions_answered", []),
        }

        # Extract classification fields (may be nested or at top level)
        classification = data.get("classification", {})

        result["section"] = classification.get("section", data.get("section", ""))
        result["subsection"] = classification.get("subsection", data.get("subsection", ""))
        result["tags"] = classification.get("tags", data.get("tags", []))
        result["access_level"] = classification.get("access_level", data.get("access_level", 1))

        return result


if __name__ == "__main__":
    """Run tests when executed directly."""
    import asyncio
    import sys
    from datetime import date
    from pathlib import Path

    # Configure logging for tests
    logging.basicConfig(level=logging.INFO)

    async def run_tests():
        """Run all summarizer tests."""
        print("\nRunning summarizer tests...\n")

        settings = get_settings()

        # Test 1: Load prompt
        print("Test 1: Load prompt...", end=" ")
        try:
            prompt = load_prompt("summarizer", settings.summarizer_model, settings)
            assert "{title}" in prompt, "Prompt missing {title} placeholder"
            assert "{speaker}" in prompt, "Prompt missing {speaker} placeholder"
            assert "{transcript}" in prompt, "Prompt missing {transcript} placeholder"
            assert len(prompt) > 100, "Prompt too short"
            print("OK")
            print(f"  Prompt length: {len(prompt)} chars")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 2: Extract JSON using shared utils
        print("\nTest 2: Extract JSON (shared utils)...", end=" ")
        try:
            plain_json = '{"summary": "Test summary", "section": "Обучение"}'
            extracted = extract_json(plain_json, json_type="object")
            assert extracted == plain_json, f"Expected {plain_json}, got {extracted}"
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 3: Extract JSON from markdown-wrapped response
        print("\nTest 3: Extract JSON (markdown)...", end=" ")
        try:
            markdown_json = '```json\n{"summary": "Test", "section": "Бизнес"}\n```'
            extracted = extract_json(markdown_json, json_type="object")
            assert "{" in extracted and "}" in extracted, "JSON markers missing"
            assert "```" not in extracted, "Markdown markers not removed"
            print("OK")
            print(f"  Extracted: {extracted}")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 4: Parse summary fields
        print("\nTest 4: Parse summary fields...", end=" ")
        try:
            summarizer = VideoSummarizer(None, settings)  # type: ignore

            test_json = """{
                "summary": "Это тестовое саммари видео.",
                "key_points": ["Пункт 1", "Пункт 2", "Пункт 3"],
                "recommendations": ["Рекомендация 1", "Рекомендация 2"],
                "target_audience": "Для всех консультантов",
                "questions_answered": ["Вопрос 1", "Вопрос 2"],
                "classification": {
                    "section": "Продукты",
                    "subsection": "Применение",
                    "tags": ["продукты", "здоровье", "питание"],
                    "access_level": 2
                }
            }"""

            summary = summarizer._parse_summary(test_json)

            assert summary.summary == "Это тестовое саммари видео."
            assert len(summary.key_points) == 3
            assert len(summary.recommendations) == 2
            assert summary.section == "Продукты"
            assert summary.subsection == "Применение"
            assert len(summary.tags) == 3
            assert summary.access_level == 2

            print("OK")
            print(f"  Section: {summary.section}, Tags: {summary.tags}")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 5: Validate section (valid and invalid)
        print("\nTest 5: Validate section...", end=" ")
        try:
            # Valid section
            valid_json = '{"summary": "", "key_points": [], "recommendations": [], "target_audience": "", "questions_answered": [], "section": "Мотивация", "subsection": "", "tags": []}'
            summary1 = summarizer._parse_summary(valid_json)
            assert summary1.section == "Мотивация", f"Expected 'Мотивация', got {summary1.section}"

            # Invalid section - should default to "Обучение"
            invalid_json = '{"summary": "", "key_points": [], "recommendations": [], "target_audience": "", "questions_answered": [], "section": "НеверныйРаздел", "subsection": "", "tags": []}'
            summary2 = summarizer._parse_summary(invalid_json)
            assert summary2.section == "Обучение", f"Expected default 'Обучение', got {summary2.section}"

            print("OK")
            print(f"  Valid section: {summary1.section}")
            print(f"  Invalid section defaulted to: {summary2.section}")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 6: Full summarization with LLM (if available)
        print("\nTest 6: Full summarization with LLM...", end=" ")
        async with OllamaClient.from_settings(settings) as client:
            status = await client.check_services()

            if not status["ollama"]:
                print("SKIPPED (Ollama unavailable)")
            else:
                try:
                    summarizer = VideoSummarizer(client, settings)

                    mock_metadata = VideoMetadata(
                        date=date(2025, 1, 8),
                        event_type="ПШ",
                        stream="SV",
                        title="Правильное питание",
                        speaker="Иван Иванов",
                        original_filename="test.mp4",
                        video_id="test-video-id",
                        source_path=Path("/test/test.mp4"),
                        archive_path=Path("/archive/test"),
                    )

                    # Create a mock cleaned transcript
                    mock_text = """
                    Сегодня мы поговорим о важности правильного питания. Это ключевой фактор
                    для здоровья и хорошего самочувствия. Многие люди недооценивают роль питания
                    в их повседневной жизни.

                    Первое, на что стоит обратить внимание — это баланс белков, жиров и углеводов.
                    Каждый из этих макронутриентов играет свою роль. Белки нужны для построения
                    мышц и восстановления тканей. Жиры важны для гормональной системы. А углеводы
                    дают нам энергию на протяжении всего дня.

                    Также не забывайте про витамины и минералы. Они участвуют во всех процессах
                    организма. Рекомендую обратить внимание на продукты Herbalife Nutrition для
                    полноценного питания.

                    В заключение хочу сказать, что правильное питание — это не диета. Это образ
                    жизни. Найдите баланс, который работает именно для вас.
                    """

                    cleaned_transcript = CleanedTranscript(
                        text=mock_text.strip(),
                        original_length=len(mock_text),
                        cleaned_length=len(mock_text.strip()),
                        corrections_made=[],
                        model_name=settings.cleaner_model,
                    )

                    # Test with full transcript (no outline - small text mode)
                    result = await summarizer.summarize(
                        outline=None,
                        metadata=mock_metadata,
                        cleaned_transcript=cleaned_transcript,
                    )

                    assert result.summary, "Summary is empty"
                    assert result.section in VALID_SECTIONS, f"Invalid section: {result.section}"
                    assert 1 <= result.access_level <= 4, f"Invalid access_level: {result.access_level}"

                    print("OK")
                    print(f"  Summary: {result.summary[:100]}...")
                    print(f"  Key points: {len(result.key_points)}")
                    print(f"  Section: {result.section}")
                    print(f"  Tags: {result.tags}")
                    print(f"  Access level: {result.access_level}")

                except Exception as e:
                    print(f"FAILED: {e}")
                    import traceback
                    traceback.print_exc()
                    return 1

        print("\n" + "=" * 40)
        print("All tests passed!")
        return 0

    sys.exit(asyncio.run(run_tests()))
