#!/usr/bin/env python3
"""
Comprehensive LLM model testing for pipeline stages.

Tests models with /no_think support for cleaner and summarizer.

v0.26: Chunker tests removed - chunking is now deterministic (H2 parsing).

Two modes:
- stage: Test one stage with all models (default)
- pipeline: Run full pipeline per-model (cleaner → summarizer)

Usage:
    # Stage mode: test cleaner with all models
    docker exec -it bz2-transcriber python3 /tmp/test_models_comprehensive.py --stage cleaner

    # Pipeline mode: run full chain per model
    docker exec -it bz2-transcriber python3 /tmp/test_models_comprehensive.py --mode pipeline
"""

import argparse
import asyncio
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, stdev

# Add app to path
sys.path.insert(0, '/app')

from app.config import Settings, get_settings, load_prompt
from app.models.schemas import CleanedTranscript, RawTranscript, TranscriptSegment, VideoMetadata
from app.services.ai_client import AIClient
from app.services.cleaner import TranscriptCleaner
from app.services.summarizer import VideoSummarizer


# =============================================================================
# Configuration
# =============================================================================

# Test data - existing transcript from previous run
TEST_DATA_PATH = "/data/archive/2025/12.22 ПШ/SV Закрытие ПО, возражения (Кухаренко Женя)/transcript_raw.txt"

# Models to test
# NOTE: Chunker tests removed in v0.26 - chunking is now deterministic (H2 parsing)
CLEANER_MODELS = ["gemma2:9b", "qwen3:14b"]
SUMMARIZER_MODELS = ["qwen2.5:14b", "qwen3:14b"]

# Models that support /no_think
NO_THINK_MODELS = ["qwen3:14b"]


# =============================================================================
# Data structures
# =============================================================================

@dataclass
class CleanerResult:
    """Result of a single cleaner test run."""
    model: str
    no_think: bool
    run: int
    success: bool
    input_chars: int
    output_chars: int
    compression: float  # percentage
    cyrillic_ratio: float  # 0-1
    sentence_ratio: float  # output/input sentences
    time_seconds: float
    error: str | None = None


@dataclass
class SummarizerResult:
    """Result of a single summarizer test run."""
    model: str
    no_think: bool
    run: int
    success: bool
    json_valid: bool
    summary_len: int  # words in summary
    key_points: int
    section: str
    tags: int
    time_seconds: float
    error: str | None = None


@dataclass
class PipelineResult:
    """Result of a full pipeline run (cleaner → summarizer).

    v0.26: Chunker removed - chunking is now deterministic (H2 parsing).
    """
    model: str
    no_think: bool
    run: int
    # Cleaner metrics
    cleaner_success: bool
    cleaner_compression: float
    cleaner_cyrillic: float
    cleaner_time: float
    cleaned_text: str | None  # For passing to next stage
    # Summarizer metrics (optional - may skip if previous failed)
    summarizer_success: bool
    summarizer_len: int
    summarizer_key_points: int
    summarizer_time: float
    # Total
    total_time: float
    errors: list[str]


# =============================================================================
# Utility functions
# =============================================================================

def count_sentences(text: str) -> int:
    """Count sentences in text using punctuation."""
    # Split on sentence-ending punctuation
    sentences = re.split(r'[.!?]+', text)
    return len([s for s in sentences if s.strip()])


def count_cyrillic_ratio(text: str) -> float:
    """Calculate ratio of Cyrillic characters in text."""
    if not text:
        return 0.0
    cyrillic = len(re.findall(r'[а-яА-ЯёЁ]', text))
    return cyrillic / len(text)


def strip_timestamps(text: str) -> str:
    """Remove timestamps like [00:12:34] from transcript.

    This improves LLM processing - models work better with clean text.
    See docs/research/Обработка_длинных_транскриптов.md section 3.4.
    """
    # Pattern: [HH:MM:SS] or [MM:SS]
    cleaned = re.sub(r'\[\d{1,2}:\d{2}(:\d{2})?\]\s*', '', text)
    # Remove multiple spaces
    cleaned = re.sub(r' +', ' ', cleaned)
    # Remove empty lines
    cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
    return cleaned.strip()


