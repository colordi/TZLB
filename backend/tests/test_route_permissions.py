from __future__ import annotations

import unittest

from fastapi import HTTPException

from backend.routers import survey as survey_router
from backend.routers import workorder as workorder_router


def make_user(role: str) -> dict:
    return {
        "id": 1 if role == "admin" else 2,
        "username": role,
        "display_name": role,
        "role": role,
        "is_active": True,
    }


def collect_endpoint_dependencies(router, path: str) -> list:
    """收集 router 内指定路径端点上挂载的依赖。"""
    dependencies = []
    for route in router.routes:
        if getattr(route, "path", None) == path:
            dependencies.extend(getattr(route, "dependencies", []) or [])
    return dependencies


def collect_mounted_dependencies(app, prefix: str) -> list:
    """收集 include_router 挂载在指定前缀上的路由级依赖。"""
    dependencies = []
    for route in app.routes:
        route_path = getattr(route, "path", None)
        if isinstance(route_path, str) and route_path.startswith(prefix):
            dependencies.extend(getattr(route, "dependencies", []) or [])
            continue

        include_context = getattr(route, "include_context", None)
        if include_context is None:
            continue
        if getattr(include_context, "prefix", None) != prefix:
            continue
        dependencies.extend(getattr(include_context, "dependencies", []) or [])
    return dependencies


async def assert_dependency_rejects(test_case: unittest.TestCase, dependencies: list, role: str) -> None:
    test_case.assertGreaterEqual(len(dependencies), 1, "端点应挂载角色依赖")
    with test_case.assertRaises(HTTPException) as context:
        await dependencies[0].dependency(make_user(role))
    test_case.assertEqual(context.exception.status_code, 403)


async def assert_dependency_allows(test_case: unittest.TestCase, dependencies: list, role: str) -> None:
    test_case.assertGreaterEqual(len(dependencies), 1, "端点应挂载角色依赖")
    user = make_user(role)
    test_case.assertIs(await dependencies[0].dependency(user), user)


class WorkorderRoutePermissionTest(unittest.IsolatedAsyncioTestCase):
    async def test_generate_endpoints_reject_investigator(self) -> None:
        for path in (
            "/generate",
            "/generate-batch",
            "/generate-batch-jobs",
            "/generate-batch-jobs/{job_id}",
            "/generate-batch-jobs/{job_id}/download",
        ):
            dependencies = collect_endpoint_dependencies(workorder_router.router, path)
            await assert_dependency_rejects(self, dependencies, "investigator")

    async def test_point_date_image_endpoints_allow_investigator(self) -> None:
        for path in (
            "/point-date-images",
            "/point-date-images/{survey_date}/{file_name}",
        ):
            dependencies = collect_endpoint_dependencies(workorder_router.router, path)
            await assert_dependency_allows(self, dependencies, "investigator")
            await assert_dependency_allows(self, dependencies, "admin")


class SurveyRoutePermissionTest(unittest.IsolatedAsyncioTestCase):
    async def test_candidates_allows_investigator(self) -> None:
        dependencies = collect_endpoint_dependencies(survey_router.router, "/candidates")
        await assert_dependency_allows(self, dependencies, "investigator")
        await assert_dependency_allows(self, dependencies, "admin")

    async def test_import_endpoints_reject_investigator(self) -> None:
        for path in ("/excel-import", "/import-template", "/pest-types"):
            dependencies = collect_endpoint_dependencies(survey_router.router, path)
            await assert_dependency_rejects(self, dependencies, "investigator")


class DataRouterPermissionTest(unittest.IsolatedAsyncioTestCase):
    async def test_data_routers_allow_admin_and_investigator(self) -> None:
        from backend.main import app

        for prefix in ("/api/data-export", "/api/data-manager", "/api/statistics"):
            dependencies = collect_mounted_dependencies(app, prefix)
            await assert_dependency_allows(self, dependencies, "investigator")
            await assert_dependency_allows(self, dependencies, "admin")


if __name__ == "__main__":
    unittest.main()
