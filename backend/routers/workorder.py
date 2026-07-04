from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import Response

from backend.exceptions import BusinessError, ConfigurationError
from backend.schemas import WorkOrderBatchGenerateRequest, WorkOrderGenerateRequest
from backend.services.date_image_folder_upload import upload_date_image_folder
from backend.services.docgen import generate_workorder_artifact, generate_workorder_batch_artifact


MULTI_RECORD_EXPORT_MESSAGE = "批量压缩导出已取消，请改为逐条导出工作单。"


router = APIRouter()


@router.post("/generate", summary="生成单条工作单")
async def generate_workorder(payload: WorkOrderGenerateRequest) -> Response:
    if len(payload.records) != 1:
        raise BusinessError(MULTI_RECORD_EXPORT_MESSAGE)

    try:
        artifact = generate_workorder_artifact(payload)
    except ValueError as exc:
        raise BusinessError(str(exc)) from exc
    except FileNotFoundError as exc:
        raise ConfigurationError("未找到工作单模板文件，请联系管理员") from exc

    encoded_name = quote(artifact.filename)
    return Response(
        content=artifact.content,
        media_type=artifact.media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
        },
    )


@router.post("/generate-batch", summary="批量生成工作单并打包为 zip")
async def generate_workorder_batch(payload: WorkOrderBatchGenerateRequest) -> Response:
    try:
        artifact = generate_workorder_batch_artifact(payload)
    except ValueError as exc:
        raise BusinessError(str(exc)) from exc
    except FileNotFoundError as exc:
        raise ConfigurationError("未找到工作单模板文件，请联系管理员") from exc

    encoded_name = quote(artifact.filename)
    return Response(
        content=artifact.content,
        media_type=artifact.media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
        },
    )


@router.post("/date-image-folder", summary="上传日期图片文件夹")
async def upload_workorder_date_image_folder(
    folder_name: str = Form(..., description="日期文件夹名称，格式 YYYY-MM-DD"),
    files: list[UploadFile] = File(..., description="日期文件夹下的文件"),
    relative_paths: list[str] = Form(..., description="浏览器提供的相对路径"),
) -> dict:
    try:
        return await upload_date_image_folder(
            folder_name=folder_name,
            files=files,
            relative_paths=relative_paths,
        )
    except ValueError as exc:
        raise BusinessError(str(exc)) from exc
