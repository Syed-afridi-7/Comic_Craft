"""FastAPI application entry point for ComicCraft."""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager ensuring required runtime directories exist."""
    settings = get_settings()
    settings.PANELS_DIR.mkdir(parents=True, exist_ok=True)
    settings.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("ComicCraft runtime directories verified and initialized.")
    yield


app = FastAPI(
    title="ComicCraft",
    description="AI Comic Story Creator",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware: allow all origins, methods, headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static assets directory
settings = get_settings()
app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")

# Include application route handlers
app.include_router(router)
