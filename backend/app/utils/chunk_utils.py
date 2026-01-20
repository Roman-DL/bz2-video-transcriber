"""
Chunk utilities for text processing.

Common utilities for chunking operations: validation, ID generation,
text splitting by words, and language validation.

Example:
    from app.utils.chunk_utils import validate_cyrillic_ratio, generate_chunk_id

    # Check if text is Russian
    ratio = validate_cyrillic_ratio("Привет мир")
    if ratio < 0.5:
        print("Warning: low Cyrillic content")

    # Generate chunk ID
    chunk_id = generate_chunk_id("video-123", 1)  # "video-123_001"
"""

import logging
import re
from dataclasses import dataclass
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def validate_cyrillic_ratio(text: str) -> float:
    """
    Calculate ratio of Cyrillic characters in text.

    Useful for validating that LLM output is Russian text
    from transcript, not generated English content.

    Args:
        text: Text to validate

    Returns:
        Ratio of Cyrillic characters (0.0 to 1.0)

    Example:
        >>> validate_cyrillic_ratio("Привет мир")
        0.9  # 9 Cyrillic chars out of 10 total (including space)
    """
    if not text:
        return 0.0

    cyrillic_count = len(re.findall(r"[а-яА-ЯёЁ]", text))
    return cyrillic_count / len(text)


def generate_chunk_id(video_id: str, index: int, zero_pad: int = 3) -> str:
    """
    Generate standardized chunk ID.

    Args:
        video_id: Base video identifier
        index: Chunk index (1-based)
        zero_pad: Number of digits for zero-padding

    Returns:
        Formatted chunk ID

    Example:
        >>> generate_chunk_id("video-123", 1)
        "video-123_001"

        >>> generate_chunk_id("test", 42, zero_pad=4)
        "test_0042"
    """
    return f"{video_id}_{index:0{zero_pad}d}"


def split_into_words(text: str) -> list[str]:
    """
    Split text into words.

    Args:
        text: Input text

    Returns:
        List of words

    Example:
        >>> split_into_words("Hello world")
        ["Hello", "world"]
    """
    return text.split()


def count_words(text: str) -> int:
    """
    Count words in text.

    Args:
        text: Input text

    Returns:
        Number of words

    Example:
        >>> count_words("Hello world")
        2
    """
    return len(text.split())


@dataclass
class ChunkBoundary:
    """
    Represents a chunk with start/end positions and metadata.

    Useful for chunk merge operations where position tracking is needed.
    """

    start_index: int
    end_index: int
    text: str
    topic: str = ""
    word_count: int = 0

    def __post_init__(self):
        if self.word_count == 0:
            self.word_count = count_words(self.text)


def create_word_chunks(
    text: str,
    chunk_size: int = 300,
    topic_generator: Callable[[int], str] | None = None,
) -> list[ChunkBoundary]:
    """
    Split text into fixed-size word chunks.

    Simple fallback chunking when semantic chunking fails.

    Args:
        text: Text to split
        chunk_size: Target words per chunk
        topic_generator: Optional function to generate topic from chunk index

    Returns:
        List of ChunkBoundary objects

    Example:
        >>> chunks = create_word_chunks("word " * 600, chunk_size=300)
        >>> len(chunks)
        2
    """
    words = text.split()
    chunks: list[ChunkBoundary] = []

    for i, start in enumerate(range(0, len(words), chunk_size)):
        chunk_words = words[start : start + chunk_size]
        chunk_text = " ".join(chunk_words)

        topic = topic_generator(i + 1) if topic_generator else f"Part {i + 1}"

        chunks.append(
            ChunkBoundary(
                start_index=start,
                end_index=start + len(chunk_words),
                text=chunk_text,
                topic=topic,
                word_count=len(chunk_words),
            )
        )

    return chunks


