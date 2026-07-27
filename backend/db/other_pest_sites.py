from __future__ import annotations

import re
from typing import Any

from backend.db.pool import ensure_pool, fetchrow, quote_identifier
from backend.db.white_moth_sites import WHITE_MOTH_SITE_PREFIX_LOCALITIES

SITE_SCHEMA = "sites"
SURVEY_SCHEMA = "survey"
OTHER_PEST_SITE_TABLE = "其他害虫点位基础表"
OTHER_PEST_SURVEY_TABLE = "其他害虫调查表"
LOCALITY_COLUMN = "属地"
# 其他害虫点位编号固定 QT 前缀 + 4 位序号（与现有数据一致），编号不含属地信息
OTHER_PEST_SITE_CODE_PREFIX = "QT"
OTHER_PEST_SITE_CODE_PATTERN = re.compile(r"^QT\d{4}$")
OTHER_PEST_SITE_CODE_EXAMPLE = "QT0001"
OTHER_PEST_SITE_CODE_SERIAL_WIDTH = 4
OTHER_PEST_SITE_LOCALITIES = tuple(dict.fromkeys(WHITE_MOTH_SITE_PREFIX_LOCALITIES.values()))


class OtherPestSiteCodeError(ValueError):
    """其他害虫点位编号或属地错误。"""


class OtherPestSiteDuplicateError(ValueError):
    """其他害虫点位编号重复。"""


def get_other_pest_site_code_rules() -> dict[str, Any]:
    """返回其他害虫点位编号规则与可选属地列表。"""

    return {
        "code_pattern": OTHER_PEST_SITE_CODE_PATTERN.pattern,
        "code_example": OTHER_PEST_SITE_CODE_EXAMPLE,
        "code_prefix": OTHER_PEST_SITE_CODE_PREFIX,
        "localities": list(OTHER_PEST_SITE_LOCALITIES),
    }


def normalize_other_pest_site_code(value: str) -> str:
    """标准化其他害虫点位编号。"""

    return (value or "").strip().upper()


def validate_other_pest_site(code: str, locality: str) -> tuple[str, str]:
    """校验其他害虫点位编号格式与属地合法性，返回标准化后的（编号, 属地）。"""

    normalized_code = normalize_other_pest_site_code(code)
    if not OTHER_PEST_SITE_CODE_PATTERN.fullmatch(normalized_code):
        raise OtherPestSiteCodeError(
            f"编号格式不正确，请输入类似 {OTHER_PEST_SITE_CODE_EXAMPLE} 的编号"
        )

    normalized_locality = (locality or "").strip()
    if normalized_locality not in OTHER_PEST_SITE_LOCALITIES:
        raise OtherPestSiteCodeError("属地不合法，请从列表中选择乡镇街道")

    return normalized_code, normalized_locality


async def get_other_pest_site_code_hint() -> dict[str, Any]:
    """返回其他害虫点位当前最大编号与建议下一编号（QT 固定前缀）。"""

    qualified_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(OTHER_PEST_SITE_TABLE)}"
    )
    width = OTHER_PEST_SITE_CODE_SERIAL_WIDTH
    code_pattern = f"^{OTHER_PEST_SITE_CODE_PREFIX}[0-9]{{{width}}}$"
    serial_pattern = f"^{OTHER_PEST_SITE_CODE_PREFIX}([0-9]{{{width}}})$"

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
    max_serial_allowed = 10**width - 1
    if max_serial is None:
        return {
            "prefix": OTHER_PEST_SITE_CODE_PREFIX,
            "latest_code": None,
            "latest_serial": None,
            "suggested_next_code": f"{OTHER_PEST_SITE_CODE_PREFIX}{1:0{width}d}",
        }

    next_serial = int(max_serial) + 1
    return {
        "prefix": OTHER_PEST_SITE_CODE_PREFIX,
        "latest_code": f"{OTHER_PEST_SITE_CODE_PREFIX}{int(max_serial):0{width}d}",
        "latest_serial": int(max_serial),
        "suggested_next_code": (
            f"{OTHER_PEST_SITE_CODE_PREFIX}{next_serial:0{width}d}"
            if next_serial <= max_serial_allowed
            else None
        ),
    }


