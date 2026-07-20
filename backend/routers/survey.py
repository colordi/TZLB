from __future__ import annotations

from datetime import date as date_cls
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from backend.db.postgres import fetch_survey_candidates_by_type
from backend.exceptions import BusinessError
from backend.schemas import PestType
from backend.services.pest_registry import validate_generation as validate_registered_generation
from backend.services.survey_excel_import import import_survey_excel
from backend.services.survey_template import generate_import_template_bytes


router = APIRouter()


@router.get("/candidates", summary="读取调查导入候选记录")
async def get_survey_candidates(
    date: date_cls | None = Query(default=None, description="调查日期，格式为 YYYY-MM-DD"),
    pest_type: PestType = Query(default="春尺蠖", description="害虫类型"),
    year: int | None = Query(default=None, description="年份，默认取调查日期年份"),
    generation: str | None = Query(default=None, description="世代，如第一代、第二代"),
) -> list[dict[str, Any]]:
    target_date = date or date_cls.today()

    try:
        resolved_generation = validate_registered_generation(pest_type, generation)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        return await fetch_survey_candidates_by_type(
            survey_date=target_date,
            pest_type=pest_type,
            year=year,
            generation=resolved_generation,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取调查导入候选数据失败：{exc}") from exc


@router.post("/excel-import", summary="上传 Excel 并导入 survey/ledger 表")
async def import_survey_excel_file(
    dry_run: bool = Query(default=True, description="true 为只预览校验，false 为确认入库"),
    file: UploadFile = File(..., description="调查 Excel 文件，仅支持 .xlsx"),
) -> dict[str, Any]:
    file_name = file.filename or ""
    if not file_name.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 格式的 Excel 文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Excel 文件为空")

    try:
        return await import_survey_excel(
            content=content,
            file_name=file_name,
            dry_run=dry_run,
        )
    except ValueError as exc:
        raise BusinessError(str(exc)) from exc


@router.get("/import-template", summary="下载数据导入模板")
async def download_survey_import_template() -> Response:
    try:
        content = await generate_import_template_bytes()
    except ValueError as exc:
        raise BusinessError(str(exc)) from exc

    exported_at = date_cls.today().strftime("%Y%m%d")
    filename = f"林业数据导入模板_{exported_at}.xlsx"
    encoded_name = quote(filename)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
        },
    )
