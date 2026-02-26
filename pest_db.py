"""
统一的害虫调查数据库操作模块

说明：
- 将原来 chunchihuo_reports_db / guohuaichihuo_reports_db / qitahaichong_reports_db
  三个重复模块合并为一个参数化模块。
- 通过 PEST_DB_CONFIGS 配置表驱动，新增害虫类型只需追加一行配置。
- 保留原数据库文件路径和表结构，无需数据迁移。
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# 允许用于 ORDER BY 的安全字段白名单
_SAFE_ORDER_COLUMNS = {
    "id", "survey_date", "region", "town_or_street", "location_id",
    "location_name", "report_time", "pest_name",
}


@dataclass(frozen=True)
class PestDBConfig:
    """单个害虫类型的数据库配置"""
    table: str                          # 表名
    db_file: str                        # 数据库文件名（位于 data/ 下）
    fields: tuple[str, ...]             # 业务字段（不含 id / report_time）
    pest_type_label: str                # 前端展示用的中文名
    display_fields: tuple[str, ...] = field(default=())  # fetch 时 SELECT 的额外展示字段

    @property
    def db_path(self) -> Path:
        return DATA_DIR / self.db_file


# ── 害虫类型注册表 ──────────────────────────────────────────
# 共享字段（春尺蠖 / 国槐尺蠖）
_CHIHUO_FIELDS = (
    "survey_date", "region", "town_or_street", "location_id",
    "location_name", "occurrence_position",
    "total_insect_count", "damage_level", "description",
)

# 其他害虫独有字段
_QITA_FIELDS = (
    "survey_date", "region", "town_or_street", "location_id",
    "location_name", "occurrence_position",
    "plot_type", "host_plant", "pest_name", "description",
)

PEST_DB_CONFIGS: dict[str, PestDBConfig] = {
    "春尺蠖": PestDBConfig(
        table="chunchihuo_reports",
        db_file="chunchihuo_reports.sqlite3",
        fields=_CHIHUO_FIELDS,
        pest_type_label="春尺蠖",
    ),
    "国槐尺蠖": PestDBConfig(
        table="guohuaichihuo_reports",
        db_file="guohuaichihuo_reports.sqlite3",
        fields=_CHIHUO_FIELDS,
        pest_type_label="国槐尺蠖",
    ),
    "其他害虫": PestDBConfig(
        table="qitahaichong_reports",
        db_file="qitahaichong_reports.sqlite3",
        fields=_QITA_FIELDS,
        pest_type_label="其他害虫",
    ),
}


def _get_config(pest_type: str) -> PestDBConfig:
    """获取害虫类型配置，不存在时抛出 ValueError。"""
    config = PEST_DB_CONFIGS.get(pest_type)
    if config is None:
        valid = ", ".join(PEST_DB_CONFIGS.keys())
        raise ValueError(f"未知的害虫类型 '{pest_type}'，有效值: {valid}")
    return config


def _validate_order_by(order_by: str) -> str:
    """校验 ORDER BY 子句，防止 SQL 注入。"""
    parts = order_by.strip().split()
    if not parts:
        return "report_time DESC"
    col = parts[0].lower()
    if col not in _SAFE_ORDER_COLUMNS:
        return "report_time DESC"
    direction = parts[1].upper() if len(parts) > 1 else "ASC"
    if direction not in ("ASC", "DESC"):
        direction = "ASC"
    return f"{col} {direction}"


# ── 公开 API ────────────────────────────────────────────────

def init_pest_db(pest_type: str) -> Path:
    """初始化指定害虫类型的数据库（建表 + 索引）。

    Returns:
        实际使用的数据库路径。
    """
    config = _get_config(pest_type)
    db_path = config.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # 构建 CREATE TABLE 语句
    col_defs = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
    for f in config.fields:
        if f == "survey_date":
            col_defs.append(f"{f} TEXT NOT NULL")
        elif f == "location_id":
            col_defs.append(f"{f} TEXT NOT NULL")
        elif f in ("total_insect_count",):
            col_defs.append(f"{f} INTEGER")
        else:
            col_defs.append(f"{f} TEXT")
    col_defs.append("report_time TEXT NOT NULL DEFAULT (date('now','localtime'))")
    col_defs.append("UNIQUE(survey_date, location_id)")

    create_sql = f"CREATE TABLE IF NOT EXISTS {config.table} (\n    " + ",\n    ".join(col_defs) + "\n);"
    index_sql = (
        f"CREATE INDEX IF NOT EXISTS idx_{config.table}_report_time "
        f"ON {config.table}(report_time);"
    )

    with sqlite3.connect(db_path) as conn:
        conn.executescript(create_sql)
        conn.executescript(index_sql)

    return db_path


def init_all_pest_dbs() -> None:
    """初始化所有已注册害虫类型的数据库。"""
    for pest_type in PEST_DB_CONFIGS:
        init_pest_db(pest_type)


def insert_pest_record(
    pest_type: str,
    record: dict,
    replace_on_conflict: bool = True,
) -> tuple[bool, str]:
    """插入单条调查记录。

    Args:
        pest_type: 害虫类型（如"春尺蠖"）
        record: 记录字典，必须包含 survey_date 和 location_id
        replace_on_conflict: 遇到重复记录时是否替换

    Returns:
        (成功标志, 消息)
    """
    config = _get_config(pest_type)

    if not record.get("survey_date") or not record.get("location_id"):
        return False, "缺少必填字段：survey_date 或 location_id"

    insert_mode = "INSERT OR REPLACE" if replace_on_conflict else "INSERT OR IGNORE"
    placeholders = ", ".join("?" for _ in config.fields)
    columns = ", ".join(config.fields)

    try:
        with sqlite3.connect(config.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"{insert_mode} INTO {config.table} ({columns}) VALUES ({placeholders})",
                tuple(record.get(f, "") for f in config.fields),
            )
            conn.commit()
            if cursor.rowcount > 0:
                return True, "记录已保存"
            return False, "记录已存在（未更新）"
    except sqlite3.Error as e:
        return False, f"数据库错误: {e}"


def insert_pest_records_batch(
    pest_type: str,
    records: list[dict],
    replace_on_conflict: bool = True,
) -> tuple[int, int, list[str]]:
    """批量插入调查记录（单事务内执行，性能优于逐条插入）。

    Returns:
        (成功数量, 失败数量, 错误消息列表)
    """
    config = _get_config(pest_type)
    insert_mode = "INSERT OR REPLACE" if replace_on_conflict else "INSERT OR IGNORE"
    columns = ", ".join(config.fields)
    placeholders = ", ".join("?" for _ in config.fields)
    sql = f"{insert_mode} INTO {config.table} ({columns}) VALUES ({placeholders})"

    success_count = 0
    fail_count = 0
    errors: list[str] = []

    # 先做必填字段预验证，将合法记录和非法记录分开
    valid_rows: list[tuple] = []
    for idx, record in enumerate(records):
        if not record.get("survey_date") or not record.get("location_id"):
            fail_count += 1
            errors.append(f"第 {idx + 1} 条记录: 缺少必填字段：survey_date 或 location_id")
        else:
            valid_rows.append(tuple(record.get(f, "") for f in config.fields))

    # 批量写入合法记录
    if valid_rows:
        try:
            with sqlite3.connect(config.db_path) as conn:
                conn.executemany(sql, valid_rows)
                conn.commit()
                success_count = len(valid_rows)
        except sqlite3.Error as e:
            fail_count += len(valid_rows)
            errors.append(f"数据库批量写入错误: {e}")

    return success_count, fail_count, errors


def fetch_pest_records(
    pest_type: str,
    order_by: str = "report_time DESC",
) -> list[dict]:
    """获取指定害虫类型的数据库记录。

    Returns:
        记录列表（字典），每条记录包含 pest_type 字段。
    """
    config = _get_config(pest_type)
    safe_order = _validate_order_by(order_by)

    # 构建 SELECT 列表
    select_cols = [f"'{config.pest_type_label}' AS pest_type"]
    select_cols.extend(config.fields)
    select_cols.append("report_time")
    select_str = ", ".join(select_cols)

    with sqlite3.connect(config.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(f"SELECT {select_str} FROM {config.table} ORDER BY {safe_order}")
        return [dict(row) for row in cursor.fetchall()]


# ── 入口 ────────────────────────────────────────────────────

if __name__ == "__main__":
    for pt in PEST_DB_CONFIGS:
        db_path = init_pest_db(pt)
        print(f"✅ {pt}: 已初始化 {db_path}")
