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
    IMAGE_STRATEGY_AUTO_DISK,
    get_pest_config,
)
from backend.services.storage import AssetStorage, get_storage_for_dir


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


def sanitize_images_to_temp(named_images: list[tuple[str, bytes]], row_id: str) -> list[Path]:
    """将装配到的素材图片校验并规范化为临时 JPEG 文件。"""

    sanitized_paths: list[Path] = []
    total_size = 0
    for index, (name, content) in enumerate(named_images[:MAX_IMAGES]):
        label = f"图片文件 {name}"
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


# 上传写入统一小写扩展名；探测顺序覆盖常见格式，避免为找一张图而 list 整目录
SCREENSHOT_PROBE_EXTENSIONS = ("jpg", "jpeg", "png", "webp")


def find_matching_screenshot_names(storage: AssetStorage, location_id: str) -> list[str]:
    """按点位编号匹配全部截图文件名。

    优先按常见扩展名 exists 探测（R2 下为 HeadObject，O(扩展名数)），
    未命中时再回退 list 整目录以兼容历史大小写/非标准扩展名。
    """

    normalized_location_id = (location_id or "").strip()
    if not normalized_location_id:
        return []

    probed = [
        name
        for ext in SCREENSHOT_PROBE_EXTENSIONS
        if storage.exists(name := f"{normalized_location_id}.{ext}")
    ]
    if probed:
        return sorted(probed, key=lambda name: natural_path_sort_key(Path(name)))

    from backend.services.point_screenshot_service import is_preview_thumbnail_name

    return sorted(
        (
            obj.name
            for obj in storage.list()
            if is_image_file(Path(obj.name))
            and not is_preview_thumbnail_name(obj.name)
            and Path(obj.name).stem.strip() == normalized_location_id
        ),
        key=lambda name: natural_path_sort_key(Path(name)),
    )


def find_point_screenshot_name(storage: AssetStorage, location_id: str) -> str | None:
    """在点位截图存储位置中按编号精确匹配（不含扩展名）第一张截图。"""

    matches = find_matching_screenshot_names(storage, location_id)
    return matches[0] if matches else None


def find_dated_location_image_names(storage: AssetStorage, location_id: str) -> list[str]:
    """列出日期存储位置下文件名以点位编号开头的全部图片。"""

    normalized_location_id = (location_id or "").strip()
    if not normalized_location_id:
        return []

    from backend.services.point_screenshot_service import is_preview_thumbnail_name

    return sorted(
        (
            obj.name
            for obj in storage.list()
            if is_image_file(Path(obj.name))
            and not is_preview_thumbnail_name(obj.name)
            and Path(obj.name).stem.startswith(normalized_location_id)
        ),
        key=lambda name: natural_path_sort_key(Path(name)),
    )


def resolve_auto_disk_images(record: WorkOrderRecord, pest_type: str) -> list[tuple[str, bytes]]:
    """按点位截图 + images/{调查日期}/ 日期现场图自动装配，最多 MAX_IMAGES 张。"""

    settings = get_settings()
    config = get_pest_config(pest_type)
    named_images: list[tuple[str, bytes]] = []

    if config.screenshot_dir_attr:
        screenshot_dir = getattr(settings, config.screenshot_dir_attr, None)
        if screenshot_dir is not None:
            storage = get_storage_for_dir(Path(screenshot_dir), settings)
            screenshot_name = find_point_screenshot_name(storage, record.location_id)
            if screenshot_name is not None:
                named_images.append((screenshot_name, storage.read(screenshot_name)))

    survey_date = (record.survey_date or "").strip()[:10]
    if survey_date:
        date_storage = get_storage_for_dir(Path(settings.images_dir) / survey_date, settings)
        for name in find_dated_location_image_names(date_storage, record.location_id):
            named_images.append((name, date_storage.read(name)))

    return named_images[:MAX_IMAGES]


def resolve_meiguobaie_images(record: WorkOrderRecord) -> list[tuple[str, bytes]]:
    """兼容旧调用：按美国白蛾配置自动装配图片。"""

    return resolve_auto_disk_images(record, "美国白蛾")


def _resolve_uploaded_strategy_images(
    record: WorkOrderRecord,
    pest_type: str,
) -> list[tuple[str, bytes]]:
    """uploaded_images：优先用记录内 Base64；为空时从点位截图存储补一张。"""

    if record.images:
        return []

    settings = get_settings()
    config = get_pest_config(pest_type)
    if not config.screenshot_dir_attr:
        return []

    screenshot_dir = getattr(settings, config.screenshot_dir_attr, None)
    if screenshot_dir is None:
        return []

    storage = get_storage_for_dir(Path(screenshot_dir), settings)
    screenshot_name = find_point_screenshot_name(storage, record.location_id)
    if screenshot_name is None:
        return []
    return [(screenshot_name, storage.read(screenshot_name))]


def resolve_record_image_paths(
    record: WorkOrderRecord,
    pest_type: str,
    row_id: str,
    temp_images: list[Path],
) -> list[Path]:
    config = get_pest_config(pest_type)
    if config.image_strategy == IMAGE_STRATEGY_AUTO_DISK:
        image_paths = sanitize_images_to_temp(
            resolve_auto_disk_images(record, pest_type),
            row_id,
        )
        temp_images.extend(image_paths)
        return image_paths

    if record.images:
        image_paths = save_base64_images(record.images, row_id)
        temp_images.extend(image_paths)
        return image_paths

    # 导入列表已不再批量携带截图 Data URL，生成时按点位从存储补图
    image_paths = sanitize_images_to_temp(
        _resolve_uploaded_strategy_images(record, pest_type),
        row_id,
    )
    temp_images.extend(image_paths)
    return image_paths
