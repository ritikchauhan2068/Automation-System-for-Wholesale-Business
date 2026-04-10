"""
Wholesale Order Automation System
FastAPI backend for capturing, parsing, and storing shopkeeper orders.
"""

import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.routers import orders, whatsapp, analytics
from app.core.config import settings
from app.core.logger import setup_logging

# Setup logging on startup
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 Wholesale Order System starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    yield
    logger.info("🛑 Wholesale Order System shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title="Wholesale Order Automation System",
    description="Automatically capture, parse, and store shopkeeper orders into Google Sheets.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware — adjust origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(orders.router,    prefix="/api/v1/orders",    tags=["Orders"])
app.include_router(whatsapp.router,  prefix="/api/v1/whatsapp",  tags=["WhatsApp"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Wholesale Order Automation System",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}