def load_test_transcript(strip_ts: bool = True) -> str:
    """Load test transcript from file.

    Args:
        strip_ts: If True, remove timestamps from transcript (default: True)
    """
    path = Path(TEST_DATA_PATH)
    if not path.exists():
        raise FileNotFoundError(f"Test data not found: {TEST_DATA_PATH}")
    text = path.read_text(encoding='utf-8')
    if strip_ts:
        original_len = len(text)
        text = strip_timestamps(text)
        print(f"  Stripped timestamps: {original_len} -> {len(text)} chars ({100 - len(text)*100//original_len}% reduction)")
    return text


def create_mock_metadata() -> VideoMetadata:
    """Create mock metadata for testing."""
    from datetime import date
    return VideoMetadata(
        date=date(2025, 12, 22),
        event_type="ПШ",
        stream="SV",
        title="Закрытие ПО, возражения",
        speaker="Кухаренко Женя",
        original_filename="test.mp4",
        video_id="test-qwen3-model",
        source_path=Path("/test/test.mp4"),
        archive_path=Path("/archive/test"),
    )


def create_raw_transcript(text: str) -> RawTranscript:
    """Create RawTranscript from text."""
    # Split into pseudo-segments (one per line or paragraph)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    segments = []
    current_time = 0.0

    for line in lines:
        duration = len(line) / 20  # ~20 chars per second estimate
        segments.append(TranscriptSegment(
            start=current_time,
            end=current_time + duration,
            text=line
        ))
        current_time += duration

    return RawTranscript(
        segments=segments,
        language="ru",
        duration_seconds=current_time,
        whisper_model="large-v3",
    )


# =============================================================================
# Cleaner testing
# =============================================================================

class CleanerTester:
    """Cleaner test runner with /no_think support."""

    def __init__(self, ai_client: AIClient, settings: Settings):
        self.ai_client = ai_client
        self.settings = settings

    async def test(
        self,
        raw_transcript: RawTranscript,
        metadata: VideoMetadata,
        model: str,
        no_think: bool = False,
        run_num: int = 1
    ) -> CleanerResult:
        """Run a single cleaner test."""
        input_text = raw_transcript.full_text
        input_chars = len(input_text)
        input_sentences = count_sentences(input_text)

        start_time = time.time()

        try:
            # Create cleaner with patched settings
            cleaner = TranscriptCleaner(self.ai_client, self.settings)
            cleaner.settings.cleaner_model = model

            # Patch user template for /no_think (must be at START of user message)
            if no_think:
                cleaner.user_template = "/no_think\n" + cleaner.user_template

            # Run cleaning
            result = await cleaner.clean(raw_transcript, metadata)
            elapsed = time.time() - start_time

            # Calculate metrics
            output_chars = result.cleaned_length
            compression = (1 - output_chars / input_chars) * 100
            cyrillic_ratio = count_cyrillic_ratio(result.text)
            output_sentences = count_sentences(result.text)
            sentence_ratio = output_sentences / input_sentences if input_sentences > 0 else 0

            return CleanerResult(
                model=model,
                no_think=no_think,
                run=run_num,
                success=True,
                input_chars=input_chars,
                output_chars=output_chars,
                compression=round(compression, 1),
                cyrillic_ratio=round(cyrillic_ratio, 2),
                sentence_ratio=round(sentence_ratio, 2),
                time_seconds=round(elapsed, 1),
            )

        except Exception as e:
            elapsed = time.time() - start_time
            return CleanerResult(
                model=model,
                no_think=no_think,
                run=run_num,
                success=False,
                input_chars=input_chars,
                output_chars=0,
                compression=0,
                cyrillic_ratio=0,
                sentence_ratio=0,
                time_seconds=round(elapsed, 1),
                error=str(e)[:200],
            )


