from __future__ import annotations

import base64
import mimetypes
from datetime import date as date_cls
from pathlib import Path
from typing import Any

from backend.config import get_settings
from backend.db.pool import fetch, quote_identifier
from backend.services.pest_registry import (
    SURVEY_IMPORT_GUO_HUAI_INCHWORM,
    SURVEY_IMPORT_MEI_GUO_BAI_E,
    SURVEY_IMPORT_OTHER_PEST,
    SURVEY_IMPORT_SPRING_INCHWORM,
    SURVEY_IMPORT_YANGSHU_SHIYE,
    get_pest_config,
)
from backend.services.storage import AssetStorage, get_storage_for_dir

SURVEY_SCHEMA = "survey"
SURVEY_LARVA_TABLE = "春尺蠖幼虫调查表"
GUO_HUAI_LARVA_TABLE = "国槐尺蠖幼虫调查表"
OTHER_PEST_SURVEY_TABLE = "其他害虫调查表"
MEI_GUO_BAI_E_SURVEY_TABLE = "美国白蛾调查表"
YANGSHU_SHIYE_SURVEY_TABLE = "杨树食叶害虫调查表"
SITE_SCHEMA = "sites"
SITE_TABLE = "杨树点位基础表"
SOPHORA_SITE_TABLE = "国槐点位基础表"
OTHER_PEST_SITE_TABLE = "其他害虫点位基础表"
WHITE_MOTH_SITE_TABLE = "美国白蛾点位基础表"
YANGSHU_SHIYE_SITE_TABLE = "杨树食叶害虫点位基础表"
LEDGER_SCHEMA = "ledger"
SPRING_INCHWORM_LEDGER_TABLE = "春尺蠖问题点位事件流水表"
GUO_HUAI_LEDGER_TABLE = "国槐尺蠖问题点位事件流水表"
WHITE_MOTH_LEDGER_TABLE = "美国白蛾问题点位事件流水表"
OTHER_PEST_LEDGER_TABLE = "其他害虫问题点位事件流水表"
YANGSHU_SHIYE_LEDGER_TABLE = "杨树食叶害虫问题点位事件流水表"
LOCALITY_COLUMN = "属地"
LEDGER_TABLE_BY_PEST = {
    "春尺蠖": SPRING_INCHWORM_LEDGER_TABLE,
    "国槐尺蠖": GUO_HUAI_LEDGER_TABLE,
    "美国白蛾": WHITE_MOTH_LEDGER_TABLE,
    "其他害虫": OTHER_PEST_LEDGER_TABLE,
    "杨树食叶害虫": YANGSHU_SHIYE_LEDGER_TABLE,
}
GENERATION_LEDGER_PESTS = frozenset({"国槐尺蠖", "美国白蛾"})
# 与 survey_import.LEDGER_HISTORY_RULES 的下派类 + 复查异常保持一致，
# 不从 survey_import 包导入，避免与 postgres 门面循环依赖。
DISPATCH_EVENT_TYPES_BY_PEST = {
    "春尺蠖": ("历史预警下派", "成虫调查下派", "幼虫调查下派", "复查异常"),
    "国槐尺蠖": ("历史预警下派", "幼虫调查下派", "复查异常"),
    "美国白蛾": ("调查下派", "复查异常"),
    "其他害虫": ("调查下派", "复查异常"),
    "杨树食叶害虫": ("调查下派", "复查异常"),
}


def build_chi_huo_larva_description(
    pest_name: str,
    locality: str,
    location_name: str,
    location_id: str,
    damage_level: str,
    total_insect_count: int | None,
) -> str:
    """根据点位信息与危害程度生成尺蠖幼虫防治描述。"""

    location_prefix = "".join(
        part.strip()
        for part in [locality, location_name, location_id]
        if (part or "").strip()
    )
    location_text = f"{location_prefix}点位，" if location_prefix else ""
    normalized_level = (damage_level or "").strip()
    level_text = normalized_level or "待判定"
    average_insect_count_text = "未记录"
    if total_insect_count is not None:
        average_insect_count_text = f"{(total_insect_count + 4) // 5}头"

    if normalized_level == "重":
        advice = "建议立即组织防治作业，并优先复核周边相邻点位。"
    elif normalized_level == "中":
        advice = "建议尽快安排防治，并持续跟踪虫情变化。"
    elif normalized_level == "轻":
        advice = "建议加强巡查，视虫情发展适时处置。"
    elif normalized_level:
        advice = "建议结合现场情况制定防治措施并复核虫情。"
    else:
        advice = "建议复核现场危害情况并及时补录调查结果。"

    return (
        f"{location_text}调查发现{pest_name}幼虫危害程度为{level_text}，"
        f"平均每标准枝{average_insect_count_text}。{advice}"
    )


