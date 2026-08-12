from __future__ import annotations

import asyncio
import io
import mimetypes
import re
import warnings
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from backend.config import get_settings
from backend.db import postgres
from backend.services.docgen import (
    SUPPORTED_IMAGE_FORMATS,
    SUPPORTED_IMAGE_FORMAT_LABEL,
    ensure_image_size_limits,
    find_matching_screenshot_names,
    find_point_screenshot_name,
    image_to_rgb,
    is_image_file,
    natural_path_sort_key,
)
from backend.services.pest_registry import get_screenshot_dir
from backend.services.storage import (
    AssetObject,
    AssetStorage,
    get_storage_for_dir,
)


POINT_CODE_PATTERN = re.compile(r"^[A-Za-z0-9一-龥_-]+$")
PREVIEW_SIZES = frozenset({"full", "thumb"})
THUMB_MAX_EDGE = 360
THUMB_JPEG_QUALITY = 82
# 与原图同目录存放：MQ001.jpg → MQ001.thumb.jpg；列表/装配时需排除
THUMB_NAME_SUFFIX = ".thumb.jpg"
IMAGE_EXTENSION_BY_FORMAT = {
    "JPEG": "jpg",
    "PNG": "png",
    "WEBP": "webp",
}
IMAGE_EXTENSIONS_BY_FORMAT = {
    "JPEG": {"jpg", "jpeg"},
    "PNG": {"png"},
    "WEBP": {"webp"},
}


def is_preview_thumbnail_name(name: str) -> bool:
    """判断是否为列表预览用持久化缩略图文件名。"""

    return str(name or "").endswith(THUMB_NAME_SUFFIX)


def thumbnail_name_for(original_name: str) -> str:
    """由原图文件名推导缩略图文件名（统一 JPEG）。"""

    stem = Path(original_name).stem
    if not stem or is_preview_thumbnail_name(original_name):
        raise ValueError("原图文件名不合法")
    return f"{stem}{THUMB_NAME_SUFFIX}"


def write_preview_thumbnail(storage: AssetStorage, original_name: str, content: bytes) -> None:
    """由原图字节生成缩略图并写入存储。"""

    storage.write(thumbnail_name_for(original_name), build_preview_thumbnail(content))


def delete_preview_thumbnail(storage: AssetStorage, original_name: str) -> None:
    """删除原图对应的缩略图（不存在时静默忽略）。"""

    try:
        storage.delete(thumbnail_name_for(original_name))
    except ValueError:
        return


def read_or_build_preview_thumbnail(
    storage: AssetStorage,
    original_name: str,
    *,
    original_content: bytes | None = None,
) -> bytes:
    """优先读持久化缩略图；缺失时现算并尝试回写。"""

    thumb_name = thumbnail_name_for(original_name)
    try:
        return storage.read(thumb_name)
    except FileNotFoundError:
        pass

    content = original_content if original_content is not None else storage.read(original_name)
    thumb_bytes = build_preview_thumbnail(content)
    try:
        storage.write(thumb_name, thumb_bytes)
    except Exception:  # noqa: BLE001 — 回写失败不影响本次预览
        pass
    return thumb_bytes


def validate_point_code(code: str) -> str:
    """校验并返回去除首尾空白后的点位编号。"""

    normalized = str(code or "").strip()
    if not normalized or POINT_CODE_PATTERN.fullmatch(normalized) is None:
        raise ValueError("点位编号只能包含中文、英文字母、数字、下划线和连字符")
    return normalized


def require_screenshot_dir(pest_type: str) -> Path:
    screenshot_dir = get_screenshot_dir(pest_type)
    if screenshot_dir is None:
        raise FileNotFoundError(f"{pest_type} 未配置点位截图目录")
    return screenshot_dir


def require_screenshot_storage(pest_type: str) -> AssetStorage:
    """返回害虫点位截图目录对应的素材存储。"""

    return get_storage_for_dir(require_screenshot_dir(pest_type), get_settings())


def detect_image_extension(content: bytes, filename: str | None) -> str:
    """校验图片内容并返回与真实图片格式匹配的扩展名。"""

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                image_format = (image.format or "").upper()
                image.verify()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError("上传图片像素尺寸过大") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("上传文件不是有效图片") from exc

    if image_format not in SUPPORTED_IMAGE_FORMATS:
        raise ValueError(
            f"图片格式不支持：{image_format or '未知'}，仅支持 {SUPPORTED_IMAGE_FORMAT_LABEL}"
        )

    original_extension = Path(filename or "").suffix.lower().lstrip(".")
    if original_extension in IMAGE_EXTENSIONS_BY_FORMAT[image_format]:
        return original_extension
    return IMAGE_EXTENSION_BY_FORMAT[image_format]


