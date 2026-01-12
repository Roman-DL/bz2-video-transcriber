"""
Transcript cleaner service.

Cleans raw transcripts using glossary term replacement and Ollama LLM.
"""

import logging
import re
import time

from app.config import Settings, get_settings, load_glossary, load_model_config, load_prompt
from app.models.schemas import CleanedTranscript, RawTranscript, VideoMetadata
from app.services.ai_client import AIClient

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("app.perf")

# Default chunking configuration (overridden by models.yaml)
DEFAULT_CHUNK_SIZE = 3000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_SMALL_TEXT_THRESHOLD = 3500


class TranscriptCleaner:
    """
    Transcript cleaning service using glossary and Ollama LLM.

    Two-step cleaning process:
    1. Glossary: Replace term variations with canonical forms
    2. LLM: Remove filler words, fix speech errors, clean formatting

    Example:
        async with AIClient(settings) as client:
            cleaner = TranscriptCleaner(client, settings)
            cleaned = await cleaner.clean(raw_transcript, metadata)
            print(cleaned.text)
    """

    def __init__(self, ai_client: AIClient, settings: Settings):
        """
        Initialize cleaner.

        Args:
            ai_client: AI client for LLM calls
            settings: Application settings
        """
        self.ai_client = ai_client
        self.settings = settings
        self.system_prompt = load_prompt("cleaner_system", settings.cleaner_model, settings)
        self.user_template = load_prompt("cleaner_user", settings.cleaner_model, settings)
        self.glossary = load_glossary(settings)

        # Load model-specific chunking configuration
        config = load_model_config(settings.cleaner_model, "cleaner", settings)
        self.chunk_size = config.get("chunk_size", DEFAULT_CHUNK_SIZE)
        self.chunk_overlap = config.get("chunk_overlap", DEFAULT_CHUNK_OVERLAP)
        self.small_text_threshold = config.get("small_text_threshold", DEFAULT_SMALL_TEXT_THRESHOLD)

    async def clean(
        self,
        raw_transcript: RawTranscript,
        metadata: VideoMetadata,
    ) -> CleanedTranscript:
        """
        Clean raw transcript.

        For large texts (>10KB), uses chunked processing to avoid LLM
        summarizing instead of cleaning.

        Args:
            raw_transcript: Raw transcript from Whisper
            metadata: Video metadata

        Returns:
            CleanedTranscript with cleaned text and statistics
        """
        original_text = raw_transcript.full_text
        original_length = len(original_text)

        logger.info(
            f"Cleaning transcript: {original_length} chars, "
            f"{len(raw_transcript.segments)} segments, "
            f"model: {self.settings.cleaner_model}"
        )

        start_time = time.time()

        # Step 1: Apply glossary replacements
        text_after_glossary, corrections = self._apply_glossary(original_text)
        logger.debug(f"Glossary applied: {len(corrections)} corrections")

        # Step 2: Split into chunks if text is large
        chunks = self._split_into_chunks(text_after_glossary)

        if len(chunks) > 1:
            logger.info(f"Large text detected, processing in {len(chunks)} chunks")

        # Step 3: Process each chunk with LLM using chat API
        cleaned_chunks = []
        total_input_chars = 0
        total_output_chars = 0

        for i, chunk in enumerate(chunks):
            user_content = self.user_template.format(transcript=chunk)

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_content},
            ]

            # Estimate output tokens: ~2 chars per token, expect 80-95% of input
            num_predict = max(int(len(chunk) * 0.5), 4096)

            chunk_result = await self.ai_client.chat(
                messages,
                model=self.settings.cleaner_model,  # gemma2:9b by default
                temperature=0.0,  # Deterministic output to prevent summarization
                num_predict=num_predict,
            )
            chunk_result = chunk_result.strip()

            # Detailed logging for each chunk
            input_len = len(chunk)
            output_len = len(chunk_result)
            chunk_reduction = (
                100 - (output_len * 100 // input_len) if input_len > 0 else 0
            )
            cyrillic_count = len(re.findall(r"[а-яА-ЯёЁ]", chunk_result))
            cyrillic_ratio = cyrillic_count / max(output_len, 1)

            total_input_chars += input_len
            total_output_chars += output_len

            # Always log each chunk stats
            logger.info(
                f"Chunk {i + 1}/{len(chunks)}: "
                f"{input_len} -> {output_len} chars ({chunk_reduction}% reduction), "
                f"cyrillic={cyrillic_ratio:.0%}"
            )

            # Log details for suspicious chunks
            if chunk_reduction > 30:
                logger.warning(
                    f"Chunk {i + 1} high reduction! "
                    f"Input start: {chunk[:100]}... | "
                    f"Output start: {chunk_result[:100]}..."
                )

            # Validation: fallback to original if LLM summarized instead of cleaning
            if chunk_reduction > 40 or cyrillic_ratio < 0.5:
                logger.error(
                    f"Chunk {i + 1} FAILED validation: "
                    f"reduction={chunk_reduction}%, cyrillic={cyrillic_ratio:.0%}. "
                    f"Using original text instead."
                )
                chunk_result = chunk
                # Recalculate stats for accurate totals
                total_output_chars = total_output_chars - output_len + len(chunk)

            cleaned_chunks.append(chunk_result)

        # Pre-merge statistics
        if len(chunks) > 1:
            overall_reduction = (
                100 - (total_output_chars * 100 // total_input_chars)
                if total_input_chars > 0
                else 0
            )
            logger.info(
                f"Pre-merge stats: total input={total_input_chars}, "
                f"total output={total_output_chars}, "
                f"overall reduction={overall_reduction}%"
            )

        # Step 4: Merge chunks (remove duplicates from overlap)
        if len(cleaned_chunks) > 1:
            pre_merge_total = sum(len(c) for c in cleaned_chunks)
            cleaned_text = self._merge_chunks(cleaned_chunks)
            post_merge_len = len(cleaned_text)
            merge_reduction = (
                100 - (post_merge_len * 100 // pre_merge_total)
                if pre_merge_total > 0
                else 0
            )
            logger.info(
                f"Merge: {pre_merge_total} -> {post_merge_len} chars "
                f"({merge_reduction}% removed as overlap)"
            )
        else:
            cleaned_text = cleaned_chunks[0] if cleaned_chunks else ""

        elapsed = time.time() - start_time

        # Clean up LLM response
        cleaned_text = cleaned_text.strip()
        cleaned_length = len(cleaned_text)

        # Validate reduction (realistic: 5-20%, max acceptable: 25%)
        reduction_percent = (
            100 - (cleaned_length * 100 // original_length)
            if original_length > 0
            else 0
        )

        if reduction_percent > 40:
            logger.error(
                f"Suspicious reduction: {reduction_percent}% - "
                f"likely summarization instead of cleaning"
            )
        elif reduction_percent > 25:
            logger.warning(
                f"High reduction: {reduction_percent}% - "
                f"possible content loss (expected 5-20%)"
            )

        logger.info(
            f"Cleaning complete: {original_length} -> {cleaned_length} chars "
            f"({reduction_percent}% reduction)"
        )

        # Performance metrics for progress estimation
        perf_logger.info(
            f"PERF | clean | "
            f"input_chars={original_length} | "
            f"output_chars={cleaned_length} | "
            f"time={elapsed:.1f}s"
        )

        return CleanedTranscript(
            text=cleaned_text,
            original_length=original_length,
            cleaned_length=cleaned_length,
            corrections_made=corrections,
            model_name=self.settings.cleaner_model,
        )

    def _apply_glossary(self, text: str) -> tuple[str, list[str]]:
        """
        Apply glossary term replacements.

        Replaces term variations with their canonical forms.
        Uses case-insensitive matching with word boundaries.

        Args:
            text: Input text

        Returns:
            Tuple of (processed text, list of corrections made)
        """
        corrections = []
        replacements = []

        # Collect all replacements from all categories
        # Skip metadata keys (version, date, total_terms)
        for category_name, terms in self.glossary.items():
            if not isinstance(terms, list):
                continue

            for term in terms:
                canonical = term.get("canonical")
                variations = term.get("variations", [])

                if not canonical or not variations:
                    continue

                for variation in variations:
                    # Skip if variation is the same as canonical
                    if variation.lower() == canonical.lower():
                        continue
                    replacements.append((variation, canonical))

        # Sort by length (longest first) to avoid partial replacements
        replacements.sort(key=lambda x: len(x[0]), reverse=True)

        # Apply replacements
        for variation, canonical in replacements:
            # Build regex pattern with word boundaries
            # Escape special regex characters in variation
            pattern = rf"\b{re.escape(variation)}\b"

            # Find matches before replacing
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            if matches:
                text = re.sub(pattern, canonical, text, flags=re.IGNORECASE)
                for match in matches:
                    corrections.append(f"{match} -> {canonical}")

        return text, corrections

    def _split_into_chunks(self, text: str) -> list[str]:
        """
        Split text into overlapping chunks for processing.

        Splits on sentence boundaries to avoid breaking mid-sentence.
        Only chunks if text exceeds small_text_threshold.

        Args:
            text: Full text to split

        Returns:
            List of text chunks (single item if text is small)
        """
        if len(text) <= self.small_text_threshold:
            return [text]

        chunks = []
        sentences = self._split_into_sentences(text)

        current_chunk: list[str] = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            # If adding this sentence exceeds chunk size, save current chunk
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))

                # Start new chunk with overlap (last N chars worth of sentences)
                overlap_length = 0
                overlap_sentences: list[str] = []
                for s in reversed(current_chunk):
                    if overlap_length + len(s) > self.chunk_overlap:
                        break
                    overlap_sentences.insert(0, s)
                    overlap_length += len(s)

                current_chunk = overlap_sentences
                current_length = overlap_length

            current_chunk.append(sentence)
            current_length += sentence_length

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        """
        Split text into sentences using regex.

        Handles Russian and English punctuation.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Split on sentence-ending punctuation followed by space or end
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _merge_chunks(self, chunks: list[str]) -> str:
        """
        Merge cleaned chunks, removing duplicate content from overlaps.

        Uses sentence matching to find where chunks overlap.

        Args:
            chunks: List of cleaned text chunks

        Returns:
            Merged text without duplicates
        """
        if not chunks:
            return ""

        if len(chunks) == 1:
            return chunks[0]

        result = chunks[0]

        for i in range(1, len(chunks)):
            current = chunks[i]

            # Find overlap by looking for common sentences
            overlap_found = False

            # Search in last ~800 chars of result
            search_window = min(len(result), 800)
            result_end = result[-search_window:]

            # Look for common sentence at start of current chunk
            sentences_in_current = self._split_into_sentences(current)

            for j, sentence in enumerate(sentences_in_current[:5]):  # Check first 5
                # Find if this sentence exists in result_end
                if sentence in result_end:
                    # Found overlap - append from next sentence
                    remaining = " ".join(sentences_in_current[j + 1 :])
                    if remaining:
                        result = result + " " + remaining
                    overlap_found = True
                    break

            if not overlap_found:
                # No overlap found - just append with space
                result = result + " " + current

        return result.strip()


if __name__ == "__main__":
    """Run tests when executed directly."""
    import asyncio
    import sys
    from datetime import date
    from pathlib import Path

    # Configure logging for tests
    logging.basicConfig(level=logging.INFO)

    async def run_tests():
        """Run all cleaner tests."""
        print("\nRunning cleaner tests...\n")

        settings = get_settings()

        # Test 1: Load glossary
        print("Test 1: Load glossary...", end=" ")
        try:
            glossary = load_glossary(settings)
            total_terms = 0
            categories = []
            for key, value in glossary.items():
                if isinstance(value, list):
                    total_terms += len(value)
                    categories.append(key)

            assert total_terms > 0, "Glossary is empty"
            print("OK")
            print(f"  Categories: {', '.join(categories)}")
            print(f"  Total terms: {total_terms}")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 2: Apply glossary
        print("\nTest 2: Apply glossary...", end=" ")
        try:
            cleaner = TranscriptCleaner(None, settings)  # type: ignore

            # Test with exact variations from glossary (case-insensitive)
            test_text = "Сегодня поговорим о гербалайф и формула один. Также расскажу про СВ и гет тим."
            processed, corrections = cleaner._apply_glossary(test_text)

            assert "Herbalife" in processed, f"Expected 'Herbalife' in: {processed}"
            assert "Формула 1" in processed, f"Expected 'Формула 1' in: {processed}"
            assert "Супервайзер" in processed, f"Expected 'Супервайзер' in: {processed}"
            assert len(corrections) > 0, "Expected some corrections"

            print("OK")
            print(f"  Input: {test_text}")
            print(f"  Output: {processed}")
            print(f"  Corrections: {corrections}")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 3: Load prompts (system + user)
        print("\nTest 3: Load prompts...", end=" ")
        try:
            assert len(cleaner.system_prompt) > 100, "System prompt too short"
            assert "{transcript}" in cleaner.user_template, "User template missing placeholder"
            user_content = cleaner.user_template.format(transcript="Test text")
            assert "Test text" in user_content, "User template not working"
            print("OK")
            print(f"  System prompt: {len(cleaner.system_prompt)} chars")
            print(f"  User template: {len(cleaner.user_template)} chars")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 4: Mock clean (without LLM)
        print("\nTest 4: Mock transcript parsing...", end=" ")
        try:
            from app.models.schemas import TranscriptSegment

            # Use exact glossary variations (nominative case)
            mock_segments = [
                TranscriptSegment(start=0.0, end=5.0, text="Ну вот, значит, сегодня поговорим о гербалайф."),
                TranscriptSegment(start=5.0, end=10.0, text="Формула один — это основной продукт. Также есть Ф2."),
            ]
            raw_transcript = RawTranscript(
                segments=mock_segments,
                language="ru",
                duration_seconds=10.0,
                whisper_model="large-v3",
            )

            # Just test glossary application on full_text
            processed, corrections = cleaner._apply_glossary(raw_transcript.full_text)
            assert "Herbalife" in processed, f"Expected 'Herbalife' in: {processed}"
            assert "Формула 1" in processed, f"Expected 'Формула 1' in: {processed}"
            assert "Формула 2" in processed, f"Expected 'Формула 2' in: {processed}"
            print("OK")
            print(f"  Original: {raw_transcript.full_text}")
            print(f"  After glossary: {processed}")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 5: Full clean with LLM (if available)
        print("\nTest 5: Full clean with LLM...", end=" ")
        async with AIClient(settings) as client:
            status = await client.check_services()

            if not status["ollama"]:
                print("SKIPPED (Ollama unavailable)")
            else:
                try:
                    cleaner = TranscriptCleaner(client, settings)

                    mock_metadata = VideoMetadata(
                        date=date(2025, 1, 8),
                        event_type="ПШ",
                        stream="SV",
                        title="Тестовое видео",
                        speaker="Тестовый Спикер",
                        original_filename="test.mp4",
                        video_id="test-video-id",
                        source_path=Path("/test/test.mp4"),
                        archive_path=Path("/archive/test"),
                    )

                    mock_segments = [
                        TranscriptSegment(
                            start=0.0,
                            end=5.0,
                            text="Ну вот, значит, э-э-э, сегодня мы поговорим о гербалайф.",
                        ),
                        TranscriptSegment(
                            start=5.0,
                            end=10.0,
                            text="Это, как бы, очень важная, ну, тема. Вы меня слышите?",
                        ),
                        TranscriptSegment(
                            start=10.0,
                            end=15.0,
                            text="Хорошо. Так вот, формула один — это основной продукт.",
                        ),
                    ]
                    raw_transcript = RawTranscript(
                        segments=mock_segments,
                        language="ru",
                        duration_seconds=15.0,
                        whisper_model="large-v3",
                    )

                    cleaned = await cleaner.clean(raw_transcript, mock_metadata)

                    assert cleaned.text, "Cleaned text is empty"
                    assert cleaned.original_length > 0
                    assert cleaned.cleaned_length > 0

                    print("OK")
                    print(f"  Original length: {cleaned.original_length}")
                    print(f"  Cleaned length: {cleaned.cleaned_length}")
                    print(f"  Corrections: {len(cleaned.corrections_made)}")
                    print(f"  Cleaned text preview: {cleaned.text[:200]}...")
                except Exception as e:
                    print(f"FAILED: {e}")
                    return 1

        print("\n" + "=" * 40)
        print("All tests passed!")
        return 0

    sys.exit(asyncio.run(run_tests()))
