from __future__ import annotations

import asyncio
from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response

from backend.exceptions import BusinessError, ConfigurationError
from backend.schemas import (
    WorkOrderBatchGenerateRequest,
    WorkOrderBatchJobCreateResponse,
    WorkOrderBatchJobStatusResponse,
    WorkOrderGenerateRequest,
)
from backend.services.point_date_image_service import (
    delete_point_date_image,
    list_date_images,
    list_point_date_images,
    resolve_point_date_image_path,
    save_point_date_images,
)
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


@router.get("/point-date-images", summary="列出指定日期的图片，可按点位编号过滤")
async def list_workorder_point_date_images(
    survey_date: str = Query(..., description="调查日期，格式 YYYY-MM-DD"),
    point_code: str | None = Query(default=None, description="点位编号，缺省时返回当日全部图片"),
) -> dict:
    try:
        images = (
            list_point_date_images(survey_date=survey_date, point_code=point_code)
            if point_code
            else list_date_images(survey_date=survey_date)
        )
        return {
            "survey_date": survey_date,
            "point_code": point_code or "",
            "images": images,
        }
    except ValueError as exc:
        raise BusinessError(str(exc)) from exc


@router.post("/point-date-images", summary="上传点位日期图片（自动按编号命名）")
async def upload_workorder_point_date_images(
    survey_date: str = Form(..., description="调查日期，格式 YYYY-MM-DD"),
    point_code: str = Form(..., description="点位编号"),
    files: list[UploadFile] = File(..., description="图片文件"),
) -> dict:
    try:
        return await save_point_date_images(
            survey_date=survey_date,
            point_code=point_code,
            files=files,
        )
    except ValueError as exc:
        raise BusinessError(str(exc)) from exc


@router.get("/point-date-images/{survey_date}/{file_name}", summary="读取点位日期图片")
async def read_workorder_point_date_image(survey_date: str, file_name: str) -> FileResponse:
    try:
        image_path = resolve_point_date_image_path(
            survey_date=survey_date,
            file_name=file_name,
        )
    except ValueError as exc:
        raise BusinessError(str(exc)) from exc
    if image_path is None:
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(image_path)


@router.delete("/point-date-images/{survey_date}/{file_name}", summary="删除点位日期图片")
async def delete_workorder_point_date_image(
    survey_date: str,
    file_name: str,
    point_code: str = Query(..., description="点位编号"),
) -> dict:
    try:
        delete_point_date_image(
            survey_date=survey_date,
            point_code=point_code,
            file_name=file_name,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise BusinessError(str(exc)) from exc
    return {"deleted": file_name}
