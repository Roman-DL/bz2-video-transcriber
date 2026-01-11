"""
Outline extractor for transcript parts using Map-Reduce pattern.

Extracts structured outline from each part using LLM (MAP phase),
then combines into unified transcript outline with topic deduplication (REDUCE phase).

Used to provide global context for chunking long transcripts.

Configuration:
    MAX_PARALLEL_LLM_REQUESTS: Maximum concurrent LLM requests (Semaphore)
    TOPIC_SIMILARITY_THRESHOLD: Jaccard similarity threshold for deduplication
"""

import asyncio
import json
import logging
import re
import time

from app.config import Settings, load_prompt
from app.models.schemas import PartOutline, TextPart, TranscriptOutline
from app.services.ai_client import AIClient

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("app.perf")

# Configuration
MAX_PARALLEL_LLM_REQUESTS = 2  # Semaphore limit for stability
TOPIC_SIMILARITY_THRESHOLD = 0.6  # Jaccard similarity for topic deduplication


class OutlineExtractor:
    """
    Extract and combine outlines from transcript parts.

    Uses Map-Reduce pattern:
    1. MAP: Extract outline from each part in parallel (with Semaphore limit)
    2. REDUCE: Combine outlines with topic deduplication

    Example:
        async with AIClient(settings) as client:
            extractor = OutlineExtractor(client, settings)
            parts = text_splitter.split(text)
            outline = await extractor.extract(parts)
            context = outline.to_context()
    """

    def __init__(
        self,
        ai_client: AIClient,
        settings: Settings,
        max_parallel: int = MAX_PARALLEL_LLM_REQUESTS,
    ):
        """
        Initialize extractor.

        Args:
            ai_client: AI client for LLM calls
            settings: Application settings
            max_parallel: Maximum concurrent LLM requests
        """
        self.ai_client = ai_client
        self.settings = settings
        self.max_parallel = max_parallel
        self.prompt_template = load_prompt("map_outline", settings)

    async def extract(self, parts: list[TextPart]) -> TranscriptOutline:
        """
        Extract combined outline from all parts.

        Processes parts in parallel (with Semaphore limit), then reduces.

        Args:
            parts: List of text parts from TextSplitter

        Returns:
            Combined TranscriptOutline with deduplicated topics
        """
        if not parts:
            return TranscriptOutline(parts=[], all_topics=[])

        logger.info(
            f"Extracting outlines from {len(parts)} parts "
            f"(max {self.max_parallel} parallel)"
        )

        start_time = time.time()

        # MAP phase: extract outlines with limited parallelism
        part_outlines = await self._extract_parallel(parts)

        # REDUCE phase: combine with deduplication
        combined = self._reduce(part_outlines)

        elapsed = time.time() - start_time

        logger.info(
            f"Outline extraction complete: {len(combined.all_topics)} unique topics "
            f"from {len(parts)} parts"
        )

        perf_logger.info(
            f"PERF | outline_extract | "
            f"parts={len(parts)} | "
            f"topics={len(combined.all_topics)} | "
            f"time={elapsed:.1f}s"
        )

        return combined

    async def extract_part_outline(
        self, part: TextPart, total_parts: int
    ) -> PartOutline:
        """
        Extract outline from a single part.

        Args:
            part: Text part to process
            total_parts: Total number of parts (for context in prompt)

        Returns:
            PartOutline with topics, key_points, summary
        """
        prompt = self._build_prompt(part, total_parts)

        try:
            response = await self.ai_client.generate(prompt)
            outline = self._parse_outline(response, part.index)

            logger.debug(
                f"Part {part.index} outline: {len(outline.topics)} topics, "
                f"{len(outline.key_points)} key points"
            )

            return outline

        except Exception as e:
            logger.warning(
                f"Failed to extract outline for part {part.index}: {e}. "
                "Using fallback."
            )
            return self._create_fallback_outline(part)

    async def _extract_parallel(self, parts: list[TextPart]) -> list[PartOutline]:
        """
        Extract outlines from all parts with limited parallelism.

        Uses Semaphore to limit concurrent LLM requests for stability.

        Args:
            parts: List of text parts

        Returns:
            List of extracted outlines (in order)
        """
        semaphore = asyncio.Semaphore(self.max_parallel)
        total_parts = len(parts)

        async def limited_extract(part: TextPart) -> PartOutline:
            async with semaphore:
                logger.debug(f"Processing part {part.index}/{total_parts}")
                return await self.extract_part_outline(part, total_parts)

        tasks = [limited_extract(part) for part in parts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        outlines: list[PartOutline] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Part {i + 1} outline extraction failed: {result}")
                outlines.append(self._create_fallback_outline(parts[i]))
            else:
                outlines.append(result)

        return outlines

    def _reduce(self, outlines: list[PartOutline]) -> TranscriptOutline:
        """
        Combine part outlines into unified transcript outline.

        Deduplicates topics with Jaccard similarity threshold.

        Args:
            outlines: List of part outlines

        Returns:
            Combined TranscriptOutline
        """
        # Collect all topics with deduplication
        all_topics: list[str] = []

        for outline in outlines:
            for topic in outline.topics:
                if not self._is_duplicate_topic(topic, all_topics):
                    all_topics.append(topic)

        total_input_topics = sum(len(o.topics) for o in outlines)
        logger.debug(
            f"Reduced {total_input_topics} topics to {len(all_topics)} unique"
        )

        return TranscriptOutline(
            parts=outlines,
            all_topics=all_topics,
        )

    def _is_duplicate_topic(self, topic: str, existing_topics: list[str]) -> bool:
        """
        Check if topic is similar to existing ones using Jaccard similarity.

        Args:
            topic: New topic to check
            existing_topics: List of existing topics

        Returns:
            True if topic is a duplicate (similarity >= threshold)
        """
        topic_words = set(topic.lower().split())

        for existing in existing_topics:
            existing_words = set(existing.lower().split())

            # Skip empty sets
            if not topic_words or not existing_words:
                continue

            # Calculate Jaccard similarity: |intersection| / |union|
            intersection = len(topic_words & existing_words)
            union = len(topic_words | existing_words)
            similarity = intersection / union

            if similarity >= TOPIC_SIMILARITY_THRESHOLD:
                logger.debug(
                    f"Duplicate topic: '{topic}' ~ '{existing}' "
                    f"(similarity: {similarity:.2f})"
                )
                return True

        return False

    def _build_prompt(self, part: TextPart, total_parts: int) -> str:
        """
        Build outline extraction prompt.

        Args:
            part: Text part to process
            total_parts: Total number of parts

        Returns:
            Complete prompt for LLM
        """
        prompt = self.prompt_template

        # Replace placeholders
        prompt = prompt.replace("{part_index}", str(part.index))
        prompt = prompt.replace("{total_parts}", str(total_parts))
        prompt = prompt.replace("{text}", part.text)

        # Build overlap context
        overlap_context = ""
        if part.has_overlap_before:
            overlap_context += "Начало текста пересекается с предыдущей частью. "
        if part.has_overlap_after:
            overlap_context += "Конец текста пересекается со следующей частью."

        prompt = prompt.replace("{overlap_context}", overlap_context.strip())

        return prompt

    def _parse_outline(self, response: str, part_index: int) -> PartOutline:
        """
        Parse LLM response into PartOutline.

        Args:
            response: Raw LLM response
            part_index: Index of the part

        Returns:
            PartOutline instance

        Raises:
            ValueError: If JSON parsing fails
        """
        # Extract JSON from response
        json_str = self._extract_json(response)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse outline JSON: {e}")
            logger.debug(f"Response was: {response[:500]}...")
            raise ValueError(f"Invalid JSON in outline response: {e}")

        # Extract and validate fields
        topics = data.get("topics", [])
        key_points = data.get("key_points", [])
        summary = data.get("summary", "")

        # Limit to expected ranges
        topics = topics[:4] if topics else ["Часть " + str(part_index)]
        key_points = key_points[:5] if key_points else ["Содержание части"]
        summary = summary[:500] if summary else "Часть транскрипта"

        return PartOutline(
            part_index=part_index,
            topics=topics,
            key_points=key_points,
            summary=summary,
        )

    def _extract_json(self, text: str) -> str:
        """
        Extract JSON object from LLM response.

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
                # Find matching closing brace
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

    def _create_fallback_outline(self, part: TextPart) -> PartOutline:
        """
        Create fallback outline when extraction fails.

        Uses first sentence as summary and generic topic.

        Args:
            part: Text part

        Returns:
            Basic PartOutline
        """
        # Extract first sentence as summary
        sentences = part.text.split(". ")
        summary = sentences[0][:300] if sentences else part.text[:300]

        # Add period if missing
        if summary and not summary.endswith("."):
            summary += "."

        return PartOutline(
            part_index=part.index,
            topics=[f"Часть {part.index}"],
            key_points=["Содержание требует ручной обработки"],
            summary=summary,
        )


if __name__ == "__main__":
    """Run tests when executed directly."""
    import sys

    from app.config import get_settings
    from app.services.text_splitter import TextSplitter

    # Configure logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(name)s | %(message)s",
    )

    async def run_tests() -> int:
        """Run all OutlineExtractor tests."""
        print("\n" + "=" * 60)
        print("OutlineExtractor Tests")
        print("=" * 60)

        settings = get_settings()

        # Test 1: Load prompt
        print("\nTest 1: Load prompt...", end=" ")
        try:
            prompt = load_prompt("map_outline", settings)
            assert "{part_index}" in prompt, "Missing {part_index}"
            assert "{total_parts}" in prompt, "Missing {total_parts}"
            assert "{text}" in prompt, "Missing {text}"
            assert "{overlap_context}" in prompt, "Missing {overlap_context}"
            print("OK")
            print(f"  Prompt length: {len(prompt)} chars")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 2: JSON extraction
        print("\nTest 2: JSON extraction...", end=" ")
        try:
            # Create extractor without ai_client for unit tests
            extractor = OutlineExtractor(None, settings)  # type: ignore

            # Plain JSON
            plain = '{"topics": ["A"], "key_points": ["B"], "summary": "C"}'
            extracted = extractor._extract_json(plain)
            assert extracted == plain

            # Markdown wrapped
            markdown = '```json\n{"topics": ["A"], "key_points": ["B"], "summary": "C"}\n```'
            extracted = extractor._extract_json(markdown)
            assert "topics" in extracted
            assert "```" not in extracted

            # With preamble
            with_text = 'Here is the result:\n{"topics": ["A"], "key_points": ["B"], "summary": "C"}\nDone.'
            extracted = extractor._extract_json(with_text)
            assert extracted.startswith("{")
            assert extracted.endswith("}")

            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 3: Topic deduplication
        print("\nTest 3: Topic deduplication...", end=" ")
        try:
            extractor = OutlineExtractor(None, settings)  # type: ignore

            existing = ["Настройка продукта Формула", "Работа с клиентами"]

            # Should be duplicate (high similarity)
            assert extractor._is_duplicate_topic(
                "Настройка продукта Формула 1", existing
            ), "Should detect as duplicate"

            # Should not be duplicate (different topic)
            assert not extractor._is_duplicate_topic(
                "Маркетинговые стратегии", existing
            ), "Should not be duplicate"

            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 4: Fallback outline
        print("\nTest 4: Fallback outline...", end=" ")
        try:
            extractor = OutlineExtractor(None, settings)  # type: ignore

            part = TextPart(
                index=1,
                text="Первое предложение тестового текста. Второе предложение.",
                start_char=0,
                end_char=100,
                has_overlap_before=False,
                has_overlap_after=False,
            )

            fallback = extractor._create_fallback_outline(part)
            assert fallback.part_index == 1
            assert len(fallback.topics) > 0
            assert len(fallback.key_points) > 0
            assert len(fallback.summary) > 0

            print("OK")
            print(f"  Summary: {fallback.summary}")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 5: Reduce with deduplication
        print("\nTest 5: Reduce with deduplication...", end=" ")
        try:
            extractor = OutlineExtractor(None, settings)  # type: ignore

            outlines = [
                PartOutline(
                    part_index=1,
                    topics=["Продукт Формула", "Работа с клиентами"],
                    key_points=["Тезис 1"],
                    summary="Часть 1",
                ),
                PartOutline(
                    part_index=2,
                    topics=["Продукт Формула 1", "Маркетинг"],  # "Продукт Формула 1" similar
                    key_points=["Тезис 2"],
                    summary="Часть 2",
                ),
            ]

            combined = extractor._reduce(outlines)

            # Should have 3 unique topics (Формула deduplicated)
            assert len(combined.all_topics) == 3, (
                f"Expected 3 topics, got {len(combined.all_topics)}: {combined.all_topics}"
            )
            assert combined.total_parts == 2

            print("OK")
            print(f"  All topics: {combined.all_topics}")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 6: Full extraction with LLM (if available)
        print("\nTest 6: Full extraction with LLM...", end=" ")

        async with AIClient(settings) as client:
            status = await client.check_services()

            if not status["ollama"]:
                print("SKIPPED (Ollama unavailable)")
            else:
                try:
                    extractor = OutlineExtractor(client, settings)
                    splitter = TextSplitter(
                        part_size=500,  # Small for testing
                        overlap_size=100,
                        min_part_size=100,
                    )

                    # Create test text
                    test_text = """
                    Сегодня мы поговорим о правильном питании. Это важная тема для здоровья.
                    Белки необходимы для построения мышц. Рекомендуется употреблять 1.5 грамма на кг веса.
                    Жиры также важны для гормональной системы. Не все жиры одинаково полезны.
                    Углеводы дают энергию на весь день. Предпочтительны сложные углеводы.
                    Витамины и минералы участвуют во всех процессах организма.
                    Важно есть разнообразную пищу и при необходимости принимать добавки.
                    В заключение: правильное питание - это образ жизни, а не диета.
                    """

                    parts = splitter.split(test_text.strip())
                    outline = await extractor.extract(parts)

                    assert outline.total_parts > 0
                    assert len(outline.all_topics) > 0

                    print("OK")
                    print(f"  Parts: {outline.total_parts}")
                    print(f"  Topics: {outline.all_topics}")

                    # Print context preview
                    context = outline.to_context()
                    print(f"\n  Context preview ({len(context)} chars):")
                    for line in context.split("\n")[:10]:
                        print(f"    {line}")

                except Exception as e:
                    print(f"FAILED: {e}")
                    import traceback
                    traceback.print_exc()
                    return 1

        print("\n" + "=" * 60)
        print("All tests passed!")
        print("=" * 60)
        return 0

    sys.exit(asyncio.run(run_tests()))
