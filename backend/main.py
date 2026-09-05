from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from backend.auth.dependencies import require_authenticated_user, require_user_role
from backend.auth.store import (
    USER_ROLE_ADMIN,
    USER_ROLE_INVESTIGATOR,
    ensure_auth_storage,
)
from backend.config import get_settings
from backend.db.admin import ensure_operation_log_storage
from backend.db.app_settings import ensure_app_settings_storage
from backend.db.data_manager import ensure_data_change_log_storage
from backend.db.postgres import close_pool
from backend.exceptions import (
    BusinessError,
    ConfigurationError,
    build_error_response,
)
from backend.logging_config import configure_logging, get_logger
from backend.routers import auth as auth_router
from backend.routers import admin as admin_router
from backend.routers import data_export as data_export_router
from backend.routers import data_manager as data_manager_router
from backend.routers import map as map_router
from backend.routers import point_screenshot as point_screenshot_router
from backend.routers import statistics as statistics_router
from backend.routers import survey as survey_router
from backend.routers import workorder as workorder_router
from backend.services import storage_config as storage_config_service


logger = get_logger(__name__)
REQUEST_ID_HEADER = "x-request-id"


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    await ensure_auth_storage()
    await ensure_operation_log_storage()
    await ensure_data_change_log_storage()
    await ensure_app_settings_storage()
    await storage_config_service.refresh_storage_config_override()
    yield
    await close_pool()


settings = get_settings()
app = FastAPI(
    title="林业调查工作单助手",
    description="工作单批量生成与 PostGIS 地图监测 API",
    version="2026.03.21",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """为每个请求生成 request_id，记录请求耗时并写入响应头。"""

    request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:16]
    request.state.request_id = request_id

    path = request.url.path
    method = request.method
    start_time = time.perf_counter()

    logger.info("请求开始 %s %s", method, path, extra={"request_id": request_id})

    try:
        response = await call_next(request)
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "请求异常 %s %s: %s",
            method,
            path,
            exc,
            extra={"request_id": request_id},
        )
        response = JSONResponse(
            status_code=500,
            content=build_error_response("服务内部错误，请联系管理员", request_id),
        )

    duration_ms = (time.perf_counter() - start_time) * 1000
    response.headers[REQUEST_ID_HEADER] = request_id
    logger.info(
        "请求完成 %s %s status=%s duration_ms=%.2f",
        method,
        path,
        response.status_code,
        duration_ms,
        extra={"request_id": request_id},
    )
    return response


@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.warning("业务异常: %s", exc, extra={"request_id": request_id})
    return JSONResponse(
        status_code=400,
        content=build_error_response(str(exc), request_id),
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.warning("参数校验失败: %s", exc, extra={"request_id": request_id})
    return JSONResponse(
        status_code=400,
        content=build_error_response(str(exc), request_id),
    )


@app.exception_handler(ConfigurationError)
async def configuration_error_handler(request: Request, exc: ConfigurationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.error("配置或服务资源异常: %s", exc, extra={"request_id": request_id})
    return JSONResponse(
        status_code=500,
        content=build_error_response(str(exc), request_id),
    )


@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.error("服务内部资源缺失: %s", exc, extra={"request_id": request_id})
    return JSONResponse(
        status_code=500,
        content=build_error_response("服务内部资源缺失，请联系管理员", request_id),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    if exc.status_code >= 500:
        logger.error("HTTP 异常 %s: %s", exc.status_code, exc.detail, extra={"request_id": request_id})
    else:
        logger.warning("HTTP 异常 %s: %s", exc.status_code, exc.detail, extra={"request_id": request_id})
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_response(exc.detail, request_id),
        headers=getattr(exc, "headers", None) or {},
    )


@app.exception_handler(Exception)
async def catchall_exception_handler(request: Request, exc: Exception) -> JSONResponse:  # noqa: BLE001
    request_id = getattr(request.state, "request_id", None)
    logger.exception("未捕获异常: %s", exc, extra={"request_id": request_id})
    return JSONResponse(
        status_code=500,
        content=build_error_response("服务内部错误，请联系管理员", request_id),
    )


app.include_router(auth_router.router, prefix="/api/auth", tags=["认证"])
app.include_router(
    workorder_router.router,
    prefix="/api/workorder",
    tags=["工作单"],
)
app.include_router(
    point_screenshot_router.router,
    prefix="/api/point-screenshots",
    tags=["点位截图"],
    dependencies=[Depends(require_user_role(USER_ROLE_ADMIN, USER_ROLE_INVESTIGATOR))],
)
app.include_router(
    map_router.router,
    prefix="/api/map",
    tags=["地图"],
    dependencies=[Depends(require_authenticated_user)],
)
app.include_router(
    survey_router.router,
    prefix="/api/survey",
    tags=["调查导入"],
)
app.include_router(
    data_export_router.router,
    prefix="/api/data-export",
    tags=["数据导出"],
    dependencies=[Depends(require_user_role(USER_ROLE_ADMIN, USER_ROLE_INVESTIGATOR))],
)
app.include_router(
    admin_router.router,
    prefix="/api/admin",
    tags=["管理后台"],
    dependencies=[Depends(require_user_role(USER_ROLE_ADMIN))],
)
app.include_router(
    data_manager_router.router,
    prefix="/api/data-manager",
    tags=["数据管理"],
    dependencies=[Depends(require_user_role(USER_ROLE_ADMIN, USER_ROLE_INVESTIGATOR))],
)
app.include_router(
    statistics_router.router,
    prefix="/api/statistics",
    tags=["数据统计"],
    dependencies=[Depends(require_user_role(USER_ROLE_ADMIN, USER_ROLE_INVESTIGATOR))],
)


@app.get("/api/health", summary="服务健康检查")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


def resolve_frontend_asset(requested_path: str) -> Path | None:
    dist_dir = settings.frontend_dist_dir
    if not dist_dir.exists():
        return None

    normalized_path = requested_path.strip("/") or "index.html"
    candidate = (dist_dir / normalized_path).resolve()
    if dist_dir.resolve() not in candidate.parents and candidate != dist_dir.resolve():
        raise HTTPException(status_code=404, detail="非法路径")
    if candidate.exists() and candidate.is_file():
        return candidate
    return dist_dir / "index.html"


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="接口不存在")
    asset = resolve_frontend_asset(full_path)
    if asset is None:
        return HTMLResponse(
            """
            <html lang="zh-CN">
              <head><meta charset="utf-8"><title>前端尚未构建</title></head>
              <body style="font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; padding: 32px;">
                <h1>前端静态资源尚未构建</h1>
                <p>开发环境请运行 <code>cd frontend && npm run dev</code>。</p>
                <p>生产环境请先执行 <code>npm run build</code>，再由 FastAPI 托管静态资源。</p>
              </body>
            </html>
            """
        )
    return FileResponse(asset)
