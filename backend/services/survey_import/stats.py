from __future__ import annotations

from typing import Any

from backend.services.survey_import.parsers import is_blank
from backend.services.survey_import.types import (
    DAMAGE_LEVEL_FIELD,
    DAMAGED_PLANT_COUNT_FIELD,
    EMPTY_LOCALITY_LABEL,
    EVENT_TYPE_FIELD,
    LOCALITY_FIELD,
    UNDAMAGED_LEVELS,
    USE_DEFAULT,
    PreparedSheet,
)


def _normalize_group_label(value: Any, empty_label: str = EMPTY_LOCALITY_LABEL) -> str:
    if is_blank(value):
        return empty_label
    return str(value).strip()


def _row_damage_status(values: dict[str, Any]) -> bool | None:
    """Return True/False when damage can be judged, otherwise None."""
    if DAMAGED_PLANT_COUNT_FIELD in values:
        raw = values.get(DAMAGED_PLANT_COUNT_FIELD)
        try:
            count = 0 if raw is None or raw is USE_DEFAULT else int(raw)
        except (TypeError, ValueError):
            count = 0
        return count > 0

    if DAMAGE_LEVEL_FIELD in values:
        level = str(values.get(DAMAGE_LEVEL_FIELD) or "").strip()
        return level not in UNDAMAGED_LEVELS

    return None


def build_sheet_stats(sheet: PreparedSheet) -> dict[str, Any]:
    """Aggregate importable-row business stats for preview UI."""
    importable_rows = [
        row for row in sheet.rows if not row.skipped_duplicate
    ]
    locality_counts: dict[str, int] = {}
    event_type_counts: dict[str, int] = {}
    damaged_count = 0
    undamaged_count = 0
    has_locality = False
    has_event_type = False
    has_damage = False

    for row in importable_rows:
        values = row.values
        if LOCALITY_FIELD in values:
            has_locality = True
            label = _normalize_group_label(values.get(LOCALITY_FIELD))
            locality_counts[label] = locality_counts.get(label, 0) + 1

        if EVENT_TYPE_FIELD in values:
            has_event_type = True
            label = _normalize_group_label(
                values.get(EVENT_TYPE_FIELD),
                empty_label="未填写",
            )
            event_type_counts[label] = event_type_counts.get(label, 0) + 1

        damage_status = _row_damage_status(values)
        if damage_status is None:
            continue
        has_damage = True
        if damage_status:
            damaged_count += 1
        else:
            undamaged_count += 1

    by_locality = [
        {"name": name, "count": count}
        for name, count in sorted(
            locality_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ] if has_locality else []

    by_event_type = [
        {"name": name, "count": count}
        for name, count in sorted(
            event_type_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ] if has_event_type else []

    return {
        "by_locality": by_locality,
        "damaged_count": damaged_count if has_damage else None,
        "undamaged_count": undamaged_count if has_damage else None,
        "by_event_type": by_event_type,
    }


def summarize_import(
    *,
    file_name: str,
    dry_run: bool,
    sheets: list[PreparedSheet],
) -> dict[str, Any]:
    sheet_summaries = []
    for sheet in sheets:
        importable_rows = max(sheet.valid_rows - sheet.skipped_duplicate_rows, 0)
        sheet_summaries.append(
            {
                "sheet_name": sheet.sheet_name,
                "schema_name": sheet.schema_name,
                "table_name": sheet.table_name,
                "row_count": sheet.row_count,
                "valid_rows": sheet.valid_rows,
                "importable_rows": importable_rows,
                "inserted_rows": sheet.inserted_rows,
                "skipped_duplicate_rows": sheet.skipped_duplicate_rows,
                "warnings": sheet.warnings,
                "errors": sheet.errors,
                "stats": build_sheet_stats(sheet),
            }
        )

    totals = {
        "sheet_count": len(sheets),
        "row_count": sum(sheet.row_count for sheet in sheets),
        "valid_rows": sum(sheet.valid_rows for sheet in sheets),
        "importable_rows": sum(
            max(sheet.valid_rows - sheet.skipped_duplicate_rows, 0) for sheet in sheets
        ),
        "inserted_rows": sum(sheet.inserted_rows for sheet in sheets),
        "skipped_duplicate_rows": sum(sheet.skipped_duplicate_rows for sheet in sheets),
        "error_count": sum(len(sheet.errors) for sheet in sheets),
    }
    return {
        "file_name": file_name,
        "dry_run": dry_run,
        "totals": totals,
        "sheets": sheet_summaries,
    }
