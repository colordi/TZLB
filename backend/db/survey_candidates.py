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
    get_pest_config,
)

SURVEY_SCHEMA = "survey"
SURVEY_LARVA_TABLE = "春尺蠖幼虫调查表"
GUO_HUAI_LARVA_TABLE = "国槐尺蠖幼虫调查表"
OTHER_PEST_SURVEY_TABLE = "其他害虫调查表"
MEI_GUO_BAI_E_SURVEY_TABLE = "美国白蛾调查表"
SITE_SCHEMA = "sites"
SITE_TABLE = "杨树点位基础表"
SOPHORA_SITE_TABLE = "国槐点位基础表"
OTHER_PEST_SITE_TABLE = "其他害虫点位基础表"
WHITE_MOTH_SITE_TABLE = "美国白蛾点位基础表"
LOCALITY_COLUMN = "属地"


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


def build_point_screenshot_index(screenshot_dir: Path) -> dict[str, Path]:
    """扫描本地点位截图目录，返回可唯一匹配的点位截图索引。"""

    if not screenshot_dir.exists() or not screenshot_dir.is_dir():
        return {}

    indexed_paths: dict[str, list[Path]] = {}
    for path in sorted(screenshot_dir.iterdir()):
        if not path.is_file():
            continue

        mime_type, _ = mimetypes.guess_type(path.name)
        if not mime_type or not mime_type.startswith("image/"):
            continue

        location_id = path.stem.strip()
        if not location_id:
            continue

        indexed_paths.setdefault(location_id, []).append(path)

    return {
        location_id: paths[0]
        for location_id, paths in indexed_paths.items()
        if len(paths) == 1
    }


def encode_image_as_data_url(image_path: Path) -> str | None:
    """读取本地图片并编码为前端可直接使用的 Data URL。"""

    mime_type, _ = mimetypes.guess_type(image_path.name)
    if not mime_type or not mime_type.startswith("image/"):
        return None

    try:
        content = image_path.read_bytes()
    except OSError:
        return None

    encoded = base64.b64encode(content).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def load_point_screenshot_images(
    location_id: str,
    screenshot_index: dict[str, Path],
) -> list[str]:
    """按点位编号匹配导入记录的默认截图。"""

    normalized_location_id = (location_id or "").strip()
    if not normalized_location_id:
        return []

    image_path = screenshot_index.get(normalized_location_id)
    if image_path is None:
        return []

    data_url = encode_image_as_data_url(image_path)
    return [data_url] if data_url else []


async def fetch_survey_candidates(
    survey_date: date_cls,
    pest_type: str = "春尺蠖",
    year: int | None = None,
    generation: str | None = None,
    include_images: bool = True,
) -> list[dict[str, Any]]:
    """读取指定日期可导入为工作单的调查记录。"""

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
    """按害虫类型读取指定日期的工作单导入候选记录。"""

    config = get_pest_config(pest_type)
    strategy_handlers = {
        SURVEY_IMPORT_OTHER_PEST: fetch_other_pest_survey_candidates,
        SURVEY_IMPORT_SPRING_INCHWORM: fetch_spring_inchworm_survey_candidates,
        SURVEY_IMPORT_GUO_HUAI_INCHWORM: fetch_guo_huai_inchworm_survey_candidates,
        SURVEY_IMPORT_MEI_GUO_BAI_E: fetch_meiguobaie_survey_candidates,
    }
    handler = strategy_handlers.get(config.survey_import_strategy or "")
    if handler is None:
        raise ValueError(f"暂不支持 {config.key} 的调查导入")
    return await handler(survey_date, include_images=include_images)