def build_spring_inchworm_description(
    locality: str,
    location_name: str,
    location_id: str,
    damage_level: str,
    total_insect_count: int | None,
) -> str:
    """根据点位信息与危害程度生成春尺蠖防治描述。"""

    return build_chi_huo_larva_description(
        pest_name="春尺蠖",
        locality=locality,
        location_name=location_name,
        location_id=location_id,
        damage_level=damage_level,
        total_insect_count=total_insect_count,
    )


def build_guo_huai_inchworm_description(
    locality: str,
    location_name: str,
    location_id: str,
    damage_level: str,
    total_insect_count: int | None,
) -> str:
    """根据点位信息与危害程度生成国槐尺蠖防治描述。"""

    return build_chi_huo_larva_description(
        pest_name="国槐尺蠖",
        locality=locality,
        location_name=location_name,
        location_id=location_id,
        damage_level=damage_level,
        total_insect_count=total_insect_count,
    )


def serialize_date_value(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def coerce_survey_date(value: date_cls | str) -> date_cls:
    if isinstance(value, date_cls):
        return value
    return date_cls.fromisoformat(str(value))


def dispatch_event_types_for_pest(pest_key: str) -> tuple[str, ...]:
    event_types = DISPATCH_EVENT_TYPES_BY_PEST.get(pest_key)
    if event_types is None:
        raise ValueError(f"{pest_key} 暂不支持按事件流水导入工单")
    return event_types


def build_dispatch_fallback_description(
    *,
    locality: str,
    location_name: str,
    location_id: str,
    event_type: str,
    damage_level: str,
    average_insect_count: int | None,
) -> str:
    """流水没有「本次详细情况」时，用下派字段拼一条可写入工单的描述。"""

    location_prefix = "".join(
        part.strip()
        for part in [locality, location_name, location_id]
        if (part or "").strip()
    )
    location_text = f"{location_prefix}点位，" if location_prefix else ""
    event_text = (event_type or "下派").strip() or "下派"
    level_text = (damage_level or "").strip() or "待判定"
    if average_insect_count is None:
        count_text = "未记录"
    else:
        count_text = f"{int(average_insect_count)}头"
    return (
        f"{location_text}{event_text}，危害程度为{level_text}，平均虫口{count_text}。"
    )


def build_point_screenshot_index(storage: AssetStorage) -> dict[str, str]:
    """列出点位截图存储位置，返回可唯一匹配的点位截图索引（编号 -> 文件名）。"""

    from backend.services.point_screenshot_service import is_preview_thumbnail_name

    indexed_names: dict[str, list[str]] = {}
    for obj in sorted(storage.list(), key=lambda item: item.name):
        if is_preview_thumbnail_name(obj.name):
            continue
        mime_type, _ = mimetypes.guess_type(obj.name)
        if not mime_type or not mime_type.startswith("image/"):
            continue

        location_id = Path(obj.name).stem.strip()
        if not location_id:
            continue

        indexed_names.setdefault(location_id, []).append(obj.name)

    return {
        location_id: names[0]
        for location_id, names in indexed_names.items()
        if len(names) == 1
    }


def encode_image_as_data_url(storage: AssetStorage, name: str) -> str | None:
    """读取素材图片并编码为前端可直接使用的 Data URL。"""

    mime_type, _ = mimetypes.guess_type(name)
    if not mime_type or not mime_type.startswith("image/"):
        return None

    try:
        content = storage.read(name)
    except OSError:
        return None

    encoded = base64.b64encode(content).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def load_point_screenshot_images(
    location_id: str,
    screenshot_index: dict[str, str],
    screenshot_storage: AssetStorage | None,
) -> list[str]:
    """按点位编号匹配导入记录的默认截图。"""

    normalized_location_id = (location_id or "").strip()
    if not normalized_location_id:
        return []

    name = screenshot_index.get(normalized_location_id)
    if name is None or screenshot_storage is None:
        return []

    data_url = encode_image_as_data_url(screenshot_storage, name)
    return [data_url] if data_url else []


async def fetch_survey_candidates(
    survey_date: date_cls,
    pest_type: str = "春尺蠖",
    year: int | None = None,
    generation: str | None = None,
    include_images: bool = True,
) -> list[dict[str, Any]]:
    """读取指定日期可导入为工作单的下派 / 复查异常事件。"""

    return await fetch_survey_candidates_by_type(
        survey_date=survey_date,
        pest_type=pest_type,
        year=year,
        generation=generation,
        include_images=include_images,
    )


async def fetch_site_points(pest_type: str) -> list[dict[str, str]]:
    """读取指定害虫的全部基础点位，不关联调查记录。"""

    config = get_pest_config(pest_type)
    site_sources = {
        "春尺蠖": (SITE_TABLE, "村"),
        "国槐尺蠖": (SOPHORA_SITE_TABLE, "村"),
        "美国白蛾": (WHITE_MOTH_SITE_TABLE, "点位名称"),
        "其他害虫": (OTHER_PEST_SITE_TABLE, "点位名称"),
        "杨树食叶害虫": (YANGSHU_SHIYE_SITE_TABLE, "村"),
    }
    source = site_sources.get(config.key)
    if source is None:
        raise ValueError(f"{config.key} 暂不支持点位截图管理")

    table_name, name_column = source
    qualified_site_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(table_name)}"
    )
    quoted_name_column = quote_identifier(name_column)
    quoted_locality_column = quote_identifier(LOCALITY_COLUMN)
    rows = await fetch(
        f"""
        SELECT
            BTRIM(COALESCE(s."编号"::text, '')) AS code,
            BTRIM(COALESCE(s.{quoted_name_column}::text, '')) AS name,
            BTRIM(COALESCE(s.{quoted_locality_column}::text, '')) AS locality
        FROM {qualified_site_table} AS s
        WHERE BTRIM(COALESCE(s."编号"::text, '')) <> ''
        ORDER BY
            BTRIM(COALESCE(s.{quoted_locality_column}::text, '')),
            BTRIM(COALESCE(s."编号"::text, ''))
        """
    )
    return [
        {
            "code": str(row["code"] or "").strip(),
            "name": str(row["name"] or "").strip(),
            "locality": str(row["locality"] or "").strip(),
        }
        for row in rows
    ]


