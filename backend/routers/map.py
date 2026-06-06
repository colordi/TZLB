from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from backend.db.postgres import (
    WhiteMothSiteCodeError,
    WhiteMothSiteDuplicateError,
    create_white_moth_site,
    fetch_admin_boundary_feature_collection,
    fetch_map_filter_options,
    fetch_reference_layer_feature_collection,
    fetch_view_feature_collection,
    get_white_moth_site_code_rules,
    get_map_view,
    list_map_views,
    list_reference_layers,
)
from backend.schemas import WhiteMothSiteCreateRequest, WhiteMothSiteResponse


router = APIRouter()


@router.get("/views", summary="列出地图视图")
async def get_views() -> list[dict]:
    try:
        return await list_map_views()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取地图视图失败：{exc}") from exc


@router.get("/reference-layers", summary="列出参考图层")
async def get_reference_layers() -> list[dict]:
    try:
        return await list_reference_layers()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取参考图层失败：{exc}") from exc


@router.get("/white-moth-sites/code-rules", summary="读取美国白蛾点位编号规则")
async def get_white_moth_site_rules() -> dict:
    return get_white_moth_site_code_rules()


@router.post(
    "/white-moth-sites",
    response_model=WhiteMothSiteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新增美国白蛾点位",
)
async def post_white_moth_site(
    payload: WhiteMothSiteCreateRequest,
) -> WhiteMothSiteResponse:
    try:
        created_site = await create_white_moth_site(
            code=payload.code,
            site_name=payload.site_name,
            longitude=payload.longitude,
            latitude=payload.latitude,
        )
        return WhiteMothSiteResponse(**created_site)
    except WhiteMothSiteCodeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except WhiteMothSiteDuplicateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"新增美国白蛾点位失败：{exc}") from exc


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


@router.get("/reference-layers/{layer_name}", summary="读取指定参考图层 GeoJSON")
async def get_reference_layer_geojson(layer_name: str) -> dict:
    try:
        return await fetch_reference_layer_feature_collection(layer_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取参考图层失败：{exc}") from exc
