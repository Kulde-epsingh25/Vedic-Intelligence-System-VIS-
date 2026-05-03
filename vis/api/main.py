"""
FastAPI main application entry point.

This module defines the FastAPI app with middleware, health checks,
and router configuration for the Vedic Intelligence System API.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# Load environment variables
load_dotenv()

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
logger.add(
    LOG_DIR / "vis_api.log",
    rotation="500 MB",
    retention="7 days",
    level=os.getenv("LOG_LEVEL", "INFO"),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup/shutdown.
    """
    # Startup
    logger.info("VIS API starting up...")
    yield
    # Shutdown
    logger.info("VIS API shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Vedic Intelligence System API",
    description="Query all ancient Sanskrit texts with AI",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Status and version
    """
    return {
        "status": "ok",
        "version": "1.0.0",
    }


# Root endpoint
@app.get("/")
async def root():
    """Root API endpoint with documentation link."""
    return {
        "message": "Vedic Intelligence System API",
        "docs": "/docs",
        "version": "1.0.0",
    }


from api.routers import ask, character, concept, graph, search, science, verse
from api.middleware.cache import CacheMiddleware
from api.middleware.rate_limit import RateLimitMiddleware

app.add_middleware(CacheMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(verse.router)
app.include_router(search.router)
app.include_router(character.router)
app.include_router(concept.router)
app.include_router(science.router)
app.include_router(graph.router)
app.include_router(ask.router)

logger.info(f"FastAPI app initialized on port {os.getenv('API_PORT', 8000)}")

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
