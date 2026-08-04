from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.services.statistics import (
    get_white_moth_daily_statistics,
    get_white_moth_generation_summary,
    get_white_moth_host_summary,
    get_white_moth_locality_summary,
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
async def get_white_moth_generation_statistics(
    year: int | None = Query(None, description="年份"),
) -> dict[str, Any]:
    try:
        return await get_white_moth_generation_summary(year=year)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取美国白蛾世代汇总失败：{exc}") from exc


@router.get("/white-moth/locality-summary", summary="读取美国白蛾各属地受害汇总")
async def get_white_moth_locality_statistics(
    year: int | None = Query(None, description="年份"),
    generation: str | None = Query(None, description="世代"),
    as_of_date: str | None = Query(
        None,
        description="调查截止日期（YYYY-MM-DD，默认今天）：仅纳入首次调查/下派日不晚于该日的点位；"
        "防治完成按台账最新状态统计，不截断完成日",
    ),
    severe_plant_threshold: int | None = Query(
        None,
        description="严重点位受害株阈值，默认 10",
        ge=1,
        le=10000,
    ),
) -> dict[str, Any]:
    try:
        return await get_white_moth_locality_summary(
            year=year,
            generation=generation,
            as_of_date=as_of_date,
            severe_plant_threshold=severe_plant_threshold,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"查询参数无效：{exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取美国白蛾属地受害汇总失败：{exc}") from exc


@router.get("/white-moth/host-summary", summary="读取美国白蛾寄主分布汇总")
async def get_white_moth_host_statistics(
    year: int | None = Query(None, description="年份"),
    generation: str | None = Query(None, description="世代"),
) -> dict[str, Any]:
    try:
        return await get_white_moth_host_summary(year=year, generation=generation)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取美国白蛾寄主分布汇总失败：{exc}") from exc
