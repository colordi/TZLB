"""
国槐尺蠖上报单 SQLite 数据库初始化脚本

说明：
- 本脚本仅负责创建数据库文件与表结构，不包含任何 Web/API 逻辑。
- 默认数据库位置：data/guohuaichihuo_reports.sqlite3
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "guohuaichihuo_reports.sqlite3"


def init_guohuaichihuo_reports_db(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    """初始化国槐尺蠖上报单数据库（创建库文件、建表、索引）。

    Args:
        db_path: SQLite 数据库文件路径（可传字符串或 Path）。

    Returns:
        实际使用的数据库路径（Path）。
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS guohuaichihuo_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                survey_date TEXT NOT NULL,
                region TEXT,
                town_or_street TEXT,
                location_id TEXT NOT NULL,
                location_name TEXT,
                occurrence_position TEXT,
                total_insect_count INTEGER,
                damage_level TEXT,
                report_time TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                description TEXT,
                UNIQUE(survey_date, location_id)
            );

            CREATE INDEX IF NOT EXISTS idx_guohuaichihuo_reports_report_time
            ON guohuaichihuo_reports(report_time);
            """
        )

    return db_path


def insert_guohuaichihuo_record(
    record: dict,
    db_path: str | Path = DEFAULT_DB_PATH,
    replace_on_conflict: bool = True
) -> tuple[bool, str]:
    """插入单条国槐尺蠖调查记录到数据库。

    Args:
        record: 记录字典，必须包含 survey_date 和 location_id
        db_path: 数据库路径
        replace_on_conflict: 如果遇到重复记录（相同的 survey_date + location_id），
                            True=替换旧记录，False=跳过插入

    Returns:
        (成功标志, 消息)
    """
    db_path = Path(db_path)

    if not record.get("survey_date") or not record.get("location_id"):
        return False, "缺少必填字段：survey_date 或 location_id"

    insert_mode = "INSERT OR REPLACE" if replace_on_conflict else "INSERT OR IGNORE"

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                {insert_mode} INTO guohuaichihuo_reports (
                    survey_date, region, town_or_street, location_id,
                    location_name, occurrence_position,
                    total_insect_count, damage_level, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.get("survey_date"),
                    record.get("region", ""),
                    record.get("town_or_street", ""),
                    record.get("location_id"),
                    record.get("location_name", ""),
                    record.get("occurrence_position", ""),
                    record.get("total_insect_count"),
                    record.get("damage_level", ""),
                    record.get("description", "")
                )
            )
            conn.commit()

            if cursor.rowcount > 0:
                return True, "记录已保存"
            return False, "记录已存在（未更新）"

    except sqlite3.Error as e:
        return False, f"数据库错误: {str(e)}"


def insert_guohuaichihuo_records_batch(
    records: list[dict],
    db_path: str | Path = DEFAULT_DB_PATH,
    replace_on_conflict: bool = True
) -> tuple[int, int, list[str]]:
    """批量插入国槐尺蠖调查记录。

    Args:
        records: 记录列表
        db_path: 数据库路径
        replace_on_conflict: 遇到重复记录时是否替换

    Returns:
        (成功数量, 失败数量, 错误消息列表)
    """
    success_count = 0
    fail_count = 0
    errors = []

    for idx, record in enumerate(records):
        success, msg = insert_guohuaichihuo_record(record, db_path, replace_on_conflict)
        if success:
            success_count += 1
        else:
            fail_count += 1
            errors.append(f"第 {idx + 1} 条记录: {msg}")

    return success_count, fail_count, errors


def fetch_guohuaichihuo_records(
    db_path: str | Path = DEFAULT_DB_PATH,
    order_by: str = "report_time DESC"
) -> list[dict]:
    """获取国槐尺蠖数据库记录（用于可视化展示）。

    Args:
        db_path: 数据库路径
        order_by: 排序字段（SQL 片段）

    Returns:
        记录列表（字典）
    """
    db_path = Path(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT
                '国槐尺蠖' AS pest_type,
                survey_date,
                region,
                town_or_street,
                location_id,
                location_name,
                occurrence_position,
                total_insect_count,
                damage_level,
                report_time,
                description
            FROM guohuaichihuo_reports
            ORDER BY {order_by}
            """
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def main() -> None:
    db_path = init_guohuaichihuo_reports_db()
    print(f"✅ 已初始化数据库: {db_path}")


if __name__ == "__main__":
    main()