async def fetch_survey_candidates_by_type(
    survey_date: date_cls,
    pest_type: str,
    year: int | None = None,
    generation: str | None = None,
    include_images: bool = True,
) -> list[dict[str, Any]]:
    """按害虫类型读取指定日期的下派 / 复查异常事件，作为工作单导入候选。"""

    config = get_pest_config(pest_type)
    target_date = coerce_survey_date(survey_date)
    resolved_year = year if year is not None else target_date.year
    strategy_handlers = {
        SURVEY_IMPORT_OTHER_PEST: fetch_other_pest_survey_candidates,
        SURVEY_IMPORT_SPRING_INCHWORM: fetch_spring_inchworm_survey_candidates,
        SURVEY_IMPORT_GUO_HUAI_INCHWORM: fetch_guo_huai_inchworm_survey_candidates,
        SURVEY_IMPORT_MEI_GUO_BAI_E: fetch_meiguobaie_survey_candidates,
        SURVEY_IMPORT_YANGSHU_SHIYE: fetch_yangshu_shiye_survey_candidates,
    }
    handler = strategy_handlers.get(config.survey_import_strategy or "")
    if handler is None:
        raise ValueError(f"暂不支持 {config.key} 的工单导入")
    return await handler(
        target_date,
        year=resolved_year,
        generation=generation,
        include_images=include_images,
    )


def _qualified_ledger_table(table_name: str) -> str:
    return f"{quote_identifier(LEDGER_SCHEMA)}.{quote_identifier(table_name)}"


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


