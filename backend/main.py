from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from backend.auth.dependencies import require_authenticated_user, require_user_role
from backend.auth.store import USER_ROLE_ADMIN, ensure_auth_storage
from backend.config import get_settings
from backend.db.postgres import close_pool
from backend.routers import auth as auth_router
from backend.routers import map as map_router
from backend.routers import survey as survey_router
from backend.routers import workorder as workorder_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    await ensure_auth_storage()
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

app.include_router(auth_router.router, prefix="/api/auth", tags=["认证"])
app.include_router(
    workorder_router.router,
    prefix="/api/workorder",
    tags=["工作单"],
    dependencies=[Depends(require_user_role(USER_ROLE_ADMIN))],
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
    dependencies=[Depends(require_user_role(USER_ROLE_ADMIN))],
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
