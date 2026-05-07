# AGENTS.md

本文件用于约束 Codex 在本项目中的默认工作方式。除非用户另有明确要求，所有回复、
说明、注释和文档均使用简体中文。

## 项目概览

这是一个林业调查工作台项目，采用 FastAPI + Vue 3 + Leaflet 架构。

- 后端位于 `backend/`，负责认证、Supabase PostgreSQL/PostGIS 数据访问、地图接口和工作单生成。
- 前端位于 `frontend/`，负责登录、工单录入、调查导入、地图展示和文件下载。
- 工作单模板位于 `templates/`。
- 数据库默认通过 `DATABASE_URL` 连接 Supabase PostgreSQL，不在前端直接使用 `supabase-js`。

## 常用命令

后端开发：

```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

前端开发：

```bash
cd frontend
npm run dev
```

后端测试：

```bash
python -m unittest discover backend/tests
```

前端测试：

```bash
cd frontend
npm test
```

前端构建：

```bash
cd frontend
npm run build
```

## 数据库与配置

- 环境变量从项目根目录 `.env` 读取，字段参考 `.env.example`。
- 业务数据来自 Supabase/PostGIS，核心 schema 包括 `survey`、`sites`、`views`、`reference`。
- 认证表为 `app_auth.users`，后端启动时会自动确保表结构存在。
- 地图视图来自 `views` schema 下包含 `geom` 字段的视图。
- Word 转换依赖 LibreOffice CLI，默认命令为 `soffice`，可通过 `LIBREOFFICE_BIN` 覆盖。

## 开发约定

- 修改前先阅读相关代码，遵循现有结构和命名风格。
- 不保留无用兼容逻辑；没有明确要求时不添加占位、TODO 或半成品实现。
- 代码注释保持克制，只在关键流程或不易理解的逻辑处使用中文说明。
- 修改认证、数据库、工作单模板、地图数据结构时，同步检查 README 和测试。
- 不要回滚用户已有修改；遇到无关脏文件时保持原样。

## 前端约定

- 前端业务接口统一通过 `frontend/src/api/` 封装。
- 页面级逻辑位于 `frontend/src/views/`，可复用组件位于 `frontend/src/components/`。
- 工单字段配置集中在 `frontend/src/components/workorder/fieldConfig.js`。
- 地图弹窗和点位样式逻辑集中在 `frontend/src/components/map/popupFields.js`。

## 后端约定

- FastAPI 入口为 `backend/main.py`。
- 数据库访问集中在 `backend/db/postgres.py`。
- 路由位于 `backend/routers/`。
- 工作单生成逻辑位于 `backend/services/docgen.py`。
- 认证逻辑位于 `backend/auth/`。

## 验证要求

- 文档类改动至少执行格式或 diff 检查。
- 前端行为改动优先运行相关 Vitest。
- 后端逻辑改动优先运行对应 `unittest`。
- 涉及 Supabase 数据结构或查询时，需要确认对象名、schema、字段和 PostGIS 几何转换逻辑一致。
