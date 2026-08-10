"""通用地图点位新增 — 面向任务视图（task_*）的 sites 基表写入。

根据任务视图绑定的 base_table 选择编号规则与插入列：
- 其他害虫：固定 QT 前缀 + 属地下拉
- 其余虫种：字母前缀自动识别属地（共享白蛾前缀表）
- 所有表：支持建议下一编号
- 若任务视图带编号清单筛选，新增编号必须落在清单内
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import asyncpg

from backend.db.pool import fetch, fetchrow, quote_identifier
from backend.db.white_moth_sites import WHITE_MOTH_SITE_PREFIX_LOCALITIES

SITE_SCHEMA = "sites"
CODE_COLUMN = "编号"
LOCALITY_COLUMN = "属地"
GEOM_COLUMN = "geom"
SITE_NAME_CANDIDATES = ("点位名称", "村", "点位")

# 与白蛾一致的属地前缀表，供除「其他害虫」外的前缀模式复用。
PREFIX_LOCALITIES = dict(WHITE_MOTH_SITE_PREFIX_LOCALITIES)
SORTED_PREFIXES = tuple(sorted(PREFIX_LOCALITIES.keys(), key=len, reverse=True))
LOCALITY_OPTIONS = tuple(dict.fromkeys(PREFIX_LOCALITIES.values()))


class GenericSiteError(ValueError):
    """通用点位业务错误（编号/属地/视图配置等）。"""


class GenericSiteDuplicateError(ValueError):
    """编号重复。"""


class GenericSiteNotSupportedError(ValueError):
    """当前视图不支持添加点位。"""


@dataclass(frozen=True)
class SiteTableProfile:
    """单个 sites 基表的写入与编号规则。"""

    table_name: str
    locality_mode: str  # "prefix" | "manual"
    serial_width: int
    name_column: str | None
    code_example: str
    fixed_prefix: str | None = None
    prefix_min: int = 2
    prefix_max: int = 3
    defaults: dict[str, Any] = field(default_factory=dict)
    # 无序列默认值的主键列，插入前手动 MAX+1
    manual_pk_column: str | None = None

    @property
    def code_pattern(self) -> str:
        if self.fixed_prefix:
            return rf"^{re.escape(self.fixed_prefix)}\d{{{self.serial_width}}}$"
        return (
            rf"^[A-Z]{{{self.prefix_min},{self.prefix_max}}}"
            rf"\d{{{self.serial_width}}}$"
        )


# 已知基表配置。未列出的表若含 编号+geom 则走动态探测。
KNOWN_SITE_PROFILES: dict[str, SiteTableProfile] = {
    "美国白蛾点位基础表": SiteTableProfile(
        table_name="美国白蛾点位基础表",
        locality_mode="prefix",
        serial_width=3,
        name_column="点位名称",
        code_example="MQ001",
    ),
    "其他害虫点位基础表": SiteTableProfile(
        table_name="其他害虫点位基础表",
        locality_mode="manual",
        serial_width=4,
        name_column="点位名称",
        code_example="QT0001",
        fixed_prefix="QT",
        prefix_min=2,
        prefix_max=2,
    ),
    "杨树点位基础表": SiteTableProfile(
        table_name="杨树点位基础表",
        locality_mode="prefix",
        serial_width=4,
        name_column="村",
        code_example="MQ0001",
        defaults={"当前点位状态": "可调查"},
    ),
    "杨树食叶害虫点位基础表": SiteTableProfile(
        table_name="杨树食叶害虫点位基础表",
        locality_mode="prefix",
        serial_width=4,
        name_column="村",
        code_example="MQ0001",
        manual_pk_column="gid",
    ),
    "国槐点位基础表": SiteTableProfile(
        table_name="国槐点位基础表",
        locality_mode="prefix",
        serial_width=4,
        name_column="村",
        code_example="MQ0001",
    ),
    "美国白蛾小区点位基础表": SiteTableProfile(
        table_name="美国白蛾小区点位基础表",
        locality_mode="prefix",
        serial_width=2,
        name_column="点位名称",
        code_example="ZC01",
    ),
}


def normalize_site_code(value: str) -> str:
    return (value or "").strip().upper()


def match_prefix(code_or_prefix: str) -> str:
    """从编号或前缀输入中匹配最长已知前缀；未匹配返回空串。"""

    text = normalize_site_code(code_or_prefix)
    if not text:
        return ""
    for prefix in SORTED_PREFIXES:
        if text == prefix:
            return prefix
        if text.startswith(prefix) and re.fullmatch(r"\d*", text[len(prefix) :]):
            return prefix
    return ""


def get_known_profile(base_table: str) -> SiteTableProfile | None:
    return KNOWN_SITE_PROFILES.get((base_table or "").strip())


async def _load_table_columns(base_table: str) -> list[str]:
    rows = await fetch(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = $1 AND table_name = $2
        ORDER BY ordinal_position
        """,
        SITE_SCHEMA,
        base_table,
    )
    return [row["column_name"] for row in rows]


