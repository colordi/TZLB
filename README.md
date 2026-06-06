# 林业调查工作台

林业调查工作台是面向林业有害生物调查、防治工单整理和点位监测的
Web 应用。项目采用 FastAPI + Vue 3 + Leaflet 的前后端分离架构，后端通过
`DATABASE_URL` 访问本机 PostgreSQL/PostGIS 数据库，前端通过 Cookie 会话访问受保护接口。

## 核心能力

- 调查导入：按调查日期从本机 PostgreSQL/PostGIS 读取春尺蠖、国槐尺蠖、美国白蛾和其他害虫问题点位。
- 工作单生成：导入记录后补充字段与现场图片，逐条生成 Word 工作单。
- 地图监测：自动读取 `views` schema 下带 `geom` 的视图，展示点位、行政区边界和筛选器。
- 登录保护：后端维护 `app_auth.users`，除登录和健康检查外的业务接口均需登录。
- 静态托管：生产构建后由 FastAPI 直接托管 `frontend/dist`。

## 技术栈

- 后端：FastAPI、asyncpg、Pydantic Settings、docxtpl、python-docx
- 前端：Vue 3、Vue Router、Vite、Vitest、Leaflet
- 数据库：PostgreSQL / PostGIS
- 文档转换：LibreOffice CLI，将渲染后的 `.docx` 转为 `.doc`

## 目录说明

```text
.
├── backend/              # FastAPI 应用、路由、认证、数据库访问和工作单生成
├── frontend/             # Vue 3 前端工作台
├── templates/            # 三类害虫对应的 Word 工作单模板
├── points/               # 本地点位截图目录，已被 git 忽略
├── docs/                 # 历史设计说明和补充文档
├── requirements.txt      # Python 依赖
└── .env.example          # 环境变量字段清单
```

## 环境要求

- Python 3.10+
- Node.js 18+
- 本机 PostgreSQL 数据库，需启用 PostGIS，并准备好业务表、视图和边界数据
- LibreOffice CLI，默认命令为 `soffice`

## 快速启动

1. 安装后端依赖：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. 安装前端依赖：

```bash
cd frontend
npm install
```

3. 配置环境变量：

```bash
cp .env.example .env
```

`.env.example` 默认指向本机数据库 `forestry_survey`：

```bash
DATABASE_URL="postgresql://yandi@localhost:5432/forestry_survey"
```

本机密码可通过 `~/.pgpass` 管理。生产部署时将 `DATABASE_URL` 改为对应服务器上的
PostgreSQL/PostGIS 连接串即可。

4. 启动开发服务：

```bash
uvicorn backend.main:app --reload --port 8000
```

```bash
cd frontend
npm run dev
```

前端默认运行在 `http://127.0.0.1:5173`，Vite 会将 `/api` 代理到
`http://127.0.0.1:8000`。

## 生产运行

先构建前端：

```bash
cd frontend
npm run build
```

再启动 FastAPI：

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

构建完成后，FastAPI 会托管 `frontend/dist`。如果没有构建前端，访问根路径会显示
“前端静态资源尚未构建”的提示页。

生产环境务必覆盖以下配置：

- `DATABASE_URL`：PostgreSQL/PostGIS 连接串
- `AUTH_SECRET_KEY`：会话签名密钥
- `AUTH_DEFAULT_ADMIN_USERNAME` / `AUTH_DEFAULT_ADMIN_PASSWORD`：初始管理员账号
- `AUTH_COOKIE_SECURE=true`：HTTPS 部署时启用安全 Cookie
- `LIBREOFFICE_BIN`：服务器上的 LibreOffice 可执行文件路径

## 数据库约定

应用通过 `DATABASE_URL` 直接连接 PostgreSQL/PostGIS。前端不使用 `supabase-js`，
也不依赖 Supabase Data API 暴露业务表。

当前业务数据已迁回本机 `forestry_survey` 数据库，核心 schema 包括：
`app_auth`、`ledger`、`reference`、`sites`、`survey`、`views`。

后端当前依赖这些 schema 和对象：

- `survey."春尺蠖成虫调查表"`：春尺蠖成虫调查表
- `survey."春尺蠖幼虫调查表"`：春尺蠖幼虫调查表
- `survey."春尺蠖围环调查表"`：春尺蠖围环调查表
- `survey."国槐尺蠖幼虫调查表"`：国槐尺蠖幼虫调查表
- `survey."美国白蛾第一代调查表"`：美国白蛾第一代调查表
- `survey."其他害虫调查表"`：其他害虫调查表
- `ledger."2026年美国白蛾第一代问题点位事件流水表"`：美国白蛾第一代问题点位事件流水表
- `ledger."2026年美国白蛾第一代问题点位台账"`：美国白蛾第一代问题点位台账
- `sites."监测点位基础表"`：监测点位基础表
- `sites."杨树点位基础表"`：杨树点位基础表
- `sites."国槐点位基础表"`：国槐点位基础表，要求 `编号` 唯一且 `geom` 不为空
- `sites."其他害虫点位基础表"`：其他害虫点位基础表
- `sites."美国白蛾点位基础表"`：美国白蛾点位基础表
- `views.*`：地图展示视图，必须包含 `geom` 字段
- `views."2026_美国白蛾第 1 代调查"`：将 `reference."通州区小区边界"` 与美国白蛾第一代调查记录关联为地图图层
- `views."国槐尺蠖幼虫历年发生情况"`：将 `sites."国槐点位基础表"` 中的年度发生情况宽字段展开为 `年份`、`发生情况`、`危害程度`
- `reference."通州区行政区边界"`：通州区行政区边界
- `reference."通州区小区边界"`：通州区小区边界
- `reference."通州国槐图层"`：通州国槐图层
- `reference."通州区村庄边界"`：通州区村庄边界
- `app_auth.users`：登录用户表，后端启动时自动创建并写入默认管理员，使用
  `role` 字段区分管理员和调查员

