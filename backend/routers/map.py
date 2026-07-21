from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.auth.dependencies import require_authenticated_user
from backend.db.admin import (
    get_enabled_map_view,
    get_enabled_reference_layer,
    list_enabled_map_views,
    list_enabled_reference_layers,
)
from backend.db.postgres import (
    MAP_MAX_LIMIT,
    WhiteMothSiteCodeError,
    WhiteMothSiteDuplicateError,
    check_white_moth_site_deletion,
    create_white_moth_site,
    delete_white_moth_site,
    fetch_admin_boundary_feature_collection,
    fetch_map_filter_options,
    fetch_reference_layer_feature_collection,
    fetch_view_feature_collection,
    get_white_moth_site_code_hint,
    get_white_moth_site_code_rules,
)
from backend.schemas import (
    WhiteMothSiteCodeHintResponse,
    WhiteMothSiteCreateRequest,
    WhiteMothSiteDeleteCheckResponse,
    WhiteMothSiteDeleteResponse,
    WhiteMothSiteResponse,
)


router = APIRouter()
RESERVED_VIEW_QUERY_PARAMS = {"bbox", "limit"}


def parse_bbox(raw_value: str | None) -> tuple[float, float, float, float] | None:
    if raw_value is None or raw_value.strip() == "":
        return None

    parts = [part.strip() for part in raw_value.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox 参数格式应为 minLng,minLat,maxLng,maxLat")

    try:
        min_lng, min_lat, max_lng, max_lat = [float(part) for part in parts]
    except ValueError as exc:
        raise ValueError("bbox 参数必须是数字") from exc

    if not (-180 <= min_lng <= 180 and -180 <= max_lng <= 180):
        raise ValueError("bbox 经度必须在 -180 到 180 之间")
    if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise ValueError("bbox 纬度必须在 -90 到 90 之间")
    if min_lng >= max_lng or min_lat >= max_lat:
        raise ValueError("bbox 最小坐标必须小于最大坐标")

    return min_lng, min_lat, max_lng, max_lat


def parse_limit(raw_value: str | None) -> int | None:
    if raw_value is None or raw_value.strip() == "":
        return None

    try:
        limit = int(raw_value)
    except ValueError as exc:
        raise ValueError("limit 参数必须是整数") from exc

    if limit < 1 or limit > MAP_MAX_LIMIT:
        raise ValueError(f"limit 参数必须在 1 到 {MAP_MAX_LIMIT} 之间")
    return limit


@router.get("/views", summary="列出地图视图")
async def get_views() -> list[dict]:
    try:
        return await list_enabled_map_views()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取地图视图失败：{exc}") from exc


@router.get("/reference-layers", summary="列出参考图层")
async def get_reference_layers() -> list[dict]:
    try:
        return await list_enabled_reference_layers()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取参考图层失败：{exc}") from exc


@router.get("/white-moth-sites/code-rules", summary="读取美国白蛾点位编号规则")
async def get_white_moth_site_rules() -> dict:
    return get_white_moth_site_code_rules()


@router.get(
    "/white-moth-sites/code-hint",
    response_model=WhiteMothSiteCodeHintResponse,
    summary="读取美国白蛾点位编号提示",
)
async def get_white_moth_site_code_hint_endpoint(
    prefix: str,
) -> WhiteMothSiteCodeHintResponse:
    try:
        return WhiteMothSiteCodeHintResponse(
            **await get_white_moth_site_code_hint(prefix)
        )
    except WhiteMothSiteCodeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取编号提示失败：{exc}") from exc


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


@router.get(
    "/white-moth-sites/{code}/delete-check",
    response_model=WhiteMothSiteDeleteCheckResponse,
    summary="删除前检查美国白蛾点位",
)
async def get_white_moth_site_delete_check(code: str) -> WhiteMothSiteDeleteCheckResponse:
    normalized_code = code.strip().upper()
    try:
        result = await check_white_moth_site_deletion(normalized_code)
        if result is None:
            return WhiteMothSiteDeleteCheckResponse(
                code=normalized_code,
                exists=False,
            )
        return WhiteMothSiteDeleteCheckResponse(exists=True, **result)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"删除前检查失败：{exc}") from exc


@router.delete(
    "/white-moth-sites/{code}",
    response_model=WhiteMothSiteDeleteResponse,
    summary="删除美国白蛾点位",
)
async def delete_white_moth_site_endpoint(
    code: str,
    current_user: dict = Depends(require_authenticated_user),
) -> WhiteMothSiteDeleteResponse:
    normalized_code = code.strip().upper()
    try:
        deleted = await delete_white_moth_site(
            code=normalized_code,
            operator=current_user,
        )
        if deleted is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"编号不存在：{normalized_code}",
            )
        return WhiteMothSiteDeleteResponse(**deleted)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"删除美国白蛾点位失败：{exc}") from exc


@router.get("/views/{view_name}", summary="读取指定地图视图的 GeoJSON")
async def get_view_geojson(view_name: str, request: Request) -> dict:
    view = await get_enabled_map_view(view_name)
    if view is None:
        raise HTTPException(status_code=404, detail=f"视图不存在或已停用：{view_name}")

    try:
        bbox = parse_bbox(request.query_params.get("bbox"))
        limit = parse_limit(request.query_params.get("limit"))
        filters: dict[str, list[str]] = {}
        for key, value in request.query_params.multi_items():
            if key in RESERVED_VIEW_QUERY_PARAMS:
                continue
            filters.setdefault(key, []).append(value)

        return await fetch_view_feature_collection(
            view_name=view_name,
            filters=filters,
            bbox=bbox,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取地图数据失败：{exc}") from exc


@router.get("/views/{view_name}/filter-options", summary="读取指定地图视图的筛选选项")
async def get_view_filter_options(view_name: str, request: Request) -> dict:
    try:
        view = await get_enabled_map_view(view_name)
        if view is None:
            raise ValueError(f"视图不存在或已停用：{view_name}")
        filters: dict[str, list[str]] = {}
        for key, value in request.query_params.multi_items():
            if key in RESERVED_VIEW_QUERY_PARAMS:
                continue
            filters.setdefault(key, []).append(value)
        return await fetch_map_filter_options(view_name, filters)
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
async def get_reference_layer_geojson(layer_name: str, request: Request) -> dict:
    try:
        bbox = parse_bbox(request.query_params.get("bbox"))
        limit = parse_limit(request.query_params.get("limit"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        layer = await get_enabled_reference_layer(layer_name)
        if layer is None:
            raise ValueError(f"参考图层不存在或已停用：{layer_name}")
        return await fetch_reference_layer_feature_collection(
            layer_name,
            bbox=bbox,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取参考图层失败：{exc}") from exc
