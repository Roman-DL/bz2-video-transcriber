"""
Job manager for pipeline processing.

Handles job lifecycle and WebSocket broadcasting for progress updates.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path

from app.models.schemas import ProcessingJob, ProcessingResult, ProcessingStatus

logger = logging.getLogger(__name__)


class JobManager:
    """
    Manager for processing jobs with WebSocket broadcasting.

    Stores jobs in-memory (suitable for MVP).
    Broadcasts progress updates to subscribed WebSocket clients.

    Example:
        manager = JobManager()
        job = manager.create_job(Path("inbox/video.mp4"))

        # Subscribe to updates
        queue = manager.subscribe(job.job_id)

        # Update progress (triggers broadcast)
        await manager.update_progress(
            job.job_id,
            ProcessingStatus.TRANSCRIBING,
            25.0,
            "Transcribing video..."
        )
    """

    def __init__(self):
        """Initialize job manager with empty stores."""
        self._jobs: dict[str, ProcessingJob] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    def create_job(self, video_path: Path) -> ProcessingJob:
        """
        Create a new processing job.

        Args:
            video_path: Path to video file

        Returns:
            Created ProcessingJob with unique ID
        """
        job_id = str(uuid.uuid4())[:8]

        job = ProcessingJob(
            job_id=job_id,
            video_path=video_path,
            status=ProcessingStatus.PENDING,
            progress=0,
            current_stage="",
            created_at=datetime.now(),
        )

        self._jobs[job_id] = job
        self._subscribers[job_id] = []

        logger.info(f"Created job {job_id} for {video_path.name}")
        return job

    def get_job(self, job_id: str) -> ProcessingJob | None:
        """
        Get job by ID.

        Args:
            job_id: Job identifier

        Returns:
            ProcessingJob or None if not found
        """
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[ProcessingJob]:
        """
        List all jobs.

        Returns:
            List of all ProcessingJob objects
        """
        return list(self._jobs.values())

    async def update_progress(
        self,
        job_id: str,
        status: ProcessingStatus,
        progress: float,
        message: str,
    ) -> None:
        """
        Update job progress and broadcast to subscribers.

        Args:
            job_id: Job identifier
            status: Current processing status
            progress: Progress percentage (0-100)
            message: Human-readable status message
        """
        job = self._jobs.get(job_id)
        if not job:
            logger.warning(f"Job {job_id} not found for progress update")
            return

        # Update job state
        job.status = status
        job.progress = progress
        job.current_stage = message

        # Broadcast to subscribers
        await self._broadcast(job_id, {
            "status": status.value,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        })

    async def complete_job(
        self,
        job_id: str,
        result: ProcessingResult,
    ) -> None:
        """
        Mark job as completed with result.

        Args:
            job_id: Job identifier
            result: Processing result
        """
        job = self._jobs.get(job_id)
        if not job:
            logger.warning(f"Job {job_id} not found for completion")
            return

        job.status = ProcessingStatus.COMPLETED
        job.progress = 100
        job.current_stage = "Completed"
        job.completed_at = datetime.now()
        job.result = result

        # Broadcast final message
        await self._broadcast(job_id, {
            "status": ProcessingStatus.COMPLETED.value,
            "progress": 100,
            "message": f"Saved {len(result.files_created)} files",
            "timestamp": datetime.now().isoformat(),
            "result": result.model_dump(mode="json"),
        })

        logger.info(f"Job {job_id} completed: {result.video_id}")

    async def fail_job(
        self,
        job_id: str,
        error: str,
    ) -> None:
        """
        Mark job as failed with error.

        Args:
            job_id: Job identifier
            error: Error message
        """
        job = self._jobs.get(job_id)
        if not job:
            logger.warning(f"Job {job_id} not found for failure")
            return

        job.status = ProcessingStatus.FAILED
        job.error = error
        job.completed_at = datetime.now()

        # Broadcast failure
        await self._broadcast(job_id, {
            "status": ProcessingStatus.FAILED.value,
            "progress": job.progress,
            "message": error,
            "timestamp": datetime.now().isoformat(),
            "error": error,
        })

        logger.error(f"Job {job_id} failed: {error}")

    def subscribe(self, job_id: str) -> asyncio.Queue:
        """
        Subscribe to job progress updates.

        Args:
            job_id: Job identifier

        Returns:
            Queue that will receive progress messages
        """
        queue: asyncio.Queue = asyncio.Queue()

        if job_id not in self._subscribers:
            self._subscribers[job_id] = []

        self._subscribers[job_id].append(queue)
        logger.debug(f"Client subscribed to job {job_id}")

        return queue

    def unsubscribe(self, job_id: str, queue: asyncio.Queue) -> None:
        """
        Unsubscribe from job progress updates.

        Args:
            job_id: Job identifier
            queue: Queue to remove
        """
        if job_id in self._subscribers:
            try:
                self._subscribers[job_id].remove(queue)
                logger.debug(f"Client unsubscribed from job {job_id}")
            except ValueError:
                pass

    async def _broadcast(self, job_id: str, message: dict) -> None:
        """
        Broadcast message to all subscribers of a job.

        Args:
            job_id: Job identifier
            message: Message to broadcast
        """
        subscribers = self._subscribers.get(job_id, [])

        for queue in subscribers:
            try:
                await queue.put(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to subscriber: {e}")


# Global job manager instance
job_manager = JobManager()


def get_job_manager() -> JobManager:
    """Get global job manager instance."""
    return job_manager
