"""主存储 + 兜底存储的双层 AssetStorage 实现。

用于 R2 模式下兼容未迁移的本地存量素材：新上传只写主存储（R2），
读取与列表合并两层（同名文件主存储优先），删除同时清理两层。
"""

from __future__ import annotations

from backend.services.storage.base import AssetObject, AssetStorage


class FallbackAssetStorage:
    """读合并、写主存、删两层的组合存储。"""

    def __init__(self, primary: AssetStorage, fallback: AssetStorage) -> None:
        self.primary = primary
        self.fallback = fallback

    def list(self) -> list[AssetObject]:
        merged: dict[str, AssetObject] = {obj.name: obj for obj in self.fallback.list()}
        for obj in self.primary.list():
            merged[obj.name] = obj
        return list(merged.values())

    def read(self, name: str) -> bytes:
        try:
            return self.primary.read(name)
        except FileNotFoundError:
            return self.fallback.read(name)

    def write(self, name: str, content: bytes) -> None:
        self.primary.write(name, content)

    def delete(self, name: str) -> None:
        self.primary.delete(name)
        self.fallback.delete(name)

    def exists(self, name: str) -> bool:
        return self.primary.exists(name) or self.fallback.exists(name)