async def fetch_spring_inchworm_survey_candidates(
    survey_date: date_cls,
    include_images: bool = True,
) -> list[dict[str, Any]]:
    """读取指定日期的春尺蠖调查导入候选记录。"""

    qualified_larva_table = (
        f"{quote_identifier(SURVEY_SCHEMA)}.{quote_identifier(SURVEY_LARVA_TABLE)}"
    )
    qualified_site_table = f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(SITE_TABLE)}"

    rows = await fetch(
        f"""
        SELECT
            l."编号" AS location_id,
            l."调查日期" AS survey_date,
            l."总虫口数" AS total_insect_count,
            BTRIM(l."危害程度") AS damage_level,
            COALESCE(l."备注", '') AS note,
            COALESCE(s.{quote_identifier(LOCALITY_COLUMN)}, '') AS locality,
            COALESCE(s."村", '') AS location_name
        FROM {qualified_larva_table} AS l
        JOIN {qualified_site_table} AS s
          ON l."编号" = s."编号"
        WHERE l."调查日期" = $1
          AND l."危害程度" IS NOT NULL
          AND BTRIM(l."危害程度") NOT IN ('', '白')
        ORDER BY
            COALESCE(s.{quote_identifier(LOCALITY_COLUMN)}, ''),
            l."编号"
        """,
        survey_date,
    )

    screenshot_index = (
        build_point_screenshot_index(get_settings().point_screenshot_dir)
        if include_images
        else {}
    )
    candidates: list[dict[str, Any]] = []
    for row in rows:
        location_id = str(row["location_id"] or "").strip()
        locality = (row["locality"] or "").strip()
        location_name = (row["location_name"] or "").strip()
        insect_count = row["total_insect_count"]
        if insect_count is not None:
            insect_count = int(insect_count)

        damage_level = (row["damage_level"] or "").strip()
        candidates.append(
            {
                "survey_date": serialize_date_value(row["survey_date"]),
                "locality": locality,
                "location_id": location_id,
                "location_name": location_name,
                "total_insect_count": insect_count,
                "damage_level": damage_level,
                "note": (row["note"] or "").strip(),
                "images": load_point_screenshot_images(location_id, screenshot_index),
                "description": build_spring_inchworm_description(
                    locality=locality,
                    location_name=location_name,
                    location_id=location_id,
                    damage_level=damage_level,
                    total_insect_count=insect_count,
                ),
            }
        )

    return candidates


async def fetch_guo_huai_inchworm_survey_candidates(
    survey_date: date_cls,
    include_images: bool = True,
) -> list[dict[str, Any]]:
    """读取指定日期的国槐尺蠖调查导入候选记录。"""

    qualified_larva_table = (
        f"{quote_identifier(SURVEY_SCHEMA)}.{quote_identifier(GUO_HUAI_LARVA_TABLE)}"
    )
    qualified_site_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(SOPHORA_SITE_TABLE)}"
    )

    rows = await fetch(
        f"""
        SELECT
            l."编号" AS location_id,
            l."调查日期" AS survey_date,
            l."总虫口数" AS total_insect_count,
            BTRIM(l."危害程度") AS damage_level,
            COALESCE(l."备注", '') AS note,
            COALESCE(s.{quote_identifier(LOCALITY_COLUMN)}, '') AS locality,
            COALESCE(s."村", '') AS location_name
        FROM {qualified_larva_table} AS l
        JOIN {qualified_site_table} AS s
          ON l."编号" = s."编号"
        WHERE l."调查日期" = $1
          AND l."危害程度" IS NOT NULL
          AND BTRIM(l."危害程度") NOT IN ('', '白', '无需防治')
        ORDER BY
            COALESCE(s.{quote_identifier(LOCALITY_COLUMN)}, ''),
            l."编号"
        """,
        survey_date,
    )

    screenshot_index = (
        build_point_screenshot_index(get_settings().sophora_point_screenshot_dir)
        if include_images
        else {}
    )
    candidates: list[dict[str, Any]] = []
    for row in rows:
        location_id = str(row["location_id"] or "").strip()
        locality = (row["locality"] or "").strip()
        location_name = (row["location_name"] or "").strip()
        insect_count = row["total_insect_count"]
        if insect_count is not None:
            insect_count = int(insect_count)

        damage_level = (row["damage_level"] or "").strip()
        candidates.append(
            {
                "survey_date": serialize_date_value(row["survey_date"]),
                "locality": locality,
                "location_id": location_id,
                "location_name": location_name,
                "total_insect_count": insect_count,
                "damage_level": damage_level,
                "note": (row["note"] or "").strip(),
                "images": load_point_screenshot_images(location_id, screenshot_index),
                "description": build_guo_huai_inchworm_description(
                    locality=locality,
                    location_name=location_name,
                    location_id=location_id,
                    damage_level=damage_level,
                    total_insect_count=insect_count,
                ),
            }
        )

    return candidates


