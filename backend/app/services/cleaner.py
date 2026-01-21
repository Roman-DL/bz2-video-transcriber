"""
Transcript cleaner service.

Cleans raw transcripts using LLM with glossary context.
"""

import logging
import re
import time

from app.config import Settings, get_settings, load_glossary_text, load_model_config, load_prompt
from app.models.schemas import CleanedTranscript, RawTranscript, VideoMetadata
from app.services.ai_clients import BaseAIClient, OllamaClient

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("app.perf")

# Default chunking configuration (overridden by models.yaml)
DEFAULT_CHUNK_SIZE = 3000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_SMALL_TEXT_THRESHOLD = 3500


class TranscriptCleaner:
    """
    Transcript cleaning service using LLM with glossary context.

    Single-step cleaning process:
    - LLM receives glossary.yaml as context and performs:
      - Terminology correction (recognizes variations by sound/meaning)
      - Filler words removal
      - Speech error fixes

    Example:
        async with OllamaClient.from_settings(settings) as client:
            cleaner = TranscriptCleaner(client, settings)
            cleaned = await cleaner.clean(raw_transcript, metadata)
            print(cleaned.text)
    """

    def __init__(self, ai_client: BaseAIClient, settings: Settings):
        """
        Initialize cleaner.

        Args:
            ai_client: AI client for LLM calls
            settings: Application settings
        """
        self.ai_client = ai_client
        self.settings = settings
        self.system_prompt = load_prompt("cleaning", "system", settings.cleaner_model, settings)
        self.user_template = load_prompt("cleaning", "user", settings.cleaner_model, settings)
        self.glossary_text = load_glossary_text(settings)

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
        Clean raw transcript using LLM with glossary context.

        For large texts (>10KB), uses chunked processing to avoid LLM
        summarizing instead of cleaning. LLM receives glossary.yaml as
        context and performs terminology correction and filler removal.

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

        # Split into chunks if text is large
        chunks = self._split_into_chunks(original_text)

        if len(chunks) > 1:
            logger.info(f"Large text detected, processing in {len(chunks)} chunks")

        # Process each chunk with LLM using chat API (with glossary context)
        cleaned_chunks = []
        total_input_chars = 0
        total_output_chars = 0

        for i, chunk in enumerate(chunks):
            user_content = self.user_template.format(
                glossary=self.glossary_text,
                transcript=chunk,
            )

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
            model_name=self.settings.cleaner_model,
        )

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

        # Test 1: Load glossary text
        print("Test 1: Load glossary text...", end=" ")
        try:
            cleaner = TranscriptCleaner(None, settings)  # type: ignore
            assert len(cleaner.glossary_text) > 1000, "Glossary text too short"
            assert "canonical:" in cleaner.glossary_text, "Missing canonical field"
            assert "variations:" in cleaner.glossary_text, "Missing variations field"
            print("OK")
            print(f"  Glossary text: {len(cleaner.glossary_text)} chars")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 2: Load prompts (system + user)
        print("\nTest 2: Load prompts...", end=" ")
        try:
            assert len(cleaner.system_prompt) > 100, "System prompt too short"
            assert "{transcript}" in cleaner.user_template, "User template missing transcript placeholder"
            assert "{glossary}" in cleaner.user_template, "User template missing glossary placeholder"
            user_content = cleaner.user_template.format(
                glossary="test glossary",
                transcript="Test text",
            )
            assert "Test text" in user_content, "User template not working"
            assert "test glossary" in user_content, "Glossary not included"
            print("OK")
            print(f"  System prompt: {len(cleaner.system_prompt)} chars")
            print(f"  User template: {len(cleaner.user_template)} chars")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 3: Full clean with LLM (if available)
        print("\nTest 3: Full clean with LLM...", end=" ")
        async with OllamaClient.from_settings(settings) as client:
            status = await client.check_services()

            if not status["ollama"]:
                print("SKIPPED (Ollama unavailable)")
            else:
                try:
                    from app.models.schemas import TranscriptSegment

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

                    # Test with terminology variations that LLM should recognize
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
                    # LLM should have corrected terms
                    assert "Herbalife" in cleaned.text or "гербалайф" not in cleaned.text.lower(), \
                        "Expected Herbalife correction"

                    print("OK")
                    print(f"  Original length: {cleaned.original_length}")
                    print(f"  Cleaned length: {cleaned.cleaned_length}")
                    print(f"  Cleaned text preview: {cleaned.text[:200]}...")
                except Exception as e:
                    print(f"FAILED: {e}")
                    return 1

        print("\n" + "=" * 40)
        print("All tests passed!")
        return 0

    sys.exit(asyncio.run(run_tests()))
