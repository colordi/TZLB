from __future__ import annotations

import mimetypes
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

from backend.config import get_settings
from backend.logging_config import get_logger


logger = get_logger(__name__)


DATE_FOLDER_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class UploadedDateImage:
    file_name: str
    status: str
    reason: str = ""


def validate_date_folder_name(folder_name: str) -> str:
    normalized = (folder_name or "").strip()
    if DATE_FOLDER_PATTERN.fullmatch(normalized) is None:
        raise ValueError("文件夹名称必须是 YYYY-MM-DD 格式")

    try:
        date.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("文件夹名称必须是有效日期") from exc

    return normalized


def parse_relative_path(relative_path: str, expected_folder_name: str) -> tuple[str, bool]:
    path_text = (relative_path or "").replace("\\", "/").strip("/")
    path = PurePosixPath(path_text)
    parts = path.parts

    if not parts or path.is_absolute() or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("文件路径不合法")
    if parts[0] != expected_folder_name:
        raise ValueError("只能上传同一个日期文件夹中的文件")
    if len(parts) != 2:
        return parts[-1], True

    return parts[-1], False


def is_supported_image_file(file_name: str) -> bool:
    mime_type, _ = mimetypes.guess_type(file_name)
    return bool(mime_type and mime_type.startswith("image/"))


def ensure_inside_directory(root: Path, candidate: Path) -> None:
    root_resolved = root.resolve()
    candidate_resolved = candidate.resolve()
    if candidate_resolved != root_resolved and root_resolved not in candidate_resolved.parents:
        raise ValueError("保存路径不合法")


async def upload_date_image_folder(
    *,
    folder_name: str,
    files: list[Any],
    relative_paths: list[str],
) -> dict[str, Any]:
    normalized_folder_name = validate_date_folder_name(folder_name)
    if not files:
        raise ValueError("请选择包含图片的日期文件夹")
    if len(files) != len(relative_paths):
        raise ValueError("文件路径数量与文件数量不一致")

    parsed_files = [
        (upload_file, *parse_relative_path(relative_path, normalized_folder_name))
        for upload_file, relative_path in zip(files, relative_paths, strict=True)
    ]

    settings = get_settings()
    images_dir = settings.images_dir
    target_dir = images_dir / normalized_folder_name
    ensure_inside_directory(images_dir, target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    results: list[UploadedDateImage] = []
    saved_count = 0
    skipped_existing_count = 0
    skipped_non_image_count = 0
    skipped_nested_count = 0

    for upload_file, file_name, is_nested in parsed_files:
        if is_nested:
            skipped_nested_count += 1
            results.append(
                UploadedDateImage(
                    file_name=file_name,
                    status="skipped_nested",
                    reason="仅上传日期文件夹根目录下的图片",
                )
            )
            continue

        if not is_supported_image_file(file_name):
            skipped_non_image_count += 1
            results.append(
                UploadedDateImage(
                    file_name=file_name,
                    status="skipped_non_image",
                    reason="非图片文件",
                )
            )
            continue

        target_path = target_dir / file_name
        ensure_inside_directory(target_dir, target_path)
        if target_path.exists():
            skipped_existing_count += 1
            results.append(
                UploadedDateImage(
                    file_name=file_name,
                    status="skipped_existing",
                    reason="同名文件已存在",
                )
            )
            continue

        content = await upload_file.read()
        target_path.write_bytes(content)
        saved_count += 1
        results.append(UploadedDateImage(file_name=file_name, status="saved"))

    logger.info(
        "日期图片文件夹上传完成: folder=%s saved=%d skipped_existing=%d skipped_non_image=%d skipped_nested=%d",
        normalized_folder_name,
        saved_count,
        skipped_existing_count,
        skipped_non_image_count,
        skipped_nested_count,
    )

    return {
        "folder_name": normalized_folder_name,
        "saved_count": saved_count,
        "skipped_existing_count": skipped_existing_count,
        "skipped_non_image_count": skipped_non_image_count,
        "skipped_nested_count": skipped_nested_count,
        "files": [
            {
                "file_name": result.file_name,
                "status": result.status,
                "reason": result.reason,
            }
            for result in results
        ],
    }