async def fetch_chi_huo_dispatch_candidates(
    survey_date: date_cls,
    *,
    pest_key: str,
    ledger_table: str,
    screenshot_dir_attr: str,
    year: int,
    generation: str | None,
    include_images: bool,
) -> list[dict[str, Any]]:
    """读取尺蠖类（春尺蠖 / 国槐尺蠖）当日下派与复查异常事件。"""

    event_types = dispatch_event_types_for_pest(pest_key)
    generation_clause = ""
    params: list[Any] = [survey_date, list(event_types), year]
    if pest_key in GENERATION_LEDGER_PESTS and generation:
        generation_clause = f'\n          AND e.{quote_identifier("世代")} = $4'
        params.append(generation)

    rows = await fetch(
        f"""
        SELECT
            BTRIM(e."编号") AS location_id,
            (e."事件时间")::date AS survey_date,
            e."事件类型"::text AS event_type,
            COALESCE(e.{quote_identifier(LOCALITY_COLUMN)}, '') AS locality,
            COALESCE(e."点位名称", '') AS location_name,
            e."本次平均虫口数" AS total_insect_count,
            BTRIM(COALESCE(e."本次危害程度", '')) AS damage_level,
            COALESCE(e."本次详细情况", '') AS event_detail,
            COALESCE(e."备注", '') AS note
        FROM {_qualified_ledger_table(ledger_table)} AS e
        WHERE (e."事件时间")::date = $1
          AND e."事件类型"::text = ANY($2::text[])
          AND e."年份" = $3{generation_clause}
        ORDER BY
            COALESCE(e.{quote_identifier(LOCALITY_COLUMN)}, ''),
            BTRIM(e."编号"),
            e."事件类型"::text
        """,
        *params,
    )

    settings = get_settings()
    screenshot_storage = get_storage_for_dir(
        getattr(settings, screenshot_dir_attr),
        settings,
    )
    screenshot_index = (
        build_point_screenshot_index(screenshot_storage) if include_images else {}
    )
    candidates: list[dict[str, Any]] = []
    for row in rows:
        location_id = str(row["location_id"] or "").strip()
        locality = (row["locality"] or "").strip()
        location_name = (row["location_name"] or "").strip()
        event_type = str(row.get("event_type") or "").strip()
        insect_count = _optional_int(row["total_insect_count"])
        damage_level = (row["damage_level"] or "").strip()
        event_detail = str(row.get("event_detail") or "").strip()
        candidates.append(
            {
                "survey_date": serialize_date_value(row["survey_date"]),
                "event_type": event_type,
                "locality": locality,
                "location_id": location_id,
                "location_name": location_name,
                "total_insect_count": insect_count,
                "damage_level": damage_level,
                "note": (row["note"] or "").strip(),
                "images": load_point_screenshot_images(
                    location_id,
                    screenshot_index,
                    screenshot_storage,
                ),
                "description": event_detail
                or build_dispatch_fallback_description(
                    locality=locality,
                    location_name=location_name,
                    location_id=location_id,
                    event_type=event_type,
                    damage_level=damage_level,
                    average_insect_count=insect_count,
                ),
            }
        )
    return candidates


async def fetch_spring_inchworm_survey_candidates(
    survey_date: date_cls,
    include_images: bool = True,
    year: int | None = None,
    generation: str | None = None,
) -> list[dict[str, Any]]:
    """读取指定日期的春尺蠖下派 / 复查异常事件。"""

    target_date = coerce_survey_date(survey_date)
    return await fetch_chi_huo_dispatch_candidates(
        target_date,
        pest_key="春尺蠖",
        ledger_table=SPRING_INCHWORM_LEDGER_TABLE,
        screenshot_dir_attr="point_screenshot_dir",
        year=year if year is not None else target_date.year,
        generation=generation,
        include_images=include_images,
    )


async def fetch_guo_huai_inchworm_survey_candidates(
    survey_date: date_cls,
    include_images: bool = True,
    year: int | None = None,
    generation: str | None = None,
) -> list[dict[str, Any]]:
    """读取指定日期的国槐尺蠖下派 / 复查异常事件。"""

    target_date = coerce_survey_date(survey_date)
    return await fetch_chi_huo_dispatch_candidates(
        target_date,
        pest_key="国槐尺蠖",
        ledger_table=GUO_HUAI_LEDGER_TABLE,
        screenshot_dir_attr="sophora_point_screenshot_dir",
        year=year if year is not None else target_date.year,
        generation=generation,
        include_images=include_images,
    )