# =============================================================================
# Summarizer testing
# =============================================================================

class SummarizerTester:
    """Summarizer test runner with /no_think support."""

    def __init__(self, ai_client: AIClient, settings: Settings):
        self.ai_client = ai_client
        self.settings = settings

    async def test(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
        model: str,
        no_think: bool = False,
        run_num: int = 1
    ) -> SummarizerResult:
        """Run a single summarizer test."""
        start_time = time.time()

        try:
            # Create summarizer with patched settings
            summarizer = VideoSummarizer(self.ai_client, self.settings)
            summarizer.settings.llm_model = model

            # Patch prompt template for /no_think (must be at START)
            if no_think:
                summarizer.prompt_template = "/no_think\n" + summarizer.prompt_template

            # Run summarization (small text mode - no outline)
            result = await summarizer.summarize(
                outline=None,
                metadata=metadata,
                cleaned_transcript=cleaned_transcript,
            )
            elapsed = time.time() - start_time

            # Calculate metrics
            summary_words = len(result.summary.split())

            return SummarizerResult(
                model=model,
                no_think=no_think,
                run=run_num,
                success=True,
                json_valid=True,
                summary_len=summary_words,
                key_points=len(result.key_points),
                section=result.section,
                tags=len(result.tags),
                time_seconds=round(elapsed, 1),
            )

        except Exception as e:
            elapsed = time.time() - start_time
            json_valid = "JSON" not in str(e)
            return SummarizerResult(
                model=model,
                no_think=no_think,
                run=run_num,
                success=False,
                json_valid=json_valid,
                summary_len=0,
                key_points=0,
                section="",
                tags=0,
                time_seconds=round(elapsed, 1),
                error=str(e)[:200],
            )


# =============================================================================
# Result aggregation and reporting
# =============================================================================

def aggregate_cleaner_results(results: list[CleanerResult]) -> dict:
    """Aggregate multiple cleaner runs into summary statistics."""
    successes = [r for r in results if r.success]
    if not successes:
        return {
            "success_rate": 0,
            "avg_compression": 0,
            "avg_cyrillic": 0,
            "avg_sentences": 0,
            "avg_time": 0,
        }

    return {
        "success_rate": len(successes) / len(results),
        "avg_compression": mean([r.compression for r in successes]),
        "avg_cyrillic": mean([r.cyrillic_ratio for r in successes]),
        "avg_sentences": mean([r.sentence_ratio for r in successes]),
        "avg_time": mean([r.time_seconds for r in successes]),
    }


def print_cleaner_report(all_results: dict[str, list[CleanerResult]]):
    """Print cleaner test report."""
    print("\n" + "=" * 70)
    print("CLEANER RESULTS")
    print("=" * 70)
    print()
    print("| Model | NoThink | Success | Compress | Cyrillic | Sentences | Time |")
    print("|-------|---------|---------|----------|----------|-----------|------|")

    for key, results in all_results.items():
        model, no_think = key.rsplit("_", 1)
        no_think_str = "Yes" if no_think == "nothink" else "No"
        stats = aggregate_cleaner_results(results)

        print(
            f"| {model:13} | {no_think_str:7} | "
            f"{stats['success_rate']*100:5.0f}% | "
            f"{stats['avg_compression']:6.1f}% | "
            f"{stats['avg_cyrillic']*100:6.0f}% | "
            f"{stats['avg_sentences']*100:7.0f}% | "
            f"{stats['avg_time']:4.1f}s |"
        )

    print()


def aggregate_summarizer_results(results: list[SummarizerResult]) -> dict:
    """Aggregate multiple summarizer runs into summary statistics."""
    successes = [r for r in results if r.success]
    if not successes:
        return {
            "success_rate": 0,
            "json_valid_rate": 0,
            "avg_summary_len": 0,
            "avg_key_points": 0,
            "avg_tags": 0,
            "avg_time": 0,
        }

    return {
        "success_rate": len(successes) / len(results),
        "json_valid_rate": sum(1 for r in results if r.json_valid) / len(results),
        "avg_summary_len": mean([r.summary_len for r in successes]),
        "avg_key_points": mean([r.key_points for r in successes]),
        "avg_tags": mean([r.tags for r in successes]),
        "avg_time": mean([r.time_seconds for r in successes]),
    }


