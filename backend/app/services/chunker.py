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

import json
import logging
import re
import time

from app.config import Settings, get_settings, load_prompt

# Configuration for handling large transcripts
LARGE_TEXT_THRESHOLD = 10000  # Above this - use outline extraction
MIN_CHUNK_WORDS = 50  # Minimum words per chunk (merge smaller ones)

from app.models.schemas import (
    CleanedTranscript,
    TranscriptChunk,
    TranscriptChunks,
    TranscriptOutline,
    VideoMetadata,
)
from app.services.ai_client import AIClient
from app.services.outline_extractor import OutlineExtractor
from app.services.text_splitter import TextSplitter

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
        self.prompt_template = load_prompt("chunker", settings)

        # Components for large text processing
        self.text_splitter = TextSplitter()
        self.outline_extractor = OutlineExtractor(ai_client, settings)

    async def chunk(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
    ) -> TranscriptChunks:
        """
        Split cleaned transcript into semantic chunks.

        For large texts (>10K chars), uses Map-Reduce approach:
        1. Splits text into overlapping parts
        2. Extracts outline from each part
        3. Uses outline as context for better chunking

        Args:
            cleaned_transcript: Cleaned transcript from cleaner service
            metadata: Video metadata (for chunk IDs)

        Returns:
            TranscriptChunks with list of semantic chunks
        """
        text = cleaned_transcript.text
        input_chars = len(text)
        word_count = len(text.split())

        logger.info(f"Chunking transcript: {input_chars} chars, {word_count} words")

        start_time = time.time()

        # Extract outline for large texts (Map-Reduce approach)
        outline: TranscriptOutline | None = None
        text_parts = self.text_splitter.split(text)

        if input_chars > LARGE_TEXT_THRESHOLD:
            logger.info(
                f"Large text detected ({input_chars} chars), "
                f"extracting outline from {len(text_parts)} parts"
            )
            outline = await self.outline_extractor.extract(text_parts)
            logger.info(
                f"Outline extracted: {outline.total_parts} parts, "
                f"{len(outline.all_topics)} unique topics"
            )

        # Process each part and collect all chunks
        all_chunks: list[TranscriptChunk] = []

        for part in text_parts:
            if len(text_parts) > 1:
                logger.debug(
                    f"Chunking part {part.index}/{len(text_parts)}: "
                    f"{part.char_count} chars"
                )

            prompt = self._build_prompt(part.text, outline)
            response = await self.ai_client.generate(prompt)

            # Parse chunks from this part
            part_chunks = self._parse_chunks(
                response, metadata.video_id, index_offset=len(all_chunks)
            )
            all_chunks.extend(part_chunks)

        # Validate and merge small chunks
        all_chunks = self._validate_and_merge_chunks(all_chunks, metadata.video_id)

        elapsed = time.time() - start_time

        result = TranscriptChunks(chunks=all_chunks)

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
        # Check for empty response
        if not response or not response.strip():
            logger.error("LLM returned empty response - text may be too large for model context")
            raise ValueError("LLM returned empty response - text may be too large")

        # Extract JSON from response (handles markdown code blocks)
        json_str = self._extract_json(response)

        # Check if extraction found anything
        if not json_str or not json_str.strip():
            logger.error(f"Could not extract JSON from response: {response[:500]}...")
            raise ValueError("Could not extract JSON from LLM response")

        # Parse JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.debug(f"Response was: {response[:500]}...")
            raise ValueError(f"Invalid JSON in LLM response: {e}")

        # Validate it's a list
        if not isinstance(data, list):
            raise ValueError(f"Expected JSON array, got {type(data).__name__}")

        # Convert to TranscriptChunk objects
        chunks = []
        for item in data:
            # Calculate actual index with offset
            local_index = item.get("index", len(chunks) + 1)
            actual_index = index_offset + local_index

            topic = item.get("topic", "")
            text = item.get("text", "")

            chunk = TranscriptChunk(
                id=f"{video_id}_{actual_index:03d}",
                index=actual_index,
                topic=topic,
                text=text,
                word_count=len(text.split()),
            )
            chunks.append(chunk)

        return chunks

    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from LLM response.

        Handles responses wrapped in markdown code blocks and
        finds JSON array even if surrounded by other text.

        Args:
            text: Raw LLM response

        Returns:
            Clean JSON string
        """
        cleaned = text.strip()

        # Try to extract from markdown code block first
        code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
        if code_block_match:
            cleaned = code_block_match.group(1).strip()

        # If still not valid JSON array, try to find it in the text
        if not cleaned.startswith("["):
            # Find the JSON array boundaries
            start_idx = cleaned.find("[")
            if start_idx != -1:
                # Find matching closing bracket
                bracket_count = 0
                end_idx = start_idx
                for i, char in enumerate(cleaned[start_idx:], start_idx):
                    if char == "[":
                        bracket_count += 1
                    elif char == "]":
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_idx = i
                            break
                cleaned = cleaned[start_idx : end_idx + 1]

        return cleaned.strip()

    def _validate_and_merge_chunks(
        self, chunks: list[TranscriptChunk], video_id: str
    ) -> list[TranscriptChunk]:
        """
        Validate chunk sizes and merge small chunks with neighbors.

        LLM sometimes ignores size requirements and creates tiny chunks.
        This method merges chunks smaller than MIN_CHUNK_WORDS with
        the next chunk to ensure meaningful semantic units.

        Args:
            chunks: List of parsed chunks
            video_id: Video ID for regenerating chunk IDs

        Returns:
            List of validated chunks with small ones merged
        """
        if not chunks:
            return chunks

        # Count small chunks for logging
        small_count = sum(1 for c in chunks if c.word_count < MIN_CHUNK_WORDS)
        if small_count > 0:
            logger.warning(
                f"Found {small_count}/{len(chunks)} chunks with < {MIN_CHUNK_WORDS} words, merging"
            )

        merged: list[TranscriptChunk] = []
        pending_text = ""
        pending_topic = ""

        for chunk in chunks:
            if chunk.word_count < MIN_CHUNK_WORDS:
                # Accumulate small chunk
                if pending_text:
                    pending_text += " " + chunk.text
                else:
                    pending_text = chunk.text
                    pending_topic = chunk.topic
            else:
                # Normal sized chunk
                if pending_text:
                    # Prepend accumulated small chunks to this one
                    combined_text = pending_text + " " + chunk.text
                    combined_topic = pending_topic or chunk.topic
                    merged.append(
                        TranscriptChunk(
                            id="",  # Will be reassigned
                            index=0,
                            topic=combined_topic,
                            text=combined_text,
                            word_count=len(combined_text.split()),
                        )
                    )
                    pending_text = ""
                    pending_topic = ""
                else:
                    merged.append(chunk)

        # Handle any remaining pending text
        if pending_text:
            if merged:
                # Append to last chunk
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
                # Only small chunks - keep as single chunk
                merged.append(
                    TranscriptChunk(
                        id="",
                        index=0,
                        topic=pending_topic,
                        text=pending_text,
                        word_count=len(pending_text.split()),
                    )
                )

        # Reassign indices and IDs
        for i, chunk in enumerate(merged):
            new_index = i + 1
            merged[i] = TranscriptChunk(
                id=f"{video_id}_{new_index:03d}",
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
            prompt = load_prompt("chunker", settings)
            assert "{transcript}" in prompt, "Prompt missing {transcript} placeholder"
            assert "{context}" in prompt, "Prompt missing {context} placeholder"
            assert len(prompt) > 100, "Prompt too short"
            print("OK")
            print(f"  Prompt length: {len(prompt)} chars")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 2: Extract JSON from plain response
        print("\nTest 2: Extract JSON (plain)...", end=" ")
        try:
            chunker = SemanticChunker(None, settings)  # type: ignore

            plain_json = '[{"index": 1, "topic": "Test", "text": "Hello"}]'
            extracted = chunker._extract_json(plain_json)
            assert extracted == plain_json, f"Expected {plain_json}, got {extracted}"
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 3: Extract JSON from markdown-wrapped response
        print("\nTest 3: Extract JSON (markdown)...", end=" ")
        try:
            markdown_json = '```json\n[{"index": 1, "topic": "Test", "text": "Hello"}]\n```'
            extracted = chunker._extract_json(markdown_json)
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
            print(f"  Chunk 1: {chunks[0].id} - {chunks[0].topic} ({chunks[0].word_count} words)")
            print(f"  Chunk 2: {chunks[1].id} - {chunks[1].topic} ({chunks[1].word_count} words)")
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
                    )

                    result = await chunker.chunk(cleaned_transcript, mock_metadata)

                    assert result.total_chunks > 0, "No chunks created"
                    assert result.avg_chunk_size > 0, "Average size is 0"

                    print("OK")
                    print(f"  Total chunks: {result.total_chunks}")
                    print(f"  Average size: {result.avg_chunk_size} words")
                    for chunk in result.chunks:
                        print(f"  - {chunk.id}: {chunk.topic} ({chunk.word_count} words)")

                except Exception as e:
                    print(f"FAILED: {e}")
                    return 1

        print("\n" + "=" * 40)
        print("All tests passed!")
        return 0

    sys.exit(asyncio.run(run_tests()))