async def create_other_pest_site(
    *,
    code: str,
    site_name: str,
    locality: str,
    longitude: float,
    latitude: float,
) -> dict[str, Any]:
    """新增其他害虫点位。编号无唯一约束，插入前显式查重。"""

    normalized_code, normalized_locality = validate_other_pest_site(code, locality)
    qualified_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(OTHER_PEST_SITE_TABLE)}"
    )

    existing = await fetchrow(
        f"""
        SELECT 1
        FROM {qualified_table}
        WHERE "编号" = $1
        LIMIT 1
        """,
        normalized_code,
    )
    if existing is not None:
        raise OtherPestSiteDuplicateError(f"编号已存在：{normalized_code}")

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
        normalized_locality,
        (site_name or "").strip(),
        longitude,
        latitude,
    )

    return dict(row or {})

async def check_other_pest_site_deletion(code: str) -> dict[str, Any] | None:
    """删除前检查其他害虫点位：返回点位信息与关联调查记录数。点位不存在返回 None。

    编号可能存在历史重复数据（含无 geom 的坏数据），优先返回带坐标的点位。
    """

    qualified_site_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(OTHER_PEST_SITE_TABLE)}"
    )
    qualified_survey_table = (
        f"{quote_identifier(SURVEY_SCHEMA)}.{quote_identifier(OTHER_PEST_SURVEY_TABLE)}"
    )

    site_row = await fetchrow(
        f"""
        SELECT
            s."编号" AS code,
            COALESCE(s.{quote_identifier(LOCALITY_COLUMN)}, '') AS locality,
            COALESCE(s."点位名称", '') AS site_name,
            ST_X(s.geom) AS longitude,
            ST_Y(s.geom) AS latitude
        FROM {qualified_site_table} AS s
        WHERE s."编号" = $1
        ORDER BY (s.geom IS NOT NULL) DESC
        LIMIT 1
        """,
        code,
    )
    if site_row is None:
        return None

    survey_count_row = await fetchrow(
        f"""
        SELECT COUNT(*) AS survey_record_count
        FROM {qualified_survey_table}
        WHERE BTRIM("编号") = $1
        """,
        code,
    )

    return {
        "code": site_row["code"],
        "locality": site_row["locality"],
        "site_name": site_row["site_name"],
        "longitude": site_row["longitude"],
        "latitude": site_row["latitude"],
        "survey_record_count": (
            survey_count_row["survey_record_count"] if survey_count_row else 0
        ),
    }

async def delete_other_pest_site(*, code: str, operator: dict[str, Any]) -> dict[str, Any] | None:
    """删除其他害虫点位并在同一事务内写入操作日志。点位不存在返回 None。

    编号无唯一约束，会删除该编号全部记录（含历史遗留的无坐标坏数据）。
    """

    from backend.db.admin import (
        ADMIN_SCHEMA,
        OPERATION_LOG_ACTION_DELETE_OTHER_PEST_SITE,
        OPERATION_LOG_TABLE,
        ensure_operation_log_storage,
    )

    await ensure_operation_log_storage()

    qualified_site_table = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(OTHER_PEST_SITE_TABLE)}"
    )
    qualified_survey_table = (
        f"{quote_identifier(SURVEY_SCHEMA)}.{quote_identifier(OTHER_PEST_SURVEY_TABLE)}"
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
            deleted_rows = await connection.fetch(
                f"""
                DELETE FROM {qualified_site_table}
                WHERE "编号" = $1
                RETURNING
                    "编号" AS code,
                    COALESCE({quote_identifier(LOCALITY_COLUMN)}, '') AS locality,
                    COALESCE("点位名称", '') AS site_name,
                    ST_X(geom) AS longitude,
                    ST_Y(geom) AS latitude
                """,
                code,
            )
            if not deleted_rows:
                return None

            deleted = next(
                (row for row in deleted_rows if row["longitude"] is not None),
                deleted_rows[0],
            )

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
                OPERATION_LOG_ACTION_DELETE_OTHER_PEST_SITE,
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
