from __future__ import annotations

import unittest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from backend.db.data_manager import _build_filter_clause, list_manageable_tables
from backend.services.data_manager import (
    MANAGEABLE_SCHEMAS,
    ManagedColumnMeta,
    ManagedTableMeta,
    coerce_value,
    get_table_meta,
    serialize_row,
    serialize_value,
    validate_insert_values,
    validate_pk_values,
    validate_update_values,
)


def make_column(
    name: str,
    data_type: str = "text",
    udt_name: str | None = None,
    is_nullable: bool = True,
    default: str = "",
    ordinal_position: int = 1,
    is_identity: bool = False,
    is_primary_key: bool = False,
    enum_labels: tuple[str, ...] = (),
) -> ManagedColumnMeta:
    return ManagedColumnMeta(
        name=name,
        data_type=data_type,
        udt_name=udt_name if udt_name is not None else data_type,
        is_nullable=is_nullable,
        default=default,
        ordinal_position=ordinal_position,
        is_identity=is_identity,
        is_primary_key=is_primary_key,
        enum_labels=enum_labels,
    )


def make_table(
    schema_name: str = "survey",
    name: str = "测试表",
    columns: tuple[ManagedColumnMeta, ...] | None = None,
    primary_key: tuple[str, ...] = ("id",),
) -> ManagedTableMeta:
    if columns is None:
        columns = (
            make_column(
                "id",
                data_type="integer",
                is_nullable=False,
                default="nextval('survey.测试表_id_seq'::regclass)",
                ordinal_position=1,
                is_primary_key=True,
            ),
            make_column("名称", data_type="text", is_nullable=False, ordinal_position=2),
            make_column("调查日期", data_type="date", ordinal_position=3),
            make_column(
                "状态",
                data_type="USER-DEFINED",
                udt_name="处理状态",
                default="'待处理'::处理状态",
                ordinal_position=4,
                enum_labels=("待处理", "已处理"),
            ),
            make_column(
                "geom",
                data_type="USER-DEFINED",
                udt_name="geometry",
                ordinal_position=5,
            ),
        )
    return ManagedTableMeta(
        schema_name=schema_name,
        name=name,
        columns=columns,
        primary_key=primary_key,
    )


class TestGetTableMeta(unittest.TestCase):
    def setUp(self):
        self.meta = make_table()
        self.metadata = {("survey", "测试表"): self.meta}

    def test_returns_meta_for_valid_schema_and_table(self):
        result = get_table_meta(self.metadata, "survey", "测试表")
        self.assertIs(result, self.meta)

    def test_rejects_invalid_schema(self):
        with self.assertRaises(ValueError):
            get_table_meta(self.metadata, "reference", "测试表")

    def test_rejects_unknown_table_in_manageable_schema(self):
        with self.assertRaises(ValueError):
            get_table_meta(self.metadata, "ledger", "不存在的表")

    def test_manageable_schemas_contents(self):
        self.assertEqual(MANAGEABLE_SCHEMAS, ("survey", "ledger", "sites"))


class TestManagedColumnMetaProperties(unittest.TestCase):
    def test_nextval_default_marks_auto_generated_and_readonly(self):
        column = make_column("id", data_type="integer", default="nextval('seq'::regclass)")
        self.assertTrue(column.is_auto_generated)
        self.assertTrue(column.is_readonly)
        self.assertTrue(column.has_default)

    def test_identity_marks_auto_generated_and_readonly(self):
        column = make_column("id", data_type="integer", is_identity=True)
        self.assertTrue(column.is_auto_generated)
        self.assertTrue(column.is_readonly)

    def test_geometry_udt_marks_geometry_and_readonly(self):
        column = make_column("geom", data_type="USER-DEFINED", udt_name="geometry")
        self.assertTrue(column.is_geometry)
        self.assertTrue(column.is_readonly)

    def test_plain_column_is_not_readonly(self):
        column = make_column("名称", data_type="text")
        self.assertFalse(column.is_geometry)
        self.assertFalse(column.is_auto_generated)
        self.assertFalse(column.is_readonly)
        self.assertFalse(column.has_default)

    def test_input_kind_select_when_enum_labels(self):
        column = make_column(
            "状态",
            data_type="USER-DEFINED",
            udt_name="处理状态",
            enum_labels=("待处理", "已处理"),
        )
        self.assertEqual(column.input_kind, "select")

    def test_input_kind_date(self):
        self.assertEqual(make_column("d", data_type="date").input_kind, "date")

    def test_input_kind_datetime(self):
        self.assertEqual(
            make_column("t", data_type="timestamp without time zone").input_kind,
            "datetime",
        )

    def test_input_kind_number_for_integer_and_float(self):
        self.assertEqual(make_column("i", data_type="integer").input_kind, "number")
        self.assertEqual(make_column("f", data_type="numeric").input_kind, "number")

    def test_input_kind_bool(self):
        self.assertEqual(make_column("b", data_type="boolean").input_kind, "bool")

    def test_input_kind_text_default(self):
        self.assertEqual(make_column("s", data_type="text").input_kind, "text")


