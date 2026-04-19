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
    point_screenshot_dir: Path = BASE_DIR / "points" / "杨树点位截图"
    temp_dir: Path = BASE_DIR / ".tmp" / "workorder_images"
    libreoffice_bin: str = Field(
        default="soffice",
        validation_alias="LIBREOFFICE_BIN",
    )
    libreoffice_timeout_seconds: int = Field(
        default=60,
        validation_alias="LIBREOFFICE_TIMEOUT_SECONDS",
    )
    cors_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
    auth_secret_key: str = Field(
        default="tzlb-dev-secret-change-me",
        validation_alias="AUTH_SECRET_KEY",
    )
    auth_cookie_name: str = Field(
        default="tzlb_session",
        validation_alias="AUTH_COOKIE_NAME",
    )
    auth_cookie_secure: bool = Field(
        default=False,
        validation_alias="AUTH_COOKIE_SECURE",
    )
    auth_bypass_localhost: bool = Field(
        default=False,
        validation_alias="AUTH_BYPASS_LOCALHOST",
    )
    auth_session_ttl_hours: int = Field(
        default=12,
        validation_alias="AUTH_SESSION_TTL_HOURS",
    )
    auth_remember_ttl_days: int = Field(
        default=30,
        validation_alias="AUTH_REMEMBER_TTL_DAYS",
    )
    auth_default_admin_username: str = Field(
        default="admin",
        validation_alias="AUTH_DEFAULT_ADMIN_USERNAME",
    )
    auth_default_admin_password: str = Field(
        default="Forestry@2026",
        validation_alias="AUTH_DEFAULT_ADMIN_PASSWORD",
    )
    auth_default_admin_display_name: str = Field(
        default="系统管理员",
        validation_alias="AUTH_DEFAULT_ADMIN_DISPLAY_NAME",
    )

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
