"""
Progress management for pipeline stages.

Calculates overall progress based on stage weights and tracks
individual stage progress.

v0.25+: Updated stage order - Longread/Summary before Chunk (now instant).
"""

import logging
from typing import Awaitable, Callable

from app.models.schemas import ProcessingStatus

logger = logging.getLogger(__name__)

# Type alias for progress callback
# Signature: (status, progress_percent, message) -> None
ProgressCallback = Callable[[ProcessingStatus, float, str], Awaitable[None]]


class ProgressManager:
    """
    Manages progress calculation and reporting for pipeline stages.

    v0.25+: Updated for new pipeline order:
        Parse -> Transcribe -> Clean -> Longread -> Summary -> Chunk -> Save

    Weights calibrated from PERF logs (v6, 2026-02-20, Claude models):
    - transcribe: ~200s (Whisper, from v4 data)
    - clean: ~340s (Claude haiku, 60K chars)
    - longread: ~220s (Claude sonnet, single-pass 62-70K chars)
    - summary: ~84s (Claude sonnet, 50K chars, includes retry)
    - chunk: <1s (deterministic H2 parsing)
    - save: <1s

    Example:
        manager = ProgressManager()
        overall = manager.calculate_overall_progress(
            ProcessingStatus.TRANSCRIBING, 50
        )  # Returns ~12.5 (1 + 11.5)
    """

    # Progress weights for each stage (must sum to 100)
    # v7: Added SLIDES (optional, 0 when skipped). Calibrated for Claude pipeline.
    STAGE_WEIGHTS = {
        ProcessingStatus.PARSING: 1,        # 0-1%: instant
        ProcessingStatus.TRANSCRIBING: 23,  # 1-24%: Whisper (~200s)
        ProcessingStatus.CLEANING: 38,      # 24-62%: Claude haiku (~340s)
        ProcessingStatus.SLIDES: 0,         # Optional: 0 when skipped
        ProcessingStatus.LONGREAD: 25,      # 62-87%: Claude sonnet single-pass (~220s)
        ProcessingStatus.SUMMARIZING: 9,    # 87-96%: Claude sonnet (~84s)
        ProcessingStatus.CHUNKING: 2,       # 96-98%: instant (H2 parsing)
        ProcessingStatus.SAVING: 2,         # 98-100%: instant
    }

    # Define stage order for progress calculation
    # v0.84+: Added SLIDES between CLEANING and LONGREAD
    STAGE_ORDER = [
        ProcessingStatus.PARSING,
        ProcessingStatus.TRANSCRIBING,
        ProcessingStatus.CLEANING,
        ProcessingStatus.SLIDES,
        ProcessingStatus.LONGREAD,
        ProcessingStatus.SUMMARIZING,
        ProcessingStatus.CHUNKING,
        ProcessingStatus.SAVING,
    ]

    def calculate_overall_progress(
        self,
        current_stage: ProcessingStatus,
        stage_progress: float = 100,
    ) -> float:
        """
        Calculate overall progress percentage.

        Args:
            current_stage: Current processing stage
            stage_progress: Progress within current stage (0-100)

        Returns:
            Overall progress (0-100)
        """
        # Calculate base progress from completed stages
        base_progress = 0.0
        for stage in self.STAGE_ORDER:
            if stage == current_stage:
                break
            base_progress += self.STAGE_WEIGHTS.get(stage, 0)

        # Add current stage progress
        current_weight = self.STAGE_WEIGHTS.get(current_stage, 0)
        stage_contribution = (stage_progress / 100) * current_weight

        return min(base_progress + stage_contribution, 100)

    async def update_progress(
        self,
        callback: ProgressCallback | None,
        status: ProcessingStatus,
        stage_progress: float,
        message: str,
    ) -> None:
        """
        Update progress via callback.

        Args:
            callback: Progress callback (may be None)
            status: Current processing status
            stage_progress: Progress within current stage (0-100)
            message: Human-readable status message
        """
        if callback is None:
            return

        overall_progress = self.calculate_overall_progress(status, stage_progress)

        try:
            await callback(status, overall_progress, message)
        except Exception as e:
            # Never fail due to callback error
            logger.warning(f"Progress callback error: {e}")

    def get_stage_weight(self, stage: ProcessingStatus) -> int:
        """Get weight for a specific stage."""
        return self.STAGE_WEIGHTS.get(stage, 0)

    def get_stage_start_percent(self, stage: ProcessingStatus) -> float:
        """Get the starting percentage for a stage."""
        return self.calculate_overall_progress(stage, 0)

    def get_stage_end_percent(self, stage: ProcessingStatus) -> float:
        """Get the ending percentage for a stage."""
        return self.calculate_overall_progress(stage, 100)


