import os
from functools import lru_cache
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()


class Settings:
    """Application settings and environment configuration."""

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        gemini_api_key: Optional[str] = None,
        hf_api_key: Optional[str] = None,
        dev_mock_ai: Optional[bool] = None,
    ):
        self.BASE_DIR: Path = (
            base_dir if base_dir is not None else Path(__file__).resolve().parent.parent
        )
        self.GEMINI_API_KEY: str = (
            gemini_api_key
            if gemini_api_key is not None
            else os.getenv("GEMINI_API_KEY", "")
        )
        self.HF_API_KEY: str = (
            hf_api_key if hf_api_key is not None else os.getenv("HF_API_KEY", "")
        )

        if dev_mock_ai is not None:
            self.DEV_MOCK_AI: bool = dev_mock_ai
        else:
            env_val = os.getenv("DEV_MOCK_AI", "").strip().lower()
            env_mock = env_val in ("true", "1", "yes")
            self.DEV_MOCK_AI = env_mock or not bool(self.GEMINI_API_KEY.strip())

        self.STATIC_DIR: Path = self.BASE_DIR / "static"
        self.PANELS_DIR: Path = self.STATIC_DIR / "panels"
        self.EXPORTS_DIR: Path = self.STATIC_DIR / "exports"

        # Ensure required static directories exist
        self.PANELS_DIR.mkdir(parents=True, exist_ok=True)
        self.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton instance of Settings."""
    return Settings()
