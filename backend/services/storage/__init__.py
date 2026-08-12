"""素材存储入口：按配置为指定本地目录返回本地或 R2 存储实现。

key 布局与本地目录结构一致：``points/{害虫}点位截图/{文件名}``、
``images/{日期}/{文件名}``，并统一挂在 ``R2_PREFIX``（默认 ``assets/``）之下，
便于存量数据原样上桶与一个桶隔离多套环境。

R2 模式返回 ``FallbackAssetStorage``：写入只进 R2，读取/列表合并 R2 与本地目录
（同名 R2 优先），因此未迁移的本地存量素材无需搬迁即可继续读取。
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.config import BASE_DIR
from backend.exceptions import ConfigurationError
from backend.services import storage_config
from backend.services.storage.base import AssetObject, AssetStorage, validate_asset_name
from backend.services.storage.fallback import FallbackAssetStorage
from backend.services.storage.local import LocalAssetStorage, ensure_inside_directory
from backend.services.storage.r2 import R2AssetStorage

__all__ = [
    "AssetObject",
    "AssetStorage",
    "FallbackAssetStorage",
    "LocalAssetStorage",
    "R2AssetStorage",
    "build_r2_storage",
    "derive_key_prefix",
    "ensure_inside_directory",
    "get_storage_for_dir",
    "test_r2_connection",
    "validate_asset_name",
]


def derive_key_prefix(directory: Path) -> str:
    """把本地目录映射为对象存储 key 前缀。

    优先取相对项目根目录的路径（如 ``points/美国白蛾点位截图``、``images/2026-07-20``），
    目录不在项目内时退化为目录名。
    """

    path = Path(directory)
    try:
        return path.relative_to(BASE_DIR).as_posix()
    except ValueError:
        pass
    try:
        return path.resolve().relative_to(BASE_DIR).as_posix()
    except ValueError:
        return path.name


@lru_cache(maxsize=8)
def _r2_client(endpoint_url: str, access_key_id: str, secret_access_key: str) -> Any:
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
    )


def build_r2_storage(directory: Path, config: Any) -> R2AssetStorage:
    """为指定本地目录对应的 R2 前缀构建存储（迁移脚本与工厂共用）。"""

    prefix_parts = [
        str(getattr(config, "r2_prefix", "") or "").strip("/"),
        derive_key_prefix(directory),
    ]
    prefix = "/".join(part for part in prefix_parts if part)
    client = _r2_client(
        str(config.r2_endpoint_url).strip(),
        str(config.r2_access_key_id).strip(),
        str(config.r2_secret_access_key).strip(),
    )
    return R2AssetStorage(client, bucket=str(config.r2_bucket).strip(), prefix=prefix)


def get_storage_for_dir(directory: Path, settings: Any) -> AssetStorage:
    """按当前生效的存储配置返回目录对应的素材存储。

    配置来源见 ``backend.services.storage_config``：数据库覆盖优先于环境变量。
    ``r2`` 模式返回带本地兜底的双层存储；配置不完整时抛出 ConfigurationError。
    """

    config = storage_config.resolve_storage_config(settings)
    if config.backend == storage_config.STORAGE_BACKEND_R2:
        try:
            storage_config.validate_storage_config(config)
        except ValueError as exc:
            raise ConfigurationError(f"素材存储配置不完整：{exc}") from exc
        return FallbackAssetStorage(
            build_r2_storage(directory, config),
            LocalAssetStorage(directory),
        )
    return LocalAssetStorage(directory)


_R2_ERROR_MESSAGES = {
    "InvalidAccessKeyId": "Access Key ID 无效",
    "SignatureDoesNotMatch": "Secret Access Key 不正确",
    "NoSuchBucket": "Bucket 不存在或无访问权限",
    "AccessDenied": "没有该 Bucket 的访问权限",
}


async def test_r2_connection(config: Any) -> None:
    """验证 R2 连接与桶可用，失败时抛出带中文说明的 ValueError。"""

    from botocore.exceptions import ClientError, EndpointConnectionError

    client = _r2_client(
        str(config.r2_endpoint_url).strip(),
        str(config.r2_access_key_id).strip(),
        str(config.r2_secret_access_key).strip(),
    )
    try:
        await asyncio.to_thread(
            client.list_objects_v2,
            Bucket=str(config.r2_bucket).strip(),
            MaxKeys=1,
        )
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        message = _R2_ERROR_MESSAGES.get(code, f"R2 返回错误（{code or '未知'}）")
        raise ValueError(f"连接 R2 失败：{message}") from exc
    except EndpointConnectionError as exc:
        raise ValueError("连接 R2 失败：无法连接 Endpoint，请检查 URL 与网络") from exc
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"连接 R2 失败：{exc}") from exc