async def fetch_other_pest_like_survey_candidates(
    survey_date: date_cls,
    *,
    pest_key: str,
    ledger_table: str,
    site_table: str,
    site_name_column: str,
    site_plot_column: str | None,
    screenshot_storage: AssetStorage,
    year: int,
    include_images: bool = True,
) -> list[dict[str, Any]]:
    """按事件流水读取其他害虫 / 杨树食叶害虫的下派与复查异常。"""

    event_types = dispatch_event_types_for_pest(pest_key)
    qualified_ledger = _qualified_ledger_table(ledger_table)
    qualified_site_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(site_table)}"
    )
    plot_expression = (
        f"COALESCE(s.{quote_identifier(site_plot_column)}, '')"
        if site_plot_column
        else "''"
    )

    rows = await fetch(
        f"""
        SELECT
            BTRIM(e."编号") AS location_id,
            (e."事件时间")::date AS survey_date,
            e."事件类型"::text AS event_type,
            BTRIM(e."虫害类型") AS pest_name,
            BTRIM(COALESCE(e."本次调查结论", '')) AS survey_result,
            COALESCE(e."本次详细情况", '') AS description,
            COALESCE(e."备注", '') AS note,
            COALESCE(e.{quote_identifier(LOCALITY_COLUMN)}, '') AS locality,
            COALESCE(
                NULLIF(BTRIM(e."点位名称"), ''),
                NULLIF(BTRIM(s.{quote_identifier(site_name_column)}), ''),
                ''
            ) AS location_name,
            COALESCE(e."寄主树种", '') AS host_plant,
            {plot_expression} AS plot_type
        FROM {qualified_ledger} AS e
        LEFT JOIN {qualified_site_table} AS s
          ON e."编号" = s."编号"
        WHERE (e."事件时间")::date = $1
          AND e."事件类型"::text = ANY($2::text[])
          AND e."年份" = $3
        ORDER BY
            COALESCE(e.{quote_identifier(LOCALITY_COLUMN)}, ''),
            BTRIM(e."编号"),
            COALESCE(e."虫害类型", ''),
            e."事件类型"::text
        """,
        survey_date,
        list(event_types),
        year,
    )

    screenshot_index = (
        build_point_screenshot_index(screenshot_storage) if include_images else {}
    )
    return [
        {
            "survey_date": serialize_date_value(row["survey_date"]),
            "event_type": (row["event_type"] or "").strip(),
            "locality": (row["locality"] or "").strip(),
            "location_id": str(row["location_id"] or "").strip(),
            "location_name": (row["location_name"] or "").strip(),
            "pest_name": (row["pest_name"] or "").strip(),
            "host_plant": (row["host_plant"] or "").strip(),
            "plot_type": (row["plot_type"] or "").strip(),
            "survey_result": (row["survey_result"] or "").strip(),
            "description": (row["description"] or "").strip(),
            "note": (row["note"] or "").strip(),
            "images": load_point_screenshot_images(
                str(row["location_id"] or "").strip(),
                screenshot_index,
                screenshot_storage,
            ),
        }
        for row in rows
    ]


async def fetch_other_pest_survey_candidates(
    survey_date: date_cls,
    include_images: bool = True,
    year: int | None = None,
    generation: str | None = None,
) -> list[dict[str, Any]]:
    """读取指定日期的其他害虫下派 / 复查异常事件。"""

    del generation
    target_date = coerce_survey_date(survey_date)
    return await fetch_other_pest_like_survey_candidates(
        target_date,
        pest_key="其他害虫",
        ledger_table=OTHER_PEST_LEDGER_TABLE,
        site_table=OTHER_PEST_SITE_TABLE,
        site_name_column="点位名称",
        site_plot_column="地块类型",
        screenshot_storage=get_storage_for_dir(
            get_settings().other_pest_point_screenshot_dir,
            get_settings(),
        ),
        year=year if year is not None else target_date.year,
        include_images=include_images,
    )


