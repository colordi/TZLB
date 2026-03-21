from __future__ import annotations

import base64
import io
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage

from backend.config import get_settings
from backend.schemas import WorkOrderGenerateRequest, WorkOrderRecord


MAX_IMAGES = 4
IMAGE_WIDTH_MM = 70
CHI_HUO_TYPES = {"春尺蠖", "国槐尺蠖"}
DOC_FIELD_MAPPING = {
    "description": "detailed_description",
    "host_plant": "host",
    "pest_name": "pest_species",
}


@dataclass(slots=True)
class GeneratedArtifact:
    filename: str
    media_type: str
    content: bytes


def get_template_path(pest_type: str) -> Path:
    settings = get_settings()
    mapping = {
        "春尺蠖": settings.templates_dir / "春尺蠖工作单模板.docx",
        "国槐尺蠖": settings.templates_dir / "国槐尺蠖工作单模板.docx",
        "其他害虫": settings.templates_dir / "其他害虫工作单模板.docx",
    }
    path = mapping.get(pest_type)
    if path is None or not path.exists():
        raise FileNotFoundError(f"未找到 {pest_type} 对应的模板文件")
    return path


def save_base64_images(base64_list: list[str], row_id: str) -> list[Path]:
    """将前端上传的 Base64 图片写入临时目录。"""

    settings = get_settings()
    paths: list[Path] = []
    for index, raw_value in enumerate(base64_list[:MAX_IMAGES]):
        try:
            encoded = raw_value.split(",", 1)[1] if "," in raw_value else raw_value
            content = base64.b64decode(encoded)
            image_path = settings.temp_dir / f"{row_id}_{index}_{uuid.uuid4().hex[:8]}.jpg"
            image_path.write_bytes(content)
            paths.append(image_path)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"第 {index + 1} 张图片无法解析：{exc}") from exc
    return paths


def cleanup_temp_images(paths: list[Path]) -> None:
    for path in paths:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            continue


def build_context(
    doc: DocxTemplate,
    record: WorkOrderRecord,
    pest_type: str,
    task_type: str,
    task_name: str,
    index: int,
    image_paths: list[Path],
) -> dict:
    """组装模板上下文。"""

    context = record.model_dump()
    context["pest_type"] = pest_type
    context["task_type"] = task_type
    context["task"] = task_name or task_type
    context["serial_number"] = str(index + 1).zfill(3)
    context["note"] = context.get("note") or ""

    if pest_type in CHI_HUO_TYPES:
        context["plot_type"] = context.get("plot_type") or "平原造林"
        context["pest_name"] = ""
        context["host_plant"] = ""
    else:
        context["plot_type"] = context.get("plot_type") or ""

    for source_key, target_key in DOC_FIELD_MAPPING.items():
        context[target_key] = context.get(source_key) or ""

    placeholders = ["img1", "img2", "img3", "img4"]
    for placeholder in placeholders:
        context[placeholder] = ""

    for idx, image_path in enumerate(image_paths[:MAX_IMAGES]):
        context[placeholders[idx]] = InlineImage(doc, str(image_path), width=Mm(IMAGE_WIDTH_MM))

    return context


def build_output_filename(record: WorkOrderRecord, index: int) -> str:
    town = record.town_or_street or "未知乡镇"
    location = record.location_name or "未命名点位"
    survey_date = record.survey_date or datetime.now().strftime("%Y-%m-%d")
    serial = record.location_id or str(index + 1).zfill(3)
    current_year = datetime.now().year
    return f"{current_year}林业有害生物防治工作单（{town}）-{location}-{survey_date}-{serial}.docx"


def render_single_document(
    template_path: Path,
    record: WorkOrderRecord,
    pest_type: str,
    task_type: str,
    task_name: str,
    index: int,
    temp_images: list[Path],
) -> tuple[str, bytes]:
    """渲染单条 Word 工作单。"""

    doc = DocxTemplate(template_path)
    row_id = f"row_{index}_{uuid.uuid4().hex[:8]}"
    image_paths = save_base64_images(record.images, row_id) if record.images else []
    temp_images.extend(image_paths)

    context = build_context(doc, record, pest_type, task_type, task_name, index, image_paths)
    doc.render(context)

    buffer = io.BytesIO()
    doc.save(buffer)
    return build_output_filename(record, index), buffer.getvalue()


def build_download_artifact(generated: list[tuple[str, bytes]]) -> GeneratedArtifact:
    """根据文件数量返回 docx 或 zip 响应。"""

    if len(generated) == 1:
        filename, content = generated[0]
        return GeneratedArtifact(
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            content=content,
        )

    archive_name = f"{datetime.now().year}林业工作单批量导出_{datetime.now():%Y%m%d_%H%M%S}.zip"
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for filename, content in generated:
            archive.writestr(filename, content)
    return GeneratedArtifact(
        filename=archive_name,
        media_type="application/zip",
        content=zip_buffer.getvalue(),
    )


def generate_workorder_artifact(payload: WorkOrderGenerateRequest) -> GeneratedArtifact:
    """生成工作单下载产物。"""

    template_path = get_template_path(payload.pest_type)
    temp_images: list[Path] = []
    generated: list[tuple[str, bytes]] = []

    try:
        for index, record in enumerate(payload.records):
            generated.append(
                render_single_document(
                    template_path=template_path,
                    record=record,
                    pest_type=payload.pest_type,
                    task_type=payload.task_type,
                    task_name=payload.task,
                    index=index,
                    temp_images=temp_images,
                )
            )
        return build_download_artifact(generated)
    finally:
        cleanup_temp_images(temp_images)
