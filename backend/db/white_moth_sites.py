from __future__ import annotations

import re
from typing import Any

import asyncpg

from backend.db.pool import ensure_pool, fetchrow, quote_identifier

SITE_SCHEMA = "sites"
SURVEY_SCHEMA = "survey"
WHITE_MOTH_SITE_TABLE = "美国白蛾点位基础表"
MEI_GUO_BAI_E_SURVEY_TABLE = "美国白蛾调查表"
LOCALITY_COLUMN = "属地"
# 前缀 2～3 位字母 + 3 位数字；三位前缀用于区分与两位前缀的冲突（如 LY / LYI / LYU）
WHITE_MOTH_SITE_CODE_PATTERN = re.compile(r"^[A-Z]{2,3}\d{3}$")
WHITE_MOTH_SITE_CODE_EXAMPLE = "MQ001"
WHITE_MOTH_SITE_PREFIX_LOCALITIES = {
    "MQ": "马驹桥镇",
    "TH": "台湖镇",
    "ZW": "张家湾镇",
    "YF": "于家务乡",
    "YL": "永乐店镇",
    "HX": "漷县镇",
    "XJ": "西集镇",
    "LC": "潞城镇",
    "SZ": "宋庄镇",
    "YS": "永顺镇",
    "YZ": "杨庄街道",
    "YQ": "玉桥街道",
    "LY": "梨园镇",
    "WJ": "文景街道",
    "JK": "九棵树街道",
    "ZC": "中仓街道",
    "XH": "新华街道",
    "LYI": "潞邑街道",
    "LYU": "潞源街道",
    "BY": "北苑街道",
    "TY": "通运街道",
    "LH": "临河里街道",
}


class WhiteMothSiteCodeError(ValueError):
    """美国白蛾点位编号格式错误。"""


class WhiteMothSiteDuplicateError(ValueError):
    """美国白蛾点位编号重复。"""


def get_white_moth_site_code_rules() -> dict[str, Any]:
    """返回美国白蛾点位编号规则。"""

    return {
        "code_pattern": WHITE_MOTH_SITE_CODE_PATTERN.pattern,
        "code_example": WHITE_MOTH_SITE_CODE_EXAMPLE,
        "prefix_localities": WHITE_MOTH_SITE_PREFIX_LOCALITIES,
    }


def normalize_white_moth_site_code(value: str) -> str:
    """标准化美国白蛾点位编号。"""

    return (value or "").strip().upper()


def resolve_white_moth_site_prefix(prefix: str) -> tuple[str, str]:
    """解析已知编号前缀及其属地。"""

    normalized_prefix = normalize_white_moth_site_code(prefix)
    locality = WHITE_MOTH_SITE_PREFIX_LOCALITIES.get(normalized_prefix)
    if locality is None:
        raise WhiteMothSiteCodeError(
            f"未知编号前缀，请输入类似 {WHITE_MOTH_SITE_CODE_EXAMPLE} 的编号"
        )
    return normalized_prefix, locality


def resolve_white_moth_site_locality(code: str) -> tuple[str, str]:
    """根据美国白蛾点位编号解析标准编号和属地。"""

    normalized_code = normalize_white_moth_site_code(code)
    if not WHITE_MOTH_SITE_CODE_PATTERN.fullmatch(normalized_code):
        raise WhiteMothSiteCodeError(
            f"编号格式不正确，请输入类似 {WHITE_MOTH_SITE_CODE_EXAMPLE} 的编号"
        )

    # 字母前缀整体匹配（支持 2～3 位，避免 LYI 被误判为 LY）
    prefix_match = re.fullmatch(r"([A-Z]{2,3})\d{3}", normalized_code)
    prefix = prefix_match.group(1) if prefix_match else ""
    locality = WHITE_MOTH_SITE_PREFIX_LOCALITIES.get(prefix)
    if locality is None:
        raise WhiteMothSiteCodeError(
            f"编号格式不正确，请输入类似 {WHITE_MOTH_SITE_CODE_EXAMPLE} 的编号"
        )

    return normalized_code, locality


async def get_white_moth_site_code_hint(prefix: str) -> dict[str, Any]:
    """按编号前缀返回该属地当前最大编号与建议下一编号。"""

    normalized_prefix, locality = resolve_white_moth_site_prefix(prefix)
    qualified_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(WHITE_MOTH_SITE_TABLE)}"
    )
    escaped_prefix = re.escape(normalized_prefix)
    code_pattern = f"^{escaped_prefix}[0-9]{{3}}$"
    serial_pattern = f"^{escaped_prefix}([0-9]{{3}})$"

    row = await fetchrow(
        f"""
        SELECT MAX(CAST(substring("编号" FROM $1) AS integer)) AS max_serial
        FROM {qualified_table}
        WHERE "编号" ~ $2
        """,
        serial_pattern,
        code_pattern,
    )
    max_serial = row["max_serial"] if row else None
    if max_serial is None:
        return {
            "prefix": normalized_prefix,
            "locality": locality,
            "latest_code": None,
            "latest_serial": None,
            "suggested_next_code": f"{normalized_prefix}001",
        }

    next_serial = int(max_serial) + 1
    return {
        "prefix": normalized_prefix,
        "locality": locality,
        "latest_code": f"{normalized_prefix}{int(max_serial):03d}",
        "latest_serial": int(max_serial),
        "suggested_next_code": (
            f"{normalized_prefix}{next_serial:03d}" if next_serial <= 999 else None
        ),
    }


