"""
FastAPI application for video transcription pipeline.

Provides HTTP API and WebSocket for video processing.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes, step_routes, websocket
from app.config import get_settings
from app.services.ai_client import AIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Logs startup info and checks AI services availability.
    """
    settings = get_settings()
    logger.info(f"Starting Video Transcriber API")
    logger.info(f"Inbox directory: {settings.inbox_dir}")
    logger.info(f"Archive directory: {settings.archive_dir}")

    # Check AI services
    async with AIClient(settings) as client:
        status = await client.check_services()
        logger.info(f"AI Services - Whisper: {status['whisper']}, Ollama: {status['ollama']}")

    yield

    logger.info("Shutting down Video Transcriber API")


app = FastAPI(
    title="Video Transcriber API",
    description="API for video transcription and summarization pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.router)
app.include_router(step_routes.router)
app.include_router(websocket.router)


@app.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns:
        Basic health status
    """
    return {"status": "ok"}


@app.get("/health/services")
async def services_health() -> dict:
    """
    Check AI services availability.

    Returns:
        Status of Whisper and Ollama services
    """
    settings = get_settings()
    async with AIClient(settings) as client:
        status = await client.check_services()
        return {
            "whisper": status["whisper"],
            "ollama": status["ollama"],
            "whisper_url": settings.whisper_url,
            "ollama_url": settings.ollama_url,
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8801,
        reload=True,
    )