if __name__ == "__main__":
    """Run tests when executed directly."""
    import asyncio

    async def run_tests():
        print("\nRunning ProgressManager tests (v0.25+)...\n")

        manager = ProgressManager()

        # Test 1: Stage weights sum to 100
        print("Test 1: Stage weights sum...", end=" ")
        total = sum(manager.STAGE_WEIGHTS.values())
        assert total == 100, f"Expected 100, got {total}"
        print("OK")

        # Test 2: PARSING at 0%
        print("Test 2: PARSING at 0%...", end=" ")
        progress = manager.calculate_overall_progress(ProcessingStatus.PARSING, 0)
        assert progress == 0, f"Expected 0, got {progress}"
        print("OK")

        # Test 3: PARSING at 100%
        print("Test 3: PARSING at 100%...", end=" ")
        progress = manager.calculate_overall_progress(ProcessingStatus.PARSING, 100)
        assert progress == 1, f"Expected 1, got {progress}"
        print("OK")

        # Test 4: TRANSCRIBING at 50%
        print("Test 4: TRANSCRIBING at 50%...", end=" ")
        progress = manager.calculate_overall_progress(ProcessingStatus.TRANSCRIBING, 50)
        expected = 1 + 11.5  # Base (PARSING=1) + 50% of TRANSCRIBING (23*0.5)
        assert abs(progress - expected) < 0.1, f"Expected {expected}, got {progress}"
        print("OK")

        # Test 5: SAVING at 0% (v0.25+: new order)
        print("Test 5: SAVING at 0%...", end=" ")
        progress = manager.calculate_overall_progress(ProcessingStatus.SAVING, 0)
        # v6: PARSING(1) + TRANSCRIBING(23) + CLEANING(38) + LONGREAD(25) + SUMMARIZING(9) + CHUNKING(2) = 98
        expected = 1 + 23 + 38 + 25 + 9 + 2  # 98
        assert progress == expected, f"Expected {expected}, got {progress}"
        print("OK")

        # Test 6: SAVING at 100%
        print("Test 6: SAVING at 100%...", end=" ")
        progress = manager.calculate_overall_progress(ProcessingStatus.SAVING, 100)
        assert progress == 100, f"Expected 100, got {progress}"
        print("OK")

        # Test 7: Update progress with callback
        print("Test 7: Update progress with callback...", end=" ")
        received = []

        async def test_callback(status, progress, message):
            received.append((status, progress, message))

        await manager.update_progress(
            test_callback, ProcessingStatus.CLEANING, 50, "Test"
        )
        assert len(received) == 1
        assert received[0][0] == ProcessingStatus.CLEANING
        # PARSING(1) + TRANSCRIBING(23) + 50% of CLEANING(38*0.5=19) = 43
        assert received[0][1] == 43, f"Expected 43, got {received[0][1]}"
        print("OK")

        # Test 8: Update progress with None callback (no error)
        print("Test 8: Update progress with None callback...", end=" ")
        await manager.update_progress(None, ProcessingStatus.PARSING, 50, "Test")
        print("OK")

        # Test 9: Stage order (v0.25+)
        print("Test 9: Stage order (v0.25+)...", end=" ")
        order = manager.STAGE_ORDER
        # Verify LONGREAD comes before CHUNKING
        longread_idx = order.index(ProcessingStatus.LONGREAD)
        chunking_idx = order.index(ProcessingStatus.CHUNKING)
        assert longread_idx < chunking_idx, "LONGREAD must come before CHUNKING"
        print("OK")

        print("\n" + "=" * 40)
        print("All ProgressManager tests passed!")
        return 0

    asyncio.run(run_tests())