class TestManagedTableMeta(unittest.TestCase):
    def test_qualified_name_quotes_schema_and_table(self):
        self.assertEqual(make_table().qualified_name, '"survey"."测试表"')

    def test_get_column_returns_column_or_none(self):
        meta = make_table()
        self.assertEqual(meta.get_column("名称").name, "名称")
        self.assertIsNone(meta.get_column("不存在"))

    def test_selectable_columns_excludes_geometry(self):
        meta = make_table()
        names = [column.name for column in meta.selectable_columns]
        self.assertNotIn("geom", names)
        self.assertIn("名称", names)


class TestCoerceValue(unittest.TestCase):
    def test_blank_values_become_none(self):
        column = make_column("名称", data_type="text")
        self.assertIsNone(coerce_value(column, None))
        self.assertIsNone(coerce_value(column, ""))
        self.assertIsNone(coerce_value(column, "   "))

    def test_date_from_iso_string(self):
        column = make_column("调查日期", data_type="date")
        self.assertEqual(coerce_value(column, "2026-07-01"), date(2026, 7, 1))

    def test_date_from_date_and_datetime(self):
        column = make_column("调查日期", data_type="date")
        self.assertEqual(coerce_value(column, date(2026, 7, 1)), date(2026, 7, 1))
        self.assertEqual(
            coerce_value(column, datetime(2026, 7, 1, 8, 30)), date(2026, 7, 1)
        )

    def test_date_rejects_invalid_string(self):
        column = make_column("调查日期", data_type="date")
        with self.assertRaises(ValueError):
            coerce_value(column, "不是一个日期")

    def test_timestamp_from_iso_string(self):
        column = make_column("创建时间", data_type="timestamp without time zone")
        self.assertEqual(
            coerce_value(column, "2026-07-01 08:30:00"), datetime(2026, 7, 1, 8, 30)
        )

    def test_timestamp_from_date_only_string(self):
        column = make_column("创建时间", data_type="timestamp without time zone")
        self.assertEqual(coerce_value(column, "2026-07-01"), datetime(2026, 7, 1))

    def test_timestamp_rejects_invalid_string(self):
        column = make_column("创建时间", data_type="timestamp without time zone")
        with self.assertRaises(ValueError):
            coerce_value(column, "abc")

    def test_integer_from_string(self):
        column = make_column("数量", data_type="integer")
        self.assertEqual(coerce_value(column, "12"), 12)

    def test_integer_from_integral_float(self):
        column = make_column("数量", data_type="integer")
        self.assertEqual(coerce_value(column, 12.0), 12)

    def test_integer_rejects_fractional_float(self):
        column = make_column("数量", data_type="integer")
        with self.assertRaises(ValueError):
            coerce_value(column, 12.5)

    def test_integer_rejects_bool(self):
        column = make_column("数量", data_type="integer")
        with self.assertRaises(ValueError):
            coerce_value(column, True)

    def test_integer_rejects_non_numeric_string(self):
        column = make_column("数量", data_type="integer")
        with self.assertRaises(ValueError):
            coerce_value(column, "十二")

    def test_float_from_string_and_number(self):
        column = make_column("面积", data_type="numeric")
        self.assertEqual(coerce_value(column, "1.5"), 1.5)
        self.assertEqual(coerce_value(column, 2), 2)
        self.assertEqual(coerce_value(column, 2.5), 2.5)

    def test_float_rejects_invalid_string(self):
        column = make_column("面积", data_type="numeric")
        with self.assertRaises(ValueError):
            coerce_value(column, "很大")

    def test_boolean_truthy_values(self):
        column = make_column("是否完成", data_type="boolean")
        self.assertIs(coerce_value(column, True), True)
        self.assertIs(coerce_value(column, "true"), True)
        self.assertIs(coerce_value(column, "1"), True)
        self.assertIs(coerce_value(column, "是"), True)
        self.assertIs(coerce_value(column, "yes"), True)

    def test_boolean_falsy_values(self):
        column = make_column("是否完成", data_type="boolean")
        self.assertIs(coerce_value(column, False), False)
        self.assertIs(coerce_value(column, "false"), False)
        self.assertIs(coerce_value(column, "0"), False)
        self.assertIs(coerce_value(column, "否"), False)
        self.assertIs(coerce_value(column, "no"), False)

    def test_boolean_rejects_invalid_string(self):
        column = make_column("是否完成", data_type="boolean")
        with self.assertRaises(ValueError):
            coerce_value(column, "也许")

    def test_text_is_stripped(self):
        column = make_column("名称", data_type="text")
        self.assertEqual(coerce_value(column, "  潞城镇  "), "潞城镇")

    def test_enum_accepts_valid_label(self):
        column = make_column(
            "状态",
            data_type="USER-DEFINED",
            udt_name="处理状态",
            enum_labels=("待处理", "已处理"),
        )
        self.assertEqual(coerce_value(column, "待处理"), "待处理")

    def test_enum_rejects_unknown_label(self):
        column = make_column(
            "状态",
            data_type="USER-DEFINED",
            udt_name="处理状态",
            enum_labels=("待处理", "已处理"),
        )
        with self.assertRaises(ValueError):
            coerce_value(column, "处理中")


