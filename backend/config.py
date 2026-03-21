from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """应用配置。"""

    database_url: str = Field(
        default="postgresql://yandi@localhost:5432/forestry_survey",
        validation_alias="DATABASE_URL",
    )
    frontend_dist_dir: Path = BASE_DIR / "frontend" / "dist"
    templates_dir: Path = BASE_DIR / "templates"
    temp_dir: Path = BASE_DIR / ".tmp" / "workorder_images"
    cors_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    return settings
