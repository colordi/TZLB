from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth.dependencies import require_user_role
from backend.auth.store import USER_ROLE_ADMIN
from backend.db.admin import (
    batch_upsert_layer_metadata,
    create_user,
    delete_user,
    get_dashboard_stats,
    get_user_by_id,
    list_layer_metadata,
    list_operation_logs,
    list_users,
    reset_user_password,
    update_user,
)
from backend.schemas import (
    AdminUserResponse,
    BatchUpdateLayersRequest,
    CreateUserRequest,
    DashboardStatsResponse,
    LayerMetadataResponse,
    OperationLogListResponse,
    ResetPasswordRequest,
    TaskViewDefinitionRequest,
    TaskViewMutationResponse,
    TaskViewPreviewResponse,
    TaskViewSourcesResponse,
    UpdateUserRequest,
)
from backend.services import view_builder


router = APIRouter(
    dependencies=[Depends(require_user_role(USER_ROLE_ADMIN))],
)


def _task_view_definition(payload: TaskViewDefinitionRequest) -> dict:
    """将请求模型转换为构建器定义，筛选键映射为中文列名。"""

    return {
        "name": payload.name,
        "display_name": payload.display_name,
        "base_table": payload.base_table,
        "related_table": payload.related_table,
        "site_name_column": payload.site_name_column,
        "filters": {
            view_builder.YEAR_COLUMN: payload.filters.year,
            view_builder.GENERATION_COLUMN: payload.filters.generation,
            "codes": payload.filters.codes,
        },
    }


# ──────────────────────────────────────────────
#  Dashboard
# ──────────────────────────────────────────────


@router.get(
    "/dashboard",
    response_model=DashboardStatsResponse,
    summary="管理概览 KPI",
)
async def get_dashboard() -> DashboardStatsResponse:
    try:
        return await get_dashboard_stats()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"读取管理概览失败：{exc}") from exc


# ──────────────────────────────────────────────
#  Layer Metadata
# ──────────────────────────────────────────────


@router.get(
    "/layers",
    response_model=list[LayerMetadataResponse],
    summary="列出图层元数据",
)
async def get_layers() -> list[LayerMetadataResponse]:
    try:
        return await list_layer_metadata()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"读取图层元数据失败：{exc}") from exc


@router.put(
    "/layers",
    response_model=list[LayerMetadataResponse],
    summary="批量更新图层元数据",
)
async def put_layers(payload: BatchUpdateLayersRequest) -> list[LayerMetadataResponse]:
    try:
        items = [item.model_dump() for item in payload.items]
        return await batch_upsert_layer_metadata(items)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"更新图层元数据失败：{exc}") from exc


# ──────────────────────────────────────────────
#  Task View Builder — 任务图层构建器
# ──────────────────────────────────────────────


@router.get(
    "/view-builder/sources",
    response_model=TaskViewSourcesResponse,
    summary="列出任务视图构建器候选源表",
)
async def get_view_builder_sources() -> TaskViewSourcesResponse:
    try:
        return await view_builder.list_builder_sources()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"读取候选源表失败：{exc}") from exc


@router.post(
    "/view-builder/preview",
    response_model=TaskViewPreviewResponse,
    summary="预览任务视图",
)
async def post_view_builder_preview(
    payload: TaskViewDefinitionRequest,
) -> TaskViewPreviewResponse:
    try:
        return await view_builder.preview_task_view(_task_view_definition(payload))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"预览任务视图失败：{exc}") from exc


@router.post(
    "/view-builder/views",
    response_model=TaskViewMutationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="发布任务视图",
)
async def post_view_builder_view(
    payload: TaskViewDefinitionRequest,
) -> TaskViewMutationResponse:
    try:
        return await view_builder.create_task_view(_task_view_definition(payload))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"发布任务视图失败：{exc}") from exc


@router.delete(
    "/view-builder/views/{view_name}",
    response_model=TaskViewMutationResponse,
    summary="删除任务视图",
)
async def delete_view_builder_view(view_name: str) -> TaskViewMutationResponse:
    try:
        deleted = await view_builder.delete_task_view(view_name)
        if deleted is None:
            raise HTTPException(status_code=404, detail=f"任务视图不存在：{view_name}")
        return deleted
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"删除任务视图失败：{exc}") from exc


# ──────────────────────────────────────────────
#  User Management
# ──────────────────────────────────────────────


@router.get(
    "/users",
    response_model=list[AdminUserResponse],
    summary="列出所有用户",
)
async def get_users() -> list[AdminUserResponse]:
    try:
        return await list_users()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"读取用户列表失败：{exc}") from exc


@router.post(
    "/users",
    response_model=AdminUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建用户",
)
async def post_user(payload: CreateUserRequest) -> AdminUserResponse:
    try:
        return await create_user(
            username=payload.username,
            password=payload.password,
            display_name=payload.display_name,
            role=payload.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"创建用户失败：{exc}") from exc


@router.put(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="更新用户信息",
)
async def put_user(user_id: int, payload: UpdateUserRequest) -> AdminUserResponse:
    try:
        user = await update_user(
            user_id=user_id,
            display_name=payload.display_name,
            role=payload.role,
            is_active=payload.is_active,
        )
        if user is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        return user
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"更新用户失败：{exc}") from exc


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除用户",
)
async def delete_user_endpoint(user_id: int) -> None:
    try:
        success = await delete_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="用户不存在")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"删除用户失败：{exc}") from exc


@router.post(
    "/users/{user_id}/reset-password",
    status_code=status.HTTP_200_OK,
    summary="重置用户密码",
)
async def post_reset_password(user_id: int, payload: ResetPasswordRequest) -> dict:
    try:
        success = await reset_user_password(user_id, payload.new_password)
        if not success:
            raise HTTPException(status_code=404, detail="用户不存在")
        return {"message": "密码重置成功"}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"重置密码失败：{exc}") from exc


# ──────────────────────────────────────────────
#  Operation Logs
# ──────────────────────────────────────────────


@router.get(
    "/operation-logs",
    response_model=OperationLogListResponse,
    summary="列出点位操作日志",
)
async def get_operation_logs(limit: int = 100, offset: int = 0) -> OperationLogListResponse:
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit 参数必须在 1 到 500 之间")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset 参数必须大于等于 0")
    try:
        items, total = await list_operation_logs(limit=limit, offset=offset)
        return OperationLogListResponse(items=items, total=total)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"读取操作日志失败：{exc}") from exc
