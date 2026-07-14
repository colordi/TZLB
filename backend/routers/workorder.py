from __future__ import annotations

import asyncio
from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from backend.exceptions import BusinessError, ConfigurationError
from backend.schemas import (
    WorkOrderBatchGenerateRequest,
    WorkOrderBatchJobCreateResponse,
    WorkOrderBatchJobStatusResponse,
    WorkOrderGenerateRequest,
)
from backend.services.date_image_folder_upload import upload_date_image_folder
from backend.services.docgen import generate_workorder_artifact, generate_workorder_batch_artifact
from backend.services.workorder_batch_jobs import batch_job_store, run_batch_export_job


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


@router.post(
    "/generate-batch-jobs",
    summary="创建批量导出任务（支持进度查询）",
    response_model=WorkOrderBatchJobCreateResponse,
)
async def create_workorder_batch_job(
    payload: WorkOrderBatchGenerateRequest,
) -> WorkOrderBatchJobCreateResponse:
    job = batch_job_store.create(total_records=len(payload.records))
    asyncio.create_task(run_batch_export_job(job.job_id, payload))
    return WorkOrderBatchJobCreateResponse(
        job_id=job.job_id,
        total=job.total,
        status=job.status,
    )


@router.get(
    "/generate-batch-jobs/{job_id}",
    summary="查询批量导出任务进度",
    response_model=WorkOrderBatchJobStatusResponse,
)
async def get_workorder_batch_job_status(job_id: str) -> WorkOrderBatchJobStatusResponse:
    job = batch_job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="批量导出任务不存在或已过期")
    return WorkOrderBatchJobStatusResponse(**job.to_status_dict())


@router.get(
    "/generate-batch-jobs/{job_id}/download",
    summary="下载已完成的批量导出文件",
)
async def download_workorder_batch_job(job_id: str) -> Response:
    job = batch_job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="批量导出任务不存在或已过期")
    if job.status == "failed":
        raise BusinessError(job.error or "批量导出失败")
    if job.status != "completed" or not job.content:
        raise BusinessError("批量导出尚未完成，请稍后再试")

    encoded_name = quote(job.filename or "批量导出.zip")
    return Response(
        content=job.content,
        media_type=job.media_type or "application/zip",
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
