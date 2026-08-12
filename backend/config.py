from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_AUTH_SECRET_KEY = "tzlb-dev-secret-change-me"
DEFAULT_AUTH_DEFAULT_ADMIN_PASSWORD = "Forestry@2026"
ALLOWED_APP_ENVS = {"development", "production"}
ALLOWED_WORKORDER_OUTPUT_FORMATS = {"doc", "docx"}
ALLOWED_ASSET_STORAGE_BACKENDS = {"local", "r2"}
ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class Settings(BaseSettings):
    """应用配置。"""

    app_env: str = Field(
        default="development",
        validation_alias="APP_ENV",
    )
    database_url: str = Field(
        default="postgresql://yandi@localhost:5432/forestry_survey",
        validation_alias="DATABASE_URL",
    )
    frontend_dist_dir: Path = BASE_DIR / "frontend" / "dist"
    templates_dir: Path = BASE_DIR / "templates"
    point_screenshot_dir: Path = BASE_DIR / "points" / "杨树点位截图"
    sophora_point_screenshot_dir: Path = BASE_DIR / "points" / "国槐点位截图"
    meiguobaie_point_screenshot_dir: Path = BASE_DIR / "points" / "美国白蛾点位截图"
    other_pest_point_screenshot_dir: Path = BASE_DIR / "points" / "其他害虫点位截图"
    yangshu_shiye_point_screenshot_dir: Path = BASE_DIR / "points" / "杨树食叶害虫点位截图"
    images_dir: Path = BASE_DIR / "images"
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
        default=DEFAULT_AUTH_SECRET_KEY,
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
        default=DEFAULT_AUTH_DEFAULT_ADMIN_PASSWORD,
        validation_alias="AUTH_DEFAULT_ADMIN_PASSWORD",
    )
    auth_default_admin_display_name: str = Field(
        default="系统管理员",
        validation_alias="AUTH_DEFAULT_ADMIN_DISPLAY_NAME",
    )
    workorder_default_output_format: str = Field(
        default="doc",
        validation_alias="WORKORDER_DEFAULT_OUTPUT_FORMAT",
    )
    workorder_image_max_bytes: int = Field(
        default=8 * 1024 * 1024,
        validation_alias="WORKORDER_IMAGE_MAX_BYTES",
    )
    workorder_image_max_total_bytes: int = Field(
        default=24 * 1024 * 1024,
        validation_alias="WORKORDER_IMAGE_MAX_TOTAL_BYTES",
    )
    workorder_image_max_dimension: int = Field(
        default=1600,
        validation_alias="WORKORDER_IMAGE_MAX_DIMENSION",
    )
    workorder_batch_max_records: int = Field(
        default=50,
        validation_alias="WORKORDER_BATCH_MAX_RECORDS",
    )
    asset_storage_backend: str = Field(
        default="local",
        validation_alias="ASSET_STORAGE_BACKEND",
    )
    r2_endpoint_url: str = Field(
        default="",
        validation_alias="R2_ENDPOINT_URL",
    )
    r2_access_key_id: str = Field(
        default="",
        validation_alias="R2_ACCESS_KEY_ID",
    )
    r2_secret_access_key: str = Field(
        default="",
        validation_alias="R2_SECRET_ACCESS_KEY",
    )
    r2_bucket: str = Field(
        default="",
        validation_alias="R2_BUCKET",
    )
    r2_prefix: str = Field(
        default="assets/",
        validation_alias="R2_PREFIX",
    )
    log_level: str = Field(
        default="INFO",
        validation_alias="LOG_LEVEL",
    )

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def normalize_app_env(value: str) -> str:
    return (value or "").strip().lower()


def normalize_output_format(value: str) -> str:
    return (value or "").strip().lower()


def validate_runtime_settings(settings: Any) -> None:
    """校验启动期配置，生产环境下发现不安全配置时直接失败。"""

    errors: list[str] = []
    app_env = normalize_app_env(settings.app_env)
    output_format = normalize_output_format(settings.workorder_default_output_format)

    if app_env not in ALLOWED_APP_ENVS:
        errors.append("APP_ENV 只能是 development 或 production")

    if output_format not in ALLOWED_WORKORDER_OUTPUT_FORMATS:
        errors.append("WORKORDER_DEFAULT_OUTPUT_FORMAT 只能是 doc 或 docx")

    if settings.workorder_image_max_bytes <= 0:
        errors.append("WORKORDER_IMAGE_MAX_BYTES 必须大于 0")
    if settings.workorder_image_max_total_bytes <= 0:
        errors.append("WORKORDER_IMAGE_MAX_TOTAL_BYTES 必须大于 0")
    if settings.workorder_image_max_total_bytes < settings.workorder_image_max_bytes:
        errors.append("WORKORDER_IMAGE_MAX_TOTAL_BYTES 不能小于 WORKORDER_IMAGE_MAX_BYTES")
    if settings.workorder_image_max_dimension <= 0:
        errors.append("WORKORDER_IMAGE_MAX_DIMENSION 必须大于 0")

    if settings.workorder_batch_max_records <= 0:
        errors.append("WORKORDER_BATCH_MAX_RECORDS 必须大于 0")

    storage_backend = str(getattr(settings, "asset_storage_backend", "local") or "").strip().lower()
    if storage_backend not in ALLOWED_ASSET_STORAGE_BACKENDS:
        errors.append("ASSET_STORAGE_BACKEND 只能是 local 或 r2")
    if storage_backend == "r2":
        if not str(getattr(settings, "r2_endpoint_url", "") or "").strip():
            errors.append("ASSET_STORAGE_BACKEND=r2 时必须配置 R2_ENDPOINT_URL")
        if not str(getattr(settings, "r2_access_key_id", "") or "").strip():
            errors.append("ASSET_STORAGE_BACKEND=r2 时必须配置 R2_ACCESS_KEY_ID")
        if not str(getattr(settings, "r2_secret_access_key", "") or "").strip():
            errors.append("ASSET_STORAGE_BACKEND=r2 时必须配置 R2_SECRET_ACCESS_KEY")
        if not str(getattr(settings, "r2_bucket", "") or "").strip():
            errors.append("ASSET_STORAGE_BACKEND=r2 时必须配置 R2_BUCKET")

    if settings.log_level.upper() not in ALLOWED_LOG_LEVELS:
        errors.append(f"LOG_LEVEL 只能是 {', '.join(sorted(ALLOWED_LOG_LEVELS))} 之一")

    if app_env == "production":
        if settings.auth_secret_key.strip() == DEFAULT_AUTH_SECRET_KEY:
            errors.append("production 下必须修改 AUTH_SECRET_KEY")
        if settings.auth_default_admin_password.strip() == DEFAULT_AUTH_DEFAULT_ADMIN_PASSWORD:
            errors.append("production 下必须修改 AUTH_DEFAULT_ADMIN_PASSWORD")
        if not settings.auth_cookie_secure:
            errors.append("production 下必须启用 AUTH_COOKIE_SECURE")
        if settings.auth_bypass_localhost:
            errors.append("production 下不能启用 AUTH_BYPASS_LOCALHOST")

    if errors:
        raise RuntimeError("配置校验失败：" + "；".join(errors))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    validate_runtime_settings(settings)
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    return settings
