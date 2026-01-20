"""
Semantic chunker service.

Splits cleaned transcripts into semantic chunks using Ollama LLM.

For large transcripts (>10K chars), uses Map-Reduce approach:
1. Splits text into overlapping parts (TextSplitter)
2. Extracts outline from each part in parallel (OutlineExtractor)
3. Uses combined outline as context for better chunking

This provides global context awareness for long videos while
maintaining stable performance on limited server resources.
"""

import logging
import time

from app.config import Settings, get_settings, load_model_config, load_prompt
from app.models.schemas import (
    CleanedTranscript,
    TextPart,
    TranscriptChunk,
    TranscriptChunks,
    TranscriptOutline,
    VideoMetadata,
)
from app.services.ai_client import AIClient
from app.services.outline_extractor import OutlineExtractor
from app.services.text_splitter import TextSplitter
from app.utils.chunk_utils import generate_chunk_id, validate_cyrillic_ratio
from app.utils.json_utils import extract_json, parse_json_safe
from app.utils.token_utils import calculate_num_predict_from_chars

# Default configuration (overridden by models.yaml)
DEFAULT_LARGE_TEXT_THRESHOLD = 10000
DEFAULT_MIN_CHUNK_WORDS = 100
DEFAULT_TARGET_CHUNK_WORDS = 250

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("app.perf")