async def fetch_yangshu_shiye_survey_candidates(
    survey_date: date_cls,
    include_images: bool = True,
    year: int | None = None,
    generation: str | None = None,
) -> list[dict[str, Any]]:
    """读取指定日期的杨树食叶害虫下派 / 复查异常事件。"""

    del generation
    target_date = coerce_survey_date(survey_date)
    return await fetch_other_pest_like_survey_candidates(
        target_date,
        pest_key="杨树食叶害虫",
        ledger_table=YANGSHU_SHIYE_LEDGER_TABLE,
        site_table=YANGSHU_SHIYE_SITE_TABLE,
        site_name_column="村",
        site_plot_column=None,
        screenshot_storage=get_storage_for_dir(
            get_settings().yangshu_shiye_point_screenshot_dir,
            get_settings(),
        ),
        year=year if year is not None else target_date.year,
        include_images=include_images,
    )


async def fetch_meiguobaie_survey_candidates(
    survey_date: date_cls,
    include_images: bool = True,
    year: int | None = None,
    generation: str | None = None,
) -> list[dict[str, Any]]:
    """读取指定日期的美国白蛾下派 / 复查异常事件。"""

    target_date = coerce_survey_date(survey_date)
    resolved_year = year if year is not None else target_date.year
    event_types = dispatch_event_types_for_pest("美国白蛾")
    generation_clause = ""
    params: list[Any] = [target_date, list(event_types), resolved_year]
    if generation:
        generation_clause = f'\n          AND e.{quote_identifier("世代")} = $4'
        params.append(generation)

    rows = await fetch(
        f"""
        SELECT
            BTRIM(e."编号") AS location_id,
            (e."事件时间")::date AS survey_date,
            e."事件类型"::text AS event_type,
            COALESCE(NULLIF(BTRIM(e."区域"), ''), '乡镇') AS region,
            COALESCE(e.{quote_identifier(LOCALITY_COLUMN)}, '') AS locality,
            COALESCE(e."点位名称", '') AS location_name,
            COALESCE(e."发生位置", '') AS occurrence_position,
            COALESCE(e."绿地性质", '') AS green_space_type,
            COALESCE(e."危害寄主", '') AS pest_hosts,
            COALESCE(e."受害株数", 0) AS damaged_plant_count,
            COALESCE(e."网幕数量", 0) AS web_nest_count,
            COALESCE(e."本次详细情况", '') AS description,
            COALESCE(e."备注", '') AS note
        FROM {_qualified_ledger_table(WHITE_MOTH_LEDGER_TABLE)} AS e
        WHERE (e."事件时间")::date = $1
          AND e."事件类型"::text = ANY($2::text[])
          AND e."年份" = $3{generation_clause}
        ORDER BY
            COALESCE(e.{quote_identifier(LOCALITY_COLUMN)}, ''),
            BTRIM(e."编号"),
            e."事件类型"::text
        """,
        *params,
    )

    screenshot_storage = get_storage_for_dir(
        get_settings().meiguobaie_point_screenshot_dir,
        get_settings(),
    )
    screenshot_index = (
        build_point_screenshot_index(screenshot_storage) if include_images else {}
    )
    return [
        {
            "survey_date": serialize_date_value(row["survey_date"]),
            "event_type": (row["event_type"] or "").strip(),
            "region": (row["region"] or "").strip(),
            "locality": (row["locality"] or "").strip(),
            "location_id": str(row["location_id"] or "").strip(),
            "location_name": (row["location_name"] or "").strip(),
            "occurrence_position": (row["occurrence_position"] or "").strip(),
            "green_space_type": (row["green_space_type"] or "").strip(),
            "pest_hosts": (row["pest_hosts"] or "").strip(),
            "damaged_plant_count": int(row["damaged_plant_count"] or 0),
            "web_nest_count": int(row["web_nest_count"] or 0),
            "description": (row["description"] or "").strip(),
            "note": (row["note"] or "").strip(),
            "images": load_point_screenshot_images(
                str(row["location_id"] or "").strip(),
                screenshot_index,
                screenshot_storage,
            ),
        }
        for row in rows
    ]