class TestValidateInsertValues(unittest.TestCase):
    def setUp(self):
        self.meta = make_table()

    def test_coerces_valid_values(self):
        cleaned = validate_insert_values(
            self.meta, {"名称": "  一号点位  ", "调查日期": "2026-07-01"}
        )
        self.assertEqual(cleaned["名称"], "一号点位")
        self.assertEqual(cleaned["调查日期"], date(2026, 7, 1))

    def test_rejects_readonly_auto_generated_column(self):
        with self.assertRaises(ValueError):
            validate_insert_values(self.meta, {"名称": "x", "id": 1})

    def test_rejects_readonly_geometry_column(self):
        with self.assertRaises(ValueError):
            validate_insert_values(self.meta, {"名称": "x", "geom": "POINT(1 1)"})

    def test_rejects_unknown_column(self):
        with self.assertRaises(ValueError):
            validate_insert_values(self.meta, {"名称": "x", "不存在": 1})

    def test_rejects_missing_required_column(self):
        with self.assertRaises(ValueError):
            validate_insert_values(self.meta, {"调查日期": "2026-07-01"})

    def test_rejects_blank_required_column(self):
        with self.assertRaises(ValueError):
            validate_insert_values(self.meta, {"名称": "   "})

    def test_nullable_column_with_default_not_forced(self):
        # “状态”非必填（可空且有默认值），缺失时不报错
        cleaned = validate_insert_values(self.meta, {"名称": "x"})
        self.assertNotIn("状态", cleaned)


