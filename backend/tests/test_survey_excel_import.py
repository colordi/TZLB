from __future__ import annotations

import unittest
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook

from backend.services.survey_excel_import import (
    build_import_plan,
    resolve_table_conflict_columns,
    run_survey_excel_import,
)


def make_workbook(sheets: dict[str, list[list[object]]]) -> bytes:
    workbook = Workbook()
    default_sheet = workbook.active
    workbook.remove(default_sheet)

    for title, rows in sheets.items():
        sheet = workbook.create_sheet(title=title)
        for row in rows:
            sheet.append(row)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def build_metadata_rows() -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
]:
    def column(
        table_name: str,
        ordinal_position: int,
        column_name: str,
        data_type: str,
        udt_name: str,
        is_nullable: str,
        column_default: str = "",
        table_schema: str = "survey",
        is_identity: str = "NO",
    ) -> dict[str, object]:
        return {
            "table_schema": table_schema,
            "table_name": table_name,
            "ordinal_position": ordinal_position,
            "column_name": column_name,
            "data_type": data_type,
            "udt_name": udt_name,
            "is_nullable": is_nullable,
            "is_identity": is_identity,
            "column_default": column_default,
        }

    def key(
        table_name: str,
        constraint_name: str,
        constraint_type: str,
        columns: list[str],
        table_schema: str = "survey",
    ) -> dict[str, object]:
        return {
            "table_schema": table_schema,
            "table_name": table_name,
            "constraint_name": constraint_name,
            "constraint_type": constraint_type,
            "columns": columns,
        }

    def index(
        table_name: str,
        index_name: str,
        columns: list[str],
        table_schema: str = "survey",
    ) -> dict[str, object]:
        return {
            "table_schema": table_schema,
            "table_name": table_name,
            "index_name": index_name,
            "columns": columns,
        }

    column_rows = [
        column("春尺蠖幼虫调查表", 1, "编号", "character varying", "varchar", "NO"),
        column("春尺蠖幼虫调查表", 2, "调查日期", "date", "date", "NO"),
        column("春尺蠖幼虫调查表", 3, "1号树", "integer", "int4", "YES", "0"),
        column("春尺蠖幼虫调查表", 4, "备注", "text", "text", "YES"),
        column(
            "美国白蛾调查表",
            1,
            "id",
            "integer",
            "int4",
            "NO",
            "nextval('survey.example_id_seq'::regclass)",
        ),
        column("美国白蛾调查表", 2, "编号", "character varying", "varchar", "NO"),
        column("美国白蛾调查表", 3, "调查日期", "date", "date", "NO"),
        column("美国白蛾调查表", 4, "属地", "character varying", "varchar", "NO"),
        column("美国白蛾调查表", 5, "点位名称", "character varying", "varchar", "NO"),
        column("美国白蛾调查表", 6, "受害株数", "integer", "int4", "NO", "0"),
        column("美国白蛾调查表", 7, "网幕数量", "integer", "int4", "NO", "0"),
        column(
            "美国白蛾调查表",
            8,
            "详细描述",
            "text",
            "text",
            "NO",
            "''::text",
        ),
        column(
            "美国白蛾调查表",
            9,
            "备注",
            "text",
            "text",
            "NO",
            "''::text",
        ),
        column("其他害虫调查表", 1, "编号", "character varying", "varchar", "NO"),
        column("其他害虫调查表", 2, "虫害类型", "character varying", "varchar", "NO"),
        column("其他害虫调查表", 3, "调查日期", "date", "date", "NO"),
        column("其他害虫调查表", 4, "调查结论", "character varying", "varchar", "NO"),
        column("其他害虫调查表", 5, "详细描述", "text", "text", "NO"),
        column(
            "美国白蛾问题点位事件流水表",
            1,
            "id",
            "integer",
            "int4",
            "NO",
            table_schema="ledger",
        ),
        column(
            "美国白蛾问题点位事件流水表",
            2,
            "事件时间",
            "timestamp without time zone",
            "timestamp",
            "NO",
            table_schema="ledger",
        ),
        column(
            "美国白蛾问题点位事件流水表",
            3,
            "事件类型",
            "USER-DEFINED",
            "meiguobaie_event_type",
            "NO",
            table_schema="ledger",
        ),
        column(
            "美国白蛾问题点位事件流水表",
            4,
            "属地",
            "character varying",
            "varchar",
            "YES",
            table_schema="ledger",
        ),
        column(
            "美国白蛾问题点位事件流水表",
            5,
            "编号",
            "character varying",
            "varchar",
            "NO",
            table_schema="ledger",
        ),
        column(
            "美国白蛾问题点位事件流水表",
            6,
            "点位名称",
            "character varying",
            "varchar",
            "YES",
            table_schema="ledger",
        ),
        column(
            "美国白蛾问题点位事件流水表",
            7,
            "受害株数",
            "integer",
            "int4",
            "NO",
            "0",
            table_schema="ledger",
        ),
        column(
            "美国白蛾问题点位事件流水表",
            8,
            "网幕数量",
            "integer",
            "int4",
            "NO",
            "0",
            table_schema="ledger",
        ),
        column(
            "美国白蛾问题点位事件流水表",
            9,
            "本次详细情况",
            "text",
            "text",
            "NO",
            table_schema="ledger",
        ),
        column(
            "美国白蛾问题点位事件流水表",
            10,
            "备注",
            "text",
            "text",
            "YES",
            table_schema="ledger",
        ),
        column(
            "美国白蛾问题点位事件流水表",
            11,
            "区域",
            "character varying",
            "varchar",
            "NO",
            "'乡镇'::character varying",
            table_schema="ledger",
        ),
        column(
            "其他害虫问题点位事件流水表",
            1,
            "id",
            "integer",
            "int4",
            "NO",
            table_schema="ledger",
            is_identity="YES",
        ),
        column(
            "其他害虫问题点位事件流水表",
            2,
            "编号",
            "character varying",
            "varchar",
            "NO",
            table_schema="ledger",
        ),
        column(
            "其他害虫问题点位事件流水表",
            3,
            "虫害类型",
            "character varying",
            "varchar",
            "NO",
            table_schema="ledger",
        ),
        column(
            "其他害虫问题点位事件流水表",
            4,
            "事件类型",
            "USER-DEFINED",
            "inspection_event_type",
            "NO",
            table_schema="ledger",
        ),
        column(
            "其他害虫问题点位事件流水表",
            5,
            "事件时间",
            "timestamp without time zone",
            "timestamp",
            "NO",
            table_schema="ledger",
        ),
        column(
            "其他害虫问题点位事件流水表",
            6,
            "本次详细情况",
            "text",
            "text",
            "NO",
            table_schema="ledger",
        ),
    ]
    constraint_rows = [
        key("春尺蠖幼虫调查表", "chun_chi_huo_larva_pkey", "PRIMARY KEY", ["编号", "调查日期"]),
        key(
            "美国白蛾调查表",
            "mei_guo_bai_e_first_generation_inspection_pkey",
            "PRIMARY KEY",
            ["id"],
        ),
        key(
            "美国白蛾调查表",
            "mgb1_unique_location_date",
            "UNIQUE",
            ["编号", "调查日期"],
        ),
        key(
            "美国白蛾问题点位事件流水表",
            "mgb1_ledger_pkey",
            "PRIMARY KEY",
            ["id"],
            table_schema="ledger",
        ),
        key(
            "其他害虫调查表",
            "other_pest_inspection_pkey",
            "PRIMARY KEY",
            ["编号", "虫害类型", "调查日期"],
        ),
        key(
            "其他害虫问题点位事件流水表",
            "other_pest_event_pkey",
            "PRIMARY KEY",
            ["id"],
            table_schema="ledger",
        ),
    ]
    unique_index_rows = [
        index("春尺蠖幼虫调查表", "chun_chi_huo_larva_pkey", ["编号", "调查日期"]),
        index(
            "其他害虫问题点位事件流水表",
            "other_pest_event_dedup_idx",
            ["编号", "虫害类型", "事件类型", "事件时间"],
            table_schema="ledger",
        ),
    ]
    return column_rows, constraint_rows, unique_index_rows