async def resolve_site_table_profile(base_table: str) -> SiteTableProfile:
    """解析基表写入配置；未知表在具备 编号+geom 时生成默认前缀模式配置。"""

    table = (base_table or "").strip()
    if not table:
        raise GenericSiteNotSupportedError("任务视图未绑定基础点位表")

    columns = await _load_table_columns(table)
    if not columns:
        raise GenericSiteNotSupportedError(f"基础点位表不存在：{table}")
    if GEOM_COLUMN not in columns:
        raise GenericSiteNotSupportedError(f"基础点位表缺少 geom：{table}")
    if CODE_COLUMN not in columns:
        raise GenericSiteNotSupportedError(f"基础点位表缺少编号字段，无法添加点位：{table}")

    known = get_known_profile(table)
    if known is not None:
        name_column = known.name_column if known.name_column in columns else None
        if name_column is None:
            for candidate in SITE_NAME_CANDIDATES:
                if candidate in columns:
                    name_column = candidate
                    break
        defaults = {key: value for key, value in known.defaults.items() if key in columns}
        manual_pk = known.manual_pk_column if known.manual_pk_column in columns else None
        return SiteTableProfile(
            table_name=table,
            locality_mode=known.locality_mode,
            serial_width=known.serial_width,
            name_column=name_column,
            code_example=known.code_example,
            fixed_prefix=known.fixed_prefix,
            prefix_min=known.prefix_min,
            prefix_max=known.prefix_max,
            defaults=defaults,
            manual_pk_column=manual_pk,
        )

    name_column = None
    for candidate in SITE_NAME_CANDIDATES:
        if candidate in columns:
            name_column = candidate
            break

    # 动态探测序号宽度：取字母前缀后纯数字编号的众数长度，默认 3。
    serial_width = 3
    sample = await fetchrow(
        f"""
        SELECT mode() WITHIN GROUP (
            ORDER BY length(substring(BTRIM("编号") FROM '[0-9]+$'))
        ) AS width
        FROM {quote_identifier(SITE_SCHEMA)}.{quote_identifier(table)}
        WHERE "编号" ~ '^[A-Za-z]{{2,3}}[0-9]+$'
        """
    )
    if sample and sample["width"]:
        width = int(sample["width"])
        if 1 <= width <= 6:
            serial_width = width

    return SiteTableProfile(
        table_name=table,
        locality_mode="prefix",
        serial_width=serial_width,
        name_column=name_column,
        code_example=f"MQ{'1'.zfill(serial_width)}",
        defaults={},
        manual_pk_column=None,
    )


def build_site_add_config_payload(
    *,
    enabled: bool,
    base_table: str | None = None,
    profile: SiteTableProfile | None = None,
    has_code_list_filter: bool = False,
    reason: str | None = None,
) -> dict[str, Any]:
    """构造前端可用的 site_add 配置块。"""

    if not enabled or profile is None:
        return {
            "enabled": False,
            "base_table": base_table,
            "reason": reason or "当前视图不支持添加点位",
            "has_code_list_filter": bool(has_code_list_filter),
        }

    payload: dict[str, Any] = {
        "enabled": True,
        "base_table": profile.table_name,
        "locality_mode": profile.locality_mode,
        "code_pattern": profile.code_pattern,
        "code_example": profile.code_example,
        "serial_width": profile.serial_width,
        "fixed_prefix": profile.fixed_prefix,
        "name_field_label": profile.name_column or "点位名称",
        "has_code_list_filter": bool(has_code_list_filter),
        "prefix_localities": (
            dict(PREFIX_LOCALITIES) if profile.locality_mode == "prefix" else {}
        ),
        "localities": (
            list(LOCALITY_OPTIONS) if profile.locality_mode == "manual" else []
        ),
    }
    return payload


