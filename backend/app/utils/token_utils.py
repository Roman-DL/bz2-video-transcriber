"""
Token estimation and num_predict calculation utilities.

LLM APIs require specifying max output tokens (num_predict in Ollama).
These utilities provide consistent estimation across services.

Token estimation:
- Russian text: ~3 chars per token (Cyrillic is often 2-3 bytes per char)
- English text: ~4 chars per token
- Mixed text: ~3.5 chars per token

Example:
    from app.utils.token_utils import estimate_tokens, calculate_num_predict

    text = "Это пример текста для оценки токенов."
    tokens = estimate_tokens(text)
    num_predict = calculate_num_predict(tokens, task="chunker")
"""

import logging
from typing import Literal

logger = logging.getLogger(__name__)

# Token estimation constants
CHARS_PER_TOKEN_RUSSIAN = 3
CHARS_PER_TOKEN_ENGLISH = 4
CHARS_PER_TOKEN_MIXED = 3.5

# Task-specific multipliers for output size estimation
# These account for how much output each task typically generates relative to input
TASK_MULTIPLIERS = {
    "cleaner": 0.95,  # Output slightly smaller than input (filler removal)
    "chunker": 1.3,  # JSON structure adds ~30% overhead
    "summarizer": 0.3,  # Summary is ~30% of input
    "longread": 1.2,  # Longread adds formatting, ~20% larger
    "outline": 0.2,  # Outline is ~20% of input
}

# Minimum num_predict values by task
MIN_NUM_PREDICT = {
    "cleaner": 4096,
    "chunker": 4096,
    "summarizer": 2048,
    "longread": 4096,
    "outline": 1024,
    "default": 2048,
}


def estimate_tokens(
    text: str,
    lang: Literal["ru", "en", "mixed"] = "ru",
) -> int:
    """
    Estimate token count for text.

    Uses simple character-based estimation. Actual token count
    depends on the specific model's tokenizer.

    Args:
        text: Input text to estimate
        lang: Language hint for better estimation:
            - "ru": Russian text (~3 chars/token)
            - "en": English text (~4 chars/token)
            - "mixed": Mixed content (~3.5 chars/token)

    Returns:
        Estimated token count

    Example:
        >>> estimate_tokens("Привет мир", lang="ru")
        3

        >>> estimate_tokens("Hello world", lang="en")
        3
    """
    if not text:
        return 0

    char_count = len(text)

    if lang == "ru":
        chars_per_token = CHARS_PER_TOKEN_RUSSIAN
    elif lang == "en":
        chars_per_token = CHARS_PER_TOKEN_ENGLISH
    else:
        chars_per_token = CHARS_PER_TOKEN_MIXED

    return int(char_count / chars_per_token)


def calculate_num_predict(
    input_tokens: int,
    task: str = "default",
    buffer_tokens: int = 500,
) -> int:
    """
    Calculate num_predict (max output tokens) for LLM call.

    Accounts for task-specific output sizes and adds safety buffer.

    Args:
        input_tokens: Estimated input token count
        task: Task type for appropriate multiplier:
            - "cleaner": Output ~95% of input
            - "chunker": Output ~130% of input (JSON overhead)
            - "summarizer": Output ~30% of input
            - "longread": Output ~120% of input
            - "outline": Output ~20% of input
        buffer_tokens: Extra tokens for safety margin

    Returns:
        Recommended num_predict value

    Example:
        >>> calculate_num_predict(1000, task="chunker")
        1800  # 1000 * 1.3 + 500

        >>> calculate_num_predict(1000, task="summarizer")
        2048  # max(1000 * 0.3 + 500, min_predict)
    """
    multiplier = TASK_MULTIPLIERS.get(task, 1.0)
    min_predict = MIN_NUM_PREDICT.get(task, MIN_NUM_PREDICT["default"])

    estimated_output = int(input_tokens * multiplier) + buffer_tokens

    return max(estimated_output, min_predict)


def calculate_num_predict_from_chars(
    char_count: int,
    task: str = "default",
    lang: Literal["ru", "en", "mixed"] = "ru",
    buffer_tokens: int = 500,
) -> int:
    """
    Calculate num_predict directly from character count.

    Convenience function combining estimate_tokens and calculate_num_predict.

    Args:
        char_count: Number of characters in input text
        task: Task type for output estimation
        lang: Language hint for token estimation
        buffer_tokens: Extra tokens for safety margin

    Returns:
        Recommended num_predict value

    Example:
        >>> calculate_num_predict_from_chars(3000, task="chunker")
        1800  # (3000/3) * 1.3 + 500
    """
    tokens = estimate_tokens("x" * char_count, lang=lang)  # Quick estimate
    return calculate_num_predict(tokens, task=task, buffer_tokens=buffer_tokens)


# Embedded tests
if __name__ == "__main__":
    import sys

    print("\nRunning token_utils tests...\n")
    errors = 0

    # Test 1: Estimate tokens for Russian text
    print("Test 1: Estimate tokens (Russian)...", end=" ")
    tokens = estimate_tokens("Привет мир")  # 10 chars
    if tokens == 3:  # 10 / 3 = 3
        print("OK")
    else:
        print(f"FAILED: expected 3, got {tokens}")
        errors += 1

    # Test 2: Estimate tokens for English text
    print("Test 2: Estimate tokens (English)...", end=" ")
    tokens = estimate_tokens("Hello world", lang="en")  # 11 chars
    if tokens == 2:  # 11 / 4 = 2
        print("OK")
    else:
        print(f"FAILED: expected 2, got {tokens}")
        errors += 1

    # Test 3: Empty text
    print("Test 3: Empty text...", end=" ")
    tokens = estimate_tokens("")
    if tokens == 0:
        print("OK")
    else:
        print(f"FAILED: expected 0, got {tokens}")
        errors += 1

    # Test 4: Calculate num_predict for chunker
    print("Test 4: Calculate num_predict (chunker)...", end=" ")
    num_predict = calculate_num_predict(1000, task="chunker")
    expected = int(1000 * 1.3) + 500  # 1800
    if num_predict == expected:
        print("OK")
    else:
        print(f"FAILED: expected {expected}, got {num_predict}")
        errors += 1

    # Test 5: Calculate num_predict respects minimum
    print("Test 5: Minimum num_predict...", end=" ")
    num_predict = calculate_num_predict(100, task="chunker")
    if num_predict == MIN_NUM_PREDICT["chunker"]:  # 4096
        print("OK")
    else:
        print(f"FAILED: expected {MIN_NUM_PREDICT['chunker']}, got {num_predict}")
        errors += 1

    # Test 6: Calculate from chars
    print("Test 6: Calculate from chars...", end=" ")
    num_predict = calculate_num_predict_from_chars(3000, task="summarizer")
    # 3000 / 3 = 1000 tokens, * 0.3 = 300 + 500 = 800, min = 2048
    if num_predict == 2048:
        print("OK")
    else:
        print(f"FAILED: expected 2048, got {num_predict}")
        errors += 1

    # Test 7: Unknown task uses default
    print("Test 7: Unknown task uses default...", end=" ")
    num_predict = calculate_num_predict(1000, task="unknown")
    # 1000 * 1.0 + 500 = 1500, min default = 2048
    if num_predict == 2048:
        print("OK")
    else:
        print(f"FAILED: expected 2048, got {num_predict}")
        errors += 1

    print("\n" + "=" * 40)
    if errors == 0:
        print("All tests passed!")
        sys.exit(0)
    else:
        print(f"{errors} test(s) failed!")
        sys.exit(1)
