from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from backend.schemas import WorkOrderGenerateRequest
from backend.services.docgen import generate_workorder_artifact


MULTI_RECORD_EXPORT_MESSAGE = "批量压缩导出已取消，请改为逐条导出工作单。"


router = APIRouter()


@router.post("/generate", summary="生成单条工作单")
async def generate_workorder(payload: WorkOrderGenerateRequest) -> Response:
    if len(payload.records) != 1:
        raise HTTPException(status_code=400, detail=MULTI_RECORD_EXPORT_MESSAGE)

    try:
        artifact = generate_workorder_artifact(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"生成工作单失败：{exc}") from exc

    encoded_name = quote(artifact.filename)
    return Response(
        content=artifact.content,
        media_type=artifact.media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
        },
    )
