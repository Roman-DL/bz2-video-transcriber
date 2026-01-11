"""
Text splitter with overlap for large transcript processing.

Splits text into parts with configurable overlap, cutting on sentence
boundaries to preserve semantic coherence. Used as first step in
Map-Reduce pipeline for outline extraction.

Configuration:
    PART_SIZE: Target size per part in characters (~8000)
    OVERLAP_SIZE: Overlap between adjacent parts (~1500)
    MIN_PART_SIZE: Minimum size for last part (merge if smaller)
"""

import logging
import re

from app.models.schemas import TextPart

logger = logging.getLogger(__name__)

# Configuration
# Уменьшено с 8000 для совместимости с контекстом gemma2:9b (8192 токена)
PART_SIZE = 6000  # Target size per part in characters (~2000 tokens)
OVERLAP_SIZE = 1500  # Overlap between adjacent parts (~20%)
MIN_PART_SIZE = 2000  # Minimum size for last part (merge if smaller)


class TextSplitter:
    """
    Split text into overlapping parts for parallel processing.

    Splits on sentence boundaries to preserve semantic coherence.
    Creates overlap regions to maintain context between parts.

    Example:
        splitter = TextSplitter()
        parts = splitter.split(long_text)
        for part in parts:
            print(f"Part {part.index}: {part.char_count} chars")
    """

    def __init__(
        self,
        part_size: int = PART_SIZE,
        overlap_size: int = OVERLAP_SIZE,
        min_part_size: int = MIN_PART_SIZE,
    ):
        """
        Initialize splitter with configuration.

        Args:
            part_size: Target size per part in characters
            overlap_size: Overlap between adjacent parts
            min_part_size: Minimum size for last part
        """
        self.part_size = part_size
        self.overlap_size = overlap_size
        self.min_part_size = min_part_size

    def split(self, text: str) -> list[TextPart]:
        """
        Split text into overlapping parts.

        For small texts (<= part_size), returns single part.
        For large texts, splits on sentence boundaries with overlap.

        Args:
            text: Full transcript text

        Returns:
            List of TextPart objects with overlap information
        """
        text = text.strip()

        if not text:
            return []

        # Text fits in single part
        if len(text) <= self.part_size:
            return [
                TextPart(
                    index=1,
                    text=text,
                    start_char=0,
                    end_char=len(text),
                    has_overlap_before=False,
                    has_overlap_after=False,
                )
            ]

        sentences = self._split_into_sentences(text)
        parts: list[TextPart] = []

        current_sentences: list[str] = []
        current_length = 0
        current_start = 0

        for sentence in sentences:
            sentence_length = len(sentence) + 1  # +1 for space between sentences

            # If adding this sentence exceeds max size and we have content, save part
            if current_length + sentence_length > self.part_size and current_sentences:
                # Create part from current sentences
                part_text = " ".join(current_sentences)
                parts.append(
                    TextPart(
                        index=len(parts) + 1,
                        text=part_text,
                        start_char=current_start,
                        end_char=current_start + len(part_text),
                        has_overlap_before=len(parts) > 0,
                        has_overlap_after=True,  # Will be corrected for last part
                    )
                )

                # Start new part with overlap from end of current
                overlap_sentences = self._get_overlap_sentences(
                    current_sentences, self.overlap_size
                )
                overlap_text = " ".join(overlap_sentences)

                # Calculate new start position (accounting for overlap)
                current_start = current_start + len(part_text) - len(overlap_text)
                current_sentences = overlap_sentences.copy()
                current_length = len(overlap_text)

            current_sentences.append(sentence)
            current_length += sentence_length

        # Handle last part
        if current_sentences:
            part_text = " ".join(current_sentences)

            # Check if last part is too small - merge with previous
            if len(part_text) < self.min_part_size and parts:
                prev_part = parts[-1]
                # Get new content (excluding overlap)
                new_content = self._remove_overlap(part_text, prev_part.text)
                merged_text = prev_part.text + " " + new_content

                parts[-1] = TextPart(
                    index=prev_part.index,
                    text=merged_text,
                    start_char=prev_part.start_char,
                    end_char=prev_part.start_char + len(merged_text),
                    has_overlap_before=prev_part.has_overlap_before,
                    has_overlap_after=False,
                )
                logger.debug(
                    f"Merged small last part ({len(part_text)} chars) "
                    f"into part {prev_part.index}"
                )
            else:
                parts.append(
                    TextPart(
                        index=len(parts) + 1,
                        text=part_text,
                        start_char=current_start,
                        end_char=current_start + len(part_text),
                        has_overlap_before=len(parts) > 0,
                        has_overlap_after=False,
                    )
                )

        # Correct has_overlap_after for last part (if not merged)
        if parts and parts[-1].has_overlap_after:
            last = parts[-1]
            parts[-1] = TextPart(
                index=last.index,
                text=last.text,
                start_char=last.start_char,
                end_char=last.end_char,
                has_overlap_before=last.has_overlap_before,
                has_overlap_after=False,
            )

        logger.info(
            f"Split text ({len(text)} chars) into {len(parts)} parts "
            f"with {self.overlap_size} char overlap"
        )

        return parts

    def _split_into_sentences(self, text: str) -> list[str]:
        """
        Split text into sentences, breaking long ones on commas.

        Handles common sentence-ending punctuation (. ! ?) followed by
        whitespace or end of string. For very long "sentences" (common with
        Whisper transcripts using commas instead of periods), further splits
        on commas.

        Args:
            text: Text to split

        Returns:
            List of sentences (stripped, non-empty)
        """
        # Split on sentence-ending punctuation followed by space
        raw_sentences = re.split(r"(?<=[.!?])\s+", text)

        sentences = []
        for s in raw_sentences:
            s = s.strip()
            if not s:
                continue
            # Если предложение слишком длинное — разбиваем по запятым
            if len(s) > self.part_size:
                # Разбиваем по запятым
                parts = re.split(r",\s*", s)
                sentences.extend(p.strip() for p in parts if p.strip())
            else:
                sentences.append(s)

        return sentences

    def _get_overlap_sentences(
        self, sentences: list[str], target_overlap: int
    ) -> list[str]:
        """
        Get sentences for overlap from end of part.

        Accumulates sentences from the end until reaching target overlap size.

        Args:
            sentences: All sentences in current part
            target_overlap: Target overlap size in characters

        Returns:
            List of sentences to include as overlap
        """
        overlap: list[str] = []
        overlap_length = 0

        for sentence in reversed(sentences):
            sentence_length = len(sentence) + 1  # +1 for space
            if overlap_length + sentence_length > target_overlap and overlap:
                break
            overlap.insert(0, sentence)
            overlap_length += sentence_length

        return overlap

    def _remove_overlap(self, text: str, prev_text: str) -> str:
        """
        Remove overlap region from start of text.

        Finds sentences in text that are also in prev_text (the overlap)
        and returns only the new content.

        Args:
            text: Current part text
            prev_text: Previous part text

        Returns:
            Text with overlap removed
        """
        sentences = self._split_into_sentences(text)

        # Find first sentence that's not in prev_text
        for i, sentence in enumerate(sentences):
            if sentence not in prev_text:
                return " ".join(sentences[i:])

        return text  # Fallback: return original if all sentences overlap