def merge_small_chunks(
    chunks: list[T],
    get_size: Callable[[T], int],
    merge_fn: Callable[[T, T], T],
    min_size: int,
    target_size: int,
) -> list[T]:
    """
    Merge small chunks into larger ones.

    Generic function for merging any items based on size.

    Args:
        chunks: List of items to potentially merge
        get_size: Function to get size of an item
        merge_fn: Function to merge two items into one
        min_size: Minimum acceptable size (smaller items are merged)
        target_size: Target size for merged chunks

    Returns:
        List with small items merged

    Example:
        >>> items = [{"text": "a", "size": 50}, {"text": "b", "size": 50}]
        >>> merged = merge_small_chunks(
        ...     items,
        ...     get_size=lambda x: x["size"],
        ...     merge_fn=lambda a, b: {"text": a["text"] + b["text"], "size": a["size"] + b["size"]},
        ...     min_size=100,
        ...     target_size=150
        ... )
    """
    if not chunks:
        return chunks

    result: list[T] = []
    pending: T | None = None
    pending_size = 0

    for chunk in chunks:
        size = get_size(chunk)

        if size < min_size:
            # Accumulate small chunk
            if pending is None:
                pending = chunk
                pending_size = size
            else:
                pending = merge_fn(pending, chunk)
                pending_size += size

            # If accumulated enough, add to result
            if pending_size >= target_size:
                result.append(pending)
                pending = None
                pending_size = 0
        else:
            # Normal sized chunk - flush pending first
            if pending is not None:
                result.append(pending)
                pending = None
                pending_size = 0
            result.append(chunk)

    # Handle remaining pending
    if pending is not None:
        if result and pending_size < min_size:
            # Merge with last result item if too small
            result[-1] = merge_fn(result[-1], pending)
        else:
            result.append(pending)

    return result


# Embedded tests
if __name__ == "__main__":
    import sys

    print("\nRunning chunk_utils tests...\n")
    errors = 0

    # Test 1: Validate cyrillic ratio
    print("Test 1: Cyrillic ratio (Russian)...", end=" ")
    ratio = validate_cyrillic_ratio("Привет мир")
    if 0.8 < ratio < 1.0:  # 9/10 = 0.9 (space is not cyrillic)
        print("OK")
    else:
        print(f"FAILED: expected ~0.9, got {ratio}")
        errors += 1

    # Test 2: Cyrillic ratio (English)
    print("Test 2: Cyrillic ratio (English)...", end=" ")
    ratio = validate_cyrillic_ratio("Hello world")
    if ratio == 0.0:
        print("OK")
    else:
        print(f"FAILED: expected 0.0, got {ratio}")
        errors += 1

    # Test 3: Generate chunk ID
    print("Test 3: Generate chunk ID...", end=" ")
    chunk_id = generate_chunk_id("video-123", 1)
    if chunk_id == "video-123_001":
        print("OK")
    else:
        print(f"FAILED: expected 'video-123_001', got '{chunk_id}'")
        errors += 1

    # Test 4: Generate chunk ID with custom padding
    print("Test 4: Chunk ID custom padding...", end=" ")
    chunk_id = generate_chunk_id("test", 42, zero_pad=4)
    if chunk_id == "test_0042":
        print("OK")
    else:
        print(f"FAILED: expected 'test_0042', got '{chunk_id}'")
        errors += 1

    # Test 5: Count words
    print("Test 5: Count words...", end=" ")
    count = count_words("Hello world how are you")
    if count == 5:
        print("OK")
    else:
        print(f"FAILED: expected 5, got {count}")
        errors += 1

    # Test 6: Create word chunks
    print("Test 6: Create word chunks...", end=" ")
    text = " ".join(["word"] * 600)
    chunks = create_word_chunks(text, chunk_size=300)
    if len(chunks) == 2 and chunks[0].word_count == 300:
        print("OK")
    else:
        print(f"FAILED: expected 2 chunks of 300 words, got {len(chunks)} chunks")
        errors += 1

    # Test 7: Merge small chunks
    print("Test 7: Merge small chunks...", end=" ")

    @dataclass
    class TestItem:
        text: str
        size: int

    items = [TestItem("a", 50), TestItem("b", 50), TestItem("c", 200)]

    merged = merge_small_chunks(
        items,
        get_size=lambda x: x.size,
        merge_fn=lambda a, b: TestItem(a.text + b.text, a.size + b.size),
        min_size=100,
        target_size=150,
    )

    if len(merged) == 2 and merged[0].text == "ab" and merged[0].size == 100:
        print("OK")
    else:
        print(f"FAILED: got {merged}")
        errors += 1

    # Test 8: Empty input
    print("Test 8: Empty inputs...", end=" ")
    if (
        validate_cyrillic_ratio("") == 0.0
        and count_words("") == 0
        and create_word_chunks("") == []
    ):
        print("OK")
    else:
        print("FAILED")
        errors += 1

    print("\n" + "=" * 40)
    if errors == 0:
        print("All tests passed!")
        sys.exit(0)
    else:
        print(f"{errors} test(s) failed!")
        sys.exit(1)