def validate_code_and_locality(
    profile: SiteTableProfile,
    *,
    code: str,
    locality: str | None,
) -> tuple[str, str]:
    """校验编号与属地，返回 (normalized_code, locality)。"""

    normalized = normalize_site_code(code)
    if not normalized:
        raise GenericSiteError("请输入编号")

    pattern = re.compile(profile.code_pattern)
    if not pattern.fullmatch(normalized):
        raise GenericSiteError(
            f"编号格式不正确，请输入类似 {profile.code_example} 的编号"
        )

    if profile.locality_mode == "manual":
        normalized_locality = (locality or "").strip()
        if normalized_locality not in LOCALITY_OPTIONS:
            raise GenericSiteError("属地不合法，请从列表中选择乡镇街道")
        return normalized, normalized_locality

    prefix = match_prefix(normalized)
    if not prefix:
        raise GenericSiteError(
            f"未知编号前缀，请输入类似 {profile.code_example} 的编号"
        )
    # 序号位数已由 pattern 保证；再确认前缀后全是数字且宽度正确
    serial = normalized[len(prefix) :]
    if len(serial) != profile.serial_width or not serial.isdigit():
        raise GenericSiteError(
            f"编号格式不正确，请输入类似 {profile.code_example} 的编号"
        )
    return normalized, PREFIX_LOCALITIES[prefix]


async def get_code_hint_for_profile(
    profile: SiteTableProfile,
    *,
    prefix: str | None = None,
) -> dict[str, Any]:
    """按配置返回建议下一编号。"""

    qualified = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(profile.table_name)}"
    )
    width = profile.serial_width

    if profile.locality_mode == "manual" and profile.fixed_prefix:
        resolved_prefix = profile.fixed_prefix
        locality = None
    else:
        resolved_prefix = match_prefix(prefix or "")
        if not resolved_prefix:
            raise GenericSiteError(
                f"未知编号前缀，请输入类似 {profile.code_example} 的编号"
            )
        locality = PREFIX_LOCALITIES.get(resolved_prefix)

    escaped = re.escape(resolved_prefix)
    code_pattern = rf"^{escaped}[0-9]{{{width}}}$"
    serial_pattern = rf"^{escaped}([0-9]{{{width}}})$"

    row = await fetchrow(
        f"""
        SELECT MAX(CAST(substring("{CODE_COLUMN}" FROM $1) AS integer)) AS max_serial
        FROM {qualified}
        WHERE "{CODE_COLUMN}" ~ $2
        """,
        serial_pattern,
        code_pattern,
    )
    max_serial = row["max_serial"] if row else None
    max_allowed = 10**width - 1

    if max_serial is None:
        return {
            "prefix": resolved_prefix,
            "locality": locality,
            "latest_code": None,
            "latest_serial": None,
            "suggested_next_code": f"{resolved_prefix}{1:0{width}d}",
        }

    next_serial = int(max_serial) + 1
    return {
        "prefix": resolved_prefix,
        "locality": locality,
        "latest_code": f"{resolved_prefix}{int(max_serial):0{width}d}",
        "latest_serial": int(max_serial),
        "suggested_next_code": (
            f"{resolved_prefix}{next_serial:0{width}d}"
            if next_serial <= max_allowed
            else None
        ),
    }


