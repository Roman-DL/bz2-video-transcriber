"""
JSON extraction and parsing utilities for LLM responses.

LLMs often return JSON wrapped in markdown code blocks or with
surrounding text. These utilities handle extraction and safe parsing.

Example:
    from app.utils.json_utils import extract_json, parse_json_safe

    # Extract JSON array from markdown
    response = '```json\\n[{"id": 1}]\\n```'
    json_str = extract_json(response, json_type="array")

    # Safe parse with default
    data = parse_json_safe(json_str, default=[])
"""

import json
import logging
import re
from typing import Any, Literal, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def extract_json(
    text: str,
    json_type: Literal["object", "array", "auto"] = "auto",
) -> str:
    """
    Extract JSON from LLM response.

    Handles responses wrapped in markdown code blocks and finds
    JSON even if surrounded by other text.

    Args:
        text: Raw LLM response
        json_type: Type of JSON to extract:
            - "object": Find JSON object {...}
            - "array": Find JSON array [...]
            - "auto": Detect based on first bracket found

    Returns:
        Clean JSON string (empty string if not found)

    Example:
        >>> extract_json('```json\\n{"key": "value"}\\n```')
        '{"key": "value"}'

        >>> extract_json('Here is the data: [1, 2, 3] done', json_type="array")
        '[1, 2, 3]'
    """
    if not text:
        return ""

    cleaned = text.strip()

    # Try to extract from markdown code block first
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if code_block_match:
        cleaned = code_block_match.group(1).strip()

    # Determine which brackets to look for
    if json_type == "auto":
        # Find first bracket to determine type
        obj_idx = cleaned.find("{")
        arr_idx = cleaned.find("[")

        if obj_idx == -1 and arr_idx == -1:
            return ""
        elif obj_idx == -1:
            json_type = "array"
        elif arr_idx == -1:
            json_type = "object"
        else:
            json_type = "object" if obj_idx < arr_idx else "array"

    # Set bracket pairs based on type
    if json_type == "object":
        open_bracket, close_bracket = "{", "}"
    else:
        open_bracket, close_bracket = "[", "]"

    # If already starts with correct bracket, validate and return
    if cleaned.startswith(open_bracket):
        return _find_matching_bracket(cleaned, open_bracket, close_bracket)

    # Find the JSON boundaries
    start_idx = cleaned.find(open_bracket)
    if start_idx == -1:
        return ""

    return _find_matching_bracket(cleaned[start_idx:], open_bracket, close_bracket)


def _find_matching_bracket(text: str, open_bracket: str, close_bracket: str) -> str:
    """
    Find matching bracket and return the complete JSON string.

    Args:
        text: Text starting with open bracket
        open_bracket: Opening bracket character
        close_bracket: Closing bracket character

    Returns:
        Complete JSON string with matching brackets
    """
    if not text or not text.startswith(open_bracket):
        return ""

    bracket_count = 0
    in_string = False
    escape_next = False

    for i, char in enumerate(text):
        if escape_next:
            escape_next = False
            continue

        if char == "\\":
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == open_bracket:
            bracket_count += 1
        elif char == close_bracket:
            bracket_count -= 1
            if bracket_count == 0:
                return text[: i + 1]

    # No matching bracket found - return as is (let JSON parser handle error)
    return text


def parse_json_safe(
    json_str: str,
    default: T = None,  # type: ignore
    log_errors: bool = True,
) -> Any | T:
    """
    Parse JSON string with error handling.

    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails
        log_errors: Whether to log parsing errors

    Returns:
        Parsed JSON data or default value

    Example:
        >>> parse_json_safe('{"key": "value"}')
        {'key': 'value'}

        >>> parse_json_safe('invalid', default=[])
        []
    """
    if not json_str or not json_str.strip():
        if log_errors:
            logger.warning("Empty JSON string provided")
        return default

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        if log_errors:
            preview = json_str[:200] + "..." if len(json_str) > 200 else json_str
            logger.warning(f"Failed to parse JSON: {e}. Input: {preview}")
        return default


# Embedded tests
if __name__ == "__main__":
    import sys

    print("\nRunning json_utils tests...\n")
    errors = 0

    # Test 1: Extract plain JSON object
    print("Test 1: Extract plain JSON object...", end=" ")
    result = extract_json('{"key": "value"}')
    if result == '{"key": "value"}':
        print("OK")
    else:
        print(f"FAILED: got {result}")
        errors += 1

    # Test 2: Extract plain JSON array
    print("Test 2: Extract plain JSON array...", end=" ")
    result = extract_json('[1, 2, 3]', json_type="array")
    if result == '[1, 2, 3]':
        print("OK")
    else:
        print(f"FAILED: got {result}")
        errors += 1

    # Test 3: Extract from markdown code block
    print("Test 3: Extract from markdown...", end=" ")
    result = extract_json('```json\n{"nested": {"value": 1}}\n```')
    if result == '{"nested": {"value": 1}}':
        print("OK")
    else:
        print(f"FAILED: got {result}")
        errors += 1

    # Test 4: Extract with surrounding text
    print("Test 4: Extract with surrounding text...", end=" ")
    result = extract_json('Here is the result: [{"id": 1}] done.')
    if result == '[{"id": 1}]':
        print("OK")
    else:
        print(f"FAILED: got {result}")
        errors += 1

    # Test 5: Handle nested brackets
    print("Test 5: Handle nested brackets...", end=" ")
    result = extract_json('{"outer": {"inner": [1, 2]}}')
    if result == '{"outer": {"inner": [1, 2]}}':
        print("OK")
    else:
        print(f"FAILED: got {result}")
        errors += 1

    # Test 6: Handle strings with brackets
    print("Test 6: Handle strings with brackets...", end=" ")
    result = extract_json('{"text": "Hello {world} [test]"}')
    if result == '{"text": "Hello {world} [test]"}':
        print("OK")
    else:
        print(f"FAILED: got {result}")
        errors += 1

    # Test 7: Auto-detect array
    print("Test 7: Auto-detect array...", end=" ")
    result = extract_json("Some text [1, 2] more text")
    if result == "[1, 2]":
        print("OK")
    else:
        print(f"FAILED: got {result}")
        errors += 1

    # Test 8: Safe parse success
    print("Test 8: Safe parse success...", end=" ")
    result = parse_json_safe('{"key": "value"}')
    if result == {"key": "value"}:
        print("OK")
    else:
        print(f"FAILED: got {result}")
        errors += 1

    # Test 9: Safe parse with default
    print("Test 9: Safe parse with default...", end=" ")
    result = parse_json_safe("invalid json", default=[], log_errors=False)
    if result == []:
        print("OK")
    else:
        print(f"FAILED: got {result}")
        errors += 1

    # Test 10: Empty input
    print("Test 10: Empty input...", end=" ")
    result = extract_json("")
    if result == "":
        print("OK")
    else:
        print(f"FAILED: got {result}")
        errors += 1

    print("\n" + "=" * 40)
    if errors == 0:
        print("All tests passed!")
        sys.exit(0)
    else:
        print(f"{errors} test(s) failed!")
        sys.exit(1)