async def create_white_moth_site(
    *,
    code: str,
    site_name: str,
    longitude: float,
    latitude: float,
) -> dict[str, Any]:
    """新增美国白蛾点位。"""

    normalized_code, locality = resolve_white_moth_site_locality(code)
    qualified_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(WHITE_MOTH_SITE_TABLE)}"
    )

    try:
        row = await fetchrow(
            f"""
            INSERT INTO {qualified_table} (
                "编号",
                {quote_identifier(LOCALITY_COLUMN)},
                "点位名称",
                geom
            )
            VALUES (
                $1,
                $2,
                $3,
                ST_SetSRID(ST_MakePoint($4, $5), 4326)
            )
            RETURNING
                gid,
                "编号" AS code,
                {quote_identifier(LOCALITY_COLUMN)} AS locality,
                COALESCE("点位名称", '') AS site_name,
                ST_X(geom) AS longitude,
                ST_Y(geom) AS latitude
            """,
            normalized_code,
            locality,
            (site_name or "").strip(),
            longitude,
            latitude,
        )
    except asyncpg.UniqueViolationError as exc:
        raise WhiteMothSiteDuplicateError(f"编号已存在：{normalized_code}") from exc

    return dict(row or {})

async def check_white_moth_site_deletion(code: str) -> dict[str, Any] | None:
    """删除前检查美国白蛾点位：返回点位信息与关联调查记录数。点位不存在返回 None。"""

    qualified_site_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(WHITE_MOTH_SITE_TABLE)}"
    )
    qualified_survey_table = (
        f"{quote_identifier(SURVEY_SCHEMA)}.{quote_identifier(MEI_GUO_BAI_E_SURVEY_TABLE)}"
    )

    row = await fetchrow(
        f"""
        SELECT
            s."编号" AS code,
            COALESCE(s.{quote_identifier(LOCALITY_COLUMN)}, '') AS locality,
            COALESCE(s."点位名称", '') AS site_name,
            ST_X(s.geom) AS longitude,
            ST_Y(s.geom) AS latitude,
            COUNT(i."编号") AS survey_record_count
        FROM {qualified_site_table} AS s
        LEFT JOIN {qualified_survey_table} AS i
          ON BTRIM(i."编号") = s."编号"
        WHERE s."编号" = $1
        GROUP BY s."编号", s.{quote_identifier(LOCALITY_COLUMN)}, s."点位名称", s.geom
        """,
        code,
    )
    if row is None:
        return None
    return {
        "code": row["code"],
        "locality": row["locality"],
        "site_name": row["site_name"],
        "longitude": row["longitude"],
        "latitude": row["latitude"],
        "survey_record_count": row["survey_record_count"],
    }

async def delete_white_moth_site(*, code: str, operator: dict[str, Any]) -> dict[str, Any] | None:
    """删除美国白蛾点位并在同一事务内写入操作日志。点位不存在返回 None。"""

    from backend.db.admin import (
        ADMIN_SCHEMA,
        OPERATION_LOG_ACTION_DELETE_WHITE_MOTH_SITE,
        OPERATION_LOG_TABLE,
        ensure_operation_log_storage,
    )

    await ensure_operation_log_storage()

    qualified_site_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(WHITE_MOTH_SITE_TABLE)}"
    )
    qualified_survey_table = (
        f"{quote_identifier(SURVEY_SCHEMA)}.{quote_identifier(MEI_GUO_BAI_E_SURVEY_TABLE)}"
    )
    qualified_log_table = (
        f'"{ADMIN_SCHEMA}"."{OPERATION_LOG_TABLE}"'
    )

    operator_id = operator.get("id")
    operator_username = operator.get("username") or ""
    operator_display_name = operator.get("display_name") or ""
    operator_role = operator.get("role") or ""

    pool = await ensure_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            deleted = await connection.fetchrow(
                f"""
                DELETE FROM {qualified_site_table}
                WHERE "编号" = $1
                RETURNING
                    gid,
                    "编号" AS code,
                    COALESCE({quote_identifier(LOCALITY_COLUMN)}, '') AS locality,
                    COALESCE("点位名称", '') AS site_name,
                    ST_X(geom) AS longitude,
                    ST_Y(geom) AS latitude
                """,
                code,
            )
            if deleted is None:
                return None

            survey_count_row = await connection.fetchrow(
                f"""
                SELECT COUNT(*) AS survey_record_count
                FROM {qualified_survey_table}
                WHERE BTRIM("编号") = $1
                """,
                code,
            )
            survey_record_count = (
                survey_count_row["survey_record_count"] if survey_count_row else 0
            )

            await connection.execute(
                f"""
                INSERT INTO {qualified_log_table} (
                    action,
                    operator_id,
                    operator_username,
                    operator_display_name,
                    operator_role,
                    site_code,
                    site_name,
                    locality,
                    longitude,
                    latitude,
                    survey_record_count
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                OPERATION_LOG_ACTION_DELETE_WHITE_MOTH_SITE,
                operator_id,
                operator_username,
                operator_display_name,
                operator_role,
                deleted["code"],
                deleted["site_name"],
                deleted["locality"],
                deleted["longitude"],
                deleted["latitude"],
                survey_record_count,
            )

            return {
                "code": deleted["code"],
                "site_name": deleted["site_name"],
                "locality": deleted["locality"],
                "longitude": deleted["longitude"],
                "latitude": deleted["latitude"],
                "survey_record_count": survey_record_count,
            }
