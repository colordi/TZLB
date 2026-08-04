"""美国白蛾寄主分布聚合（纯 Python，可无库单测）。

输入为 sql_host.WHITE_MOTH_HOST_RAW_SQL 返回的原始行
（code / host_raw / plants / locality），此处负责树种名归一化、
按树种聚合点位（去重）与株数、host×locality 矩阵、Top N + 其他合并。
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

# 榜外树种合并为该桶
OTHER_HOST_NAME = "其他"

# 寄主构成榜保留的树种数，其余并入「其他」
TOP_HOST_LIMIT = 12

# 去尾部「树」之外的显式别名映射（去「树」规则无法覆盖的写法）
_HOST_ALIASES: dict[str, str] = {
    "柿子": "柿",
    "红叶李": "紫叶李",
    "君迁": "君迁子",
}


def normalize_host_name(raw: Any) -> str:
    """归一化树种名：去空白 → 显式别名 → 去尾部「树」。空值返回空串。"""
    name = str(raw or "").strip()
    if not name:
        return ""
    if name in _HOST_ALIASES:
        return _HOST_ALIASES[name]
    if len(name) > 1 and name.endswith("树"):
        name = name[: -len("树")]
    return _HOST_ALIASES.get(name, name)


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def aggregate_host_summary(
    rows: Iterable[Mapping[str, Any]],
    *,
    top_limit: int = TOP_HOST_LIMIT,
) -> dict[str, Any]:
    """聚合原始寄主行为前端寄主分布负载。

    返回：
      hosts: 按受害株数降序的寄主榜（Top N + 其他），每项含
             host / points（点位去重）/ plants / share（株数占比）/ localities
      totals: 寄主树种数（不含「其他」）、受害株总数、受害点位总数、优势寄主
    """
    host_points: dict[str, set[str]] = {}
    host_plants: dict[str, int] = {}
    host_locality_plants: dict[str, dict[str, int]] = {}
    all_points: set[str] = set()

    for row in rows:
        host = normalize_host_name(row.get("host_raw"))
        if not host:
            continue
        plants = max(_to_int(row.get("plants")), 0)
        code = str(row.get("code") or "").strip()
        locality = str(row.get("locality") or "").strip() or "其他单位"

        host_plants[host] = host_plants.get(host, 0) + plants
        if code:
            host_points.setdefault(host, set()).add(code)
            all_points.add(code)
        if plants:
            locality_plants = host_locality_plants.setdefault(host, {})
            locality_plants[locality] = locality_plants.get(locality, 0) + plants

    total_plants = sum(host_plants.values())
    ranked = sorted(
        host_plants,
        key=lambda host: (-host_plants[host], host),
    )

    def build_item(host: str) -> dict[str, Any]:
        plants = host_plants.get(host, 0)
        localities = [
            {"locality": locality, "plants": plants}
            for locality, plants in sorted(
                host_locality_plants.get(host, {}).items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]
        return {
            "host": host,
            "points": len(host_points.get(host, set())),
            "plants": plants,
            "share": (plants / total_plants) if total_plants else 0,
            "localities": localities,
        }

    top_hosts = ranked[:top_limit]
    rest_hosts = ranked[top_limit:]

    hosts = [build_item(host) for host in top_hosts]
    if rest_hosts:
        other_plants = sum(host_plants[host] for host in rest_hosts)
        other_points: set[str] = set()
        other_locality_plants: dict[str, int] = {}
        for host in rest_hosts:
            other_points |= host_points.get(host, set())
            for locality, plants in host_locality_plants.get(host, {}).items():
                other_locality_plants[locality] = other_locality_plants.get(locality, 0) + plants
        hosts.append(
            {
                "host": OTHER_HOST_NAME,
                "points": len(other_points),
                "plants": other_plants,
                "share": (other_plants / total_plants) if total_plants else 0,
                "localities": [
                    {"locality": locality, "plants": plants}
                    for locality, plants in sorted(
                        other_locality_plants.items(),
                        key=lambda item: (-item[1], item[0]),
                    )
                ],
                "merged_hosts": len(rest_hosts),
            }
        )

    top_host = None
    if top_hosts:
        top_host = {
            "host": top_hosts[0],
            "plants": host_plants[top_hosts[0]],
            "points": len(host_points.get(top_hosts[0], set())),
            "share": (host_plants[top_hosts[0]] / total_plants) if total_plants else 0,
        }

    return {
        "totals": {
            "host_species": len(ranked),
            "damaged_plants": total_plants,
            "damaged_points": len(all_points),
            "top_host": top_host,
        },
        "hosts": hosts,
    }