class FakeTransaction:
    def __init__(self, connection: "FakeConnection") -> None:
        self.connection = connection

    async def __aenter__(self) -> None:
        self.connection.transaction_entered = True

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.connection.transaction_exited = True


class FakeConnection:
    def __init__(self, existing_keys: set[tuple[object, ...]] | None = None) -> None:
        self.column_rows, self.constraint_rows, self.unique_index_rows = build_metadata_rows()
        self.existing_keys = existing_keys or set()
        self.insert_calls: list[tuple[str, tuple[object, ...]]] = []
        self.execute_calls: list[str] = []
        self.fetchval_calls: list[str] = []
        self.transaction_entered = False
        self.transaction_exited = False

    async def fetch(self, query: str, *args):
        if "information_schema.columns" in query:
            return self.column_rows
        if "information_schema.table_constraints" in query:
            return self.constraint_rows
        if "pg_index" in query:
            return self.unique_index_rows
        raise AssertionError(f"unexpected fetch query: {query}")

    async def fetchrow(self, query: str, *args):
        normalized_query = query.strip().upper()
        if normalized_query.startswith("SELECT"):
            return {"exists": 1} if tuple(args) in self.existing_keys else None
        if normalized_query.startswith("INSERT"):
            self.insert_calls.append((query, tuple(args)))
            return {"inserted": 1}
        raise AssertionError(f"unexpected fetchrow query: {query}")

    async def fetchval(self, query: str, *args):
        self.fetchval_calls.append(query)
        if "COALESCE(MAX(id), 0) + 1" in query:
            return 328
        raise AssertionError(f"unexpected fetchval query: {query}")

    async def execute(self, query: str, *args):
        self.execute_calls.append(query)
        return "OK"

    def transaction(self) -> FakeTransaction:
        return FakeTransaction(self)


