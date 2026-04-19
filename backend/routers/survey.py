from __future__ import annotations

from datetime import date as date_cls
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.db.postgres import fetch_survey_candidates_by_type
from backend.schemas import PestType


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
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取调查导入候选数据失败：{exc}") from exc
