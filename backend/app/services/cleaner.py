"""
Transcript cleaner service.

Cleans raw transcripts using glossary term replacement and Ollama LLM.
"""

import logging
import re
import time

from app.config import Settings, get_settings, load_glossary, load_prompt
from app.models.schemas import CleanedTranscript, RawTranscript, VideoMetadata
from app.services.ai_client import AIClient

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("app.perf")


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
        self.prompt_template = load_prompt("cleaner", settings)
        self.glossary = load_glossary(settings)

    async def clean(
        self,
        raw_transcript: RawTranscript,
        metadata: VideoMetadata,
    ) -> CleanedTranscript:
        """
        Clean raw transcript.

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
            f"{len(raw_transcript.segments)} segments"
        )

        start_time = time.time()

        # Step 1: Apply glossary replacements
        text_after_glossary, corrections = self._apply_glossary(original_text)
        logger.debug(f"Glossary applied: {len(corrections)} corrections")

        # Step 2: Build prompt and call LLM
        prompt = self._build_prompt(text_after_glossary, metadata)
        cleaned_text = await self.ai_client.generate(prompt)

        elapsed = time.time() - start_time

        # Clean up LLM response (remove any leading/trailing whitespace)
        cleaned_text = cleaned_text.strip()
        cleaned_length = len(cleaned_text)

        logger.info(
            f"Cleaning complete: {original_length} -> {cleaned_length} chars "
            f"({100 - cleaned_length * 100 // original_length}% reduction)"
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

    def _build_prompt(self, text: str, metadata: VideoMetadata) -> str:
        """
        Build cleaning prompt from template.

        Args:
            text: Text to clean (after glossary processing)
            metadata: Video metadata (for context)

        Returns:
            Complete prompt for LLM
        """
        return self.prompt_template.format(transcript=text)


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

        # Test 3: Build prompt
        print("\nTest 3: Build prompt...", end=" ")
        try:
            prompt = cleaner._build_prompt("Test transcript text", None)  # type: ignore
            assert "Test transcript text" in prompt, "Transcript not in prompt"
            assert len(prompt) > 100, "Prompt too short"
            print("OK")
            print(f"  Prompt length: {len(prompt)} chars")
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
