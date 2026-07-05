from __future__ import annotations

from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from backend.services.data_export import (
    DataExportArtifact,
    export_all_tables,
    export_pest_type,
    export_single_table,
    list_export_tables,
    list_pest_export_types,
)


router = APIRouter()


def build_download_response(artifact: DataExportArtifact) -> Response:
    encoded_name = quote(artifact.filename)
    return Response(
        content=artifact.content,
        media_type=artifact.media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
        },
    )


@router.get("/tables", summary="列出可导出的调查数据表")
async def get_export_tables() -> list[dict[str, Any]]:
    try:
        return await list_export_tables()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取可导出数据表失败：{exc}") from exc


@router.get("/download", summary="导出 survey 和 ledger 全部表")
async def download_all_export_tables() -> Response:
    try:
        return build_download_response(await export_all_tables())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"导出全部数据表失败：{exc}") from exc


@router.get("/pest-types", summary="按虫种列出可导出的数据表")
async def get_pest_export_types() -> list[dict[str, Any]]:
    try:
        return await list_pest_export_types()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"读取虫种导出信息失败：{exc}") from exc


@router.get("/pest/{pest}/download", summary="导出单个虫种全部关联数据表")
async def download_pest_export(
    pest: str,
    year: str | None = None,
    generation: str | None = None,
) -> Response:
    try:
        return build_download_response(await export_pest_type(pest, year=year, generation=generation))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"导出虫种数据失败：{exc}") from exc


@router.get("/tables/{schema_name}/{table_name}/download", summary="导出单张调查数据表")
async def download_export_table(schema_name: str, table_name: str) -> Response:
    try:
        return build_download_response(
            await export_single_table(schema_name=schema_name, table_name=table_name)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"导出数据表失败：{exc}") from exc