def print_summarizer_report(all_results: dict[str, list[SummarizerResult]]):
    """Print summarizer test report."""
    print("\n" + "=" * 70)
    print("SUMMARIZER RESULTS")
    print("=" * 70)
    print()
    print("| Model | NoThink | Success | JSON | Summary | KeyPts | Tags | Time |")
    print("|-------|---------|---------|------|---------|--------|------|------|")

    for key, results in all_results.items():
        model, no_think = key.rsplit("_", 1)
        no_think_str = "Yes" if no_think == "nothink" else "No"
        stats = aggregate_summarizer_results(results)

        print(
            f"| {model:13} | {no_think_str:7} | "
            f"{stats['success_rate']*100:5.0f}% | "
            f"{stats['json_valid_rate']*100:3.0f}% | "
            f"{stats['avg_summary_len']:5.0f}w | "
            f"{stats['avg_key_points']:4.0f} | "
            f"{stats['avg_tags']:4.0f} | "
            f"{stats['avg_time']:4.1f}s |"
        )

    print()


def print_pipeline_report(all_results: dict[str, list[PipelineResult]]):
    """Print full pipeline test report.

    v0.26: Chunker removed - pipeline is now cleaner → summarizer.
    """
    print("\n" + "=" * 90)
    print("PIPELINE RESULTS (per-model full chain)")
    print("=" * 90)
    print()

    for key, results in all_results.items():
        model, no_think = key.rsplit("_", 1)
        no_think_str = "/no_think" if no_think == "nothink" else "standard"

        print(f"\n### {model} ({no_think_str})")
        print("-" * 70)

        for r in results:
            print(f"\nRun {r.run}:")
            print(f"  Cleaner:    {'OK' if r.cleaner_success else 'FAIL'} | "
                  f"compress={r.cleaner_compression:.1f}% | "
                  f"cyrillic={r.cleaner_cyrillic*100:.0f}% | "
                  f"time={r.cleaner_time:.1f}s")

            if r.cleaner_success:
                print(f"  Summarizer: {'OK' if r.summarizer_success else 'FAIL'} | "
                      f"len={r.summarizer_len}w | "
                      f"key_pts={r.summarizer_key_points} | "
                      f"time={r.summarizer_time:.1f}s")
            else:
                print(f"  Summarizer: SKIPPED (cleaner failed)")

            print(f"  TOTAL:      {r.total_time:.1f}s")

            if r.errors:
                for err in r.errors:
                    print(f"  ERROR: {err}")

    # Summary table
    print("\n" + "=" * 90)
    print("SUMMARY TABLE")
    print("=" * 90)
    print()
    print("| Model | NoThink | Clean | Summ | Total Time |")
    print("|-------|---------|-------|------|------------|")

    for key, results in all_results.items():
        model, no_think = key.rsplit("_", 1)
        no_think_str = "Yes" if no_think == "nothink" else "No"

        clean_ok = sum(1 for r in results if r.cleaner_success)
        summ_ok = sum(1 for r in results if r.summarizer_success)
        total = len(results)
        avg_time = mean([r.total_time for r in results])

        print(
            f"| {model:13} | {no_think_str:7} | "
            f"{clean_ok}/{total} | "
            f"{summ_ok}/{total} | "
            f"{avg_time:8.1f}s |"
        )

    print()


# =============================================================================
# Main test runners
# =============================================================================

