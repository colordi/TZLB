# 林业调查工作单助手

林业调查工作单助手是一个面向林业调查与防治业务的 Web 工具，提供调查导入后的工作单生成和地图点位监测两类核心能力。项目采用 FastAPI + Vue 3 + Leaflet 的前后端分离架构，后端负责工作单生成、地图视图查询和静态资源托管，前端负责调查导入、记录整理和地图展示。

## 功能概览

- 工作单整理与生成：通过调查数据导入记录，补充现场图片并逐条生成 Word 工作单。
- 地图点位展示：支持按地图视图、乡镇和调查状态筛选点位，并展示行政区边界与图例。
- 单页访问：前端构建后由 FastAPI 统一托管静态资源，便于部署。

## 技术栈

- 后端：FastAPI、asyncpg、docxtpl、python-docx、LibreOffice CLI
- 前端：Vue 3、Vue Router、Vite、Leaflet
- 数据库：PostgreSQL / PostGIS
- 文档模板：`templates/` 下的 `.docx` 模板文件，导出时会转换为 `.doc`

## 目录结构

```text
.
├── backend/              # FastAPI 后端
├── frontend/             # Vue 3 前端
├── templates/            # 工作单 Word 模板
├── requirements.txt      # Python 依赖
└── .env.example          # 环境变量示例
```

## 环境要求

- Python 3.10+ 或兼容版本
- Node.js 18+ 或兼容版本
- PostgreSQL 数据库，建议启用 PostGIS

## 快速开始

### 1. 准备后端环境

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，并按实际数据库地址修改：

```bash
DATABASE_URL=postgresql://yandi@localhost:5432/forestry_survey
```

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

### 4. 启动开发服务

后端：

```bash
uvicorn backend.main:app --reload --port 8000
```

前端：

```bash
cd frontend
npm run dev
```

前端开发服务器默认运行在 `http://127.0.0.1:5173`，并会把 `/api` 请求代理到 `http://127.0.0.1:8000`。

## 生产构建

先构建前端，再启动后端：

```bash
cd frontend
npm run build
```

构建完成后，FastAPI 会优先托管 `frontend/dist` 下的静态资源。若未构建前端，访问根路径时会看到提示页。

## 接口说明

### 健康检查

- `GET /api/health`

### 认证相关

- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`

首次启动后端时，会自动创建 `auth.users` 表，并初始化默认管理员账号：

- 用户名：`admin`
- 密码：`Forestry@2026`

建议在部署前通过 `.env` 覆盖以下配置：

- `AUTH_SECRET_KEY`
- `AUTH_DEFAULT_ADMIN_USERNAME`
- `AUTH_DEFAULT_ADMIN_PASSWORD`
- `AUTH_COOKIE_SECURE`

### 工作单生成

- `POST /api/workorder/generate`

请求体主要字段：

- `pest_type`：害虫类型，支持 `春尺蠖`、`国槐尺蠖`、`其他害虫`
- `task_type`：统防统治类型
- `task`：任务名称
- `records`：工作单记录列表，但接口单次只接受 1 条记录，每条记录最多 4 张图片

说明：

- 批量压缩导出已取消。
- 前端会按记录逐条调用接口，并分别导出多个独立的 `.doc` 文件。

生产环境补充要求：

- 服务器需要可执行的 LibreOffice 命令行工具，默认读取 `soffice`
- 如路径不同，可通过 `LIBREOFFICE_BIN` 覆盖
- 如转换耗时较长，可通过 `LIBREOFFICE_TIMEOUT_SECONDS` 调整超时

### 地图相关

- `GET /api/map/views`
- `GET /api/map/views/{view_name}`
- `GET /api/map/views/{view_name}/filter-options`
- `GET /api/map/layers/admin-boundary`

## 数据约定

- 地图视图来自数据库 `views` schema 下的视图。
- 地图视图需要包含 `geom` 字段，后端会自动转换为 GeoJSON。
- 行政区边界来自 `reference.admin_boundary` 表。
- 工作单模板位于 `templates/` 目录，文件名分别对应不同害虫类型。

## 开发提示

- 前端未登录时默认入口是 `/login`，登录后可访问 `/workorder` 和 `/map`。
- 工单页以“导入调查数据”为主要入口，导入后可继续修正字段、删除记录并补充现场图片。
- 地图底图默认使用 OpenStreetMap HOT 图源。
- 如果数据库连接失败，地图接口和工作单导出都会受影响。
- 认证模块会在应用启动时自动确保 `auth.users` 表存在，并写入默认管理员账号（若账号已存在则不会覆盖）。
- 后端静态托管依赖 `frontend/dist`，生产环境务必先执行前端构建。
