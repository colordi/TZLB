"""把本地点位截图与日期现场图片迁移到 Cloudflare R2。

用法（仓库根目录、激活 .venv）：

    # 只打印迁移计划，不上传
    python -m backend.scripts.migrate_assets_to_r2 --dry-run

    # 正式迁移
    python -m backend.scripts.migrate_assets_to_r2

行为说明：

- 遍历各害虫点位截图目录（pest_registry 配置）与 ``images/{日期}/`` 子目录，
  按与本地一致的相对 key（``R2_PREFIX`` 前缀 + 相对项目根目录路径）上传图片。
- 幂等：R2 上已存在且大小一致的对象跳过，可中断后重复执行。
- 只上传，不删除任何本地文件；本地副本保留为冷备。
- 需要在 .env 中配置 R2_ENDPOINT_URL / R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY /
  R2_BUCKET（ASSET_STORAGE_BACKEND 保持 local 也可以执行本脚本）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from backend.config import get_settings
from backend.services.docgen.images import is_image_file
from backend.services.pest_registry import list_pest_configs
from backend.services.storage import build_r2_storage, derive_key_prefix
from backend.services.storage_config import storage_config_from_settings


def collect_asset_dirs() -> list[Path]:
    """汇总需要迁移的本地目录：各害虫点位截图目录 + images 下的日期子目录。"""

    settings = get_settings()
    dirs: list[Path] = []
    for config in list_pest_configs():
        if not config.screenshot_dir_attr:
            continue
        screenshot_dir = getattr(settings, config.screenshot_dir_attr, None)
        if screenshot_dir is not None:
            dirs.append(Path(screenshot_dir))

    images_dir = Path(settings.images_dir)
    if images_dir.is_dir():
        dirs.extend(path for path in sorted(images_dir.iterdir()) if path.is_dir())
    return dirs


def iter_image_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return [
        path
        for path in sorted(directory.iterdir())
        if path.is_file() and is_image_file(path)
    ]


def ensure_r2_settings() -> None:
    settings = get_settings()
    missing = [
        name
        for name in ("r2_endpoint_url", "r2_access_key_id", "r2_secret_access_key", "r2_bucket")
        if not str(getattr(settings, name, "") or "").strip()
    ]
    if missing:
        env_names = "、".join(name.upper() for name in missing)
        raise SystemExit(f"迁移前请在 .env 中配置：{env_names}")


def migrate_directory(directory: Path, *, dry_run: bool) -> tuple[int, int, int]:
    """迁移单个目录，返回 (上传数, 跳过数, 上传字节数)。"""

    config = storage_config_from_settings(get_settings())
    storage = build_r2_storage(directory, config)
    remote_sizes = {obj.name: obj.size_bytes for obj in storage.list()}

    uploaded = 0
    skipped = 0
    uploaded_bytes = 0
    for path in iter_image_files(directory):
        size = path.stat().st_size
        if remote_sizes.get(path.name) == size:
            skipped += 1
            continue
        if dry_run:
            print(f"  [dry-run] 将上传 {path.name}（{size} 字节）")
        else:
            storage.write(path.name, path.read_bytes())
            print(f"  已上传 {path.name}（{size} 字节）")
        uploaded += 1
        uploaded_bytes += size
    return uploaded, skipped, uploaded_bytes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="把本地工单素材迁移到 Cloudflare R2")
    parser.add_argument("--dry-run", action="store_true", help="只打印迁移计划，不上传")
    args = parser.parse_args(argv)

    ensure_r2_settings()
    dirs = collect_asset_dirs()

    total_uploaded = 0
    total_skipped = 0
    total_bytes = 0
    for directory in dirs:
        files = iter_image_files(directory)
        if not files:
            continue
        prefix = derive_key_prefix(directory)
        print(f"目录 {directory} -> 前缀 {prefix}（本地图片 {len(files)} 个）")
        uploaded, skipped, uploaded_bytes = migrate_directory(directory, dry_run=args.dry_run)
        print(f"  小计：上传 {uploaded}，跳过 {skipped}")
        total_uploaded += uploaded
        total_skipped += skipped
        total_bytes += uploaded_bytes

    action = "待上传" if args.dry_run else "已上传"
    print(
        f"迁移{'计划' if args.dry_run else '完成'}：{action} {total_uploaded} 个文件"
        f"（{total_bytes / 1024 / 1024:.1f} MB），跳过 {total_skipped} 个（远端已存在且大小一致）。"
    )
    print("本地文件均未删除；确认 R2 可用后可择机清理。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