class SemanticChunker:
    """
    Semantic chunking service using Ollama LLM.

    Splits cleaned transcripts into self-contained semantic chunks
    optimized for RAG search (100-400 words each).

    For large texts (>10K chars), uses Map-Reduce approach:
    1. Splits text into overlapping parts
    2. Extracts outline from each part
    3. Uses outline as context for chunking

    Example:
        async with AIClient(settings) as client:
            chunker = SemanticChunker(client, settings)
            chunks = await chunker.chunk(cleaned_transcript, metadata)
            print(f"Created {chunks.total_chunks} chunks")
    """

    def __init__(self, ai_client: AIClient, settings: Settings):
        """
        Initialize chunker.

        Args:
            ai_client: AI client for LLM calls
            settings: Application settings
        """
        self.ai_client = ai_client
        self.settings = settings
        self.prompt_template = load_prompt("chunker", settings.chunker_model, settings)

        # Load model-specific chunking configuration
        chunker_config = load_model_config(settings.chunker_model, "chunker", settings)
        self.large_text_threshold = chunker_config.get(
            "large_text_threshold", DEFAULT_LARGE_TEXT_THRESHOLD
        )
        self.min_chunk_words = chunker_config.get(
            "min_chunk_words", DEFAULT_MIN_CHUNK_WORDS
        )
        self.target_chunk_words = chunker_config.get(
            "target_chunk_words", DEFAULT_TARGET_CHUNK_WORDS
        )

        # Load text_splitter config and create component
        splitter_config = load_model_config(
            settings.chunker_model, "text_splitter", settings
        )
        self.text_splitter = TextSplitter(
            part_size=splitter_config.get("part_size", 6000),
            overlap_size=splitter_config.get("overlap_size", 1500),
            min_part_size=splitter_config.get("min_part_size", 2000),
        )
        self.outline_extractor = OutlineExtractor(ai_client, settings)

    async def chunk(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
        text_parts: list[TextPart] | None = None,
        outline: TranscriptOutline | None = None,
    ) -> TranscriptChunks:
        """
        Split cleaned transcript into semantic chunks.

        For large texts (>10K chars), uses Map-Reduce approach:
        1. Splits text into overlapping parts
        2. Extracts outline from each part
        3. Uses outline as context for better chunking

        When text_parts and outline are provided (from pipeline),
        skips splitting and outline extraction to avoid duplication.

        Args:
            cleaned_transcript: Cleaned transcript from cleaner service
            metadata: Video metadata (for chunk IDs)
            text_parts: Pre-split text parts (optional, extracted if not provided)
            outline: Pre-extracted outline (optional, extracted for large texts)

        Returns:
            TranscriptChunks with list of semantic chunks
        """
        text = cleaned_transcript.text
        input_chars = len(text)
        word_count = len(text.split())

        start_time = time.time()

        # Split text if not provided
        if text_parts is None:
            text_parts = self.text_splitter.split(text)

        # Extract outline for large texts if not provided
        if outline is None and input_chars > self.large_text_threshold:
            logger.info(
                f"Large text detected ({input_chars} chars), "
                f"extracting outline from {len(text_parts)} parts"
            )
            outline = await self.outline_extractor.extract(text_parts)
            logger.info(
                f"Outline extracted: {outline.total_parts} parts, "
                f"{len(outline.all_topics)} unique topics"
            )
            logger.info(
                f"Chunking transcript: {input_chars} chars, {word_count} words"
            )
        elif outline is not None and outline.total_parts > 0:
            logger.info(
                f"Chunking with pre-extracted outline: {input_chars} chars, "
                f"{len(text_parts)} parts, {len(outline.all_topics)} topics"
            )
        else:
            logger.info(
                f"Chunking transcript: {input_chars} chars, {word_count} words"
            )

        # Process each part and collect all chunks
        all_chunks = await self._process_parts(text_parts, outline, metadata.video_id)

        # Log total before merge
        logger.info(
            f"Total chunks before merge: {len(all_chunks)}, "
            f"total words: {sum(c.word_count for c in all_chunks)}"
        )

        # Validate and merge small chunks
        all_chunks = self._validate_and_merge_chunks(all_chunks, metadata.video_id)

        elapsed = time.time() - start_time

        result = TranscriptChunks(
            chunks=all_chunks,
            model_name=self.settings.chunker_model,
        )

        logger.info(
            f"Chunking complete: {result.total_chunks} chunks, "
            f"avg size {result.avg_chunk_size} words"
        )

        # Performance metrics for progress estimation
        perf_logger.info(
            f"PERF | chunk | "
            f"input_chars={input_chars} | "
            f"chunks={result.total_chunks} | "
            f"time={elapsed:.1f}s"
        )

        return result

    async def chunk_with_outline(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
        text_parts: list[TextPart],
        outline: TranscriptOutline | None,
    ) -> TranscriptChunks:
        """
        Split transcript into chunks using pre-extracted outline.

        Deprecated: Use chunk() with text_parts and outline parameters instead.
        Kept for backward compatibility with existing pipeline code.

        Args:
            cleaned_transcript: Cleaned transcript from cleaner service
            metadata: Video metadata (for chunk IDs)
            text_parts: Pre-split text parts from TextSplitter
            outline: Pre-extracted outline (None for small texts)

        Returns:
            TranscriptChunks with list of semantic chunks
        """
        return await self.chunk(
            cleaned_transcript=cleaned_transcript,
            metadata=metadata,
            text_parts=text_parts,
            outline=outline,
        )

    async def _process_parts(
        self,
        text_parts: list[TextPart],
        outline: TranscriptOutline | None,
        video_id: str,
    ) -> list[TranscriptChunk]:
        """
        Process text parts and collect chunks.

        Args:
            text_parts: List of text parts to process
            outline: Optional outline for context
            video_id: Video ID for chunk IDs

        Returns:
            List of all chunks from all parts
        """
        all_chunks: list[TranscriptChunk] = []
        model = self.settings.chunker_model

        for part in text_parts:
            if len(text_parts) > 1:
                logger.debug(
                    f"Chunking part {part.index}/{len(text_parts)}: "
                    f"{part.char_count} chars"
                )

            prompt = self._build_prompt(part.text, outline)

            # Diagnostic: prompt size for context overflow debugging
            logger.info(
                f"Part {part.index}/{len(text_parts)}: "
                f"prompt={len(prompt)} chars (~{len(prompt)//3} tokens), "
                f"text={part.char_count} chars"
            )

            # Dynamic num_predict based on text size
            # Chunker copies entire text to output, needs large num_predict
            num_predict = calculate_num_predict_from_chars(
                part.char_count, task="chunker"
            )

            response = await self.ai_client.generate(
                prompt, model=model, num_predict=num_predict
            )

            # Check for empty response with diagnostics
            if not response or not response.strip():
                logger.error(
                    f"Part {part.index}: Empty LLM response. "
                    f"Prompt: {len(prompt)} chars (~{len(prompt)//3} tokens), "
                    f"Model: {model}"
                )
                raise ValueError(
                    f"LLM returned empty response for part {part.index}. "
                    f"Prompt size: {len(prompt)} chars (~{len(prompt)//3} tokens). "
                    f"May exceed model context window."
                )

            # Parse chunks from this part
            part_chunks = self._parse_chunks(
                response, video_id, index_offset=len(all_chunks)
            )

            # Fallback: create simple word-based chunks if parsing failed
            if not part_chunks:
                logger.warning(f"Part {part.index}: using fallback chunking")
                part_chunks = self._create_fallback_part_chunks(
                    part.text, video_id, index_offset=len(all_chunks)
                )

            all_chunks.extend(part_chunks)

            # Log chunk sizes for debugging
            logger.info(
                f"Part {part.index}/{len(text_parts)}: {len(part_chunks)} chunks, "
                f"sizes: {[c.word_count for c in part_chunks]}"
            )

        return all_chunks

    def _build_prompt(
        self, text: str, outline: TranscriptOutline | None = None
    ) -> str:
        """
        Build chunking prompt from template with optional outline context.

        Args:
            text: Cleaned transcript text (or part of it)
            outline: Optional TranscriptOutline for context (for large texts)

        Returns:
            Complete prompt for LLM
        """
        prompt = self.prompt_template

        # Add context from outline if available
        if outline and outline.total_parts > 0:
            context = outline.to_context()
            prompt = prompt.replace("{context}", context)
        else:
            prompt = prompt.replace("{context}", "")

        # Use replace() instead of format() because the prompt contains
        # JSON examples with curly braces that would confuse str.format()
        return prompt.replace("{transcript}", text)

    def _parse_chunks(
        self, response: str, video_id: str, index_offset: int = 0
    ) -> list[TranscriptChunk]:
        """
        Parse LLM response into TranscriptChunk objects.

        Args:
            response: Raw LLM response (JSON or markdown-wrapped JSON)
            video_id: Video ID for generating chunk IDs
            index_offset: Offset for chunk indices (when processing in parts)

        Returns:
            List of TranscriptChunk objects
        """
        # Check for empty response - return empty list for fallback
        if not response or not response.strip():
            logger.warning("LLM returned empty response - will use fallback chunking")
            return []

        # Extract JSON from response (handles markdown code blocks)
        json_str = extract_json(response, json_type="array")

        # Check if extraction found anything - return empty list for fallback
        if not json_str or not json_str.strip():
            logger.warning(
                f"Could not extract JSON from response, will use fallback: "
                f"{response[:200]}..."
            )
            return []

        # Parse JSON with safe parser
        data = parse_json_safe(json_str, default=None, log_errors=True)

        if data is None:
            logger.warning("Failed to parse JSON, will use fallback chunking")
            return []

        # Validate it's a list - return empty for fallback
        if not isinstance(data, list):
            logger.warning(
                f"Expected JSON array, got {type(data).__name__}, will use fallback"
            )
            return []

        # Convert to TranscriptChunk objects
        chunks = []
        for item in data:
            # Calculate actual index with offset
            local_index = item.get("index", len(chunks) + 1)
            actual_index = index_offset + local_index

            topic = item.get("topic", "")
            text = item.get("text", "")

            # Validate: text should be Russian (from transcript, not generated)
            cyrillic_ratio = validate_cyrillic_ratio(text)
            if cyrillic_ratio < 0.5:
                logger.error(
                    f"Chunk {actual_index} has non-Russian text "
                    f"(cyrillic={cyrillic_ratio:.0%}): {text[:100]}..."
                )

            chunk = TranscriptChunk(
                id=generate_chunk_id(video_id, actual_index),
                index=actual_index,
                topic=topic,
                text=text,
                word_count=len(text.split()),
            )
            chunks.append(chunk)

        return chunks

    def _validate_and_merge_chunks(
        self, chunks: list[TranscriptChunk], video_id: str
    ) -> list[TranscriptChunk]:
        """
        Validate chunk sizes and merge small chunks into groups.

        LLM sometimes ignores size requirements and creates tiny chunks.
        This method merges chunks smaller than self.min_chunk_words into groups
        of self.target_chunk_words to ensure meaningful semantic units.

        Args:
            chunks: List of parsed chunks
            video_id: Video ID for regenerating chunk IDs

        Returns:
            List of validated chunks with small ones merged into groups
        """
        if not chunks:
            return chunks

        # Count small chunks for logging
        small_count = sum(
            1 for c in chunks if c.word_count < self.min_chunk_words
        )
        if small_count > 0:
            logger.warning(
                f"Found {small_count}/{len(chunks)} chunks with "
                f"< {self.min_chunk_words} words, merging"
            )

        merged: list[TranscriptChunk] = []
        pending_text = ""
        pending_topic = ""
        pending_words = 0

        for chunk in chunks:
            if chunk.word_count < self.min_chunk_words:
                # Accumulate small chunk
                if pending_text:
                    pending_text += " " + chunk.text
                else:
                    pending_text = chunk.text
                    pending_topic = chunk.topic
                pending_words += chunk.word_count

                # If accumulated enough, create merged chunk
                if pending_words >= self.target_chunk_words:
                    merged.append(
                        TranscriptChunk(
                            id="",
                            index=0,
                            topic=pending_topic,
                            text=pending_text,
                            word_count=pending_words,
                        )
                    )
                    pending_text = ""
                    pending_topic = ""
                    pending_words = 0
            else:
                # Normal sized chunk - flush pending first
                if pending_text:
                    merged.append(
                        TranscriptChunk(
                            id="",
                            index=0,
                            topic=pending_topic,
                            text=pending_text,
                            word_count=pending_words,
                        )
                    )
                    pending_text = ""
                    pending_topic = ""
                    pending_words = 0
                merged.append(chunk)

        # Handle any remaining pending text
        if pending_text:
            if merged and pending_words < self.min_chunk_words:
                # Append to last chunk if too small
                last = merged[-1]
                combined_text = last.text + " " + pending_text
                merged[-1] = TranscriptChunk(
                    id="",
                    index=0,
                    topic=last.topic,
                    text=combined_text,
                    word_count=len(combined_text.split()),
                )
            else:
                # Keep as separate chunk
                merged.append(
                    TranscriptChunk(
                        id="",
                        index=0,
                        topic=pending_topic,
                        text=pending_text,
                        word_count=pending_words,
                    )
                )

        # Reassign indices and IDs
        for i, chunk in enumerate(merged):
            new_index = i + 1
            merged[i] = TranscriptChunk(
                id=generate_chunk_id(video_id, new_index),
                index=new_index,
                topic=chunk.topic,
                text=chunk.text,
                word_count=chunk.word_count,
            )

        if len(merged) < len(chunks):
            logger.info(
                f"Merged small chunks: {len(chunks)} -> {len(merged)} chunks"
            )

        return merged

    def _create_fallback_part_chunks(
        self,
        text: str,
        video_id: str,
        index_offset: int = 0,
    ) -> list[TranscriptChunk]:
        """
        Create fallback chunks when LLM parsing fails for a text part.

        Simply splits text into fixed-size chunks (~300 words) without
        semantic analysis. Used as graceful degradation when LLM fails.

        Args:
            text: Text to chunk
            video_id: Video ID for generating chunk IDs
            index_offset: Offset for chunk indices

        Returns:
            List of TranscriptChunk objects
        """
        words = text.split()
        chunk_size = self.target_chunk_words or 300
        chunks: list[TranscriptChunk] = []

        for i, start in enumerate(range(0, len(words), chunk_size)):
            chunk_words = words[start : start + chunk_size]
            chunk_text = " ".join(chunk_words)
            actual_index = index_offset + i + 1

            chunks.append(
                TranscriptChunk(
                    id=generate_chunk_id(video_id, actual_index),
                    index=actual_index,
                    topic=f"Часть {actual_index}",
                    text=chunk_text,
                    word_count=len(chunk_words),
                )
            )

        logger.info(f"Created {len(chunks)} fallback chunks from {len(words)} words")
        return chunks


