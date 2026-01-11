#!/usr/bin/env python3
"""
Test different LLM models for chunking to find the most reliable one.

Usage:
    docker exec -it bz2-transcriber python3 /app/scripts/test_chunker_models.py
"""

import asyncio
import json
import sys
import time
from statistics import mean, stdev

# Add app to path
sys.path.insert(0, '/app')

from app.config import get_settings
from app.services.ai_client import AIClient
from app.services.chunker import SemanticChunker
from app.services.cleaner import TranscriptCleaner
from app.services.parser import parse_filename
from app.services.transcriber import WhisperTranscriber


MODELS_TO_TEST = [
    "qwen2.5:14b",
    "gemma2:9b",
]

VIDEO_FILENAME = "2025.12.22 ПШ.SV Закрытие ПО, возражения (Кухаренко Женя).mp4"
NUM_RUNS = 2  # Number of runs per model for stability check


async def prepare_data():
    """Run parse -> transcribe -> clean pipeline to get cleaned transcript."""
    settings = get_settings()

    print("=" * 60)
    print("STEP 1: Parsing metadata...")
    metadata = parse_filename(VIDEO_FILENAME)
    print(f"  video_id: {metadata.video_id}")
    print(f"  duration: {metadata.duration_seconds}s")

    print("\nSTEP 2: Transcribing (this may take a few minutes)...")
    from pathlib import Path
    async with AIClient(settings) as ai_client:
        transcriber = WhisperTranscriber(ai_client, settings)
        raw_transcript, _ = await transcriber.transcribe(Path(metadata.source_path))
        print(f"  segments: {len(raw_transcript.segments)}")
        print(f"  duration: {raw_transcript.duration_seconds}s")

        print("\nSTEP 3: Cleaning transcript...")
        cleaner = TranscriptCleaner(ai_client, settings)
        cleaned = await cleaner.clean(raw_transcript, metadata)
        compression = round((1 - cleaned.cleaned_length / cleaned.original_length) * 100, 1)
        print(f"  char_count: {cleaned.cleaned_length}")
        print(f"  compression: {compression}%")

        return cleaned, metadata


async def test_single_model(model: str, cleaned_transcript, metadata, run_num: int = 1):
    """Test chunking with a specific model."""
    settings = get_settings()

    start_time = time.time()
    try:
        async with AIClient(settings) as ai_client:
            # Override model for this test
            chunker = SemanticChunker(ai_client, settings)
            chunker.settings.chunker_model = model

            result = await chunker.chunk(cleaned_transcript, metadata)
            elapsed = time.time() - start_time

            # Calculate detailed metrics
            sizes = [c.word_count for c in result.chunks]
            small_chunks = sum(1 for s in sizes if s < 100)
            normal_chunks = sum(1 for s in sizes if 100 <= s <= 400)
            large_chunks = sum(1 for s in sizes if s > 400)

            # Get sample topics
            topics = [c.topic[:40] for c in result.chunks[:3]]

            return {
                "model": model,
                "run": run_num,
                "success": True,
                "chunks": result.total_chunks,
                "avg_size": result.avg_chunk_size,
                "min_size": min(sizes) if sizes else 0,
                "max_size": max(sizes) if sizes else 0,
                "small_chunks": small_chunks,
                "normal_chunks": normal_chunks,
                "large_chunks": large_chunks,
                "topics": topics,
                "time": round(elapsed, 1),
                "error": None
            }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "model": model,
            "run": run_num,
            "success": False,
            "chunks": 0,
            "avg_size": 0,
            "min_size": 0,
            "max_size": 0,
            "small_chunks": 0,
            "normal_chunks": 0,
            "large_chunks": 0,
            "topics": [],
            "time": round(elapsed, 1),
            "error": str(e)[:150]
        }


async def main():
    print("=" * 60)
    print("CHUNKER MODEL COMPARISON TEST (EXTENDED)")
    print("=" * 60)

    # Prepare data
    cleaned, metadata = await prepare_data()
    word_count = len(cleaned.text.split())
    print(f"\nCleaned transcript: {word_count} words")

    # Test each model multiple times
    print("\n" + "=" * 60)
    print(f"TESTING MODELS ({NUM_RUNS} runs each)")
    print("=" * 60)

    all_results = []
    for model in MODELS_TO_TEST:
        print(f"\n{'='*40}")
        print(f"MODEL: {model}")
        print("="*40)

        model_results = []
        for run in range(1, NUM_RUNS + 1):
            print(f"\n  Run {run}/{NUM_RUNS}...")
            result = await test_single_model(model, cleaned, metadata, run)
            model_results.append(result)
            all_results.append(result)

            if result["success"]:
                print(f"    SUCCESS: {result['chunks']} chunks")
                print(f"    Sizes: min={result['min_size']}, avg={result['avg_size']}, max={result['max_size']}")
                print(f"    Distribution: small(<100)={result['small_chunks']}, normal(100-400)={result['normal_chunks']}, large(>400)={result['large_chunks']}")
                print(f"    Sample topics: {result['topics'][:2]}")
                print(f"    Time: {result['time']}s")
            else:
                print(f"    FAILED: {result['error']}")

        # Model summary
        successes = [r for r in model_results if r["success"]]
        failures = [r for r in model_results if not r["success"]]

        print(f"\n  STABILITY: {len(successes)}/{NUM_RUNS} successful runs")
        if failures:
            print(f"  ERRORS: {[f['error'][:50] for f in failures]}")

    # Final summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)

    for model in MODELS_TO_TEST:
        model_runs = [r for r in all_results if r["model"] == model]
        successes = [r for r in model_runs if r["success"]]

        print(f"\n{model}:")
        print(f"  Success rate: {len(successes)}/{len(model_runs)}")

        if successes:
            avg_chunks = mean([r["chunks"] for r in successes])
            avg_size = mean([r["avg_size"] for r in successes])
            avg_normal = mean([r["normal_chunks"] for r in successes])
            avg_time = mean([r["time"] for r in successes])

            print(f"  Avg chunks: {avg_chunks:.1f}")
            print(f"  Avg chunk size: {avg_size:.0f} words")
            print(f"  Avg normal chunks (100-400 words): {avg_normal:.1f}")
            print(f"  Avg time: {avg_time:.1f}s")

    # Recommendation
    print("\n" + "=" * 60)
    print("RECOMMENDATION")
    print("=" * 60)

    scores = {}
    for model in MODELS_TO_TEST:
        model_runs = [r for r in all_results if r["model"] == model]
        successes = [r for r in model_runs if r["success"]]

        if not successes:
            scores[model] = 0
            continue

        # Score based on: success rate, number of chunks, chunk quality
        success_rate = len(successes) / len(model_runs)
        avg_chunks = mean([r["chunks"] for r in successes])
        avg_normal_ratio = mean([r["normal_chunks"] / max(r["chunks"], 1) for r in successes])

        # Ideal: 10-20 chunks for ~3000 words, mostly normal-sized
        chunk_penalty = abs(avg_chunks - 15) / 15  # Penalty for being far from ideal
        score = success_rate * (1 - chunk_penalty * 0.5) * (0.5 + avg_normal_ratio * 0.5)

        scores[model] = score
        print(f"{model}: score={score:.2f} (success={success_rate:.0%}, chunks={avg_chunks:.0f}, normal_ratio={avg_normal_ratio:.0%})")

    best_model = max(scores, key=scores.get)
    print(f"\nBEST MODEL: {best_model}")

    return all_results


if __name__ == "__main__":
    asyncio.run(main())
