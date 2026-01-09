"""
WebSocket handler for real-time progress updates.

Provides live streaming of pipeline processing progress.
"""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.schemas import ProcessingStatus
from app.services.job_manager import get_job_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/{job_id}")
async def job_progress_websocket(websocket: WebSocket, job_id: str) -> None:
    """
    WebSocket endpoint for real-time job progress updates.

    Connect to receive streaming progress updates for a specific job.
    Messages are JSON objects with status, progress, message, and timestamp.

    Connection automatically closes when job completes or fails.

    Example client (Python):
        async with websockets.connect(f"ws://localhost:8801/ws/{job_id}") as ws:
            async for message in ws:
                data = json.loads(message)
                print(f"{data['status']}: {data['progress']}% - {data['message']}")

    Args:
        websocket: WebSocket connection
        job_id: Job identifier to subscribe to
    """
    job_manager = get_job_manager()

    # Check if job exists
    job = job_manager.get_job(job_id)
    if not job:
        await websocket.close(code=4004, reason=f"Job not found: {job_id}")
        return

    await websocket.accept()
    logger.info(f"WebSocket connected for job {job_id}")

    # Send current job state immediately
    await websocket.send_json({
        "status": job.status.value,
        "progress": job.progress,
        "message": job.current_stage or "Connected",
        "timestamp": job.created_at.isoformat(),
    })

    # If job already completed/failed, close connection
    if job.status in (ProcessingStatus.COMPLETED, ProcessingStatus.FAILED):
        if job.result:
            await websocket.send_json({
                "status": job.status.value,
                "progress": job.progress,
                "message": f"Saved {len(job.result.files_created)} files",
                "timestamp": job.completed_at.isoformat() if job.completed_at else "",
                "result": job.result.model_dump(mode="json"),
            })
        await websocket.close()
        return

    # Subscribe to updates
    queue = job_manager.subscribe(job_id)

    try:
        while True:
            try:
                # Wait for next message with timeout
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json(message)

                # Close on completion/failure
                if message.get("status") in (
                    ProcessingStatus.COMPLETED.value,
                    ProcessingStatus.FAILED.value,
                ):
                    break

            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
    finally:
        job_manager.unsubscribe(job_id, queue)
        logger.info(f"WebSocket closed for job {job_id}")