if __name__ == "__main__":
    """Run tests when executed directly."""
    import asyncio
    import sys
    from datetime import date
    from pathlib import Path

    # Configure logging for tests
    logging.basicConfig(level=logging.INFO)

    async def run_tests():
        """Run all chunker tests."""
        print("\nRunning chunker tests...\n")

        settings = get_settings()

        # Test 1: Load prompt
        print("Test 1: Load prompt...", end=" ")
        try:
            prompt = load_prompt("chunker", settings.chunker_model, settings)
            assert "{transcript}" in prompt, "Prompt missing {transcript} placeholder"
            assert "{context}" in prompt, "Prompt missing {context} placeholder"
            assert len(prompt) > 100, "Prompt too short"
            print("OK")
            print(f"  Prompt length: {len(prompt)} chars")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 2: Extract JSON using shared utils
        print("\nTest 2: Extract JSON (shared utils)...", end=" ")
        try:
            plain_json = '[{"index": 1, "topic": "Test", "text": "Hello"}]'
            extracted = extract_json(plain_json, json_type="array")
            assert extracted == plain_json, f"Expected {plain_json}, got {extracted}"
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 3: Extract JSON from markdown-wrapped response
        print("\nTest 3: Extract JSON (markdown)...", end=" ")
        try:
            markdown_json = (
                '```json\n[{"index": 1, "topic": "Test", "text": "Hello"}]\n```'
            )
            extracted = extract_json(markdown_json, json_type="array")
            assert "[" in extracted and "]" in extracted, "JSON markers missing"
            assert "```" not in extracted, "Markdown markers not removed"
            print("OK")
            print(f"  Extracted: {extracted}")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 4: Parse chunks
        print("\nTest 4: Parse chunks...", end=" ")
        try:
            chunker = SemanticChunker(None, settings)  # type: ignore

            test_json = """[
                {"index": 1, "topic": "Первая тема", "text": "Это текст первого чанка с несколькими словами."},
                {"index": 2, "topic": "Вторая тема", "text": "А это текст второго чанка."}
            ]"""

            chunks = chunker._parse_chunks(test_json, "test-video-id")

            assert len(chunks) == 2, f"Expected 2 chunks, got {len(chunks)}"
            assert chunks[0].id == "test-video-id_001", f"Wrong ID: {chunks[0].id}"
            assert chunks[0].topic == "Первая тема"
            assert chunks[0].word_count > 0
            assert chunks[1].index == 2

            print("OK")
            print(
                f"  Chunk 1: {chunks[0].id} - {chunks[0].topic} "
                f"({chunks[0].word_count} words)"
            )
            print(
                f"  Chunk 2: {chunks[1].id} - {chunks[1].topic} "
                f"({chunks[1].word_count} words)"
            )
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 5: Full chunking with LLM (if available)
        print("\nTest 5: Full chunking with LLM...", end=" ")
        async with AIClient(settings) as client:
            status = await client.check_services()

            if not status["ollama"]:
                print("SKIPPED (Ollama unavailable)")
            else:
                try:
                    chunker = SemanticChunker(client, settings)

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

                    # Create a mock cleaned transcript (realistic length)
                    mock_text = """
                    Сегодня мы поговорим о важности правильного питания. Это ключевой фактор
                    для здоровья и хорошего самочувствия. Многие люди недооценивают роль питания
                    в их повседневной жизни. Но на самом деле это основа всего.

                    Первое, на что стоит обратить внимание — это баланс белков, жиров и углеводов.
                    Каждый из этих макронутриентов играет свою роль. Белки нужны для построения
                    мышц и восстановления тканей. Жиры важны для гормональной системы. А углеводы
                    дают нам энергию на протяжении всего дня.

                    Также не забывайте про витамины и минералы. Они участвуют во всех процессах
                    организма. Без них невозможно нормальное функционирование. Поэтому важно
                    есть разнообразную пищу и при необходимости принимать добавки.

                    В заключение хочу сказать, что правильное питание — это не диета. Это образ
                    жизни. Не нужно ограничивать себя жёстко. Нужно найти баланс, который работает
                    именно для вас. И тогда вы увидите результаты.
                    """

                    cleaned_transcript = CleanedTranscript(
                        text=mock_text.strip(),
                        original_length=len(mock_text),
                        cleaned_length=len(mock_text.strip()),
                        corrections_made=[],
                        model_name=settings.cleaner_model,
                    )

                    result = await chunker.chunk(cleaned_transcript, mock_metadata)

                    assert result.total_chunks > 0, "No chunks created"
                    assert result.avg_chunk_size > 0, "Average size is 0"

                    print("OK")
                    print(f"  Total chunks: {result.total_chunks}")
                    print(f"  Average size: {result.avg_chunk_size} words")
                    for chunk in result.chunks:
                        print(
                            f"  - {chunk.id}: {chunk.topic} ({chunk.word_count} words)"
                        )

                except Exception as e:
                    print(f"FAILED: {e}")
                    return 1

        print("\n" + "=" * 40)
        print("All tests passed!")
        return 0

    sys.exit(asyncio.run(run_tests()))
