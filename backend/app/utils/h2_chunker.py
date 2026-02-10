"""
Deterministic H2 chunking for markdown documents.

Parses markdown by H2 headings to create semantic chunks.
Used after Longread/Story generation for RAG retrieval.

v0.42+: Added total_tokens estimation for chunk metadata.

Example:
    from app.utils.h2_chunker import chunk_by_h2

    markdown = '''
    ## Введение
    Текст введения...

    ## Основная часть
    Текст основной части...
    '''
    chunks = chunk_by_h2(markdown, "video-123")
    # chunks.total_chunks == 2
    # chunks.total_tokens == 150  # estimated
"""

import logging
import re

from app.models.schemas import TranscriptChunk, TranscriptChunks
from app.utils.chunk_utils import count_words, generate_chunk_id
from app.utils.token_utils import estimate_tokens

logger = logging.getLogger(__name__)

# Pattern to match H2 headers (## Title)
H2_PATTERN = re.compile(r"^## ", re.MULTILINE)

# Pattern to clean emoji prefixes from story headers (1️⃣ 2️⃣ etc)
EMOJI_NUMBER_PATTERN = re.compile(r"^[\d️⃣\uFE0F]+\s*")

# Model name for deterministic chunking
DETERMINISTIC_MODEL = "deterministic"

# Maximum words per chunk before splitting by paragraphs (BZ2-Bot contract)
MAX_CHUNK_WORDS = 600


def chunk_by_h2(markdown: str, video_id: str) -> TranscriptChunks:
    """
    Chunk markdown document by H2 headers.

    Splits markdown at ## headings, creating one chunk per section.
    Handles story emoji prefixes (1️⃣, 2️⃣, etc) by stripping them.

    Args:
        markdown: Markdown text with H2 sections
        video_id: Base video identifier for chunk IDs

    Returns:
        TranscriptChunks with deterministic chunking

    Example:
        >>> md = "## Intro\\nHello\\n\\n## Main\\nWorld"
        >>> chunks = chunk_by_h2(md, "vid-1")
        >>> chunks.total_chunks
        2
        >>> chunks.chunks[0].topic
        'Intro'
    """
    if not markdown or not markdown.strip():
        logger.warning("Empty markdown provided, creating fallback chunk")
        return _create_fallback_chunk(video_id)

    # Split by ## headers
    sections = H2_PATTERN.split(markdown)
    chunks: list[TranscriptChunk] = []

    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue

        # First section before any ## is preamble (usually empty or title)
        # Skip if it doesn't have meaningful content
        if i == 0 and not H2_PATTERN.search(f"## {section}"):
            # This is content before the first H2
            if len(section) < 100:  # Skip short preambles
                continue
            # If substantial preamble, treat as introduction
            topic = "Введение"
            content = section
        else:
            # Parse title and content from section
            lines = section.split("\n", 1)
            topic = _clean_topic(lines[0].strip())
            content = lines[1].strip() if len(lines) > 1 else ""

        if not content:
            logger.debug(f"Skipping empty section: {topic}")
            continue

        chunk_index = len(chunks) + 1
        chunk_id = generate_chunk_id(video_id, chunk_index)
        word_count = count_words(content)

        chunks.append(
            TranscriptChunk(
                id=chunk_id,
                index=chunk_index,
                topic=topic,
                text=content,
                word_count=word_count,
            )
        )

    if not chunks:
        logger.warning("No H2 sections found, creating fallback chunk")
        return _create_fallback_chunk(video_id, markdown)

    # Split large chunks by paragraphs (v0.60+, BZ2-Bot contract: max 600 words)
    chunks = _split_large_chunks(chunks, video_id)

    # Calculate total tokens (v0.42+)
    total_text = " ".join(c.text for c in chunks)
    total_tokens = estimate_tokens(total_text, lang="ru")

    logger.info(
        "chunked_by_h2",
        extra={
            "chunks": len(chunks),
            "avg_words": sum(c.word_count for c in chunks) // len(chunks),
            "total_tokens": total_tokens,
        },
    )

    return TranscriptChunks(
        chunks=chunks,
        model_name=DETERMINISTIC_MODEL,
        total_tokens=total_tokens,
    )


