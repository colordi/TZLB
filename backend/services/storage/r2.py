"""Cloudflare R2（S3 兼容）前缀范围的素材存储实现。

boto3 调用为同步阻塞；与现有本地磁盘实现保持一致，由调用方决定是否在
异步上下文中以线程池包装。网络/鉴权异常不在这里兜底，直接向上抛出。
"""

from __future__ import annotations

from typing import Any

from botocore.exceptions import ClientError

from backend.services.storage.base import AssetObject, validate_asset_name


_NOT_FOUND_CODES = {"NoSuchKey", "NoSuchBucket", "404", "NotFound"}


def _is_not_found(exc: ClientError) -> bool:
    code = exc.response.get("Error", {}).get("Code", "")
    return str(code) in _NOT_FOUND_CODES


class R2AssetStorage:
    """以 R2 桶内某个 key 前缀为存储位置的 AssetStorage 实现。"""

    def __init__(self, client: Any, *, bucket: str, prefix: str) -> None:
        self._client = client
        self._bucket = bucket
        self._prefix = prefix.strip("/")

    @property
    def bucket(self) -> str:
        return self._bucket

    @property
    def prefix(self) -> str:
        return self._prefix

    def object_key(self, name: str) -> str:
        return f"{self._prefix}/{validate_asset_name(name)}"

    def list(self) -> list[AssetObject]:
        objects: list[AssetObject] = []
        list_prefix = f"{self._prefix}/"
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=list_prefix):
            for item in page.get("Contents", []):
                name = str(item["Key"])[len(list_prefix):]
                # 不递归子层级，与本地目录的 iterdir 语义一致
                if not name or "/" in name:
                    continue
                objects.append(AssetObject(name=name, size_bytes=int(item.get("Size", 0))))
        return objects

    def read(self, name: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=self.object_key(name))
        except ClientError as exc:
            if _is_not_found(exc):
                raise FileNotFoundError(f"素材不存在：{name}") from exc
            raise
        return response["Body"].read()

    def write(self, name: str, content: bytes) -> None:
        self._client.put_object(Bucket=self._bucket, Key=self.object_key(name), Body=content)

    def delete(self, name: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=self.object_key(name))

    def exists(self, name: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=self.object_key(name))
        except ClientError as exc:
            if _is_not_found(exc):
                return False
            raise
        return True
