"""
FastAPI application for video transcription pipeline.

Provides HTTP API for video processing with SSE progress updates.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import models_routes, routes, step_routes
from app.config import get_settings
from app.logging_config import setup_logging
from app.services.ai_clients import OllamaClient

# Configure logging before anything else
settings = get_settings()
setup_logging(settings)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Logs startup info and checks AI services availability.
    """
    logger.info("Starting Video Transcriber API")
    logger.info(f"Log level: {settings.log_level}")
    logger.info(f"Inbox directory: {settings.inbox_dir}")
    logger.info(f"Archive directory: {settings.archive_dir}")

    # Check AI services
    async with OllamaClient.from_settings(settings) as client:
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
app.include_router(models_routes.router)


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
    async with OllamaClient.from_settings(settings) as client:
        status = await client.check_services()
        return {
            "whisper": status["whisper"],
            "ollama": status["ollama"],
            "whisper_url": settings.whisper_url,
            "ollama_url": settings.ollama_url,
            "whisper_include_timestamps": settings.whisper_include_timestamps,
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8801,
        reload=True,
    )