if __name__ == "__main__":
    """Run tests when executed directly."""
    import sys

    # Configure logging for tests
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)s | %(message)s",
    )

    def run_tests() -> int:
        """Run all TextSplitter tests."""
        print("\n" + "=" * 60)
        print("TextSplitter Tests")
        print("=" * 60)

        splitter = TextSplitter(
            part_size=200,  # Small size for testing
            overlap_size=50,
            min_part_size=40,
        )

        # Test 1: Empty text
        print("\nTest 1: Empty text...", end=" ")
        try:
            result = splitter.split("")
            assert result == [], f"Expected empty list, got {result}"
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 2: Small text (no split needed)
        print("\nTest 2: Small text (single part)...", end=" ")
        try:
            small_text = "This is a small text. It should not be split."
            result = splitter.split(small_text)
            assert len(result) == 1, f"Expected 1 part, got {len(result)}"
            assert result[0].text == small_text
            assert result[0].index == 1
            assert result[0].has_overlap_before is False
            assert result[0].has_overlap_after is False
            print("OK")
            print(f"  Part 1: {result[0].char_count} chars")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 3: Large text (multiple parts with overlap)
        print("\nTest 3: Large text (multiple parts)...", end=" ")
        try:
            # Create text with clear sentence boundaries
            sentences = [
                "First sentence about topic A.",
                "Second sentence continues topic A.",
                "Third sentence still on topic A.",
                "Fourth sentence starts topic B.",
                "Fifth sentence about topic B.",
                "Sixth sentence more on topic B.",
                "Seventh sentence new topic C.",
                "Eighth sentence about topic C.",
            ]
            large_text = " ".join(sentences)

            result = splitter.split(large_text)
            assert len(result) >= 2, f"Expected multiple parts, got {len(result)}"

            # Check overlap flags
            assert result[0].has_overlap_before is False
            assert result[0].has_overlap_after is True
            assert result[-1].has_overlap_before is True
            assert result[-1].has_overlap_after is False

            # Print parts for inspection
            print("OK")
            for part in result:
                overlap_info = []
                if part.has_overlap_before:
                    overlap_info.append("overlap_before")
                if part.has_overlap_after:
                    overlap_info.append("overlap_after")
                flags = f" ({', '.join(overlap_info)})" if overlap_info else ""
                print(f"  Part {part.index}: {part.char_count} chars{flags}")
                # Show first 50 chars
                preview = part.text[:50] + "..." if len(part.text) > 50 else part.text
                print(f"    Preview: {preview}")

        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 4: Sentence splitting
        print("\nTest 4: Sentence splitting...", end=" ")
        try:
            text = "First! Second? Third. Fourth."
            sentences = splitter._split_into_sentences(text)
            assert len(sentences) == 4, f"Expected 4 sentences, got {len(sentences)}"
            assert sentences[0] == "First!"
            assert sentences[1] == "Second?"
            assert sentences[2] == "Third."
            assert sentences[3] == "Fourth."
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 5: Overlap calculation
        print("\nTest 5: Overlap calculation...", end=" ")
        try:
            sentences = ["A.", "B.", "C.", "D.", "E."]
            # Target 10 chars overlap, each sentence is 2-3 chars
            overlap = splitter._get_overlap_sentences(sentences, 10)
            assert len(overlap) >= 2, f"Expected at least 2 sentences, got {overlap}"
            print("OK")
            print(f"  Input: {sentences}")
            print(f"  Overlap: {overlap}")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 6: Long sentence split by commas (Whisper artifact)
        print("\nTest 6: Long sentence with commas (Whisper artifact)...", end=" ")
        try:
            comma_splitter = TextSplitter(part_size=100)
            long_sentence = (
                "Это очень длинное предложение без точек, "
                "которое продолжается с запятыми, "
                "и ещё немного текста, "
                "и ещё больше текста здесь, "
                "потому что Whisper так делает."
            )
            sentences = comma_splitter._split_into_sentences(long_sentence)
            assert len(sentences) >= 3, f"Expected >=3 parts, got {len(sentences)}"
            print("OK")
            print(f"  Input: {len(long_sentence)} chars")
            print(f"  Output: {len(sentences)} parts")
            for i, s in enumerate(sentences[:3]):
                print(f"    Part {i+1}: {s[:40]}...")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 7: Real-world text with default settings
        print("\nTest 7: Real-world text (default settings)...", end=" ")
        try:
            real_splitter = TextSplitter()  # Default settings: 8000/1500/2000

            # Simulate ~20K chars text
            paragraph = (
                "Это параграф текста о важной теме. "
                "Здесь обсуждаются различные аспекты проблемы. "
                "Приводятся примеры и рекомендации. "
                "В конце делается вывод по теме. "
            )  # ~200 chars

            real_text = paragraph * 100  # ~20K chars

            result = real_splitter.split(real_text)
            assert len(result) >= 2, f"Expected multiple parts for 20K chars"

            # Check all parts are within limits
            for part in result:
                # Allow some slack for sentence boundaries
                assert part.char_count <= real_splitter.part_size + 500, (
                    f"Part {part.index} too large: {part.char_count}"
                )

            print("OK")
            print(f"  Input: {len(real_text)} chars")
            print(f"  Output: {len(result)} parts")
            total_overlap = sum(1 for p in result if p.has_overlap_before)
            print(f"  Parts with overlap: {total_overlap}")

        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        print("\n" + "=" * 60)
        print("All tests passed!")
        print("=" * 60)
        return 0

    sys.exit(run_tests())
