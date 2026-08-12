"""素材存储的运行时配置：环境变量为底，数据库覆盖优先。

管理员在「管理后台 → 存储配置」保存的配置写入 ``app_admin.app_settings``，
服务启动时载入内存快照（单进程应用，与批量任务存储同假设）。
此后所有素材读写按合并后的配置选择存储后端。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.db import app_settings as app_settings_db

STORAGE_BACKEND_LOCAL = "local"
STORAGE_BACKEND_R2 = "r2"
ALLOWED_STORAGE_BACKENDS = frozenset({STORAGE_BACKEND_LOCAL, STORAGE_BACKEND_R2})
DEFAULT_R2_PREFIX = "assets/"

STORAGE_CONFIG_KEYS = (
    "asset_storage_backend",
    "r2_endpoint_url",
    "r2_access_key_id",
    "r2_secret_access_key",
    "r2_bucket",
    "r2_prefix",
)


@dataclass(frozen=True, slots=True)
class StorageConfig:
    """一份完整的素材存储配置。"""

    backend: str = STORAGE_BACKEND_LOCAL
    r2_endpoint_url: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = ""
    r2_prefix: str = DEFAULT_R2_PREFIX


_override: StorageConfig | None = None


def _normalize_backend(value: str) -> str:
    return (value or "").strip().lower() or STORAGE_BACKEND_LOCAL


def _normalize_prefix(value: str) -> str:
    return (value or "").strip() or DEFAULT_R2_PREFIX


def storage_config_from_settings(settings: Any) -> StorageConfig:
    """从环境变量配置（Settings 或测试用命名空间）构建存储配置。"""

    return StorageConfig(
        backend=_normalize_backend(str(getattr(settings, "asset_storage_backend", "") or "")),
        r2_endpoint_url=str(getattr(settings, "r2_endpoint_url", "") or "").strip(),
        r2_access_key_id=str(getattr(settings, "r2_access_key_id", "") or "").strip(),
        r2_secret_access_key=str(getattr(settings, "r2_secret_access_key", "") or "").strip(),
        r2_bucket=str(getattr(settings, "r2_bucket", "") or "").strip(),
        r2_prefix=_normalize_prefix(str(getattr(settings, "r2_prefix", "") or "")),
    )


def get_storage_config_override() -> StorageConfig | None:
    """返回数据库覆盖配置，未加载或不存在时为 None。"""

    return _override


def set_storage_config_override(config: StorageConfig | None) -> None:
    """直接设置内存覆盖快照（测试与启动加载用）。"""

    global _override
    _override = config


async def refresh_storage_config_override() -> None:
    """从数据库加载存储配置覆盖快照，没有任何覆盖时清空。"""

    rows = await app_settings_db.load_app_settings()
    values = {key: rows[key] for key in STORAGE_CONFIG_KEYS if key in rows}
    if not values:
        set_storage_config_override(None)
        return
    set_storage_config_override(
        StorageConfig(
            backend=_normalize_backend(values.get("asset_storage_backend", "")),
            r2_endpoint_url=values.get("r2_endpoint_url", "").strip(),
            r2_access_key_id=values.get("r2_access_key_id", "").strip(),
            r2_secret_access_key=values.get("r2_secret_access_key", "").strip(),
            r2_bucket=values.get("r2_bucket", "").strip(),
            r2_prefix=_normalize_prefix(values.get("r2_prefix", "")),
        )
    )


def resolve_storage_config(settings: Any) -> StorageConfig:
    """返回当前生效的存储配置：数据库覆盖优先，其次环境变量。"""

    override = get_storage_config_override()
    if override is not None:
        return override
    return storage_config_from_settings(settings)


def validate_storage_config(config: StorageConfig) -> None:
    """校验存储配置完整性，不合法时抛出 ValueError（中文说明）。"""

    if config.backend not in ALLOWED_STORAGE_BACKENDS:
        raise ValueError("存储后端只能是 local 或 r2")
    if config.backend != STORAGE_BACKEND_R2:
        return
    if not config.r2_endpoint_url:
        raise ValueError("使用 R2 存储需要填写 Endpoint URL")
    if not config.r2_access_key_id:
        raise ValueError("使用 R2 存储需要填写 Access Key ID")
    if not config.r2_secret_access_key:
        raise ValueError("使用 R2 存储需要填写 Secret Access Key")
    if not config.r2_bucket:
        raise ValueError("使用 R2 存储需要填写 Bucket 名称")


def build_config_from_payload(
    payload: Any,
    *,
    fallback_secret: str = "",
) -> StorageConfig:
    """把管理后台表单 payload 归一化为 StorageConfig；密钥留空时沿用 fallback。"""

    return StorageConfig(
        backend=_normalize_backend(str(getattr(payload, "backend", "") or "")),
        r2_endpoint_url=str(getattr(payload, "r2_endpoint_url", "") or "").strip(),
        r2_access_key_id=str(getattr(payload, "r2_access_key_id", "") or "").strip(),
        r2_secret_access_key=(
            str(getattr(payload, "r2_secret_access_key", "") or "").strip() or fallback_secret
        ),
        r2_bucket=str(getattr(payload, "r2_bucket", "") or "").strip(),
        r2_prefix=_normalize_prefix(str(getattr(payload, "r2_prefix", "") or "")),
    )


def config_to_settings_dict(config: StorageConfig) -> dict[str, str]:
    """把 StorageConfig 展开为 app_settings 表的键值对。"""

    return {
        "asset_storage_backend": config.backend,
        "r2_endpoint_url": config.r2_endpoint_url,
        "r2_access_key_id": config.r2_access_key_id,
        "r2_secret_access_key": config.r2_secret_access_key,
        "r2_bucket": config.r2_bucket,
        "r2_prefix": config.r2_prefix,
    }
