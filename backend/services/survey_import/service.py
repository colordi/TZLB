from __future__ import annotations

from typing import Any

import asyncpg

from backend.db.postgres import ensure_pool
from backend.logging_config import get_logger
from backend.services.survey_import.dispatch_correction import correct_dispatch_event_types
from backend.services.survey_import.metadata import fetch_survey_table_metadata
from backend.services.survey_import.persistence import (
    has_errors,
    insert_valid_rows,
    mark_database_duplicates,
)
from backend.services.survey_import.plan import build_import_plan, mark_file_duplicates
from backend.services.survey_import.stats import summarize_import

logger = get_logger(__name__)


async def run_survey_excel_import(
    *,
    content: bytes,
    file_name: str,
    dry_run: bool,
    connection: asyncpg.Connection,
) -> dict[str, Any]:
    logger.info("开始 Excel 导入: file=%s size=%d bytes dry_run=%s", file_name, len(content), dry_run)
    metadata = await fetch_survey_table_metadata(connection)
    sheets = build_import_plan(content, metadata)

    sheet_summaries = [
        f"{sheet.sheet_name}(rows={sheet.row_count},valid={sheet.valid_rows},errors={len(sheet.errors)})"
        for sheet in sheets
    ]
    logger.info("Excel 解析完成: sheets=[%s]", ", ".join(sheet_summaries))

    if not sheets:
        return summarize_import(file_name=file_name, dry_run=dry_run, sheets=[])

    if not has_errors(sheets):
        await correct_dispatch_event_types(connection, sheets, metadata)
        for sheet in sheets:
            mark_file_duplicates(sheet)
        await mark_database_duplicates(connection, sheets, metadata)

    if dry_run or has_errors(sheets):
        summary = summarize_import(file_name=file_name, dry_run=dry_run, sheets=sheets)
        logger.info("Excel 预览完成: %s", summary.get("totals"))
        return summary

    async with connection.transaction():
        await insert_valid_rows(connection, sheets, metadata)

    summary = summarize_import(file_name=file_name, dry_run=dry_run, sheets=sheets)
    logger.info("Excel 入库完成: %s", summary.get("totals"))
    return summary


async def import_survey_excel(
    *,
    content: bytes,
    file_name: str,
    dry_run: bool,
) -> dict[str, Any]:
    pool = await ensure_pool()
    async with pool.acquire() as connection:
        return await run_survey_excel_import(
            content=content,
            file_name=file_name,
            dry_run=dry_run,
            connection=connection,
        )
