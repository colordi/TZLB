from __future__ import annotations

import unittest
from datetime import date
from io import BytesIO
from unittest.mock import AsyncMock, patch

from openpyxl import load_workbook

from backend.routers.data_export import build_download_response
from backend.services.data_export import (
    DataExportArtifact,
    ExportTableMeta,
    build_unique_sheet_names,
    export_all_tables,
    fetch_export_table_metadata,
)


class FakeAcquire:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakePool:
    def __init__(self, connection):
        self.connection = connection

    def acquire(self):
        return FakeAcquire(self.connection)


class FakeConnection:
    def __init__(self):
        self.fetch_calls: list[tuple[str, tuple]] = []
        self.fetchrow_calls: list[str] = []
        self.metadata_rows = [
            {
                "table_schema": "survey",
                "table_name": "春尺蠖幼虫调查表",
                "object_type": "table",
                "columns": ["编号", "调查日期"],
            },
            {
                "table_schema": "ledger",
                "table_name": "美国白蛾问题点位台账",
                "object_type": "table",
                "columns": ["编号", "备注"],
            },
            {
                "table_schema": "ledger",
                "table_name": "美国白蛾问题点位视图",
                "object_type": "view",
                "columns": ["编号", "属地"],
            },
        ]
        self.counts = {
            '"survey"."春尺蠖幼虫调查表"': 1,
            '"ledger"."美国白蛾问题点位台账"': 0,
            '"ledger"."美国白蛾问题点位视图"': 1,
        }
        self.table_rows = {
            '"survey"."春尺蠖幼虫调查表"': [
                {
                    "编号": "YF001",
                    "调查日期": date(2026, 4, 1),
                }
            ],
            '"ledger"."美国白蛾问题点位台账"': [],
            '"ledger"."美国白蛾问题点位视图"': [
                {
                    "编号": "MQ001",
                    "属地": "马驹桥镇",
                }
            ],
        }

    async def fetch(self, query: str, *args):
        self.fetch_calls.append((query, args))
        if "information_schema.tables" in query:
            schema_name = args[1]
            table_name = args[2]
            return [
                row
                for row in self.metadata_rows
                if (schema_name is None or row["table_schema"] == schema_name)
                and (table_name is None or row["table_name"] == table_name)
            ]

        for qualified_table, rows in self.table_rows.items():
            if qualified_table in query:
                return rows
        return []

    async def fetchrow(self, query: str, *args):
        self.fetchrow_calls.append(query)
        for qualified_table, count in self.counts.items():
            if qualified_table in query:
                return {"row_count": count}
        return {"row_count": 0}


class DataExportServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_metadata_reads_allowed_survey_and_ledger_tables_and_views(self) -> None:
        connection = FakeConnection()

        tables = await fetch_export_table_metadata(connection)

        self.assertEqual([table.schema_name for table in tables], ["survey", "ledger", "ledger"])
        self.assertEqual(tables[0].table_name, "春尺蠖幼虫调查表")
        self.assertEqual(tables[0].column_count, 2)
        self.assertEqual(tables[0].row_count, 1)
        self.assertEqual(tables[2].object_type, "view")
        self.assertEqual(connection.fetch_calls[0][1][0], ["survey", "ledger"])

    async def test_metadata_rejects_unknown_schema(self) -> None:
        with self.assertRaises(ValueError) as context:
            await fetch_export_table_metadata(FakeConnection(), schema_name="sites")

        self.assertEqual(str(context.exception), "不支持导出 schema：sites")

    async def test_export_all_tables_contains_summary_and_table_sheets(self) -> None:
        connection = FakeConnection()

        with patch(
            "backend.services.data_export.ensure_pool",
            new=AsyncMock(return_value=FakePool(connection)),
        ):
            artifact = await export_all_tables()

        workbook = load_workbook(BytesIO(artifact.content), read_only=True, data_only=True)
        self.assertIn("导出说明", workbook.sheetnames)
        self.assertIn("survey.春尺蠖幼虫调查表", workbook.sheetnames)
        self.assertIn("ledger.美国白蛾问题点位台账", workbook.sheetnames)
        self.assertIn("ledger.美国白蛾问题点位视图", workbook.sheetnames)

        summary_rows = list(workbook["导出说明"].iter_rows(values_only=True))
        self.assertIn(("导出范围", "survey, ledger 表和视图"), summary_rows)
        self.assertIn(
            (
                "survey",
                "春尺蠖幼虫调查表",
                "表",
                "survey.春尺蠖幼虫调查表",
                1,
                2,
            ),
            summary_rows,
        )
        survey_rows = list(workbook["survey.春尺蠖幼虫调查表"].iter_rows(values_only=True))
        self.assertEqual(survey_rows[0], ("编号", "调查日期"))
        self.assertEqual(survey_rows[1][0], "YF001")

    def test_sheet_names_are_truncated_and_deduplicated(self) -> None:
        sheet_names = build_unique_sheet_names(
            [
                ExportTableMeta(
                    schema_name="survey",
                    table_name="一个非常非常非常非常非常非常非常非常长的调查表名称",
                    object_type="table",
                    columns=("编号",),
                    row_count=0,
                ),
                ExportTableMeta(
                    schema_name="ledger",
                    table_name="一个非常非常非常非常非常非常非常非常长的调查表名称",
                    object_type="view",
                    columns=("编号",),
                    row_count=0,
                ),
            ]
        )

        names = list(sheet_names.values())
        self.assertEqual(len(names), 2)
        self.assertEqual(len(names[0]), 31)
        self.assertEqual(len(names[1]), 31)
        self.assertNotEqual(names[0], names[1])


class DataExportRouterTest(unittest.TestCase):
    def test_download_response_sets_xlsx_attachment_headers(self) -> None:
        response = build_download_response(
            DataExportArtifact(
                filename="调查数据导出_20260606_120000.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                content=b"xlsx-bytes",
            )
        )

        self.assertEqual(response.body, b"xlsx-bytes")
        self.assertIn(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            response.headers["content-type"],
        )
        self.assertIn("attachment;", response.headers["content-disposition"])
        self.assertIn(
            "%E8%B0%83%E6%9F%A5%E6%95%B0%E6%8D%AE%E5%AF%BC%E5%87%BA_20260606_120000.xlsx",
            response.headers["content-disposition"],
        )


if __name__ == "__main__":
    unittest.main()