async def create_generic_site(
    *,
    base_table: str,
    code: str,
    site_name: str,
    locality: str | None,
    longitude: float,
    latitude: float,
    allowed_codes: list[str] | None = None,
) -> dict[str, Any]:
    """向指定 sites 基表插入点位。"""

    profile = await resolve_site_table_profile(base_table)
    normalized_code, resolved_locality = validate_code_and_locality(
        profile, code=code, locality=locality
    )

    if allowed_codes:
        allowed_set = {normalize_site_code(item) for item in allowed_codes if item}
        if normalized_code not in allowed_set:
            raise GenericSiteError(
                f"该任务视图限定了编号清单，新编号 {normalized_code} 不在清单中，"
                "添加后不会出现在当前视图。请改用清单内编号，或先在图层管理中调整编号清单。"
            )

    qualified = (
        f"{quote_identifier(SITE_SCHEMA)}.{quote_identifier(profile.table_name)}"
    )

    existing = await fetchrow(
        f"""
        SELECT 1
        FROM {qualified}
        WHERE BTRIM("{CODE_COLUMN}"::text) = $1
        LIMIT 1
        """,
        normalized_code,
    )
    if existing is not None:
        raise GenericSiteDuplicateError(f"编号已存在：{normalized_code}")

    columns = await _load_table_columns(profile.table_name)
    insert_columns: list[str] = [CODE_COLUMN]
    values_sql: list[str] = ["$1"]
    args: list[Any] = [normalized_code]
    arg_index = 2

    if LOCALITY_COLUMN in columns:
        insert_columns.append(LOCALITY_COLUMN)
        values_sql.append(f"${arg_index}")
        args.append(resolved_locality)
        arg_index += 1

    if profile.name_column and profile.name_column in columns:
        insert_columns.append(profile.name_column)
        values_sql.append(f"${arg_index}")
        args.append((site_name or "").strip())
        arg_index += 1

    for default_column, default_value in profile.defaults.items():
        if default_column in columns and default_column not in insert_columns:
            insert_columns.append(default_column)
            values_sql.append(f"${arg_index}")
            args.append(default_value)
            arg_index += 1

    if profile.manual_pk_column and profile.manual_pk_column in columns:
        pk_col = profile.manual_pk_column
        next_pk = await fetchrow(
            f"SELECT COALESCE(MAX({quote_identifier(pk_col)}), 0) + 1 AS next_id "
            f"FROM {qualified}"
        )
        insert_columns.append(pk_col)
        values_sql.append(f"${arg_index}")
        args.append(int(next_pk["next_id"]) if next_pk else 1)
        arg_index += 1

    lon_placeholder = f"${arg_index}"
    lat_placeholder = f"${arg_index + 1}"
    args.extend([longitude, latitude])
    insert_columns.append(GEOM_COLUMN)
    values_sql.append(
        f"ST_SetSRID(ST_MakePoint({lon_placeholder}, {lat_placeholder}), 4326)"
    )

    column_sql = ", ".join(quote_identifier(col) for col in insert_columns)
    value_sql = ", ".join(values_sql)

    returning_name = (
        f"COALESCE({quote_identifier(profile.name_column)}, '')"
        if profile.name_column and profile.name_column in columns
        else "''::text"
    )
    returning_locality = (
        f"COALESCE({quote_identifier(LOCALITY_COLUMN)}, '')"
        if LOCALITY_COLUMN in columns
        else "''::text"
    )
    if "gid" in columns:
        gid_expr = f"{quote_identifier('gid')} AS gid"
    elif "id" in columns:
        gid_expr = f"{quote_identifier('id')} AS gid"
    else:
        gid_expr = "NULL::integer AS gid"

    try:
        row = await fetchrow(
            f"""
            INSERT INTO {qualified} ({column_sql})
            VALUES ({value_sql})
            RETURNING
                {gid_expr},
                BTRIM({quote_identifier(CODE_COLUMN)}::text) AS code,
                {returning_locality} AS locality,
                {returning_name} AS site_name,
                ST_X({quote_identifier(GEOM_COLUMN)}) AS longitude,
                ST_Y({quote_identifier(GEOM_COLUMN)}) AS latitude
            """,
            *args,
        )
    except asyncpg.UniqueViolationError as exc:
        raise GenericSiteDuplicateError(f"编号已存在：{normalized_code}") from exc

    return dict(row or {})