async def run_cleaner_tests(ai_client: AIClient, settings: Settings, num_runs: int = 3, strip_ts: bool = True) -> dict[str, list[CleanerResult]]:
    """Run all cleaner tests."""
    print("\n" + "=" * 70)
    print("TESTING CLEANER")
    print("=" * 70)

    # Load test data
    print("\nLoading test transcript...")
    transcript_text = load_test_transcript(strip_ts=strip_ts)
    raw_transcript = create_raw_transcript(transcript_text)
    metadata = create_mock_metadata()
    print(f"  Loaded: {len(transcript_text)} chars, {len(raw_transcript.segments)} segments")

    tester = CleanerTester(ai_client, settings)
    all_results: dict[str, list[CleanerResult]] = {}

    for model in CLEANER_MODELS:
        # Test without /no_think
        print(f"\n--- {model} (standard) ---")
        key = f"{model}_standard"
        all_results[key] = []

        for run in range(1, num_runs + 1):
            print(f"  Run {run}/{num_runs}...", end=" ", flush=True)
            result = await tester.test(raw_transcript, metadata, model, no_think=False, run_num=run)
            all_results[key].append(result)

            if result.success:
                print(f"OK: {result.compression:.1f}% compression, {result.cyrillic_ratio*100:.0f}% cyrillic")
            else:
                print(f"FAILED: {result.error}")

        # Test with /no_think if supported
        if model in NO_THINK_MODELS:
            print(f"\n--- {model} (/no_think) ---")
            key = f"{model}_nothink"
            all_results[key] = []

            for run in range(1, num_runs + 1):
                print(f"  Run {run}/{num_runs}...", end=" ", flush=True)
                result = await tester.test(raw_transcript, metadata, model, no_think=True, run_num=run)
                all_results[key].append(result)

                if result.success:
                    print(f"OK: {result.compression:.1f}% compression, {result.cyrillic_ratio*100:.0f}% cyrillic")
                else:
                    print(f"FAILED: {result.error}")

    return all_results


async def run_summarizer_tests(
    ai_client: AIClient,
    settings: Settings,
    num_runs: int = 3,
    cleaned_text: str | None = None,
    strip_ts: bool = True
) -> dict[str, list[SummarizerResult]]:
    """Run all summarizer tests."""
    print("\n" + "=" * 70)
    print("TESTING SUMMARIZER")
    print("=" * 70)

    # Use provided cleaned text or load from file
    if cleaned_text is None:
        print("\nLoading test transcript (will clean first)...")
        transcript_text = load_test_transcript(strip_ts=strip_ts)
        raw_transcript = create_raw_transcript(transcript_text)
        metadata = create_mock_metadata()

        # Clean with baseline model first
        cleaner = TranscriptCleaner(ai_client, settings)
        cleaned_result = await cleaner.clean(raw_transcript, metadata)
        cleaned_text = cleaned_result.text
        print(f"  Cleaned: {len(cleaned_text)} chars")

    metadata = create_mock_metadata()
    cleaned_transcript = CleanedTranscript(
        text=cleaned_text,
        original_length=len(cleaned_text),
        cleaned_length=len(cleaned_text),
        model_name="test",
    )

    tester = SummarizerTester(ai_client, settings)
    all_results: dict[str, list[SummarizerResult]] = {}

    for model in SUMMARIZER_MODELS:
        # Test without /no_think
        print(f"\n--- {model} (standard) ---")
        key = f"{model}_standard"
        all_results[key] = []

        for run in range(1, num_runs + 1):
            print(f"  Run {run}/{num_runs}...", end=" ", flush=True)
            result = await tester.test(cleaned_transcript, metadata, model, no_think=False, run_num=run)
            all_results[key].append(result)

            if result.success:
                print(f"OK: {result.summary_len}w summary, {result.key_points} pts, section={result.section}")
            else:
                print(f"FAILED: {result.error}")

        # Test with /no_think if supported
        if model in NO_THINK_MODELS:
            print(f"\n--- {model} (/no_think) ---")
            key = f"{model}_nothink"
            all_results[key] = []

            for run in range(1, num_runs + 1):
                print(f"  Run {run}/{num_runs}...", end=" ", flush=True)
                result = await tester.test(cleaned_transcript, metadata, model, no_think=True, run_num=run)
                all_results[key].append(result)

                if result.success:
                    print(f"OK: {result.summary_len}w summary, {result.key_points} pts, section={result.section}")
                else:
                    print(f"FAILED: {result.error}")

    return all_results


