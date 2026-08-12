"""本地磁盘目录的素材存储实现。"""

from __future__ import annotations

from pathlib import Path

from backend.services.storage.base import AssetObject, validate_asset_name


def ensure_inside_directory(root: Path, candidate: Path) -> None:
    """确保 candidate 位于 root 目录之内，防止路径穿越。"""

    root_resolved = root.resolve()
    candidate_resolved = candidate.resolve()
    if candidate_resolved != root_resolved and root_resolved not in candidate_resolved.parents:
        raise ValueError("保存路径不合法")


class LocalAssetStorage:
    """以本地目录为存储位置的 AssetStorage 实现。"""

    def __init__(self, directory: Path) -> None:
        self._directory = Path(directory)

    @property
    def directory(self) -> Path:
        return self._directory

    def _resolve(self, name: str) -> Path:
        target = self._directory / validate_asset_name(name)
        ensure_inside_directory(self._directory, target)
        return target

    def list(self) -> list[AssetObject]:
        if not self._directory.is_dir():
            return []

        objects: list[AssetObject] = []
        for path in self._directory.iterdir():
            if not path.is_file():
                continue
            try:
                ensure_inside_directory(self._directory, path)
            except ValueError:
                # 跳过指向目录外的符号链接
                continue
            objects.append(AssetObject(name=path.name, size_bytes=path.stat().st_size))
        return objects

    def read(self, name: str) -> bytes:
        target = self._resolve(name)
        if not target.is_file():
            raise FileNotFoundError(f"素材不存在：{name}")
        return target.read_bytes()

    def write(self, name: str, content: bytes) -> None:
        target = self._resolve(name)
        self._directory.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def delete(self, name: str) -> None:
        target = self._resolve(name)
        try:
            target.unlink()
        except FileNotFoundError:
            return

    def exists(self, name: str) -> bool:
        return self._resolve(name).is_file()
