"""
Shared utilities for LLM services.

This package contains reusable utilities extracted from individual services
to reduce code duplication and provide consistent behavior across the codebase.

Modules:
    json_utils: JSON extraction and parsing from LLM responses
    token_utils: Token estimation and num_predict calculation
    chunk_utils: Chunk merging and validation utilities
    h2_chunker: Deterministic H2-based markdown chunking (v0.25+)
"""

from app.utils.chunk_utils import (
    count_words,
    generate_chunk_id,
    validate_cyrillic_ratio,
)
from app.utils.h2_chunker import chunk_by_h2
from app.utils.json_utils import extract_json, parse_json_safe
from app.utils.token_utils import (
    calculate_num_predict,
    calculate_num_predict_from_chars,
    estimate_tokens,
)

__all__ = [
    # json_utils
    "extract_json",
    "parse_json_safe",
    # token_utils
    "estimate_tokens",
    "calculate_num_predict",
    "calculate_num_predict_from_chars",
    # chunk_utils
    "validate_cyrillic_ratio",
    "generate_chunk_id",
    "count_words",
    # h2_chunker
    "chunk_by_h2",
]
