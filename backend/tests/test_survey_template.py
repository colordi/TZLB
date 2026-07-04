from __future__ import annotations

import unittest
from io import BytesIO

from openpyxl import load_workbook

from backend.services.survey_excel_import import ColumnMeta, TableMeta
from backend.services.survey_template import build_import_template_bytes


class SurveyTemplateTest(unittest.TestCase):
    def test_template_contains_columns_and_example_row(self) -> None:
        metadata = {
            "春尺蠖幼虫调查表": TableMeta(
                schema_name="survey",
                name="春尺蠖幼虫调查表",
                columns={
                    "编号": ColumnMeta(
                        name="编号",
                        data_type="character varying",
                        udt_name="varchar",
                        is_nullable=False,
                        default="",
                        ordinal_position=1,
                    ),
                    "调查日期": ColumnMeta(
                        name="调查日期",
                        data_type="date",
                        udt_name="date",
                        is_nullable=False,
                        default="",
                        ordinal_position=2,
                    ),
                    "受害株数": ColumnMeta(
                        name="受害株数",
                        data_type="integer",
                        udt_name="int4",
                        is_nullable=True,
                        default="0",
                        ordinal_position=3,
                    ),
                    "备注": ColumnMeta(
                        name="备注",
                        data_type="text",
                        udt_name="text",
                        is_nullable=True,
                        default="",
                        ordinal_position=4,
                    ),
                },
                conflict_columns=("编号",),
            ),
        }

        content = build_import_template_bytes(metadata)
        workbook = load_workbook(BytesIO(content))

        self.assertEqual(workbook.sheetnames, ["春尺蠖幼虫调查表"])
        worksheet = workbook.active
        self.assertIsNotNone(worksheet)

        headers = [cell.value for cell in worksheet[1]]
        self.assertEqual(headers, ["编号", "调查日期", "受害株数", "备注"])

        examples = [cell.value for cell in worksheet[2]]
        self.assertEqual(examples[0], "示例值")
        self.assertEqual(examples[1], "2026-05-01")
        self.assertEqual(examples[2], 1)
        self.assertEqual(examples[3], "示例值")

    def test_required_columns_are_marked(self) -> None:
        metadata = {
            "测试表": TableMeta(
                schema_name="survey",
                name="测试表",
                columns={
                    "必填列": ColumnMeta(
                        name="必填列",
                        data_type="character varying",
                        udt_name="varchar",
                        is_nullable=False,
                        default="",
                        ordinal_position=1,
                    ),
                    "可空列": ColumnMeta(
                        name="可空列",
                        data_type="text",
                        udt_name="text",
                        is_nullable=True,
                        default="",
                        ordinal_position=2,
                    ),
                },
                conflict_columns=("必填列",),
            ),
        }

        content = build_import_template_bytes(metadata)
        workbook = load_workbook(BytesIO(content))
        worksheet = workbook.active
        self.assertIsNotNone(worksheet)

        required_header = worksheet.cell(row=1, column=1)
        optional_header = worksheet.cell(row=1, column=2)
        self.assertTrue(required_header.font.bold)
        self.assertIsNotNone(required_header.comment)
        self.assertIn("必填", required_header.comment.text)
        self.assertNotEqual(required_header.fill.start_color.rgb, optional_header.fill.start_color.rgb)


if __name__ == "__main__":
    unittest.main()