class SurveyExcelImportTest(unittest.TestCase):
    def setUp(self) -> None:
        column_rows, constraint_rows, unique_index_rows = build_metadata_rows()
        columns_by_table = {}
        for row in column_rows:
            columns_by_table.setdefault(
                (row["table_schema"], row["table_name"]),
                {},
            )[row["column_name"]] = row
        self.metadata = {}
        from backend.services.survey_excel_import import ColumnMeta, TableMeta

        for (schema_name, table_name), raw_columns in columns_by_table.items():
            columns = {
                name: ColumnMeta(
                    name=name,
                    data_type=row["data_type"],
                    udt_name=row["udt_name"],
                    is_nullable=row["is_nullable"] == "YES",
                    default=row["column_default"],
                    ordinal_position=row["ordinal_position"],
                    is_identity=row["is_identity"] == "YES",
                )
                for name, row in raw_columns.items()
            }
            candidates = [
                tuple(row["columns"])
                for row in [*constraint_rows, *unique_index_rows]
                if row["table_schema"] == schema_name and row["table_name"] == table_name
            ]
            conflict_columns, supports_on_conflict = resolve_table_conflict_columns(
                schema_name,
                table_name,
                candidates,
                columns,
            )
            self.metadata[table_name] = TableMeta(
                schema_name=schema_name,
                name=table_name,
                columns=columns,
                conflict_columns=conflict_columns,
                supports_on_conflict=supports_on_conflict,
            )

    def test_unknown_non_empty_sheet_reports_error(self) -> None:
        content = make_workbook({"未知调查表": [["编号"], ["YF0001"]]})

        plan = build_import_plan(content, self.metadata)

        self.assertEqual(plan[0].sheet_name, "未知调查表")
        self.assertIn("sheet 名称必须与 survey 或 ledger 中的可写表完全一致", plan[0].errors[0])

    def test_valid_workbook_converts_date_integer_and_ignores_auto_id(self) -> None:
        content = make_workbook(
            {
                "美国白蛾调查表": [
                    ["id", "编号", "调查日期", "属地", "点位名称"],
                    [99, "MQ001", 46128, "马驹桥镇", "九周路"],
                ]
            }
        )

        plan = build_import_plan(content, self.metadata)

        self.assertEqual(plan[0].warnings, [])
        self.assertEqual(plan[0].valid_rows, 1)
        self.assertEqual(plan[0].rows[0].values["编号"], "MQ001")
        self.assertEqual(plan[0].rows[0].values["调查日期"], date(2026, 4, 16))
        self.assertNotIn("id", plan[0].rows[0].values)

    def test_missing_required_column_reports_error(self) -> None:
        content = make_workbook(
            {
                "其他害虫调查表": [
                    ["编号", "虫害类型", "调查日期", "调查结论"],
                    ["QT0001", "蚜虫", "2026-04-17", "发现问题"],
                ]
            }
        )

        plan = build_import_plan(content, self.metadata)

        self.assertIn("缺少必填列：详细描述", plan[0].errors)

    def test_decimal_integer_cell_reports_row_error(self) -> None:
        content = make_workbook(
            {
                "春尺蠖幼虫调查表": [
                    ["编号", "调查日期", "1号树"],
                    ["YF0001", "2026-04-16", 1.5],
                ]
            }
        )

        plan = build_import_plan(content, self.metadata)

        self.assertEqual(plan[0].valid_rows, 0)
        self.assertIn("1号树：整数列不能包含小数", plan[0].errors[0])

    def test_file_duplicates_are_skipped(self) -> None:
        content = make_workbook(
            {
                "春尺蠖幼虫调查表": [
                    ["编号", "调查日期", "1号树"],
                    ["YF0001", "2026-04-16", 1],
                    ["YF0001", "2026-04-16", 2],
                ]
            }
        )

        plan = build_import_plan(content, self.metadata)

        self.assertEqual(plan[0].valid_rows, 2)
        self.assertEqual(plan[0].skipped_duplicate_rows, 1)
        self.assertTrue(plan[0].rows[1].skipped_duplicate)

    def test_ledger_sheet_uses_schema_and_unique_index_for_conflict(self) -> None:
        content = make_workbook(
            {
                "其他害虫问题点位事件流水表": [
                    ["id", "编号", "虫害类型", "事件类型", "事件时间", "本次详细情况"],
                    [100, "QT0001", "蚜虫", "新增", 46128.3541666667, "  首次发现  "],
                ]
            }
        )

        plan = build_import_plan(content, self.metadata)

        self.assertEqual(plan[0].schema_name, "ledger")
        self.assertEqual(plan[0].table_name, "其他害虫问题点位事件流水表")
        self.assertEqual(plan[0].warnings, [])
        self.assertEqual(plan[0].valid_rows, 1)
        self.assertNotIn("id", plan[0].rows[0].values)
        self.assertEqual(
            self.metadata["其他害虫问题点位事件流水表"].conflict_columns,
            ("编号", "虫害类型", "事件类型", "事件时间"),
        )
        self.assertEqual(
            plan[0].rows[0].conflict_values,
            ("QT0001", "蚜虫", "新增", datetime(2026, 4, 16, 8, 30)),
        )
        self.assertEqual(plan[0].rows[0].values["本次详细情况"], "首次发现")

    def test_ledger_view_sheet_is_not_importable(self) -> None:
        content = make_workbook(
            {"其他害虫问题点位台账": [["编号"], ["QT0001"]]}
        )

        plan = build_import_plan(content, self.metadata)

        self.assertEqual(plan[0].schema_name, None)
        self.assertIn("survey 或 ledger 中的可写表", plan[0].errors[0])


