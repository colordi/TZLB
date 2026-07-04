# Dashboard 管理后台实现方案

> 状态:方案设计稿(待评审)
> 编制日期:2026-07-04
> 适用项目:TZLB 林业调查工作台(FastAPI + Vue3 + Leaflet + PostgreSQL/PostGIS)

---

## 一、背景与现状

### 1.1 项目现状

林业有害生物调查工作台,当前 5 个页面:`/login`、`/workorder`、`/map`、`/data-export`、
`/data-statistics`。**没有任何管理后台、总览看板、用户管理或配置界面。**

关键现状:

- **图层完全自动,无可配入口**
  - 点位图层 = `views` schema 下带 `geom` 的视图(后端 `list_map_views()` 动态枚举,
    `backend/db/postgres.py:175`)
  - 参考图层 = `reference` schema 下带 `geom` 的基础表(`list_reference_layers()`,
    `backend/db/postgres.py:212`)
  - 颜色、顺序、显隐默认值、别名全是前端硬编码常量(`LeafletMap.vue` 调色板 +
    `popupFields.js` 配色表),刷新即重置,无持久化
  - 加图层只能靠写 SQL 迁移(如 `20260622_add_tongzhou_baila_view.sql`),
    管理员在 UI 上动不了

- **用户/配置无管理界面**
  - admin 默认账号写死在 `.env`,无任何用户管理接口(增删调查员、改密、改角色都得改库或
    改 .env 重启)
  - 所有配置在 `backend/config.py` 走 `.env`,无运行时配置

### 1.2 已确认的需求边界(用户决策)

| 维度 | 决策 |
|---|---|
| 核心定位 | **管理后台(可写)**:管图层、管用户、管配置 |
| 图层深度 | **轻量元数据**:顺序、显隐默认值、别名、启用开关;不改 SQL、不改颜色逻辑 |
| 用户管理 | **需要**:UI 增删 investigator、改密、改角色 |
| 信息架构 | **独立 `/admin` 模块**:自带左侧导航,admin 专属,现有页面不动 |

---

## 二、方案总览

新增 **`/admin` 独立模块**(仅 admin 可见),含三个子页面:

| 页面 | 路由 | 功能 |
|---|---|---|
| 管理概览 | `/admin` | KPI 看板:用户数/角色分布、图层数、各虫种点位计数 |
| 用户管理 | `/admin/users` | 增删查改用户、重置密码、改角色/启用状态 |
| 图层管理 | `/admin/layers` | 调整图层顺序、显隐默认值、显示别名、启用开关 |

后端新增 `app_admin` schema 和一张 `layer_metadata` 元数据表,复用现有认证/会话/角色
体系,**不引入新依赖**。

核心收益:

- **用户管理**:解决"增删调查员只能手动改库"的真实痛点
- **图层管理**:让管理员在 UI 上调整图层顺序、显隐默认值、显示别名,刷新不再重置;
  地图页颜色逻辑不动(轻量元数据原则)
- **管理概览**:汇总分散在多处的 admin 信息,作为管理首页

不动:`/workorder` `/map` `/data-export` `/data-statistics` 路由和行为完全保持;
`popupFields.js` 和 `LeafletMap.vue` 的配色逻辑不动。

---

## 三、后端改动

### 3.1 新建迁移 `backend/db/migrations/20260704_admin_dashboard.sql`

建 schema `app_admin`,建表 `app_admin.layer_metadata`:

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | BIGSERIAL PK | 主键 |
| `layer_key` | TEXT NOT NULL | 图层唯一标识,值 = 视图表名或参考层表名 |
| `layer_type` | TEXT NOT NULL | `'view'`(点位图层)/ `'reference'`(参考图层),CHECK 约束 |
| `display_name` | TEXT NULL | 显示别名,空时回退到原 name/label |
| `sort_order` | INT NOT NULL DEFAULT 0 | 排序,越小越靠前 |
| `default_visible` | BOOLEAN NOT NULL DEFAULT FALSE | 参考图层的默认显隐 |
| `is_enabled` | BOOLEAN NOT NULL DEFAULT TRUE | 是否在地图上展示,关掉即从列表隐藏 |
| `updated_at` | TIMESTAMPTZ DEFAULT NOW() | 更新时间 |

约束:`UNIQUE(layer_type, layer_key)`。

对当前已知图层插入初始行(sort_order 按 `name` 默认序,参考层 `default_visible` 沿用
现有 `== 行政边界` 逻辑)。

### 3.2 新建 `backend/db/admin.py`(或并入 `postgres.py`)

数据访问层:

- 图层元数据:`list_layer_metadata()` / `upsert_layer_metadata()` /
  `update_layer_metadata()`
- 用户管理:`list_users()` / `create_user()` / `update_user()`(display_name/role/is_active)
  / `reset_user_password()` / `delete_user()`(禁止删自己、禁止删最后一个 admin)
- `count_users_by_role()` 等 dashboard 聚合查询

### 3.3 新建 `backend/routers/admin.py`

prefix `/api/admin`,依赖 `require_user_role(USER_ROLE_ADMIN)`。

端点清单: