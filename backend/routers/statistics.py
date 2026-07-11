from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.services.statistics import (
    get_white_moth_daily_statistics,
    get_white_moth_generation_summary,
)


router = APIRouter()


@router.get("/white-moth/daily", summary="读取美国白蛾每日信息统计")
async def get_white_moth_daily(
    year: int | None = Query(None, description="年份"),
    generation: str | None = Query(None, description="世代"),
) -> dict[str, Any]:
    try:
        return await get_white_moth_daily_statistics(year=year, generation=generation)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取美国白蛾每日统计失败：{exc}") from exc


@router.get("/white-moth/generation-summary", summary="读取美国白蛾各世代汇总")
async def get_white_moth_generation_statistics() -> dict[str, Any]:
    try:
        return await get_white_moth_generation_summary()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取美国白蛾世代汇总失败：{exc}") from exc
