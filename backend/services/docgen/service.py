from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from backend.config import get_settings, normalize_output_format
from backend.logging_config import get_logger
from backend.schemas import WorkOrderGenerateRequest
from backend.services.docgen.constants import (
    DOC_MEDIA_TYPE,
    DOCX_MEDIA_TYPE,
    ZIP_MEDIA_TYPE,
    GeneratedArtifact,
)
from backend.services.docgen.images import cleanup_temp_images

logger = get_logger(__name__)


def _pkg():
    """Late-bound package access so tests can patch ``backend.services.docgen.*``."""
    from backend.services import docgen as package

    return package


def build_download_artifact(filename: str, content: bytes, media_type: str) -> GeneratedArtifact:
    """返回单个下载产物。"""

    return GeneratedArtifact(
        filename=filename,
        media_type=media_type,
        content=content,
    )


def resolve_output_format(payload: WorkOrderGenerateRequest) -> str:
    settings = get_settings()
    return normalize_output_format(payload.output_format or settings.workorder_default_output_format)


def generate_workorder_artifact(payload: WorkOrderGenerateRequest) -> GeneratedArtifact:
    """生成工作单下载产物。"""

    if len(payload.records) != 1:
        raise ValueError("批量压缩导出已取消，请改为逐条导出工作单。")

    template_path = _pkg().get_template_path(payload.pest_type)
    output_format = resolve_output_format(payload)
    temp_images: list[Path] = []
    record = payload.records[0]

    logger.info(
        "开始生成工作单: pest_type=%s task_type=%s output_format=%s location=%s date=%s images=%d",
        payload.pest_type,
        payload.task_type,
        output_format,
        record.location_name,
        record.survey_date,
        len(record.images),
    )

    try:
        filename, content = _pkg().render_single_document(
            template_path=template_path,
            record=record,
            pest_type=payload.pest_type,
            task_type=payload.task_type,
            task_name=payload.task,
            index=0,
            temp_images=temp_images,
            year=payload.year,
        )
        if output_format == "doc":
            filename, content = _pkg().convert_docx_bytes_to_doc(filename, content)
            logger.info("工作单生成完成: %s (doc)", filename)
            return build_download_artifact(filename, content, DOC_MEDIA_TYPE)
        if output_format == "docx":
            logger.info("工作单生成完成: %s (docx)", filename)
            return build_download_artifact(filename, content, DOCX_MEDIA_TYPE)
        raise ValueError("输出格式只能是 doc 或 docx")
    finally:
        cleanup_temp_images(temp_images)


@dataclass(slots=True)
class BatchResult:
    filename: str
    content: bytes


@dataclass(slots=True)
class BatchFailure:
    index: int
    location_name: str
    location_id: str
    reason: str


def build_batch_zip_filename(success_count: int, year: int | None = None) -> str:
    resolved_year = year if year is not None else datetime.now().year
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{resolved_year}年工作单批量导出_{timestamp}_{success_count}份.zip"


def generate_workorder_batch_artifact(
    payload: WorkOrderGenerateRequest,
    progress_callback=None,
) -> GeneratedArtifact:
    """批量生成工作单并打包为 zip。

    单条失败不影响整体流程，成功文件放入 zip，失败记录写入 失败记录.json。
    如果全部失败，则抛出 ValueError 统一返回 400。

    progress_callback 可选，签名：
    callback(current: int, total: int, phase: str, message: str = "") -> None
    - phase=generating：每完成一条记录调用一次（current 为已处理条数）
    - phase=packing：开始打包时调用
    - phase=completed：打包完成时调用
    """

    template_path = _pkg().get_template_path(payload.pest_type)
    output_format = resolve_output_format(payload)
    successes: list[BatchResult] = []
    failures: list[BatchFailure] = []
    total_records = len(payload.records)
    # 文档生成 + 打包 两段步骤，便于前端显示真实进度
    total_steps = total_records + 1

    def report(current: int, phase: str, message: str = "") -> None:
        if progress_callback is None:
            return
        progress_callback(current, total_steps, phase, message)

    logger.info(
        "开始批量生成工作单: pest_type=%s task_type=%s output_format=%s count=%d",
        payload.pest_type,
        payload.task_type,
        output_format,
        total_records,
    )

    for index, record in enumerate(payload.records):
        temp_images: list[Path] = []
        location_label = record.location_name or record.location_id or f"第{index + 1}条"
        try:
            filename, content = _pkg().render_single_document(
                template_path=template_path,
                record=record,
                pest_type=payload.pest_type,
                task_type=payload.task_type,
                task_name=payload.task,
                index=index,
                temp_images=temp_images,
                year=payload.year,
            )
            if output_format == "doc":
                filename, content = _pkg().convert_docx_bytes_to_doc(filename, content)
            successes.append(BatchResult(filename=filename, content=content))
        except Exception as exc:  # noqa: BLE001
            reason = str(exc)
            logger.warning(
                "第 %d 条工作单生成失败: location=%s reason=%s",
                index + 1,
                record.location_name,
                reason,
            )
            failures.append(
                BatchFailure(
                    index=index + 1,
                    location_name=record.location_name or "未命名点位",
                    location_id=record.location_id or "",
                    reason=reason,
                )
            )
        finally:
            cleanup_temp_images(temp_images)
            report(
                index + 1,
                "generating",
                f"正在生成 {index + 1}/{total_records}：{location_label}",
            )

    if not successes:
        failure_details = "；".join(
            f"第 {failure.index} 条（{failure.location_name}）: {failure.reason}"
            for failure in failures
        )
        raise ValueError(f"批量导出全部失败：{failure_details}")

    report(total_records, "packing", "正在打包导出文件…")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for result in successes:
            archive.writestr(f"工作单/{result.filename}", result.content)

        if failures:
            failures_json = io.StringIO()
            json.dump(
                {
                    "total": total_records,
                    "success_count": len(successes),
                    "failure_count": len(failures),
                    "failures": [
                        {
                            "index": failure.index,
                            "location_name": failure.location_name,
                            "location_id": failure.location_id,
                            "reason": failure.reason,
                        }
                        for failure in failures
                    ],
                },
                failures_json,
                ensure_ascii=False,
                indent=2,
            )
            archive.writestr("失败记录.json", failures_json.getvalue())

    logger.info(
        "批量生成工作单完成: success=%d failure=%d",
        len(successes),
        len(failures),
    )

    report(total_steps, "completed", f"已完成 {len(successes)} 份工作单打包")

    return GeneratedArtifact(
        filename=build_batch_zip_filename(len(successes), payload.year),
        media_type=ZIP_MEDIA_TYPE,
        content=buffer.getvalue(),
    )
