# 林业调查工作单助手 — 重构设计文档

**日期：** 2026-03-21
**状态：** 已确认，待实施

---

## Context

当前项目是一个基于 Flask + Vanilla JS + SQLite 的桌面端应用（PyInstaller 打包），代码结构混乱：单文件模板超过 1000 行、AI 解析与数据录入耦合、样式文件近 2000 行无模块化。随着需求演进（接入本地 PostgreSQL/PostGIS 数据、切换至 Web 部署），现有架构已无法支撑。

**重构目标：**
1. 移除 AI 解析功能，释放相关 UI 空间
2. 以两大核心功能为中心重建项目结构：**工作单批量生成** 和 **PostGIS 地图监测**
3. 切换至 FastAPI + Vue 3 前后端分离架构，部署为 Web 服务

---

## 技术栈

| 层级 | 选型 |
|------|------|
| 后端框架 | FastAPI (Python) + asyncpg |
| 前端框架 | Vue 3 + Vite |
| 数据库 | PostgreSQL (`forestry_survey`) via asyncpg，不再使用 SQLite |
| 地图库 | Leaflet.js（Vue 组件封装） |
| 文档生成 | docxtpl（保留现有 Word 模板） |
| 部署 | Web 服务器（Vite build → FastAPI StaticFiles 挂载） |

---

## 项目目录结构

```
TZLB/
├── backend/
│   ├── main.py                  # FastAPI 入口，挂载路由 + StaticFiles
│   ├── routers/
│   │   ├── workorder.py         # POST /api/workorder/generate
│   │   └── map.py               # GET /api/map/views, /api/map/views/{name}
│   ├── services/
│   │   └── docgen.py            # Word 生成逻辑（迁移自 app.py:593-725）
│   ├── db/
│   │   └── postgres.py          # asyncpg 连接池，查询工具
│   ├── schemas.py               # Pydantic 请求/响应模型
│   └── config.py                # Settings（从 .env 读取 DATABASE_URL）
│
├── frontend/
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue              # 顶部导航 + <router-view>
│   │   ├── router/index.js      # /workorder → WorkOrderView，/map → MapView
│   │   ├── views/
│   │   │   ├── WorkOrderView.vue
│   │   │   └── MapView.vue
│   │   ├── components/
│   │   │   ├── workorder/
│   │   │   │   ├── PestSelector.vue   # 害虫类型 + 调查类型下拉
│   │   │   │   ├── RecordForm.vue     # 单条记录表单（字段按 pest_type 切换）
│   │   │   │   └── RecordTable.vue    # 多条记录列表 + Excel 粘贴
│   │   │   └── map/
│   │   │       ├── LeafletMap.vue     # Leaflet 容器，渲染 GeoJSON 点位
│   │   │       └── MapLegend.vue      # 颜色图例 + 图层开关
│   │   └── api/
│   │       ├── workorder.js     # fetch POST /api/workorder/generate
│   │       └── map.js           # fetch GET /api/map/views[/{name}]
│   └── vite.config.js           # 开发时 /api → localhost:8000 代理
│
├── templates/                   # Word 模板（三个 .docx，保留不动）
├── requirements.txt             # fastapi, uvicorn, asyncpg, docxtpl, python-docx
└── .env                         # DATABASE_URL=postgresql://yandi@localhost:5432/forestry_survey
```

**删除的文件：**
- `ai_parser.py`、`config.py`（旧 AI 配置）
- `launcher.py`、`runtime_paths.py`、`tzlb.spec`（PyInstaller 相关）
- `pest_db.py`（SQLite 数据层）
- `data/`（本地 GeoJSON，未来由 PostGIS 提供）
- `static/style.css`（由 Vue 组件样式替代）
- `templates/index.html`、`records.html`、`map_test.html`（Jinja2 模板）

---

## API 设计

### 工作单生成