class TestValidateUpdateValues(unittest.TestCase):
    def setUp(self):
        self.meta = make_table()

    def test_coerces_valid_values(self):
        cleaned = validate_update_values(self.meta, {"名称": "新名称"})
        self.assertEqual(cleaned, {"名称": "新名称"})

    def test_rejects_empty_values(self):
        with self.assertRaises(ValueError):
            validate_update_values(self.meta, {})

    def test_rejects_primary_key_column(self):
        with self.assertRaises(ValueError):
            validate_update_values(self.meta, {"id": 2})

    def test_rejects_readonly_column(self):
        with self.assertRaises(ValueError):
            validate_update_values(self.meta, {"geom": "POINT(1 1)"})

    def test_rejects_unknown_column(self):
        with self.assertRaises(ValueError):
            validate_update_values(self.meta, {"不存在": 1})


class TestValidatePkValues(unittest.TestCase):
    def setUp(self):
        self.meta = make_table()

    def test_coerces_pk_values(self):
        cleaned = validate_pk_values(self.meta, {"id": "3"})
        self.assertEqual(cleaned, {"id": 3})

    def test_rejects_table_without_primary_key(self):
        meta = make_table(primary_key=())
        with self.assertRaises(ValueError):
            validate_pk_values(meta, {"id": 1})

    def test_rejects_missing_pk_value(self):
        with self.assertRaises(ValueError):
            validate_pk_values(self.meta, {})

    def test_rejects_blank_pk_value(self):
        with self.assertRaises(ValueError):
            validate_pk_values(self.meta, {"id": "  "})

    def test_rejects_extra_non_pk_column(self):
        with self.assertRaises(ValueError):
            validate_pk_values(self.meta, {"id": 1, "名称": "x"})


class TestBuildFilterClause(unittest.TestCase):
    def setUp(self):
        self.meta = make_table()

    def make_event_table(self) -> ManagedTableMeta:
        return make_table(
            schema_name="ledger",
            name="事件流水表",
            columns=(
                make_column("编号", data_type="text", ordinal_position=1),
                make_column(
                    "事件时间",
                    data_type="timestamp without time zone",
                    ordinal_position=2,
                ),
            ),
            primary_key=("编号",),
        )

    def test_text_filter_uses_ilike(self):
        where, args = _build_filter_clause(self.meta, {"名称": "宋庄"})
        self.assertEqual(where, 'WHERE CAST("名称" AS text) ILIKE $1')
        self.assertEqual(args, ["%宋庄%"])

    def test_date_range_both_ends_inclusive(self):
        where, args = _build_filter_clause(
            self.meta, {"调查日期": {"from": "2026-07-01", "to": "2026-07-31"}}
        )
        self.assertEqual(where, 'WHERE "调查日期" >= $1 AND "调查日期" <= $2')
        self.assertEqual(args, [date(2026, 7, 1), date(2026, 7, 31)])

    def test_date_range_open_ends(self):
        where, args = _build_filter_clause(
            self.meta, {"调查日期": {"from": "2026-07-01"}}
        )
        self.assertEqual(where, 'WHERE "调查日期" >= $1')
        self.assertEqual(args, [date(2026, 7, 1)])

        where, args = _build_filter_clause(
            self.meta, {"调查日期": {"to": "2026-07-31"}}
        )
        self.assertEqual(where, 'WHERE "调查日期" <= $1')
        self.assertEqual(args, [date(2026, 7, 31)])

    def test_timestamp_range_to_covers_whole_day(self):
        meta = self.make_event_table()
        where, args = _build_filter_clause(
            meta, {"事件时间": {"from": "2026-07-01", "to": "2026-07-31"}}
        )
        self.assertEqual(where, 'WHERE "事件时间" >= $1 AND "事件时间" < $2')
        self.assertEqual(args, [datetime(2026, 7, 1), datetime(2026, 8, 1)])

    def test_range_and_text_filters_share_placeholders(self):
        where, args = _build_filter_clause(
            self.meta, {"名称": "宋庄", "调查日期": {"from": "2026-07-01"}}
        )
        self.assertEqual(
            where,
            'WHERE CAST("名称" AS text) ILIKE $1 AND "调查日期" >= $2',
        )
        self.assertEqual(args, ["%宋庄%", date(2026, 7, 1)])

    def test_empty_range_is_skipped(self):
        where, args = _build_filter_clause(self.meta, {"调查日期": {}})
        self.assertEqual(where, "")
        self.assertEqual(args, [])

    def test_range_rejects_non_date_column(self):
        with self.assertRaises(ValueError):
            _build_filter_clause(self.meta, {"名称": {"from": "2026-07-01"}})

    def test_range_rejects_unknown_keys(self):
        with self.assertRaises(ValueError):
            _build_filter_clause(
                self.meta, {"调查日期": {"from": "2026-07-01", "op": "gt"}}
            )

    def test_range_rejects_invalid_date(self):
        with self.assertRaises(ValueError):
            _build_filter_clause(self.meta, {"调查日期": {"from": "不是日期"}})

    def test_rejects_unknown_and_geometry_columns(self):
        with self.assertRaises(ValueError):
            _build_filter_clause(self.meta, {"不存在": "x"})
        with self.assertRaises(ValueError):
            _build_filter_clause(self.meta, {"geom": "POINT(1 1)"})


