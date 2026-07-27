## 项目概览

林业调查工作台是一个前后端分离的 Web 应用，用于林业有害生物调查、防治工单整理和点位监测。

- 后端：`backend/` 目录，FastAPI + asyncpg + Pydantic Settings

- 前端：`frontend/` 目录，Vue 3 + Vue Router + Vite + Vitest + Leaflet + Tailwind CSS v4 + shadcn-vue（forestry light 主题，设计规范见 `docs/specs/frontend-design-system.md`）

- 数据库：本机 PostgreSQL/PostGIS，连接串由 `.env` 中的 `DATABASE_URL` 指定

- 文档转换：LibreOffice CLI（默认 `soffice`），用于将 `.docx` 转为 `.doc`

- 模板：`templates/` 目录下的 Word 工作单模板

## 核心要求
- 在前端代码修改完成后，一定要再次使用`npm run build`进行构建。 

## 常用命令

所有命令默认在仓库根目录执行。项目使用 Python 虚拟环境 `.venv` 和 `frontend/node_modules`。

### 安装依赖

```bash
# 后端
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 开发服务

```bash
# 后端开发服（热重载）
uvicorn backend.main:app --reload --port 8000

# 前端开发服
# 监听 0.0.0.0:5173，并将 /api 代理到 http://127.0.0.1:8000
cd frontend
npm run dev
```

### 测试

```bash
# 后端全部测试
python -m unittest discover backend/tests

# 后端单个测试文件
python -m unittest backend.tests.test_auth_security

# 后端单个测试用例
python -m unittest backend.tests.test_auth_security.TestPasswordHashing.test_verify_password

# 前端全部测试
cd frontend
npm test

# 前端单个测试文件
npx vitest run src/api/__tests__/auth.spec.js

# 前端单个测试用例
npx vitest run -t "should login"
```

### 构建

```bash
# 前端生产构建，输出到 frontend/dist
cd frontend
npm run build

# 构建后由 FastAPI 直接托管 frontend/dist
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## 架构与约定

### 前端 UI 约定

- 现行设计规范：`docs/specs/frontend-design-system.md`（色彩 token、布局、组件唯一实现、地图域规范），修改前端 UI 前必读。
- 主题 token 在 `frontend/src/styles/themes/forestry-light.css`；业务代码禁止裸 hex/rgb 与 Tailwind 调色板直色，一律用语义 token。
- 组件唯一来源：`@/components/ui/*`（shadcn-vue）+ `@/components/common/*`（PageHeader、EmptyState、ConfirmDialog）；弹窗用 ui/dialog、确认用 ui/alert-dialog，toast 用 `useToast()`（vue-sonner）。
- Leaflet 运行时色值的唯一来源是 `frontend/src/config/map-palette.js`（危害程度等行业色值锁定，见规范 §2.5）。

### 后端结构

- `backend/main.py`：FastAPI 应用入口。注册所有 router、配置 CORS、异常处理、请求日志中间件，以及托管前端静态资源的路由。

- `backend/routers/`：API 路由，统一以 `/api` 为前缀。

- `backend/services/`：业务逻辑，如工单生成、调查导入、数据统计、Excel 导入等。

- `backend/db/postgres.py`：asyncpg 连接池管理。

- `backend/auth/`：基于 Cookie 的会话认证，包含密码哈希、令牌解析、依赖注入。

- `backend/config.py`：Pydantic Settings 配置，生产环境会在启动时校验安全配置。

- `backend/schemas.py`：Pydantic 请求/响应模型。

- `backend/tests/`：unittest 测试。

### 认证与授权

- 后端维护 `app_auth.users` 表，启动时自动建表并写入默认管理员。

- 会话通过 Cookie（默认名 `tzlb_session`）传递，使用 `AUTH_SECRET_KEY` 签名。

- 角色有两种：`admin` 和 `investigator`。`admin` 可访问所有功能；`investigator` 只能访问地图点位。

- 本地开发可设置 `AUTH_BYPASS_LOCALHOST=true`，并在请求头中携带 `x-tzlb-local-auth-bypass: 1` 跳过登录。生产环境必须关闭该选项。

- 生产环境（`APP_ENV=production`）会强制要求修改默认 `AUTH_SECRET_KEY`、默认管理员密码，并启用 `AUTH_COOKIE_SECURE`、禁用 `AUTH_BYPASS_LOCALHOST`。

