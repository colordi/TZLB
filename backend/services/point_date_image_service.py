"""点位日期图片的上传、列举与删除。

图片保存在 ``images/{调查日期}/`` 目录下，统一命名为 ``{点位编号}-{序号}.{扩展名}``，
与美国白蛾工单生成时 ``docgen.find_dated_location_images`` 的"文件名以点位编号开头"
匹配规则兼容，用户无需在本地预先改名。
"""

from __future__ import annotations

import re
from datetime import date as date_cls
from pathlib import Path
from typing import Any

from backend.config import get_settings
from backend.logging_config import get_logger
from backend.services.docgen import (
    ensure_image_size_limits,
    is_image_file,
    natural_path_sort_key,
)
from backend.services.point_screenshot_service import (
    detect_image_extension,
    ensure_inside_directory,
    validate_point_code,
)


logger = get_logger(__name__)


DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_survey_date(survey_date: str) -> str:
    """校验并返回 YYYY-MM-DD 格式的有效日期。"""

    normalized = (survey_date or "").strip()
    if DATE_PATTERN.fullmatch(normalized) is None:
        raise ValueError("日期必须是 YYYY-MM-DD 格式")

    try:
        date_cls.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("日期必须是有效日期") from exc

    return normalized


def resolve_date_dir(survey_date: str) -> Path:
    """校验日期并返回 images 下对应的日期目录（不要求已存在）。"""

    normalized_date = validate_survey_date(survey_date)
    images_dir = get_settings().images_dir
    date_dir = images_dir / normalized_date
    ensure_inside_directory(images_dir, date_dir)
    return date_dir


def list_date_images(*, survey_date: str) -> list[dict[str, Any]]:
    """列出指定日期目录下的全部图片。"""

    date_dir = resolve_date_dir(survey_date)
    if not date_dir.is_dir():
        return []

    return [
        {"file_name": path.name, "size_bytes": path.stat().st_size}
        for path in sorted(date_dir.iterdir(), key=natural_path_sort_key)
        if path.is_file() and is_image_file(path)
    ]


def list_point_date_images(*, survey_date: str, point_code: str) -> list[dict[str, Any]]:
    """列出某点位在指定日期目录下的全部图片（文件名以点位编号开头）。"""

    normalized_code = validate_point_code(point_code)
    return [
        image
        for image in list_date_images(survey_date=survey_date)
        if Path(image["file_name"]).stem.startswith(normalized_code)
    ]


def resolve_point_date_image_path(*, survey_date: str, file_name: str) -> Path | None:
    """解析日期目录下的图片路径，不存在时返回 None。"""

    date_dir = resolve_date_dir(survey_date)
    name = validate_image_file_name(file_name)
    target = date_dir / name
    ensure_inside_directory(date_dir, target)
    if not target.is_file() or not is_image_file(target):
        return None
    return target


def validate_image_file_name(file_name: str) -> str:
    """校验文件名不含路径成分且为图片文件。"""

    name = (file_name or "").strip()
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise ValueError("文件名不合法")
    if not is_image_file(Path(name)):
        raise ValueError("只能访问图片文件")
    return name


def _next_sequence(date_dir: Path, point_code: str) -> int:
    pattern = re.compile(rf"^{re.escape(point_code)}-(\d+)$")
    max_sequence = 0
    if date_dir.is_dir():
        for path in date_dir.iterdir():
            match = pattern.match(path.stem)
            if match:
                max_sequence = max(max_sequence, int(match.group(1)))
    return max_sequence + 1


async def save_point_date_images(
    *,
    survey_date: str,
    point_code: str,
    files: list[Any],
) -> dict[str, Any]:
    """把上传的图片保存为 ``{点位编号}-{序号}.{扩展名}``，序号在现有文件基础上递增。"""

    normalized_code = validate_point_code(point_code)
    date_dir = resolve_date_dir(survey_date)
    if not files:
        raise ValueError("请选择要上传的图片")

    payloads: list[tuple[str, bytes]] = []
    for upload_file in files:
        payloads.append((getattr(upload_file, "filename", "") or "未命名", await upload_file.read()))

    total_size = 0
    for original_name, content in payloads:
        total_size += len(content)
        ensure_image_size_limits(content, f"图片“{original_name}”", total_size)

    date_dir.mkdir(parents=True, exist_ok=True)

    saved: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    sequence = _next_sequence(date_dir, normalized_code)

    for original_name, content in payloads:
        try:
            extension = detect_image_extension(content, original_name)
        except ValueError as exc:
            rejected.append({"file_name": original_name, "reason": str(exc)})
            continue

        target = date_dir / f"{normalized_code}-{sequence}.{extension}"
        while target.exists():
            sequence += 1
            target = date_dir / f"{normalized_code}-{sequence}.{extension}"

        target.write_bytes(content)
        saved.append({"file_name": target.name, "size_bytes": len(content)})
        sequence += 1

    logger.info(
        "点位日期图片上传完成: date=%s point=%s saved=%d rejected=%d",
        survey_date,
        normalized_code,
        len(saved),
        len(rejected),
    )

    return {
        "survey_date": survey_date,
        "point_code": normalized_code,
        "saved_count": len(saved),
        "saved": saved,
        "rejected": rejected,
    }


def delete_point_date_image(*, survey_date: str, point_code: str, file_name: str) -> None:
    """删除指定点位的日期图片，仅允许删除文件名以该点位编号开头的图片。"""

    normalized_code = validate_point_code(point_code)
    date_dir = resolve_date_dir(survey_date)
    name = validate_image_file_name(file_name)
    if not Path(name).stem.startswith(normalized_code):
        raise ValueError("只能删除文件名以该点位编号开头的图片")

    target = date_dir / name
    ensure_inside_directory(date_dir, target)
    if not target.is_file():
        raise FileNotFoundError(f"图片不存在：{name}")

    target.unlink()
    logger.info("点位日期图片已删除: date=%s point=%s file=%s", survey_date, normalized_code, name)
