from __future__ import annotations

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
    find_point_screenshot,
    image_to_rgb,
    is_image_file,
    natural_path_sort_key,
)
from backend.services.pest_registry import get_screenshot_dir


POINT_CODE_PATTERN = re.compile(r"^[A-Za-z0-9\u4e00-\u9fa5_-]+$")
PREVIEW_SIZES = frozenset({"full", "thumb"})
THUMB_MAX_EDGE = 360
THUMB_JPEG_QUALITY = 82
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


def validate_point_code(code: str) -> str:
    """校验并返回去除首尾空白后的点位编号。"""

    normalized = str(code or "").strip()
    if not normalized or POINT_CODE_PATTERN.fullmatch(normalized) is None:
        raise ValueError("点位编号只能包含中文、英文字母、数字、下划线和连字符")
    return normalized


def ensure_inside_directory(root: Path, candidate: Path) -> None:
    """确保 candidate 位于 root 目录之内，防止路径穿越。"""

    root_resolved = root.resolve()
    candidate_resolved = candidate.resolve()
    if candidate_resolved != root_resolved and root_resolved not in candidate_resolved.parents:
        raise ValueError("保存路径不合法")


def require_screenshot_dir(pest_type: str) -> Path:
    screenshot_dir = get_screenshot_dir(pest_type)
    if screenshot_dir is None:
        raise FileNotFoundError(f"{pest_type} 未配置点位截图目录")
    return screenshot_dir


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


def list_screenshot_files(screenshot_dir: Path) -> list[Path]:
    if not screenshot_dir.is_dir():
        return []

    files: list[Path] = []
    for path in screenshot_dir.iterdir():
        if not path.is_file() or not is_image_file(path):
            continue
        try:
            ensure_inside_directory(screenshot_dir, path)
        except ValueError:
            continue
        files.append(path)
    return sorted(files, key=natural_path_sort_key)


def find_matching_files(screenshot_dir: Path, code: str) -> list[Path]:
    if not screenshot_dir.is_dir():
        return []
    return [
        path
        for path in screenshot_dir.iterdir()
        if path.is_file() and path.stem.strip() == code
    ]


async def list_point_screenshot_status(pest_type: str) -> list[dict[str, object]]:
    """合并基础点位与截图目录，返回每个点位的截图状态。"""

    points = await postgres.fetch_site_points(pest_type)
    screenshot_dir = require_screenshot_dir(pest_type)
    screenshot_index: dict[str, str] = {}
    for path in list_screenshot_files(screenshot_dir):
        screenshot_index.setdefault(path.stem.strip(), path.name)

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
    screenshot_dir = require_screenshot_dir(pest_type)
    max_bytes = get_settings().workorder_image_max_bytes
    content = await upload_file.read(max_bytes + 1)
    ensure_image_size_limits(content, "点位截图")
    extension = detect_image_extension(content, upload_file.filename)

    screenshot_dir.mkdir(parents=True, exist_ok=True)
    for existing_path in find_matching_files(screenshot_dir, normalized_code):
        ensure_inside_directory(screenshot_dir, existing_path)
        existing_path.unlink()

    target_path = screenshot_dir / f"{normalized_code}.{extension}"
    ensure_inside_directory(screenshot_dir, target_path)
    target_path.write_bytes(content)
    return {
        "code": normalized_code,
        "filename": target_path.name,
        "size": len(content),
    }


def delete_point_screenshot(pest_type: str, code: str) -> dict[str, object]:
    """删除点位编号对应的全部截图文件。"""

    normalized_code = validate_point_code(code)
    screenshot_dir = require_screenshot_dir(pest_type)
    matching_files = find_matching_files(screenshot_dir, normalized_code)
    if not matching_files:
        raise FileNotFoundError(f"未找到点位 {normalized_code} 的截图")

    for path in matching_files:
        ensure_inside_directory(screenshot_dir, path)
        path.unlink()
    return {"code": normalized_code, "deleted": True}


def _build_thumbnail_bytes(content: bytes) -> bytes:
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
        raise ValueError("截图像素尺寸过大，无法生成缩略图") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("截图文件损坏，无法生成缩略图") from exc


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

    normalized_size = str(size or "full").strip().lower()
    if normalized_size not in PREVIEW_SIZES:
        raise ValueError("预览尺寸仅支持 full 或 thumb")

    normalized_code = validate_point_code(code)
    screenshot_dir = require_screenshot_dir(pest_type)
    screenshot_path = find_point_screenshot(screenshot_dir, normalized_code)
    if screenshot_path is None:
        raise FileNotFoundError(f"未找到点位 {normalized_code} 的截图")

    ensure_inside_directory(screenshot_dir, screenshot_path)
    content = screenshot_path.read_bytes()
    if normalized_size == "thumb":
        return _build_thumbnail_bytes(content), "image/jpeg"

    media_type, _ = mimetypes.guess_type(screenshot_path.name)
    return content, media_type or "application/octet-stream"