### 路由权限映射

在 `backend/main.py` 中，router 通过 `Depends` 注册：

- `/api/auth`：公开

- `/api/health`：公开

- `/api/map`：需要登录

- `/api/workorder`、`/api/survey`、`/api/data-export`、`/api/statistics`、`/api/data-manager`：需要 `admin`

前端路由守卫在 `frontend/src/router/index.js` 中实现，权限逻辑在 `frontend/src/auth/permissions.js` 中。

### 工单生成

- 害虫类型注册在 `backend/services/pest_registry.py` 中，每种害虫包含：字段配置、必填字段、任务模板（`task_template`）、世代列表（`generations`）、统防统治类型、模板文件名、默认值和图片策略。年份和世代作为运行时参数，由 `build_task(entry, year, generation)` 渲染任务名。

- 当前支持：`春尺蠖`、`国槐尺蠖`、`美国白蛾`、`其他害虫`。

- 图片策略有两种：

  - `uploaded_images`：直接使用前端上传的图片。

  - `auto_disk_images`（历史名 `white_moth_auto_images`）：按点位编号从对应 `points/*点位截图/` 和 `images/{调查日期}/` 自动装配图片（美国白蛾、其他害虫）。

- 生成流程：`backend/services/docgen.py` 使用 `docxtpl` 渲染 `templates/林业有害生物防治工作单模板.docx`，生成 `.docx`，再通过 LibreOffice 转换为 `.doc`。

- 前端在 `frontend/src/views/WorkOrderView.vue` 中逐条调用 `POST /api/workorder/generate`，分别下载文件。

### 地图点位

- `backend/routers/map.py` 自动枚举 `views` schema 下所有包含 `geom` 字段的视图。

- 后端将几何统一转换为 WGS84 GeoJSON 返回。

- 前端 `frontend/src/components/map/LeafletMap.vue` 使用 Leaflet 渲染点位、边界和筛选器。

- 地图弹窗字段来自视图除 `geom` 外的所有字段；筛选器根据字段名自动推断，如 `属地`、`调查日期`、`年份`、`世代`、`危害程度` 等。

- 行政区边界来自 `reference."通州区行政区边界"`。

### 数据库依赖

应用运行依赖以下核心 schema 和对象（详见 README.md）：

- `app_auth.users`：认证用户表

- `app_admin.data_change_logs`：数据管理模块的变更审计日志，后端启动时自动建表

- `survey.*`：调查表（春尺蠖、国槐尺蠖、美国白蛾、其他害虫），均含 `年份` 列；美国白蛾和国槐尺蠖含 `世代` 列

- `ledger.*`：问题点位事件流水和台账（美国白蛾、国槐尺蠖、春尺蠖、其他害虫），均含 `年份` 列

- `sites.*`：监测点位基础表；`杨树点位基础表` 含 `当前点位状态` 字段（可调查/不可调查/伐除）

- `reference.*`：行政区、小区、村庄边界等

- `views.*`：地图展示视图，必须包含 `geom`

### 新增害虫类型

新增害虫类型需要同步修改以下位置：

- `backend/services/pest_registry.py`：注册害虫配置

- `backend/schemas.py`：如字段校验需要调整

- `backend/db/postgres.py`：调查导入 SQL

- `backend/services/docgen.py`：Word 上下文字段

- `frontend/src/components/workorder/fieldConfig.js`：前端字段配置

- `templates/`：如需独立模板

### 配置说明

环境变量通过 `.env` 管理，参考 `.env.example`。关键配置：

- `DATABASE_URL`：PostgreSQL/PostGIS 连接串

- `AUTH_SECRET_KEY`：会话签名密钥

- `AUTH_COOKIE_SECURE`：HTTPS 部署时启用

- `AUTH_BYPASS_LOCALHOST`：本地免登

- `LIBREOFFICE_BIN`：LibreOffice 可执行文件路径

- `WORKORDER_DEFAULT_OUTPUT_FORMAT`：`doc` 或 `docx`

- `WORKORDER_IMAGE_MAX_BYTES`、`WORKORDER_IMAGE_MAX_TOTAL_BYTES`、`WORKORDER_IMAGE_MAX_DIMENSION`：图片大小与压缩限制