def _clean_topic(topic: str) -> str:
    """
    Clean topic string by removing emoji number prefixes.

    Story format uses 1️⃣, 2️⃣ etc. These should be stripped.

    Args:
        topic: Raw topic string

    Returns:
        Cleaned topic without emoji prefixes

    Example:
        >>> _clean_topic("1️⃣ Кто они")
        'Кто они'
        >>> _clean_topic("Обычный заголовок")
        'Обычный заголовок'
    """
    cleaned = EMOJI_NUMBER_PATTERN.sub("", topic).strip()
    return cleaned if cleaned else topic


def _split_large_chunks(
    chunks: list[TranscriptChunk], video_id: str
) -> list[TranscriptChunk]:
    """Split chunks exceeding MAX_CHUNK_WORDS by paragraphs.

    Preserves original topic for all sub-chunks. Re-indexes all chunks
    sequentially after splitting.

    Args:
        chunks: Original chunks from H2 parsing
        video_id: Video identifier for chunk ID generation

    Returns:
        List of chunks with large ones split by paragraphs
    """
    result: list[TranscriptChunk] = []

    for chunk in chunks:
        if chunk.word_count <= MAX_CHUNK_WORDS:
            result.append(chunk)
            continue

        parts = _split_by_paragraphs(chunk.text, MAX_CHUNK_WORDS)
        if len(parts) <= 1:
            # Cannot split further (single large paragraph)
            result.append(chunk)
            continue

        logger.info(
            "chunk_split",
            extra={
                "topic": chunk.topic,
                "original_words": chunk.word_count,
                "parts": len(parts),
            },
        )

        for part_text in parts:
            result.append(
                TranscriptChunk(
                    id="",  # Will be re-assigned below
                    index=0,
                    topic=chunk.topic,
                    text=part_text,
                    word_count=count_words(part_text),
                )
            )

    # Re-index all chunks sequentially
    for i, chunk in enumerate(result):
        chunk.index = i + 1
        chunk.id = generate_chunk_id(video_id, i + 1)

    return result


def _split_by_paragraphs(text: str, max_words: int) -> list[str]:
    """Split text by paragraphs to fit within word limit.

    Greedily accumulates paragraphs until adding the next one
    would exceed the limit, then starts a new part.

    Args:
        text: Text to split
        max_words: Maximum words per part

    Returns:
        List of text parts, each within the word limit
    """
    paragraphs = text.split("\n\n")
    parts: list[str] = []
    current: list[str] = []
    current_words = 0

    for para in paragraphs:
        para_words = count_words(para)
        if current and current_words + para_words > max_words:
            parts.append("\n\n".join(current))
            current = [para]
            current_words = para_words
        else:
            current.append(para)
            current_words += para_words

    if current:
        parts.append("\n\n".join(current))

    return parts


