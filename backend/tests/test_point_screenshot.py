from __future__ import annotations

import io
import struct
import unittest
import zlib
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from PIL import Image

from backend.routers.point_screenshot import (
    delete_point_screenshot as delete_route,
    preview_point_screenshot as preview_route,
)
from backend.services.docgen import find_point_screenshot
from backend.services.point_screenshot_service import (
    delete_point_screenshot,
    list_point_screenshot_status,
    read_point_screenshot,
    save_point_screenshot,
)


class FakeUploadFile:
    def __init__(self, content: bytes, filename: str = "screenshot.png") -> None:
        self.content = content
        self.filename = filename
        self.read_size: int | None = None

    async def read(self, size: int = -1) -> bytes:
        self.read_size = size
        return self.content if size < 0 else self.content[:size]


def build_image_bytes(image_format: str) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), color=(45, 120, 80)).save(buffer, format=image_format)
    return buffer.getvalue()


def build_oversized_pixel_png() -> bytes:
    content = bytearray(build_image_bytes("PNG"))
    content[16:20] = struct.pack(">I", 10_000)
    content[20:24] = struct.pack(">I", 10_000)
    content[29:33] = struct.pack(">I", zlib.crc32(content[12:29]) & 0xFFFFFFFF)
    return bytes(content)


