from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from backend.exceptions import BusinessError
from backend.services import point_screenshot_service


router = APIRouter()


@router.get("/status", summary="查询点位截图状态")
async def get_point_screenshot_status(pest_type: str) -> dict:
    try:
        points = await point_screenshot_service.list_point_screenshot_status(pest_type)
    except ValueError as exc:
        raise BusinessError(str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"pest_type": pest_type.strip(), "points": points}


@router.post("/upload", summary="上传或替换点位截图")
async def upload_point_screenshot(
    pest_type: str = Form(...),
    code: str = Form(...),
    file: UploadFile = File(...),
) -> dict:
    try:
        return await point_screenshot_service.save_point_screenshot(
            pest_type,
            code,
            file,
        )
    except ValueError as exc:
        raise BusinessError(str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/", summary="删除点位截图")
async def delete_point_screenshot(pest_type: str, code: str) -> dict:
    try:
        return point_screenshot_service.delete_point_screenshot(pest_type, code)
    except ValueError as exc:
        raise BusinessError(str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/preview", summary="预览点位截图")
async def preview_point_screenshot(
    pest_type: str,
    code: str,
    size: Literal["full", "thumb"] = "full",
) -> Response:
    try:
        content, media_type = point_screenshot_service.read_point_screenshot(
            pest_type,
            code,
            size=size,
        )
    except ValueError as exc:
        raise BusinessError(str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type=media_type,
        headers={"Cache-Control": "private, max-age=300"},
    )
