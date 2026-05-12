from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from backend.db.postgres import (
    fetch_admin_boundary_feature_collection,
    fetch_map_filter_options,
    fetch_view_feature_collection,
    get_map_view,
    list_map_views,
)


router = APIRouter()


@router.get("/views", summary="列出地图视图")
async def get_views() -> list[dict]:
    try:
        return await list_map_views()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取地图视图失败：{exc}") from exc


@router.get("/views/{view_name}", summary="读取指定地图视图的 GeoJSON")
async def get_view_geojson(view_name: str, request: Request) -> dict:
    view = await get_map_view(view_name)
    if view is None:
        raise HTTPException(status_code=404, detail=f"视图不存在：{view_name}")

    try:
        filters: dict[str, list[str]] = {}
        for key, value in request.query_params.multi_items():
            filters.setdefault(key, []).append(value)

        return await fetch_view_feature_collection(
            view_name=view_name,
            filters=filters,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取地图数据失败：{exc}") from exc


@router.get("/views/{view_name}/filter-options", summary="读取指定地图视图的筛选选项")
async def get_view_filter_options(view_name: str) -> dict:
    try:
        return await fetch_map_filter_options(view_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取筛选选项失败：{exc}") from exc


@router.get("/layers/admin-boundary", summary="读取行政区边界图层")
async def get_admin_boundary_geojson() -> dict:
    try:
        return await fetch_admin_boundary_feature_collection()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取行政区边界失败：{exc}") from exc
