"""
Progress estimator for pipeline stages.

Provides time-based progress estimation for long-running operations.
Uses coefficients from config/performance.yaml.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Awaitable, Callable

from app.config import Settings, get_settings, load_performance_config
from app.models.schemas import ProcessingStatus

logger = logging.getLogger(__name__)

# Type alias for progress callback
# Args: status, progress%, message, estimated_seconds, elapsed_seconds
ProgressCallback = Callable[[ProcessingStatus, float, str, float, float], Awaitable[None]]


@dataclass
class StageEstimate:
    """Estimated time for a pipeline stage."""

    stage: ProcessingStatus
    estimated_seconds: float
    message: str


class ProgressEstimator:
    """
    Estimates progress for pipeline stages based on input metrics.

    Uses performance coefficients to calculate estimated time,
    then interpolates progress percentage over time.

    Example:
        estimator = ProgressEstimator(settings)

        # Before transcription
        estimate = estimator.estimate_transcribe(video_duration=300)

        # Start ticker
        ticker = await estimator.start_ticker(
            stage=ProcessingStatus.TRANSCRIBING,
            estimated_seconds=estimate.estimated_seconds,
            message="Transcribing video",
            callback=progress_callback,
        )

        # After transcription completes
        await estimator.stop_ticker(ticker, ...)

    Attributes:
        settings: Application settings
        config: Performance coefficients from YAML
    """

    def __init__(self, settings: Settings | None = None):
        """
        Initialize progress estimator.

        Args:
            settings: Application settings (uses defaults if None)
        """
        self.settings = settings or get_settings()
        self.config = load_performance_config(self.settings)

    # ═══════════════════════════════════════════════════════════════════════════
    # Estimation Methods
    # ═══════════════════════════════════════════════════════════════════════════

    def estimate_transcribe(self, video_duration_seconds: float) -> StageEstimate:
        """
        Estimate transcription time based on video duration.

        Formula: base_time + (video_duration * factor_per_video_second)

        Args:
            video_duration_seconds: Video duration in seconds

        Returns:
            StageEstimate with estimated time
        """
        cfg = self.config.get("transcribe", {})
        factor = cfg.get("factor_per_video_second", 0.29)
        base = cfg.get("base_time", 5.0)

        estimated = base + (video_duration_seconds * factor)

        return StageEstimate(
            stage=ProcessingStatus.TRANSCRIBING,
            estimated_seconds=estimated,
            message=f"Transcribing ~{video_duration_seconds/60:.0f} min video",
        )

    def estimate_transcribe_by_filesize(self, file_size_bytes: int) -> StageEstimate:
        """
        Estimate transcription time based on file size (fallback).

        Uses heuristic: ~5MB per minute of typical video.

        Args:
            file_size_bytes: Video file size in bytes

        Returns:
            StageEstimate with estimated time
        """
        # Estimate duration: ~5MB per minute = 83333 bytes per second
        estimated_duration = file_size_bytes / 83333
        return self.estimate_transcribe(estimated_duration)

    def estimate_clean(self, input_chars: int) -> StageEstimate:
        """
        Estimate cleaning time based on input text length.

        Formula: base_time + (input_chars / 1000 * factor_per_1k_chars)

        Args:
            input_chars: Number of characters in raw transcript

        Returns:
            StageEstimate with estimated time
        """
        cfg = self.config.get("clean", {})
        factor = cfg.get("factor_per_1k_chars", 1.8)
        base = cfg.get("base_time", 2.0)

        estimated = base + (input_chars / 1000 * factor)

        return StageEstimate(
            stage=ProcessingStatus.CLEANING,
            estimated_seconds=estimated,
            message=f"Cleaning {input_chars:,} chars",
        )

    def estimate_chunk(self, input_chars: int) -> StageEstimate:
        """
        Estimate chunking time based on input text length.

        Formula: base_time + (input_chars / 1000 * factor_per_1k_chars)

        Args:
            input_chars: Number of characters in cleaned transcript

        Returns:
            StageEstimate with estimated time
        """
        cfg = self.config.get("chunk", {})
        factor = cfg.get("factor_per_1k_chars", 6.0)
        base = cfg.get("base_time", 2.0)

        estimated = base + (input_chars / 1000 * factor)

        return StageEstimate(
            stage=ProcessingStatus.CHUNKING,
            estimated_seconds=estimated,
            message=f"Chunking {input_chars:,} chars",
        )

    def estimate_summarize(self, input_chars: int) -> StageEstimate:
        """
        Estimate summarization time based on input text length.

        Formula: base_time + (input_chars / 1000 * factor_per_1k_chars)

        Args:
            input_chars: Number of characters in cleaned transcript

        Returns:
            StageEstimate with estimated time
        """
        cfg = self.config.get("summarize", {})
        factor = cfg.get("factor_per_1k_chars", 10.0)
        base = cfg.get("base_time", 3.0)

        estimated = base + (input_chars / 1000 * factor)

        return StageEstimate(
            stage=ProcessingStatus.SUMMARIZING,
            estimated_seconds=estimated,
            message=f"Summarizing {input_chars:,} chars",
        )

    def get_fixed_stage_time(self, stage: str) -> float:
        """
        Get fixed time for non-estimated stages (parse, save).

        Args:
            stage: Stage name ("parse" or "save")

        Returns:
            Fixed time in seconds
        """
        fixed = self.config.get("fixed_stages", {})
        return fixed.get(stage, 1.0)

    # ═══════════════════════════════════════════════════════════════════════════
    # Progress Ticker
    # ═══════════════════════════════════════════════════════════════════════════

    async def start_ticker(
        self,
        stage: ProcessingStatus,
        estimated_seconds: float,
        message: str,
        callback: ProgressCallback,
        max_progress: float = 95.0,
        interval: float = 1.0,
    ) -> asyncio.Task:
        """
        Start progress ticker that updates every interval.

        The ticker interpolates progress from 0% to max_progress over
        the estimated time. If the operation takes longer, progress
        stays at max_progress until explicitly stopped.

        Args:
            stage: Current processing stage
            estimated_seconds: Estimated time for this stage
            message: Human-readable status message
            callback: Async callback for progress updates
            max_progress: Maximum progress before completion (default 95%)
            interval: Update interval in seconds (default 1.0)

        Returns:
            asyncio.Task that can be cancelled to stop the ticker
        """

        async def ticker_loop():
            start_time = time.time()
            tick_count = 0

            while True:
                elapsed = time.time() - start_time
                tick_count += 1

                # Calculate progress based on elapsed time
                if estimated_seconds > 0:
                    progress = min((elapsed / estimated_seconds) * 100, max_progress)
                else:
                    progress = max_progress

                logger.info(
                    f"Ticker {stage.value}: {progress:.1f}% "
                    f"(tick #{tick_count}, elapsed={elapsed:.1f}s)"
                )

                try:
                    await callback(stage, progress, message, estimated_seconds, elapsed)
                except Exception as e:
                    logger.warning(f"Ticker callback error: {e}")

                await asyncio.sleep(interval)

        task = asyncio.create_task(ticker_loop())
        logger.info(
            f"Started ticker for {stage.value}, estimated: {estimated_seconds:.1f}s"
        )
        return task

    async def stop_ticker(
        self,
        ticker: asyncio.Task | None,
        stage: ProcessingStatus,
        callback: ProgressCallback,
        message: str,
        estimated_seconds: float = 0.0,
        actual_seconds: float = 0.0,
    ) -> None:
        """
        Stop progress ticker and send 100% completion.

        Args:
            ticker: Task to cancel (may be None)
            stage: Stage that completed
            callback: Async callback for final progress update
            message: Completion message
            estimated_seconds: Original estimated time (for logging)
            actual_seconds: Actual elapsed time (for logging)
        """
        if ticker is not None:
            ticker.cancel()
            try:
                await ticker
            except asyncio.CancelledError:
                pass

        # Send final 100% progress (elapsed equals estimated at 100%)
        try:
            await callback(stage, 100, message, actual_seconds, actual_seconds)
        except Exception as e:
            logger.warning(f"Final callback error: {e}")

        # Log accuracy for future calibration
        if estimated_seconds > 0 and actual_seconds > 0:
            ratio = actual_seconds / estimated_seconds
            logger.info(
                f"PERF | {stage.value} | "
                f"estimated={estimated_seconds:.1f}s | "
                f"actual={actual_seconds:.1f}s | "
                f"ratio={ratio:.2f}"
            )

        logger.debug(f"Stopped ticker for {stage.value}")
