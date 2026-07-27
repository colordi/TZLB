from __future__ import annotations

import base64
import io
import mimetypes
import re
import uuid
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from backend.config import get_settings
from backend.schemas import WorkOrderRecord
from backend.services.docgen.constants import (
    MAX_IMAGES,
    SUPPORTED_IMAGE_FORMATS,
    SUPPORTED_IMAGE_FORMAT_LABEL,
)
from backend.services.pest_registry import (
    IMAGE_STRATEGY_WHITE_MOTH_AUTO,
    get_pest_config,
)


def format_size_limit(size: int) -> str:
    if size % (1024 * 1024) == 0:
        return f"{size // (1024 * 1024)} MB"
    if size % 1024 == 0:
        return f"{size // 1024} KB"
    return f"{size} 字节"


def decode_base64_image(raw_value: str, index: int) -> bytes:
    encoded = raw_value.split(",", 1)[1] if "," in raw_value else raw_value
    try:
        return base64.b64decode(encoded, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"第 {index + 1} 张图片无法解析：不是有效的 Base64 图片数据") from exc


def ensure_image_size_limits(content: bytes, label: str, total_size: int | None = None) -> None:
    settings = get_settings()
    if len(content) > settings.workorder_image_max_bytes:
        raise ValueError(
            f"{label}超过单图大小限制（{format_size_limit(settings.workorder_image_max_bytes)}）"
        )
    if total_size is not None and total_size > settings.workorder_image_max_total_bytes:
        raise ValueError(
            f"图片总大小超过限制（{format_size_limit(settings.workorder_image_max_total_bytes)}）"
        )


def image_to_rgb(image: Image.Image) -> Image.Image:
    if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
        rgba_image = image.convert("RGBA")
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(rgba_image, mask=rgba_image.getchannel("A"))
        return background
    return image.convert("RGB")


def resize_image_if_needed(image: Image.Image) -> Image.Image:
    settings = get_settings()
    max_dimension = settings.workorder_image_max_dimension
    longest_edge = max(image.size)
    if longest_edge <= max_dimension:
        return image

    scale = max_dimension / longest_edge
    target_size = (
        max(1, int(image.width * scale)),
        max(1, int(image.height * scale)),
    )
    resized = image.copy()
    resized.thumbnail(target_size, Image.Resampling.LANCZOS)
    return resized


def write_sanitized_image(content: bytes, output_path: Path, label: str) -> Path:
    try:
        with Image.open(io.BytesIO(content)) as image:
            image.load()
            image_format = (image.format or "").upper()
            if image_format not in SUPPORTED_IMAGE_FORMATS:
                raise ValueError(
                    f"{label}格式不支持：{image_format or '未知'}，仅支持 {SUPPORTED_IMAGE_FORMAT_LABEL}"
                )
            normalized_image = resize_image_if_needed(image_to_rgb(image))
    except UnidentifiedImageError as exc:
        raise ValueError(f"{label}不是有效图片") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_image.save(output_path, format="JPEG", quality=85, optimize=True)
    return output_path


def build_temp_image_path(row_id: str, index: int) -> Path:
    settings = get_settings()
    return settings.temp_dir / f"{row_id}_{index}_{uuid.uuid4().hex[:8]}.jpg"


def save_base64_images(base64_list: list[str], row_id: str) -> list[Path]:
    """将前端上传的 Base64 图片写入临时目录。"""

    paths: list[Path] = []
    total_size = 0
    for index, raw_value in enumerate(base64_list[:MAX_IMAGES]):
        label = f"第 {index + 1} 张图片"
        content = decode_base64_image(raw_value, index)
        total_size += len(content)
        ensure_image_size_limits(content, label, total_size)
        paths.append(write_sanitized_image(content, build_temp_image_path(row_id, index), label))
    return paths


def sanitize_existing_image_paths(paths: list[Path], row_id: str) -> list[Path]:
    """将磁盘图片校验并规范化为临时 JPEG 文件。"""

    sanitized_paths: list[Path] = []
    total_size = 0
    for index, path in enumerate(paths[:MAX_IMAGES]):
        label = f"图片文件 {path.name}"
        content = path.read_bytes()
        total_size += len(content)
        ensure_image_size_limits(content, label, total_size)
        sanitized_paths.append(
            write_sanitized_image(content, build_temp_image_path(row_id, index), label)
        )
    return sanitized_paths


def cleanup_temp_images(paths: list[Path]) -> None:
    for path in paths:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            continue


def is_image_file(path: Path) -> bool:
    mime_type, _ = mimetypes.guess_type(path.name)
    return bool(mime_type and mime_type.startswith("image/"))


def natural_path_sort_key(path: Path) -> tuple[tuple[int, int | str], ...]:
    parts = re.split(r"(\d+)", path.stem.lower())
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in parts
        if part
    )


def unique_existing_images(paths: list[Path]) -> list[Path]:
    images: list[Path] = []
    seen: set[str] = set()

    for path in paths:
        if not path.is_file() or not is_image_file(path):
            continue

        marker = str(path.resolve())
        if marker in seen:
            continue

        seen.add(marker)
        images.append(path)
        if len(images) >= MAX_IMAGES:
            break

    return images


def find_point_screenshot(screenshot_dir: Path, location_id: str) -> Path | None:
    normalized_location_id = (location_id or "").strip()
    if not normalized_location_id or not screenshot_dir.is_dir():
        return None

    matches = sorted(
        (
            path
            for path in screenshot_dir.iterdir()
            if path.is_file()
            and is_image_file(path)
            and path.stem.strip() == normalized_location_id
        ),
        key=natural_path_sort_key,
    )
    return matches[0] if matches else None


def find_dated_location_images(images_dir: Path, survey_date: str, location_id: str) -> list[Path]:
    normalized_location_id = (location_id or "").strip()
    normalized_date = (survey_date or "").strip()[:10]
    if not normalized_location_id or not normalized_date:
        return []

    dated_dir = images_dir / normalized_date
    if not dated_dir.is_dir():
        return []

    return sorted(
        (
            path
            for path in dated_dir.iterdir()
            if path.is_file()
            and is_image_file(path)
            and path.stem.startswith(normalized_location_id)
        ),
        key=natural_path_sort_key,
    )


def resolve_meiguobaie_image_paths(record: WorkOrderRecord) -> list[Path]:
    """按美国白蛾工作单规则自动装配图片，最多 4 张。"""

    settings = get_settings()
    image_paths: list[Path] = []

    point_screenshot = find_point_screenshot(
        settings.meiguobaie_point_screenshot_dir,
        record.location_id,
    )
    if point_screenshot is not None:
        image_paths.append(point_screenshot)

    image_paths.extend(
        find_dated_location_images(
            settings.images_dir,
            record.survey_date,
            record.location_id,
        )
    )

    return unique_existing_images(image_paths)


def resolve_record_image_paths(
    record: WorkOrderRecord,
    pest_type: str,
    row_id: str,
    temp_images: list[Path],
) -> list[Path]:
    config = get_pest_config(pest_type)
    if config.image_strategy == IMAGE_STRATEGY_WHITE_MOTH_AUTO:
        image_paths = sanitize_existing_image_paths(resolve_meiguobaie_image_paths(record), row_id)
        temp_images.extend(image_paths)
        return image_paths

    image_paths = save_base64_images(record.images, row_id) if record.images else []
    temp_images.extend(image_paths)
    return image_paths
