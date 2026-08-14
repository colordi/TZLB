from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ALLOWED_EXPORT_SCHEMAS = ("survey", "ledger")
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
INVALID_SHEET_NAME_CHARS = set('[]:*?/\\')
MAX_SHEET_NAME_LENGTH = 31

PEST_TABLE_MAPPING: dict[str, list[tuple[str, str]]] = {
    "美国白蛾": [
        ("survey", "美国白蛾调查表"),
        ("ledger", "美国白蛾问题点位事件流水表"),
        ("ledger", "美国白蛾问题点位台账"),
    ],
    "国槐尺蠖": [
        ("survey", "国槐尺蠖幼虫调查表"),
        ("ledger", "国槐尺蠖问题点位事件流水表"),
        ("ledger", "国槐尺蠖问题点位台账"),
    ],
    "春尺蠖": [
        ("survey", "春尺蠖成虫调查表"),
        ("survey", "春尺蠖幼虫调查表"),
        ("survey", "春尺蠖围环调查表"),
        ("ledger", "春尺蠖问题点位事件流水表"),
        ("ledger", "春尺蠖问题点位台账"),
    ],
    "其他害虫": [
        ("survey", "其他害虫调查表"),
        ("ledger", "其他害虫问题点位事件流水表"),
        ("ledger", "其他害虫问题点位台账"),
    ],
    "杨树食叶害虫": [
        ("survey", "杨树食叶害虫调查表"),
        ("ledger", "杨树食叶害虫问题点位事件流水表"),
        ("ledger", "杨树食叶害虫问题点位台账"),
    ],
    "白蜡蛀干害虫": [
        ("survey", "白蜡蛀干害虫调查表"),
    ],
}


@dataclass(frozen=True)
class ExportTableMeta:
    schema_name: str
    table_name: str
    object_type: str
    columns: tuple[str, ...]
    row_count: int

    @property
    def column_count(self) -> int:
        return len(self.columns)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema_name": self.schema_name,
            "table_name": self.table_name,
            "object_type": self.object_type,
            "column_count": self.column_count,
            "row_count": self.row_count,
        }

    def to_summary_row(self) -> list[Any]:
        return [self.schema_name, self.table_name, self.object_type, self.row_count, self.column_count]


@dataclass(frozen=True)
class PestExportMeta:
    pest_type: str
    tables: tuple[ExportTableMeta, ...]
    total_row_count: int
    available_years: tuple[str, ...] = ()
    available_generations: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "pest_type": self.pest_type,
            "tables": [t.to_public_dict() for t in self.tables],
            "total_row_count": self.total_row_count,
            "available_years": list(self.available_years),
            "available_generations": list(self.available_generations),
        }


@dataclass(frozen=True)
class DataExportArtifact:
    filename: str
    media_type: str
    content: bytes
