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
    ResetPasswordRequest,
    UpdateUserRequest,
)


router = APIRouter(
    dependencies=[Depends(require_user_role(USER_ROLE_ADMIN))],
)


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