地图接口会自动枚举 `views` schema 下所有带 `geom` 的视图，并将几何统一转换为
WGS84 GeoJSON。除 `views."通州区监测点位分布"` 外，地图视图默认只保留
`编号`、`属地`、`点位名称`、`调查日期`、`危害程度` 等核心展示和筛选字段，避免
弹窗内容臃肿。若视图包含 `属地` 字段，会启用属地筛选；若包含 `调查日期`
字段，会启用“调查 / 未调查”筛选；若包含 `年份`、`危害程度`、`害虫类型`
等字段，会由后端返回动态筛选配置供前端渲染。

## 业务流程

### 登录

首次启动时，后端会确保 `app_auth.users` 存在，并尝试写入默认管理员：

- 用户名：`admin`
- 密码：`Forestry@2026`

默认账号已存在时不会覆盖。正式部署前请在 `.env` 中改掉默认账号、密码和
`AUTH_SECRET_KEY`。

用户角色：

- `admin`：可访问工单录入、调查导入和地图点位。
- `investigator`：仅可访问地图点位；前端不会展示工单录入入口，后端也会拒绝工单和调查导入接口。

### 工单录入

1. 进入 `/workorder`。
2. 选择害虫类型和统防统治任务。
3. 点击“导入调查数据”，按日期从本机数据库查询可导入记录。
4. 导入后在表格中点开记录，补充描述、备注和现场图片。
5. 点击“生成工作单”，前端会逐条调用后端接口并下载多个 `.doc` 文件。

当前支持的害虫类型：

- `春尺蠖`
- `国槐尺蠖`
- `美国白蛾`
- `其他害虫`

每条工作单记录最多上传 4 张图片。春尺蠖、国槐尺蠖和美国白蛾导入时会尝试按点位编号匹配
`points/杨树点位截图`、`points/国槐点位截图` 或 `points/美国白蛾点位截图`
下的本地截图。

美国白蛾生成 Word 工单时会重新按磁盘文件装配图片：第一张优先取
`points/美国白蛾点位截图/{编号}.*`，后续图片从 `images/{调查日期}/`
下所有以 `{编号}` 为文件名前缀的图片中按序补齐，最多使用 4 张。

### 地图点位

进入 `/map` 后，前端会读取可用地图视图、行政区边界和点位数据。点位样式会根据
`危害程度`、`严重程度`、`等级`、`级别` 等字段推断轻中重等级；弹窗内容来自当前视图
除 `geom` 外的字段。

## API 概览

无需登录：

- `GET /api/health`
- `POST /api/auth/login`
- `POST /api/auth/logout`

需要有效会话：

- `GET /api/auth/me`
- `GET /api/map/views`
- `GET /api/map/views/{view_name}`
- `GET /api/map/views/{view_name}/filter-options`
- `GET /api/map/layers/admin-boundary`

需要管理员角色：

- `GET /api/survey/candidates?date=YYYY-MM-DD&pest_type=春尺蠖`
  （`pest_type` 也可为 `国槐尺蠖`、`美国白蛾`、`其他害虫`）
- `POST /api/workorder/generate`

`POST /api/workorder/generate` 只接受单条记录。批量压缩导出已取消，前端会按记录逐条
调用接口并分别下载文件。

## 常用命令

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

## 常见问题

- 数据库连接失败：检查 `DATABASE_URL`、本机 PostgreSQL 服务、`~/.pgpass` 和 5432 端口。
- 地图没有视图：确认 `views` schema 下存在带 `geom` 字段的视图。
- 地图边界为空：确认 `reference."通州区行政区边界"` 存在且 `geom` 不为空。
- 工作单生成失败：确认模板文件存在，并检查 `LIBREOFFICE_BIN` 是否能在服务器执行。
- 本机开发想临时免登：`npm run dev` 在 localhost 下会使用前端本机测试用户，
  避免路由守卫卡在登录页；若要后端业务接口也返回真实数据，仍需设置
  `AUTH_BYPASS_LOCALHOST=true`。该能力只应在本地调试使用。
- 如需在前端开发服测试登录页流程，可设置 `VITE_AUTH_BYPASS_LOCALHOST=false`
  后重新启动前端开发服务。

## 维护提示

- 新增害虫类型时，需要同步更新 `backend/schemas.py`、`backend/db/postgres.py`、
  `backend/services/docgen.py`、`frontend/src/components/workorder/fieldConfig.js` 和模板文件。
- 新增地图视图时，只要放在 `views` schema 且包含 `geom`，前端会自动出现在视图列表中。
- 修改 Word 模板后，注意确保模板占位字段能被 `docgen.py` 提供，否则后端会拒绝生成。
- `docs/superpowers/specs` 是历史设计记录，运行方式以当前代码和本 README 为准。