class RunSurveyExcelImportTest(unittest.IsolatedAsyncioTestCase):
    async def test_dry_run_marks_database_duplicates_without_writing(self) -> None:
        content = make_workbook(
            {
                "春尺蠖幼虫调查表": [
                    ["编号", "调查日期", "1号树"],
                    ["YF0001", "2026-04-16", 1],
                    ["YF0002", "2026-04-16", 2],
                ]
            }
        )
        connection = FakeConnection(existing_keys={("YF0001", date(2026, 4, 16))})

        result = await run_survey_excel_import(
            content=content,
            file_name="调查.xlsx",
            dry_run=True,
            connection=connection,
        )

        self.assertEqual(result["totals"]["valid_rows"], 2)
        self.assertEqual(result["totals"]["skipped_duplicate_rows"], 1)
        self.assertEqual(result["totals"]["inserted_rows"], 0)
        self.assertEqual(connection.insert_calls, [])
        self.assertFalse(connection.transaction_entered)

    async def test_formal_import_uses_transaction_and_inserts_valid_rows(self) -> None:
        content = make_workbook(
            {
                "春尺蠖幼虫调查表": [
                    ["编号", "调查日期", "1号树", "备注"],
                    ["YF0002", "2026-04-16", 2, "  需复查  "],
                ]
            }
        )
        connection = FakeConnection()

        result = await run_survey_excel_import(
            content=content,
            file_name="调查.xlsx",
            dry_run=False,
            connection=connection,
        )

        self.assertEqual(result["totals"]["inserted_rows"], 1)
        self.assertEqual(result["totals"]["skipped_duplicate_rows"], 0)
        self.assertEqual(len(connection.insert_calls), 1)
        self.assertTrue(connection.transaction_entered)
        self.assertTrue(connection.transaction_exited)

    async def test_formal_import_generates_mgb1_ledger_rows_in_backend(self) -> None:
        content = make_workbook(
            {
                "美国白蛾调查表": [
                    ["编号", "调查日期", "属地", "点位名称", "受害株数", "网幕数量", "详细描述", "备注"],
                    ["MQ001", "2026-05-26", "马驹桥镇", "九周路", 3, 2, "发现网幕", "现场备注"],
                ]
            }
        )
        connection = FakeConnection()

        result = await run_survey_excel_import(
            content=content,
            file_name="美国白蛾调查.xlsx",
            dry_run=False,
            connection=connection,
        )

        self.assertEqual(result["totals"]["sheet_count"], 2)
        self.assertEqual(result["totals"]["inserted_rows"], 2)
        self.assertEqual(result["totals"]["importable_rows"], 2)
        survey_sheet = result["sheets"][0]
        self.assertEqual(
            survey_sheet["stats"]["by_locality"],
            [{"name": "马驹桥镇", "count": 1}],
        )
        self.assertEqual(survey_sheet["stats"]["damaged_count"], 1)
        self.assertEqual(survey_sheet["stats"]["undamaged_count"], 0)
        ledger_sheet = result["sheets"][1]
        self.assertEqual(
            ledger_sheet["stats"]["by_event_type"],
            [{"name": "调查下派", "count": 1}],
        )
        self.assertEqual(ledger_sheet["stats"]["damaged_count"], 1)
        self.assertEqual(len(connection.insert_calls), 2)
        self.assertEqual(len(connection.execute_calls), 1)
        self.assertIn("LOCK TABLE", connection.execute_calls[0])
        self.assertEqual(len(connection.fetchval_calls), 1)
        ledger_query, ledger_args = connection.insert_calls[1]
        self.assertIn('"ledger"."美国白蛾问题点位事件流水表"', ledger_query)
        self.assertIn("WHERE NOT EXISTS", ledger_query)
        self.assertEqual(ledger_args[0], 328)
        self.assertIn("调查下派", ledger_args)
        self.assertIn("MQ001", ledger_args)
        self.assertIn("发现网幕", ledger_args)
        self.assertTrue(connection.transaction_entered)
        self.assertTrue(connection.transaction_exited)

    async def test_preview_summary_aggregates_locality_damage_and_event_type(self) -> None:
        content = make_workbook(
            {
                "美国白蛾调查表": [
                    ["编号", "调查日期", "属地", "点位名称", "受害株数", "网幕数量", "详细描述", "备注"],
                    ["MQ001", "2026-05-26", "马驹桥镇", "九周路", 3, 2, "发现网幕", ""],
                    ["MQ002", "2026-05-26", "马驹桥镇", "小杜社", 0, 0, "未见受害", ""],
                    ["TY001", "2026-05-26", "通运街道", "滨河", 1, 1, "发现网幕", ""],
                ]
            }
        )
        connection = FakeConnection()

        result = await run_survey_excel_import(
            content=content,
            file_name="美国白蛾调查.xlsx",
            dry_run=True,
            connection=connection,
        )

        self.assertEqual(result["totals"]["importable_rows"], 6)
        survey_sheet = next(
            sheet for sheet in result["sheets"] if sheet["table_name"] == "美国白蛾调查表"
        )
        ledger_sheet = next(
            sheet
            for sheet in result["sheets"]
            if sheet["table_name"] == "美国白蛾问题点位事件流水表"
        )
        self.assertEqual(
            survey_sheet["stats"]["by_locality"],
            [
                {"name": "马驹桥镇", "count": 2},
                {"name": "通运街道", "count": 1},
            ],
        )
        self.assertEqual(survey_sheet["stats"]["damaged_count"], 2)
        self.assertEqual(survey_sheet["stats"]["undamaged_count"], 1)
        self.assertEqual(survey_sheet["stats"]["by_event_type"], [])
        self.assertEqual(
            ledger_sheet["stats"]["by_event_type"],
            [{"name": "调查下派", "count": 3}],
        )
        self.assertEqual(ledger_sheet["stats"]["damaged_count"], 2)
        self.assertEqual(ledger_sheet["stats"]["undamaged_count"], 1)
        self.assertEqual(connection.insert_calls, [])

    async def test_existing_mgb1_ledger_sheet_is_imported_without_backend_generation(self) -> None:
        content = make_workbook(
            {
                "美国白蛾调查表": [
                    ["编号", "调查日期", "属地", "点位名称", "详细描述"],
                    ["MQ001", "2026-05-26", "马驹桥镇", "九周路", "发现网幕"],
                ],
                "美国白蛾问题点位事件流水表": [
                    ["编号", "事件类型", "事件时间", "本次详细情况"],
                    ["MQ001", "调查下派", "2026-05-26", "按 ledger sheet 写入"],
                ],
            }
        )
        connection = FakeConnection()

        result = await run_survey_excel_import(
            content=content,
            file_name="美国白蛾调查及流水.xlsx",
            dry_run=True,
            connection=connection,
        )

        self.assertEqual(result["totals"]["sheet_count"], 2)
        ledger_sheet = result["sheets"][1]
        self.assertEqual(ledger_sheet["schema_name"], "ledger")
        self.assertEqual(ledger_sheet["valid_rows"], 1)
        self.assertNotIn("根据 survey", " ".join(ledger_sheet["warnings"]))
        self.assertEqual(connection.insert_calls, [])
        self.assertFalse(connection.transaction_entered)

    async def test_formal_import_with_errors_does_not_write(self) -> None:
        content = make_workbook(
            {
                "春尺蠖幼虫调查表": [
                    ["编号", "调查日期", "1号树"],
                    ["YF0002", "2026-04-16", 2.5],
                ]
            }
        )
        connection = FakeConnection()

        result = await run_survey_excel_import(
            content=content,
            file_name="调查.xlsx",
            dry_run=False,
            connection=connection,
        )

        self.assertEqual(result["totals"]["error_count"], 1)
        self.assertEqual(connection.insert_calls, [])
        self.assertFalse(connection.transaction_entered)


class OtherPestTriggerMigrationTest(unittest.TestCase):
    def test_trigger_migration_uses_current_chinese_table_and_locality_names(self) -> None:
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "db"
            / "migrations"
            / "20260606_fix_other_pest_trigger_chinese_names.sql"
        )

        migration_sql = migration_path.read_text(encoding="utf-8")

        self.assertIn('sites."其他害虫点位基础表"', migration_sql)
        self.assertIn('"属地"', migration_sql)
        self.assertNotIn("sites.other_pest_sites", migration_sql)
        self.assertNotIn('"乡镇"', migration_sql)


if __name__ == "__main__":
    unittest.main()
