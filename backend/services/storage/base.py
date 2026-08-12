"""工单素材的存储抽象：本地磁盘与对象存储（R2/S3 兼容）的统一接口。

接口以“单个目录/前缀”为作用范围，所有 ``name`` 均为不含路径分隔符的文件名，
与现状的目录布局（``points/*点位截图/``、``images/{日期}/``）一一对应。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AssetObject:
    """存储位置下的一个素材文件。"""

    name: str
    size_bytes: int


class AssetStorage(Protocol):
    """单目录/单前缀范围的素材存储接口。"""

    def list(self) -> list[AssetObject]:
        """列出当前位置下的全部文件（不递归子层级）。"""
        ...

    def read(self, name: str) -> bytes:
        """读取文件内容，不存在时抛出 FileNotFoundError。"""
        ...

    def write(self, name: str, content: bytes) -> None:
        """写入（覆盖）文件。"""
        ...

    def delete(self, name: str) -> None:
        """删除文件，不存在时静默忽略。"""
        ...

    def exists(self, name: str) -> bool:
        """判断文件是否存在。"""
        ...


def validate_asset_name(name: str) -> str:
    """校验并返回不含路径成分的文件名。"""

    normalized = (name or "").strip()
    if not normalized or normalized in {".", ".."} or "/" in normalized or "\\" in normalized:
        raise ValueError("文件名不合法")
    return normalized