# Models to test in pipeline mode
PIPELINE_MODELS = ["gemma2:9b", "qwen3:14b"]


async def run_pipeline_tests(
    ai_client: AIClient,
    settings: Settings,
    num_runs: int = 1,
    strip_ts: bool = True
) -> dict[str, list[PipelineResult]]:
    """Run full pipeline per model: cleaner → summarizer.

    v0.26: Chunker removed - chunking is now deterministic (H2 parsing).

    Each model runs its own cleaned text through summarizer,
    allowing fair comparison of end-to-end performance.
    """
    print("\n" + "=" * 90)
    print("PIPELINE MODE: Full chain per model")
    print("=" * 90)

    # Load test data
    print("\nLoading test transcript...")
    transcript_text = load_test_transcript(strip_ts=strip_ts)
    raw_transcript = create_raw_transcript(transcript_text)
    metadata = create_mock_metadata()
    print(f"  Loaded: {len(transcript_text)} chars, {len(raw_transcript.segments)} segments")

    all_results: dict[str, list[PipelineResult]] = {}

    for model in PIPELINE_MODELS:
        # Test configurations: standard and /no_think (if supported)
        configs = [("standard", False)]
        if model in NO_THINK_MODELS:
            configs.append(("nothink", True))

        for config_name, no_think in configs:
            key = f"{model}_{config_name}"
            all_results[key] = []
            no_think_label = " (/no_think)" if no_think else ""

            print(f"\n{'='*70}")
            print(f"MODEL: {model}{no_think_label}")
            print(f"{'='*70}")

            for run_num in range(1, num_runs + 1):
                print(f"\n--- Run {run_num}/{num_runs} ---")
                start_total = time.time()
                errors: list[str] = []

                # === STAGE 1: CLEANER ===
                print(f"\n[1/2] Cleaner...", end=" ", flush=True)
                cleaner_start = time.time()

                try:
                    cleaner = TranscriptCleaner(ai_client, settings)
                    cleaner.settings.cleaner_model = model
                    if no_think:
                        cleaner.user_template = "/no_think\n" + cleaner.user_template

                    cleaned_result = await cleaner.clean(raw_transcript, metadata)
                    cleaner_time = time.time() - cleaner_start

                    compression = (1 - cleaned_result.cleaned_length / len(transcript_text)) * 100
                    cyrillic = count_cyrillic_ratio(cleaned_result.text)

                    print(f"OK ({compression:.1f}% compress, {cyrillic*100:.0f}% cyrillic, {cleaner_time:.1f}s)")
                    cleaner_success = True
                    cleaned_text = cleaned_result.text

                except Exception as e:
                    cleaner_time = time.time() - cleaner_start
                    print(f"FAILED: {str(e)[:100]}")
                    errors.append(f"Cleaner: {str(e)[:100]}")
                    cleaner_success = False
                    compression = 0
                    cyrillic = 0
                    cleaned_text = None

                # === STAGE 2: SUMMARIZER ===
                summarizer_success = False
                summarizer_len = 0
                summarizer_key_points = 0
                summarizer_time = 0

                if cleaner_success and cleaned_text:
                    print(f"[2/2] Summarizer...", end=" ", flush=True)
                    summarizer_start = time.time()

                    try:
                        # Use cleaned transcript for summarizer (small text mode)
                        cleaned_for_summ = CleanedTranscript(
                            text=cleaned_text,
                            original_length=len(cleaned_text),
                            cleaned_length=len(cleaned_text),
                            model_name=model,
                        )

                        summarizer = VideoSummarizer(ai_client, settings)
                        summarizer.settings.llm_model = model
                        if no_think:
                            summarizer.prompt_template = "/no_think\n" + summarizer.prompt_template

                        summ_result = await summarizer.summarize(
                            outline=None,
                            metadata=metadata,
                            cleaned_transcript=cleaned_for_summ,
                        )
                        summarizer_time = time.time() - summarizer_start

                        summarizer_len = len(summ_result.summary.split())
                        summarizer_key_points = len(summ_result.key_points)

                        print(f"OK ({summarizer_len}w, {summarizer_key_points} pts, {summarizer_time:.1f}s)")
                        summarizer_success = True

                    except Exception as e:
                        summarizer_time = time.time() - summarizer_start
                        print(f"FAILED: {str(e)[:100]}")
                        errors.append(f"Summarizer: {str(e)[:100]}")
                else:
                    print(f"[2/2] Summarizer... SKIPPED (cleaner failed)")

                total_time = time.time() - start_total

                result = PipelineResult(
                    model=model,
                    no_think=no_think,
                    run=run_num,
                    cleaner_success=cleaner_success,
                    cleaner_compression=compression,
                    cleaner_cyrillic=cyrillic,
                    cleaner_time=cleaner_time,
                    cleaned_text=cleaned_text,
                    summarizer_success=summarizer_success,
                    summarizer_len=summarizer_len,
                    summarizer_key_points=summarizer_key_points,
                    summarizer_time=summarizer_time,
                    total_time=total_time,
                    errors=errors,
                )
                all_results[key].append(result)

                print(f"\nTotal: {total_time:.1f}s | "
                      f"Clean={'OK' if cleaner_success else 'FAIL'} | "
                      f"Summ={'OK' if summarizer_success else 'FAIL'}")

    return all_results


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Comprehensive LLM model testing")
    parser.add_argument(
        "--mode",
        choices=["stage", "pipeline"],
        default="stage",
        help="Test mode: 'stage' tests one stage with all models, 'pipeline' runs full chain per model"
    )
    parser.add_argument(
        "--stage",
        choices=["cleaner", "summarizer", "all"],
        default="cleaner",
        help="Which stage to test in stage mode (default: cleaner). Note: chunker removed in v0.26."
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of runs per configuration (default: 3)"
    )
    parser.add_argument(
        "--no-strip-timestamps",
        action="store_true",
        help="Keep timestamps in transcript (default: strip them)"
    )
    args = parser.parse_args()

    num_runs = args.runs
    strip_ts = not args.no_strip_timestamps

    print("=" * 70)
    print("COMPREHENSIVE MODEL TESTING")
    print("=" * 70)
    print(f"\nMode: {args.mode}")
    if args.mode == "stage":
        print(f"Stage: {args.stage}")
    print(f"Runs per config: {num_runs}")
    print(f"Strip timestamps: {strip_ts}")
    print(f"Test data: {TEST_DATA_PATH}")

    settings = get_settings()

    async with AIClient(settings) as ai_client:
        # Check services
        status = await ai_client.check_services()
        if not status["ollama"]:
            print("\nERROR: Ollama not available!")
            return 1

        print(f"\nOllama: OK")

        if args.mode == "pipeline":
            # Pipeline mode: run full chain per model
            pipeline_results = await run_pipeline_tests(ai_client, settings, num_runs, strip_ts)
            print_pipeline_report(pipeline_results)
        else:
            # Stage mode: test one stage with all models
            if args.stage in ["cleaner", "all"]:
                cleaner_results = await run_cleaner_tests(ai_client, settings, num_runs, strip_ts)
                print_cleaner_report(cleaner_results)

            if args.stage in ["summarizer", "all"]:
                summarizer_results = await run_summarizer_tests(ai_client, settings, num_runs, strip_ts=strip_ts)
                print_summarizer_report(summarizer_results)

    print("\n" + "=" * 70)
    print("TESTING COMPLETE")
    print("=" * 70)
    print("\nUpdate RFC with results: docs/proposals/qwen3-model-testing.md")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