def list_screenshot_objects(storage: AssetStorage) -> list[AssetObject]:
    """列出截图存储位置下的原图文件（排除持久化缩略图），按文件名自然排序。"""

    return sorted(
        (
            obj
            for obj in storage.list()
            if is_image_file(Path(obj.name)) and not is_preview_thumbnail_name(obj.name)
        ),
        key=lambda obj: natural_path_sort_key(Path(obj.name)),
    )


def find_matching_names(storage: AssetStorage, code: str) -> list[str]:
    """按点位编号匹配截图文件名；优先扩展名探测，避免整目录 list。"""

    return find_matching_screenshot_names(storage, code)


async def list_point_screenshot_status(pest_type: str) -> list[dict[str, object]]:
    """合并基础点位与截图存储，返回每个点位的截图状态。"""

    points = await postgres.fetch_site_points(pest_type)
    storage = require_screenshot_storage(pest_type)
    objects = await asyncio.to_thread(list_screenshot_objects, storage)
    screenshot_index: dict[str, str] = {}
    for obj in objects:
        screenshot_index.setdefault(Path(obj.name).stem.strip(), obj.name)

    return [
        {
            "code": point["code"],
            "name": point["name"],
            "locality": point["locality"],
            "has_screenshot": point["code"] in screenshot_index,
            "screenshot_filename": screenshot_index.get(point["code"]),
        }
        for point in points
    ]


async def save_point_screenshot(
    pest_type: str,
    code: str,
    upload_file: UploadFile,
) -> dict[str, object]:
    """保存点位截图；已有相同编号的任意扩展名文件会被替换。"""

    normalized_code = validate_point_code(code)
    storage = require_screenshot_storage(pest_type)
    max_bytes = get_settings().workorder_image_max_bytes
    content = await upload_file.read(max_bytes + 1)
    ensure_image_size_limits(content, "点位截图")
    extension = detect_image_extension(content, upload_file.filename)

    for existing_name in find_matching_names(storage, normalized_code):
        delete_preview_thumbnail(storage, existing_name)
        storage.delete(existing_name)

    filename = f"{normalized_code}.{extension}"
    storage.write(filename, content)
    try:
        write_preview_thumbnail(storage, filename, content)
    except ValueError:
        # 缩略图生成失败不阻断原图上传
        pass
    return {
        "code": normalized_code,
        "filename": filename,
        "size": len(content),
    }


def delete_point_screenshot(pest_type: str, code: str) -> dict[str, object]:
    """删除点位编号对应的全部截图文件。"""

    normalized_code = validate_point_code(code)
    storage = require_screenshot_storage(pest_type)
    matching_names = find_matching_names(storage, normalized_code)
    if not matching_names:
        raise FileNotFoundError(f"未找到点位 {normalized_code} 的截图")

    for name in matching_names:
        delete_preview_thumbnail(storage, name)
        storage.delete(name)
    return {"code": normalized_code, "deleted": True}


def build_preview_thumbnail(content: bytes) -> bytes:
    """将原图缩放为列表用缩略图，统一输出 JPEG。"""

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                image.load()
                rgb_image = image_to_rgb(image)
                rgb_image.thumbnail(
                    (THUMB_MAX_EDGE, THUMB_MAX_EDGE),
                    Image.Resampling.LANCZOS,
                )
                buffer = io.BytesIO()
                rgb_image.save(
                    buffer,
                    format="JPEG",
                    quality=THUMB_JPEG_QUALITY,
                    optimize=True,
                )
                return buffer.getvalue()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError("图片像素尺寸过大，无法生成缩略图") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("图片文件损坏，无法生成缩略图") from exc


def normalize_preview_size(size: str | None) -> str:
    """校验预览尺寸参数，仅允许 full / thumb。"""

    normalized = str(size or "full").strip().lower()
    if normalized not in PREVIEW_SIZES:
        raise ValueError("预览尺寸仅支持 full 或 thumb")
    return normalized


def read_point_screenshot(
    pest_type: str,
    code: str,
    *,
    size: str = "full",
) -> tuple[bytes, str]:
    """读取点位截图内容和媒体类型。

    size:
      - full: 原图
      - thumb: 最长边不超过 THUMB_MAX_EDGE 的 JPEG 缩略图
    """

    normalized_size = normalize_preview_size(size)
    normalized_code = validate_point_code(code)
    storage = require_screenshot_storage(pest_type)
    screenshot_name = find_point_screenshot_name(storage, normalized_code)
    if screenshot_name is None:
        raise FileNotFoundError(f"未找到点位 {normalized_code} 的截图")

    if normalized_size == "thumb":
        return read_or_build_preview_thumbnail(storage, screenshot_name), "image/jpeg"

    content = storage.read(screenshot_name)
    media_type, _ = mimetypes.guess_type(screenshot_name)
    return content, media_type or "application/octet-stream"