class PointScreenshotTest(unittest.IsolatedAsyncioTestCase):
    async def test_list_status_returns_points_with_screenshot_flag(self) -> None:
        with TemporaryDirectory() as tempdir:
            screenshot_dir = Path(tempdir)
            (screenshot_dir / "YB001.jpg").write_bytes(build_image_bytes("JPEG"))
            points = [
                {"code": "YB001", "name": "张家村东", "locality": "永顺镇"},
                {"code": "YB002", "name": "张家村西", "locality": "永顺镇"},
            ]

            with (
                patch(
                    "backend.services.point_screenshot_service.postgres.fetch_site_points",
                    new=AsyncMock(return_value=points),
                ),
                patch(
                    "backend.services.point_screenshot_service.get_screenshot_dir",
                    return_value=screenshot_dir,
                ),
            ):
                result = await list_point_screenshot_status("春尺蠖")

        self.assertEqual(
            result,
            [
                {
                    "code": "YB001",
                    "name": "张家村东",
                    "locality": "永顺镇",
                    "has_screenshot": True,
                    "screenshot_filename": "YB001.jpg",
                },
                {
                    "code": "YB002",
                    "name": "张家村西",
                    "locality": "永顺镇",
                    "has_screenshot": False,
                    "screenshot_filename": None,
                },
            ],
        )

    async def test_list_status_ignores_screenshot_symlink_outside_directory(self) -> None:
        with TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            screenshot_dir = root / "screenshots"
            screenshot_dir.mkdir()
            outside_image = root / "outside.png"
            outside_image.write_bytes(build_image_bytes("PNG"))
            (screenshot_dir / "YB001.png").symlink_to(outside_image)
            points = [{"code": "YB001", "name": "张家村东", "locality": "永顺镇"}]

            with (
                patch(
                    "backend.services.point_screenshot_service.postgres.fetch_site_points",
                    new=AsyncMock(return_value=points),
                ),
                patch(
                    "backend.services.point_screenshot_service.get_screenshot_dir",
                    return_value=screenshot_dir,
                ),
            ):
                result = await list_point_screenshot_status("春尺蠖")

        self.assertFalse(result[0]["has_screenshot"])
        self.assertIsNone(result[0]["screenshot_filename"])

    async def test_upload_creates_file_named_by_code(self) -> None:
        with TemporaryDirectory() as tempdir:
            screenshot_dir = Path(tempdir) / "screenshots"
            content = build_image_bytes("PNG")
            with patch(
                "backend.services.point_screenshot_service.get_screenshot_dir",
                return_value=screenshot_dir,
            ):
                result = await save_point_screenshot(
                    "春尺蠖",
                    "YB001",
                    FakeUploadFile(content),
                )

            target = screenshot_dir / "YB001.png"
            self.assertTrue(target.is_file())
            self.assertEqual(target.read_bytes(), content)
            self.assertEqual(
                result,
                {"code": "YB001", "filename": "YB001.png", "size": len(content)},
            )

    async def test_upload_replaces_existing_different_extension(self) -> None:
        with TemporaryDirectory() as tempdir:
            screenshot_dir = Path(tempdir)
            old_path = screenshot_dir / "YB001.jpg"
            old_path.write_bytes(build_image_bytes("JPEG"))
            content = build_image_bytes("PNG")

            with patch(
                "backend.services.point_screenshot_service.get_screenshot_dir",
                return_value=screenshot_dir,
            ):
                await save_point_screenshot(
                    "春尺蠖",
                    "YB001",
                    FakeUploadFile(content),
                )

            self.assertFalse(old_path.exists())
            self.assertEqual((screenshot_dir / "YB001.png").read_bytes(), content)
            self.assertEqual(
                find_point_screenshot(screenshot_dir, "YB001"),
                screenshot_dir / "YB001.png",
            )

    async def test_upload_rejects_invalid_code(self) -> None:
        with self.assertRaisesRegex(ValueError, "点位编号"):
            await save_point_screenshot(
                "春尺蠖",
                "../YB001",
                FakeUploadFile(build_image_bytes("PNG")),
            )

    async def test_upload_rejects_unsupported_format(self) -> None:
        with TemporaryDirectory() as tempdir:
            with patch(
                "backend.services.point_screenshot_service.get_screenshot_dir",
                return_value=Path(tempdir),
            ):
                with self.assertRaisesRegex(ValueError, "图片格式不支持"):
                    await save_point_screenshot(
                        "春尺蠖",
                        "YB001",
                        FakeUploadFile(build_image_bytes("GIF"), "screenshot.gif"),
                    )

    async def test_upload_reads_only_size_limit_plus_one_byte(self) -> None:
        upload_file = FakeUploadFile(b"12345")
        settings = SimpleNamespace(workorder_image_max_bytes=4)

        with (
            patch(
                "backend.services.point_screenshot_service.get_screenshot_dir",
                return_value=Path("/tmp/screenshots"),
            ),
            patch(
                "backend.services.point_screenshot_service.get_settings",
                return_value=settings,
            ),
            patch(
                "backend.services.docgen.get_settings",
                return_value=settings,
            ),
        ):
            with self.assertRaisesRegex(ValueError, "超过单图大小限制"):
                await save_point_screenshot("春尺蠖", "YB001", upload_file)

        self.assertEqual(upload_file.read_size, 5)

    async def test_upload_rejects_oversized_pixel_image(self) -> None:
        with TemporaryDirectory() as tempdir:
            with patch(
                "backend.services.point_screenshot_service.get_screenshot_dir",
                return_value=Path(tempdir),
            ):
                with self.assertRaisesRegex(ValueError, "像素尺寸过大"):
                    await save_point_screenshot(
                        "春尺蠖",
                        "YB001",
                        FakeUploadFile(build_oversized_pixel_png()),
                    )

    async def test_delete_removes_file(self) -> None:
        with TemporaryDirectory() as tempdir:
            screenshot_dir = Path(tempdir)
            jpg_path = screenshot_dir / "YB001.jpg"
            png_path = screenshot_dir / "YB001.png"
            jpg_path.write_bytes(build_image_bytes("JPEG"))
            png_path.write_bytes(build_image_bytes("PNG"))

            with patch(
                "backend.services.point_screenshot_service.get_screenshot_dir",
                return_value=screenshot_dir,
            ):
                result = delete_point_screenshot("春尺蠖", "YB001")

            self.assertEqual(result, {"code": "YB001", "deleted": True})
            self.assertFalse(jpg_path.exists())
            self.assertFalse(png_path.exists())

    async def test_delete_nonexistent_returns_404(self) -> None:
        with TemporaryDirectory() as tempdir:
            with patch(
                "backend.services.point_screenshot_service.get_screenshot_dir",
                return_value=Path(tempdir),
            ):
                with self.assertRaises(HTTPException) as context:
                    await delete_route("春尺蠖", "YB404")

        self.assertEqual(context.exception.status_code, 404)
        self.assertIn("未找到点位 YB404 的截图", context.exception.detail)

    async def test_preview_reads_image_with_correct_media_type(self) -> None:
        with TemporaryDirectory() as tempdir:
            screenshot_dir = Path(tempdir)
            content = build_image_bytes("PNG")
            (screenshot_dir / "MQ001.png").write_bytes(content)

            with patch(
                "backend.services.point_screenshot_service.get_screenshot_dir",
                return_value=screenshot_dir,
            ):
                read_content, media_type = read_point_screenshot("美国白蛾", "MQ001")
                response = await preview_route("美国白蛾", "MQ001")

        self.assertEqual(read_content, content)
        self.assertEqual(media_type, "image/png")
        self.assertEqual(response.body, content)
        self.assertEqual(response.headers["content-type"], "image/png")

    async def test_main_routes_require_admin_role(self) -> None:
        from backend.main import app

        expected_paths = {
            "/api/point-screenshots/status",
            "/api/point-screenshots/upload",
            "/api/point-screenshots/",
            "/api/point-screenshots/preview",
        }

        # 路径注册：优先读 OpenAPI（新旧 FastAPI 都稳定）；
        # 权限依赖：兼容 0.139 的 _IncludedRouter 与旧版展开后的 APIRoute。
        openapi_paths = {
            path
            for path in app.openapi().get("paths", {})
            if path.startswith("/api/point-screenshots")
        }
        self.assertEqual(openapi_paths, expected_paths)

        admin_dependencies = []
        for route in app.routes:
            route_path = getattr(route, "path", None)
            if isinstance(route_path, str) and route_path.startswith("/api/point-screenshots"):
                admin_dependencies.extend(getattr(route, "dependencies", []) or [])
                continue

            include_context = getattr(route, "include_context", None)
            if include_context is None:
                continue
            if getattr(include_context, "prefix", None) != "/api/point-screenshots":
                continue
            admin_dependencies.extend(getattr(include_context, "dependencies", []) or [])

        self.assertGreaterEqual(len(admin_dependencies), 1, "点位截图路由应挂载 admin 依赖")

        admin_dependency = admin_dependencies[0].dependency
        with self.assertRaises(HTTPException) as context:
            await admin_dependency(
                {
                    "id": 2,
                    "username": "investigator",
                    "display_name": "调查员",
                    "role": "investigator",
                    "is_active": True,
                }
            )

        self.assertEqual(context.exception.status_code, 403)
        self.assertEqual(context.exception.detail, "当前账号无权访问该功能")


if __name__ == "__main__":
    unittest.main()
