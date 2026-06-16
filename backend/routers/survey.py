from __future__ import annotations

from datetime import date as date_cls
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from backend.db.postgres import fetch_survey_candidates_by_type
from backend.schemas import PestType
from backend.services.survey_excel_import import import_survey_excel


router = APIRouter()


@router.get("/candidates", summary="读取调查导入候选记录")
async def get_survey_candidates(
    date: date_cls | None = Query(default=None, description="调查日期，格式为 YYYY-MM-DD"),
    pest_type: PestType = Query(default="春尺蠖", description="害虫类型"),
) -> list[dict[str, Any]]:
    target_date = date or date_cls.today()

    try:
        return await fetch_survey_candidates_by_type(
            survey_date=target_date,
            pest_type=pest_type,
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
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"导入调查 Excel 失败：{exc}") from exc
