from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.auth.dependencies import get_current_user
from backend.db.data_manager import (
    MAX_PAGE_SIZE,
    delete_row,
    fetch_rows,
    get_columns,
    insert_row,
    list_change_logs,
    list_manageable_tables,
    update_row,
)
from backend.schemas import (
    DataManagerChangeLogListResponse,
    DataManagerColumnInfo,
    DataManagerRowCreateRequest,
    DataManagerRowDeleteRequest,
    DataManagerRowsResponse,
    DataManagerRowUpdateRequest,
    DataManagerTableInfo,
)
from backend.services.data_manager import (
    fetch_managed_table_metadata,
    get_table_meta,
    validate_insert_values,
    validate_pk_values,
    validate_update_values,
)
from backend.db.postgres import ensure_pool


router = APIRouter()


def _handle_error(exc: Exception, prefix: str) -> HTTPException:
    if isinstance(exc, ValueError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail=f"{prefix}：{exc}")


@router.get(
    "/tables",
    response_model=list[DataManagerTableInfo],
    summary="列出可管理的数据表",
)
async def get_tables() -> list[dict[str, Any]]:
    try:
        return await list_manageable_tables()
    except Exception as exc:  # noqa: BLE001
        raise _handle_error(exc, "读取数据表清单失败") from exc


@router.get(
    "/tables/{schema_name}/{table_name}/columns",
    response_model=list[DataManagerColumnInfo],
    summary="读取数据表列元数据",
)
async def get_table_columns(schema_name: str, table_name: str) -> list[dict[str, Any]]:
    try:
        return await get_columns(schema_name, table_name)
    except Exception as exc:  # noqa: BLE001
        raise _handle_error(exc, "读取列元数据失败") from exc


@router.get(
    "/tables/{schema_name}/{table_name}/rows",
    response_model=DataManagerRowsResponse,
    summary="分页读取数据表行数据",
)
async def get_table_rows(
    schema_name: str,
    table_name: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
    sort: str | None = None,
    filters: str | None = Query(default=None, description="JSON 编码的列过滤条件"),
) -> dict[str, Any]:
    try:
        parsed_filters: dict[str, Any] = json.loads(filters) if filters else {}
        if not isinstance(parsed_filters, dict):
            raise ValueError("filters 参数必须是 JSON 对象")
        return await fetch_rows(
            schema_name,
            table_name,
            page=page,
            page_size=page_size,
            sort=sort,
            filters=parsed_filters,
        )
    except Exception as exc:  # noqa: BLE001
        raise _handle_error(exc, "读取行数据失败") from exc


@router.post(
    "/tables/{schema_name}/{table_name}/rows",
    response_model=dict,
    status_code=201,
    summary="新增一条记录",
)
async def post_table_row(
    schema_name: str,
    table_name: str,
    payload: DataManagerRowCreateRequest,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        values = await _validate_insert(schema_name, table_name, payload.values)
        return await insert_row(
            schema_name, table_name, values=values, operator=current_user
        )
    except Exception as exc:  # noqa: BLE001
        raise _handle_error(exc, "新增记录失败") from exc


@router.put(
    "/tables/{schema_name}/{table_name}/rows",
    response_model=dict,
    summary="按主键更新一条记录",
)
async def put_table_row(
    schema_name: str,
    table_name: str,
    payload: DataManagerRowUpdateRequest,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        pk_values, values = await _validate_update(
            schema_name, table_name, payload.pk, payload.values
        )
        return await update_row(
            schema_name,
            table_name,
            pk_values=pk_values,
            values=values,
            operator=current_user,
        )
    except Exception as exc:  # noqa: BLE001
        raise _handle_error(exc, "更新记录失败") from exc


@router.delete(
    "/tables/{schema_name}/{table_name}/rows",
    response_model=dict,
    summary="按主键删除一条记录",
)
async def delete_table_row(
    schema_name: str,
    table_name: str,
    payload: DataManagerRowDeleteRequest,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        pk_values = await _validate_pk(schema_name, table_name, payload.pk)
        return await delete_row(
            schema_name, table_name, pk_values=pk_values, operator=current_user
        )
    except Exception as exc:  # noqa: BLE001
        raise _handle_error(exc, "删除记录失败") from exc


@router.get(
    "/change-logs",
    response_model=DataManagerChangeLogListResponse,
    summary="分页读取数据变更日志",
)
async def get_change_logs(
    schema_name: str | None = None,
    table_name: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> DataManagerChangeLogListResponse:
    try:
        items, total = await list_change_logs(
            schema_name=schema_name, table_name=table_name, limit=limit, offset=offset
        )
        return DataManagerChangeLogListResponse(items=items, total=total)
    except Exception as exc:  # noqa: BLE001
        raise _handle_error(exc, "读取变更日志失败") from exc


async def _validate_insert(
    schema_name: str, table_name: str, values: dict[str, Any]
) -> dict[str, Any]:
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        metadata = await fetch_managed_table_metadata(connection)
    meta = get_table_meta(metadata, schema_name, table_name)
    return validate_insert_values(meta, values)


async def _validate_update(
    schema_name: str, table_name: str, pk: dict[str, Any], values: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        metadata = await fetch_managed_table_metadata(connection)
    meta = get_table_meta(metadata, schema_name, table_name)
    return validate_pk_values(meta, pk), validate_update_values(meta, values)


async def _validate_pk(
    schema_name: str, table_name: str, pk: dict[str, Any]
) -> dict[str, Any]:
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        metadata = await fetch_managed_table_metadata(connection)
    meta = get_table_meta(metadata, schema_name, table_name)
    return validate_pk_values(meta, pk)