def _create_fallback_chunk(video_id: str, text: str = "") -> TranscriptChunks:
    """
    Create fallback single chunk when no H2 structure found.

    Args:
        video_id: Video identifier
        text: Optional text content

    Returns:
        TranscriptChunks with single fallback chunk
    """
    content = text.strip() if text else ""

    chunk = TranscriptChunk(
        id=generate_chunk_id(video_id, 1),
        index=1,
        topic="Полный текст",
        text=content,
        word_count=count_words(content),
    )

    # Calculate total tokens (v0.42+)
    total_tokens = estimate_tokens(content, lang="ru") if content else 0

    return TranscriptChunks(
        chunks=[chunk],
        model_name=DETERMINISTIC_MODEL,
        total_tokens=total_tokens,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Embedded Tests
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    print("\n" + "=" * 60)
    print("Running h2_chunker tests...")
    print("=" * 60 + "\n")

    errors = 0

    # Test 1: Basic H2 chunking
    print("Test 1: Basic H2 chunking...", end=" ")
    markdown = """## Введение
Это текст введения. Он содержит несколько предложений.

## Основная часть
Это основной контент документа. Здесь много информации.

## Заключение
Выводы по теме.
"""
    chunks = chunk_by_h2(markdown, "test-1")
    if chunks.total_chunks == 3 and chunks.chunks[0].topic == "Введение":
        print("OK")
    else:
        print(f"FAILED: expected 3 chunks, got {chunks.total_chunks}")
        errors += 1

    # Test 2: Story with emoji prefixes
    print("Test 2: Story emoji prefixes...", end=" ")
    story_md = """## 1️⃣ Кто они
История персонажей.

## 2️⃣ Проблема
Описание проблемы.

## 3️⃣ Решение
Как решили проблему.
"""
    chunks = chunk_by_h2(story_md, "story-1")
    if (
        chunks.total_chunks == 3
        and chunks.chunks[0].topic == "Кто они"
        and chunks.chunks[1].topic == "Проблема"
    ):
        print("OK")
    else:
        print(f"FAILED: topics = {[c.topic for c in chunks.chunks]}")
        errors += 1

    # Test 3: Empty markdown
    print("Test 3: Empty markdown...", end=" ")
    chunks = chunk_by_h2("", "empty-1")
    if chunks.total_chunks == 1 and chunks.chunks[0].topic == "Полный текст":
        print("OK")
    else:
        print("FAILED: expected fallback chunk")
        errors += 1

    # Test 4: No H2 structure
    print("Test 4: No H2 structure...", end=" ")
    plain_text = "Это просто текст без заголовков. Много слов здесь."
    chunks = chunk_by_h2(plain_text, "plain-1")
    if chunks.total_chunks == 1:
        print("OK")
    else:
        print(f"FAILED: expected 1 fallback chunk, got {chunks.total_chunks}")
        errors += 1

    # Test 5: Chunk IDs are correct
    print("Test 5: Chunk ID format...", end=" ")
    markdown = """## First
Content one.

## Second
Content two.
"""
    chunks = chunk_by_h2(markdown, "vid-123")
    if chunks.chunks[0].id == "vid-123_001" and chunks.chunks[1].id == "vid-123_002":
        print("OK")
    else:
        print(f"FAILED: IDs = {[c.id for c in chunks.chunks]}")
        errors += 1

    # Test 6: Word count is calculated
    print("Test 6: Word count...", end=" ")
    markdown = """## Test
Один два три четыре пять.
"""
    chunks = chunk_by_h2(markdown, "wc-1")
    if chunks.chunks[0].word_count == 5:
        print("OK")
    else:
        print(f"FAILED: expected 5 words, got {chunks.chunks[0].word_count}")
        errors += 1

    # Test 7: Model name is "deterministic"
    print("Test 7: Model name...", end=" ")
    markdown = """## Section
Content.
"""
    chunks = chunk_by_h2(markdown, "model-1")
    if chunks.model_name == "deterministic":
        print("OK")
    else:
        print(f"FAILED: expected 'deterministic', got '{chunks.model_name}'")
        errors += 1

    # Test 8: Skip empty sections
    print("Test 8: Skip empty sections...", end=" ")
    markdown = """## With content
Real content here.

## Empty

## Another with content
More real content.
"""
    chunks = chunk_by_h2(markdown, "skip-1")
    if chunks.total_chunks == 2:
        print("OK")
    else:
        print(f"FAILED: expected 2 chunks (empty skipped), got {chunks.total_chunks}")
        errors += 1

    # Test 9: Clean topic with multiple emoji formats
    print("Test 9: Clean various emoji formats...", end=" ")
    test_cases = [
        ("1️⃣ Topic", "Topic"),
        ("2️⃣  Topic", "Topic"),
        ("12 Topic", "Topic"),
        ("Normal topic", "Normal topic"),
        ("  Spaced  ", "Spaced"),
    ]
    all_passed = True
    for raw, expected in test_cases:
        result = _clean_topic(raw)
        if result != expected:
            all_passed = False
            print(f"\n  FAILED: _clean_topic('{raw}') = '{result}', expected '{expected}'")
    if all_passed:
        print("OK")
    else:
        errors += 1

    # Test 10: Preamble handling
    print("Test 10: Preamble handling...", end=" ")
    markdown = """# Title
Short preamble.

## First Section
Content of first section.

## Second Section
Content of second section.
"""
    chunks = chunk_by_h2(markdown, "preamble-1")
    # Short preamble should be skipped
    if chunks.total_chunks == 2 and chunks.chunks[0].topic == "First Section":
        print("OK")
    else:
        print(f"FAILED: expected 2 chunks, got {chunks.total_chunks}")
        errors += 1

    # Test 11: Split large chunk (700 words → 2 parts)
    print("Test 11: Split large chunk (700 words)...", end=" ")
    para1 = " ".join(["слово"] * 350)
    para2 = " ".join(["текст"] * 350)
    markdown = f"## Большая тема\n{para1}\n\n{para2}\n"
    chunks = chunk_by_h2(markdown, "split-1")
    if chunks.total_chunks == 2:
        ok = (
            chunks.chunks[0].topic == "Большая тема"
            and chunks.chunks[1].topic == "Большая тема"
            and chunks.chunks[0].word_count <= MAX_CHUNK_WORDS
            and chunks.chunks[1].word_count <= MAX_CHUNK_WORDS
            and chunks.chunks[0].index == 1
            and chunks.chunks[1].index == 2
        )
        if ok:
            print("OK")
        else:
            print(f"FAILED: topics={[c.topic for c in chunks.chunks]}, "
                  f"words={[c.word_count for c in chunks.chunks]}")
            errors += 1
    else:
        print(f"FAILED: expected 2 chunks, got {chunks.total_chunks}")
        errors += 1

    # Test 12: No split for small chunk (500 words)
    print("Test 12: No split for small chunk (500 words)...", end=" ")
    small_text = " ".join(["слово"] * 500)
    markdown = f"## Маленькая тема\n{small_text}\n"
    chunks = chunk_by_h2(markdown, "nosplit-1")
    if chunks.total_chunks == 1 and chunks.chunks[0].word_count == 500:
        print("OK")
    else:
        print(f"FAILED: chunks={chunks.total_chunks}, words={chunks.chunks[0].word_count}")
        errors += 1

    # Test 13: Split very large chunk (1200 words → 2-3 parts)
    print("Test 13: Split very large chunk (1200 words)...", end=" ")
    paras = [" ".join(["текст"] * 300) for _ in range(4)]
    markdown = "## Огромная тема\n" + "\n\n".join(paras) + "\n"
    chunks = chunk_by_h2(markdown, "bigsplit-1")
    if chunks.total_chunks >= 2:
        all_under_limit = all(c.word_count <= MAX_CHUNK_WORDS for c in chunks.chunks)
        all_same_topic = all(c.topic == "Огромная тема" for c in chunks.chunks)
        if all_under_limit and all_same_topic:
            print(f"OK ({chunks.total_chunks} parts)")
        else:
            print(f"FAILED: over_limit={not all_under_limit}, mixed_topics={not all_same_topic}")
            errors += 1
    else:
        print(f"FAILED: expected >=2 chunks, got {chunks.total_chunks}")
        errors += 1

    # Test 14: Boundary case (exactly 600 words → no split)
    print("Test 14: Boundary (600 words, no split)...", end=" ")
    exact_text = " ".join(["граница"] * 600)
    markdown = f"## Граничный случай\n{exact_text}\n"
    chunks = chunk_by_h2(markdown, "boundary-1")
    if chunks.total_chunks == 1 and chunks.chunks[0].word_count == 600:
        print("OK")
    else:
        print(f"FAILED: chunks={chunks.total_chunks}, words={chunks.chunks[0].word_count}")
        errors += 1

    # Test 15: Split preserves sequential indexing with mixed chunks
    print("Test 15: Mixed split and non-split chunks...", end=" ")
    small_section = " ".join(["мало"] * 100)
    large_para1 = " ".join(["много"] * 350)
    large_para2 = " ".join(["ещё"] * 350)
    markdown = (
        f"## Маленькая\n{small_section}\n\n"
        f"## Большая\n{large_para1}\n\n{large_para2}\n\n"
        f"## Финальная\n{small_section}\n"
    )
    chunks = chunk_by_h2(markdown, "mixed-1")
    # Expect: Маленькая(1), Большая-part1(2), Большая-part2(3), Финальная(4)
    if chunks.total_chunks == 4:
        ids_ok = all(
            chunks.chunks[i].index == i + 1
            and chunks.chunks[i].id == f"mixed-1_{i+1:03d}"
            for i in range(4)
        )
        if ids_ok:
            print("OK")
        else:
            print(f"FAILED: indices={[c.index for c in chunks.chunks]}")
            errors += 1
    else:
        print(f"FAILED: expected 4 chunks, got {chunks.total_chunks}")
        errors += 1

    # Summary
    print("\n" + "=" * 60)
    if errors == 0:
        print("All tests passed!")
        sys.exit(0)
    else:
        print(f"{errors} test(s) failed!")
        sys.exit(1)
