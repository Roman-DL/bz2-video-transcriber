"""
Pricing utilities for LLM cost calculation.

Calculates API costs based on token usage and model pricing.
Pricing data is loaded from config/models.yaml.

Example:
    from app.utils.pricing_utils import calculate_cost, get_model_pricing

    pricing = get_model_pricing("claude-sonnet-4-5")
    # {'input': 3.00, 'output': 15.00}

    cost = calculate_cost("claude-sonnet-4-5", input_tokens=1000, output_tokens=500)
    # 0.0105 (= 1000 * 3/1M + 500 * 15/1M)
"""

import logging
from typing import TypedDict

from app.config import load_models_config

logger = logging.getLogger(__name__)

# Cache for model pricing (loaded once)
_pricing_cache: dict[str, dict[str, float]] | None = None


class ModelPricing(TypedDict):
    """Pricing per 1M tokens."""

    input: float
    output: float


def get_model_pricing(model_name: str) -> ModelPricing | None:
    """
    Get pricing for a model from config.

    Args:
        model_name: Model identifier (e.g., "claude-sonnet-4-5")

    Returns:
        Pricing dict with 'input' and 'output' per 1M tokens,
        or None if model has no pricing (free/local models)

    Example:
        >>> get_model_pricing("claude-sonnet-4-5")
        {'input': 3.0, 'output': 15.0}

        >>> get_model_pricing("gemma2:9b")
        None
    """
    global _pricing_cache

    if _pricing_cache is None:
        _pricing_cache = _load_pricing_config()

    return _pricing_cache.get(model_name)


def calculate_cost(
    model_name: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """
    Calculate cost for a model API call.

    Args:
        model_name: Model identifier
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Cost in USD (0.0 for free/local models)

    Example:
        >>> calculate_cost("claude-sonnet-4-5", 1000, 500)
        0.0105
    """
    pricing = get_model_pricing(model_name)

    if pricing is None:
        return 0.0

    # Pricing is per 1M tokens
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    total = input_cost + output_cost

    logger.debug(
        f"Cost for {model_name}: "
        f"${input_cost:.6f} (in) + ${output_cost:.6f} (out) = ${total:.6f}"
    )

    return round(total, 6)


def _load_pricing_config() -> dict[str, dict[str, float]]:
    """
    Load pricing configuration from models.yaml.

    Returns:
        Dict mapping model_id to pricing dict
    """
    pricing: dict[str, dict[str, float]] = {}

    try:
        config = load_models_config()

        # Load Claude models pricing
        for model in config.get("claude_models", []):
            model_id = model.get("id")
            model_pricing = model.get("pricing")

            if model_id and model_pricing:
                pricing[model_id] = {
                    "input": float(model_pricing.get("input", 0)),
                    "output": float(model_pricing.get("output", 0)),
                }
                logger.debug(f"Loaded pricing for {model_id}: {pricing[model_id]}")

    except Exception as e:
        logger.warning(f"Failed to load pricing config: {e}")

    return pricing


def clear_pricing_cache() -> None:
    """Clear the pricing cache (for testing)."""
    global _pricing_cache
    _pricing_cache = None


# ═══════════════════════════════════════════════════════════════════════════
# Embedded Tests
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)

    print("\n" + "=" * 60)
    print("Running pricing_utils tests...")
    print("=" * 60 + "\n")

    errors = 0

    # Test 1: Get Claude Sonnet pricing
    print("Test 1: Get Claude Sonnet pricing...", end=" ")
    clear_pricing_cache()
    pricing = get_model_pricing("claude-sonnet-4-5")
    if pricing and pricing["input"] == 3.0 and pricing["output"] == 15.0:
        print("OK")
        print(f"  Pricing: ${pricing['input']}/${pricing['output']} per 1M tokens")
    else:
        print(f"FAILED: got {pricing}")
        errors += 1

    # Test 2: Get local model pricing (should be None)
    print("Test 2: Local model pricing (None)...", end=" ")
    pricing = get_model_pricing("gemma2:9b")
    if pricing is None:
        print("OK")
    else:
        print(f"FAILED: expected None, got {pricing}")
        errors += 1

    # Test 3: Calculate cost for Claude Sonnet
    print("Test 3: Calculate cost...", end=" ")
    cost = calculate_cost("claude-sonnet-4-5", input_tokens=1000, output_tokens=500)
    expected = (1000 / 1_000_000) * 3.0 + (500 / 1_000_000) * 15.0  # 0.0105
    if abs(cost - expected) < 0.0001:
        print("OK")
        print(f"  1000 in + 500 out = ${cost:.6f}")
    else:
        print(f"FAILED: expected {expected}, got {cost}")
        errors += 1

    # Test 4: Calculate cost for local model (free)
    print("Test 4: Local model cost (free)...", end=" ")
    cost = calculate_cost("gemma2:9b", input_tokens=10000, output_tokens=5000)
    if cost == 0.0:
        print("OK")
    else:
        print(f"FAILED: expected 0.0, got {cost}")
        errors += 1

    # Test 5: Get Haiku pricing
    print("Test 5: Get Haiku pricing...", end=" ")
    pricing = get_model_pricing("claude-haiku-4-5")
    if pricing and pricing["input"] == 1.0 and pricing["output"] == 5.0:
        print("OK")
    else:
        print(f"FAILED: got {pricing}")
        errors += 1

    # Test 6: Get Opus pricing
    print("Test 6: Get Opus pricing...", end=" ")
    pricing = get_model_pricing("claude-opus-4-5")
    if pricing and pricing["input"] == 15.0 and pricing["output"] == 75.0:
        print("OK")
    else:
        print(f"FAILED: got {pricing}")
        errors += 1

    # Summary
    print("\n" + "=" * 60)
    if errors == 0:
        print("All tests passed!")
        sys.exit(0)
    else:
        print(f"{errors} test(s) failed!")
        sys.exit(1)