class TestSerialize(unittest.TestCase):
    def test_serialize_value_datetime(self):
        self.assertEqual(
            serialize_value(datetime(2026, 7, 1, 8, 30, 5)), "2026-07-01 08:30:05"
        )

    def test_serialize_value_date(self):
        self.assertEqual(serialize_value(date(2026, 7, 1)), "2026-07-01")

    def test_serialize_value_decimal(self):
        self.assertEqual(serialize_value(Decimal("1.5")), 1.5)

    def test_serialize_value_passthrough(self):
        self.assertEqual(serialize_value("文本"), "文本")
        self.assertIsNone(serialize_value(None))

    def test_serialize_row_mixed_types(self):
        row = {
            "id": 1,
            "名称": "一号点位",
            "调查日期": date(2026, 7, 1),
            "更新时间": datetime(2026, 7, 2, 9, 0, 0),
            "面积": Decimal("2.50"),
            "备注": None,
        }
        self.assertEqual(
            serialize_row(row),
            {
                "id": 1,
                "名称": "一号点位",
                "调查日期": "2026-07-01",
                "更新时间": "2026-07-02 09:00:00",
                "面积": 2.5,
                "备注": None,
            },
        )


class _FakeAcquire:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _FakePool:
    def __init__(self, connection):
        self.connection = connection

    def acquire(self):
        return _FakeAcquire(self.connection)


class _ListTablesFakeConnection:
    """list_manageable_tables 用的假连接：一旦出现 reltuples 估计查询直接报错。"""

    def __init__(self):
        self.column_rows = [
            {
                "table_schema": "survey",
                "table_name": "测试表",
                "ordinal_position": 1,
                "column_name": "id",
                "data_type": "integer",
                "udt_name": "int4",
                "is_nullable": "NO",
                "is_identity": "NO",
                "column_default": None,
            },
        ]
        self.pk_rows = [
            {"table_schema": "survey", "table_name": "测试表", "columns": ["id"]},
        ]
        self.counts = {'"survey"."测试表"': 42}

    async def fetch(self, query, *args):
        if "reltuples" in query or "pg_class" in query:
            raise AssertionError("行数统计不应使用 reltuples 估计值")
        if "information_schema.columns" in query:
            return self.column_rows
        if "information_schema.table_constraints" in query:
            return self.pk_rows
        return []

    async def fetchrow(self, query, *args):
        for qualified, count in self.counts.items():
            if qualified in query:
                return {"row_count": count}
        return {"row_count": 0}


class TestListManageableTables(unittest.IsolatedAsyncioTestCase):
    async def test_returns_exact_row_counts(self):
        connection = _ListTablesFakeConnection()

        with patch(
            "backend.db.data_manager.ensure_pool",
            new=AsyncMock(return_value=_FakePool(connection)),
        ):
            tables = await list_manageable_tables()

        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0]["schema_name"], "survey")
        self.assertEqual(tables[0]["table_name"], "测试表")
        self.assertEqual(tables[0]["row_count"], 42)
        self.assertTrue(tables[0]["has_primary_key"])
        self.assertEqual(tables[0]["primary_key"], ["id"])


if __name__ == "__main__":
    unittest.main()
