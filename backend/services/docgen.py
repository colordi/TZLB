from __future__ import annotations

import base64
import io
import subprocess
import tempfile
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
DOC_MEDIA_TYPE = "application/msword"
DOC_CONVERT_FILTER = "MS Word 97"
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
    serial_number = record.serial_number if record.serial_number is not None else index + 1
    context["pest_type"] = pest_type
    context["task_type"] = task_type
    context["task"] = task_name or task_type
    context["serial_number"] = str(serial_number).zfill(3)
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


def replace_suffix(filename: str, suffix: str) -> str:
    return f"{Path(filename).stem}{suffix}"


def ensure_template_context_complete(
    doc: DocxTemplate, context: dict, template_path: Path
) -> None:
    """确保模板中的占位字段都能在上下文中找到值。"""

    missing_variables = sorted(doc.get_undeclared_template_variables(context=context))
    if missing_variables:
        missing_list = "、".join(missing_variables)
        raise ValueError(f"模板缺少渲染字段：{missing_list}（模板：{template_path.name}）")


def ensure_template_markers_resolved(content: bytes, template_path: Path) -> None:
    """确保渲染后的文档中不存在未替换的模板标记。"""

    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        unresolved_files: list[str] = []
        for member in archive.namelist():
            if not member.startswith("word/") or not member.endswith(".xml"):
                continue
            xml_text = archive.read(member).decode("utf-8", errors="ignore")
            if "{{" in xml_text or "{%" in xml_text or "{#" in xml_text:
                unresolved_files.append(member)

    if unresolved_files:
        unresolved_list = "、".join(unresolved_files)
        raise ValueError(
            f"模板渲染后仍存在未替换占位：{unresolved_list}（模板：{template_path.name}）"
        )


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
    ensure_template_context_complete(doc, context, template_path)
    doc.render(context)

    buffer = io.BytesIO()
    doc.save(buffer)
    content = buffer.getvalue()
    ensure_template_markers_resolved(content, template_path)
    return build_output_filename(record, index), content


def convert_docx_bytes_to_doc(filename: str, content: bytes) -> tuple[str, bytes]:
    """使用 LibreOffice 将 docx 字节流转换为 doc。"""

    settings = get_settings()
    source_filename = replace_suffix(filename, ".docx")
    target_filename = replace_suffix(filename, ".doc")

    with tempfile.TemporaryDirectory(dir=settings.temp_dir, prefix="workorder_export_") as workdir:
        workdir_path = Path(workdir)
        source_path = workdir_path / source_filename
        target_path = workdir_path / target_filename
        source_path.write_bytes(content)

        try:
            subprocess.run(
                [
                    settings.libreoffice_bin,
                    "--headless",
                    "--convert-to",
                    f"doc:{DOC_CONVERT_FILTER}",
                    "--outdir",
                    str(workdir_path),
                    str(source_path),
                ],
                check=True,
                capture_output=True,
                timeout=settings.libreoffice_timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"未找到 LibreOffice 命令行工具：{settings.libreoffice_bin}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("LibreOffice 转换超时，请稍后重试。") from exc
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="ignore").strip() if exc.stderr else ""
            stdout = exc.stdout.decode("utf-8", errors="ignore").strip() if exc.stdout else ""
            detail = stderr or stdout or "未知错误"
            raise RuntimeError(f"LibreOffice 转换失败：{detail}") from exc

        if not target_path.exists():
            raise RuntimeError("LibreOffice 转换失败：未生成 .doc 文件。")

        return target_filename, target_path.read_bytes()


def build_download_artifact(filename: str, content: bytes) -> GeneratedArtifact:
    """返回单个 doc 下载产物。"""

    return GeneratedArtifact(
        filename=filename,
        media_type=DOC_MEDIA_TYPE,
        content=content,
    )


def generate_workorder_artifact(payload: WorkOrderGenerateRequest) -> GeneratedArtifact:
    """生成工作单下载产物。"""

    if len(payload.records) != 1:
        raise ValueError("批量压缩导出已取消，请改为逐条导出工作单。")

    template_path = get_template_path(payload.pest_type)
    temp_images: list[Path] = []

    try:
        filename, content = render_single_document(
            template_path=template_path,
            record=payload.records[0],
            pest_type=payload.pest_type,
            task_type=payload.task_type,
            task_name=payload.task,
            index=0,
            temp_images=temp_images,
        )
        filename, content = convert_docx_bytes_to_doc(filename, content)
        return build_download_artifact(filename, content)
    finally:
        cleanup_temp_images(temp_images)