```
POST /api/workorder/generate

请求体：
{
  "pest_type": "春尺蠖" | "国槐尺蠖" | "其他害虫",
  "task_type": "普查" | "防治" | "应急防治",
  "records": [
    {
      "survey_date": "2026-03-21",
      "town_or_street": "张家湾镇",
      "location_id": "ZW0026",
      "location_name": "张湾村",
      "occurrence_position": "道路绿化带",
      "total_insect_count": 15,       // 尺蠖类专有
      "damage_level": "轻",            // 尺蠖类专有
      "pest_name": "美国白蛾",         // 其他害虫专有
      "host_plant": "杨树",            // 其他害虫专有
      "description": "...",
      "images": ["base64..."]          // 可选，最多 4 张
    }
  ]
}

响应：
- 单条记录 → Content-Type: application/vnd.openxmlformats (.docx)
- 多条记录 → Content-Type: application/zip
```

逻辑来源：`app.py:593-725`（`_render_single_doc` + `_build_file_response`）

### 地图数据

```
GET /api/map/views
响应：[{ "name": "2026_春尺蠖成虫调查", "columns": ["编号","乡镇","村","调查日期","总虫口数"] }, ...]
查询 information_schema 动态发现 views schema 下所有视图

GET /api/map/views/{view_name}
响应：标准 GeoJSON FeatureCollection
SQL：
  SELECT ST_AsGeoJSON(ST_Transform(geom, 4326)) AS geom,
         编号, 乡镇, 村, 调查日期, 总虫口数
  FROM views."{view_name}"
支持可选 query param 过滤：?乡镇=张家湾镇
安全：view_name 须与 GET /api/map/views 返回的白名单比对，拒绝不存在的视图名
```

---

## 前端组件设计

### WorkOrderView 数据流

```
PestSelector（pest_type, task_type）
    ↓ prop 传入
RecordTable
    ├── RecordForm × N（字段按 pest_type 显示/隐藏）
    └── [🚀 批量生成工作单] → POST /api/workorder/generate → 触发浏览器下载
```

- `RecordForm` 接收 `pest_type` prop，v-if 控制字段显隐，替代现有 ~200 行条件 JS
- Excel 粘贴批量填入逻辑迁移自 `records.html`
- 图片上传：Base64 编码后随表单提交，后端写临时文件 → InlineImage → 清理

### MapView 数据流

```
挂载时 GET /api/map/views → 填充视图选择器
    ↓
选择视图 → GET /api/map/views/{name} → GeoJSON
    ↓
LeafletMap.vue
  ├── L.geoJSON() 渲染点位
  ├── pointToLayer：按 总虫口数 分级配色
  │     0 → 灰  |  1-10 → 浅绿  |  11-50 → 橙  |  50+ → 红
  └── onEachFeature：Popup 显示编号、乡镇、村、日期、虫口数
```

---

## 开发 & 部署

### 开发模式

```
# 后端
uvicorn backend.main:app --reload --port 8000

# 前端（另开终端）
cd frontend && npm run dev   # :5173，/api 请求代理至 :8000
```

### 生产部署

```
cd frontend && npm run build     # 输出到 frontend/dist/
uvicorn backend.main:app         # FastAPI 挂载 dist/ 作为 StaticFiles
```

---

## 迁移对照表

| 现有代码 | 迁移至 | 说明 |
|---------|--------|------|
| `app.py:593-725` | `backend/services/docgen.py` | Word 生成逻辑，完整迁移 |
| `app.py:447-471` | `backend/routers/workorder.py` | 路由逻辑重写为 FastAPI |
| `app.py:346-445` | `backend/routers/map.py` | 地图路由，替换为 PG 查询 |
| `pest_db.py` | 删除 | SQLite 不再需要 |
| `app.py:136-174` | 删除 | 坐标转换交给 PostGIS |
| `templates/*.docx` | `templates/*.docx` | 原样保留 |

---

## 验证方式

1. **后端启动**：`uvicorn backend.main:app --reload`，访问 `http://localhost:8000/docs` 确认 OpenAPI 文档正常
2. **工作单生成**：在前端填入 2-3 条记录，点击生成，确认下载 .zip 文件，打开 Word 文档内容正确
3. **地图加载**：切换到地图页，确认视图选择器显示 `2026_春尺蠖成虫调查`，地图点位按虫口数正确着色
4. **视图动态发现**：在 PG 中新建一个测试视图，刷新页面后选择器自动出现新视图
5. **前端构建**：`npm run build` 无报错，FastAPI 生产模式下前端页面正常加载
