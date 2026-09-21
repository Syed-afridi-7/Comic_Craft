"""Google Gemini client configuration and lifecycle management."""

import logging
from typing import Any, Optional
try:
    import google.generativeai as genai
except ImportError:
    genai = None

from app.config import get_settings

logger = logging.getLogger(__name__)


def configure_gemini() -> Optional[Any]:
    """Configure Google Gemini API client if API key is provided and mock mode is disabled.

    Returns:
        The configured google.generativeai module if configured, None otherwise.
    """
    settings = get_settings()
    api_key = settings.GEMINI_API_KEY.strip() if settings.GEMINI_API_KEY else ""

    if genai is None or not api_key or settings.DEV_MOCK_AI:
        logger.info("Gemini AI client disabled: running in mock mode or API key missing.")
        return None

    try:
        genai.configure(api_key=api_key)
        logger.info("Google Gemini API client configured successfully.")
        return genai
    except Exception as exc:
        logger.warning("Failed to configure Google Gemini API client: %s", exc)
        return None