async def fetch_other_pest_survey_candidates(
    survey_date: date_cls,
    include_images: bool = True,
) -> list[dict[str, Any]]:
    """读取指定日期的其他害虫调查导入候选记录。"""

    qualified_survey_table = (
        f"{quote_identifier(SURVEY_SCHEMA)}.{quote_identifier(OTHER_PEST_SURVEY_TABLE)}"
    )
    qualified_site_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(OTHER_PEST_SITE_TABLE)}"
    )

    rows = await fetch(
        f"""
        SELECT
            i."编号" AS location_id,
            i."调查日期" AS survey_date,
            BTRIM(i."虫害类型") AS pest_name,
            BTRIM(i."调查结论") AS survey_result,
            COALESCE(i."详细描述", '') AS description,
            COALESCE(s.{quote_identifier(LOCALITY_COLUMN)}, '') AS locality,
            COALESCE(
                NULLIF(BTRIM(i."点位名称"), ''),
                NULLIF(BTRIM(s."点位名称"), ''),
                ''
            ) AS location_name,
            COALESCE(s."寄主树种", '') AS host_plant,
            COALESCE(s."地块类型", '') AS plot_type
        FROM {qualified_survey_table} AS i
        JOIN {qualified_site_table} AS s
          ON i."编号" = s."编号"
        WHERE i."调查日期" = $1
          AND BTRIM(COALESCE(i."调查结论", '')) = '发现问题'
        ORDER BY
            COALESCE(s.{quote_identifier(LOCALITY_COLUMN)}, ''),
            i."编号",
            COALESCE(i."虫害类型", '')
        """,
        survey_date,
    )

    screenshot_index = (
        build_point_screenshot_index(get_settings().other_pest_point_screenshot_dir)
        if include_images
        else {}
    )
    return [
        {
            "survey_date": serialize_date_value(row["survey_date"]),
            "locality": (row["locality"] or "").strip(),
            "location_id": str(row["location_id"] or "").strip(),
            "location_name": (row["location_name"] or "").strip(),
            "pest_name": (row["pest_name"] or "").strip(),
            "host_plant": (row["host_plant"] or "").strip(),
            "plot_type": (row["plot_type"] or "").strip(),
            "survey_result": (row["survey_result"] or "").strip(),
            "description": (row["description"] or "").strip(),
            "note": "",
            "images": load_point_screenshot_images(
                str(row["location_id"] or "").strip(),
                screenshot_index,
            ),
        }
        for row in rows
    ]


async def fetch_meiguobaie_survey_candidates(
    survey_date: date_cls,
    include_images: bool = True,
) -> list[dict[str, Any]]:
    """读取指定日期的美国白蛾调查导入候选记录。"""

    qualified_survey_table = (
        f"{quote_identifier(SURVEY_SCHEMA)}.{quote_identifier(MEI_GUO_BAI_E_SURVEY_TABLE)}"
    )

    rows = await fetch(
        f"""
        SELECT
            BTRIM(i."编号") AS location_id,
            i."调查日期" AS survey_date,
            COALESCE(NULLIF(BTRIM(i."区域"), ''), '乡镇') AS region,
            COALESCE(i.{quote_identifier(LOCALITY_COLUMN)}, '') AS locality,
            COALESCE(i."点位名称", '') AS location_name,
            COALESCE(i."发生位置", '') AS occurrence_position,
            COALESCE(i."绿地性质", '') AS green_space_type,
            COALESCE(i."危害寄主", '') AS pest_hosts,
            COALESCE(i."受害株数", 0) AS damaged_plant_count,
            COALESCE(i."网幕数量", 0) AS web_nest_count,
            COALESCE(i."详细描述", '') AS description,
            COALESCE(i."备注", '') AS note
        FROM {qualified_survey_table} AS i
        WHERE i."调查日期" = $1
          AND BTRIM(COALESCE(i."详细描述", '')) <> ''
          AND (
              COALESCE(i."受害株数", 0) > 0
              OR COALESCE(i."网幕数量", 0) > 0
          )
        ORDER BY
            COALESCE(i.{quote_identifier(LOCALITY_COLUMN)}, ''),
            BTRIM(i."编号")
        """,
        survey_date,
    )

    screenshot_index = (
        build_point_screenshot_index(get_settings().meiguobaie_point_screenshot_dir)
        if include_images
        else {}
    )
    candidates: list[dict[str, Any]] = []
    for row in rows:
        location_id = str(row["location_id"] or "").strip()
        damaged_plant_count = row["damaged_plant_count"]
        web_nest_count = row["web_nest_count"]
        candidates.append(
            {
                "survey_date": serialize_date_value(row["survey_date"]),
                "region": (row["region"] or "").strip(),
                "locality": (row["locality"] or "").strip(),
                "location_id": location_id,
                "location_name": (row["location_name"] or "").strip(),
                "occurrence_position": (row["occurrence_position"] or "").strip(),
                "green_space_type": (row["green_space_type"] or "").strip(),
                "pest_hosts": (row["pest_hosts"] or "").strip(),
                "damaged_plant_count": int(damaged_plant_count or 0),
                "web_nest_count": int(web_nest_count or 0),
                "description": (row["description"] or "").strip(),
                "note": (row["note"] or "").strip(),
                "images": load_point_screenshot_images(location_id, screenshot_index),
            }
        )

    return candidates
