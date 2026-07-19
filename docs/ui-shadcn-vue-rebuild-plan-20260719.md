# 前端 UI 完全重构计划（路径 C：shadcn-vue + Tailwind + Claude 主题）

> **状态**: 执行中 · P7/P1/P2 已完成，下一步 P3  
> **编制日期**: 2026-07-19  
> **最后更新**: 2026-07-19  
> **适用项目**: TZLB 林业调查工作台（Vue 3 + Vite + Leaflet + FastAPI）  
> **目标参考**: [tweakcn Claude 主题](https://tweakcn.com/editor/theme?theme=claude)（**原样配色**）+ shadcn-vue  
> **维护约定**: 每完成一个阶段/任务，必须更新本文「进度总表」与对应阶段的状态勾选；阻塞与决策写入「变更记录」。

---

## 0. 如何维护本文档

### 0.1 完成一项任务后（强制）

1. 将对应任务 `[ ]` 改为 `[x]`，并填写 **完成日期**。
2. 更新 **§1 进度总表** 中该阶段的状态与备注。
3. 若有范围/方案变更，追加一行到 **§12 变更记录**。
4. 阶段结束时写清：改了哪些目录、验证命令与结果、遗留问题。

### 0.2 状态枚举

| 状态 | 含义 |
|------|------|
| `pending` | 未开始 |
| `in_progress` | 进行中 |
| `blocked` | 阻塞（须写原因） |
| `done` | 已完成且验证通过 |
| `skipped` | 有意跳过（须写原因） |

### 0.3 单次实施粒度与分支策略

- **长驻 feature 分支**：`ui-shadcn-rebuild`（名称固定，从最新 `main` 拉出）。
- **`main` / `origin/main` 在整次 UI 重构完成前保持不动**；不往 main 合阶段性 PR。
- 每个阶段在 feature 分支上 **单独 commit**（可再拆 1～3 个小 commit），便于回看与 bisect。
- 日常查看/调试：checkout `ui-shadcn-rebuild` 后 `npm run dev`；需要对照旧版时切回 `main`。
- 全部阶段（P2～P8）完成并回归通过后，再 **一次（或最终整理后的）PR 合入 main**。
- 每个阶段结束必须跑：`cd frontend && npm test && npm run build`。
- **业务 API、路由权限、Cookie 会话逻辑默认不改**；本计划聚焦 UI 层。

---

## 1. 进度总表

| 阶段 | 名称 | 状态 | 完成日期 | 备注 |
|------|------|------|----------|------|
| P0 | 决策冻结与基线 | `done` | 2026-07-19 | 见 §4 已决；P0.2 截图可选跳过；主题快照并入 P1 |
| P1 | 工程基建（Tailwind + shadcn-vue + 主题） | `done` | 2026-07-19 | Tailwind v4 + Claude light + components.json；未装 preflight |
| P2 | 设计系统与基础组件 | `done` | 2026-07-19 | 2a～2g 已接入；Sidebar 为 JS 适配；旧 Toast 并存 |
| P3 | 应用壳与登录 | `pending` | — | **当前焦点** · App shell + Login |
| P4 | 管理与数据轻页 | `pending` | — | admin + export + statistics |
| P5 | 工单域 | `pending` | — | WorkOrder + 子组件 + 点位截图 |
| P6 | 地图域 | `pending` | — | MapView + Leaflet + 工具条 |
| P7 | 删除 `/design` 预览体系 | `done` | 2026-07-19 | 路由/组件/fixtures/样式/测试已删；工单 preview 耦合已剥离 |
| P8 | 旧样式清理与收尾 | `pending` | — | 删死 CSS、统一 token、文档 |

**当前焦点**: **P3 应用壳与登录**。

---

## 2. 目标与非目标

### 2.1 目标

1. 前端视觉与交互统一到 **shadcn-vue** 组件体系。
2. 样式主通道改为 **Tailwind CSS**，主题 token **原样采用 tweakcn Claude 配色**（暖橙 primary + 暖纸色底，不改林业绿）。
3. **仅 light 模式**；不实现暗色切换（CSS 可不引入 `.dark` 变量集）。
4. 页面级 UI **按阶段小步合 main**，业务行为（鉴权、API、工单生成、地图数据）保持等价。
5. **删除整棵 `/design` 预览**（路由、组件、fixtures、design CSS、相关测试）。

### 2.2 非目标（本计划不做）

- 后端 API / 数据库 schema 改造。
- 新业务功能（除非重构时发现 blocker 的最小修补）。
- 为了主题而引入 React 或 Next.js。
- 暗色模式 / 主题切换。
- 保留或改造 `/design` 预览（直接删除）。
- 强行 100% utility 化 Leaflet 内部 DOM（地图允许保留定向 CSS）。

### 2.3 成功标准

- 正式业务路由全部使用新壳 + 新组件，无「半旧半新」壳层泄漏。
- 仓库内无 `/design` 路由与 design 预览死代码。
- 主题色为 Claude light 原样语义变量。
- `npm test` 与 `npm run build` 通过。
- 关键路径手测通过：登录/退出、角色导航、工单导入生成、地图筛选与点选、数据导出、管理后台 CRUD 入口。
- P8 后仅保留一套 token，无林业绿旧 token 与 Claude 双轨并存。

---

## 3. 现状基线（重构前）

| 项 | 现状 |
|----|------|
| 框架 | Vue 3 + Vue Router + Vite + Vitest |
| 样式 | 手写 CSS + scoped；`styles.css` + `styles/*`；约 1 万行样式相关代码 |
| Token | 自研 `--color-*`（林业绿）+ design 预览 oklch 另一套 |
| 状态 | composables + 少量 module store；无 Pinia |
| 组件库 | 无；对话框/表格等自研 |
| 地图 | Leaflet；大量自定义与 `.leaflet-*` 覆盖 |
| 图标 | `@lucide/vue`（与 shadcn 生态兼容，可保留） |
| 设计预览 | `/design/*` 独立布局与 mock，免登 |

### 3.1 正式业务路由清单

| 路由 | 视图 | 角色 | 重构优先级阶段 |
|------|------|------|----------------|
| `/login` | `LoginView.vue` | 公开 | P3 |
| `/workorder` | `WorkOrderView.vue` | admin | P5 |
| `/workorder/point-screenshots` | `PointScreenshotView.vue` | admin | P5 |
| `/map` | `MapView.vue` | 登录即可 | P6 |
| `/data-export` | `DataExportView.vue` | admin | P4 |
| `/data-statistics` | `DataStatisticsView.vue` | admin | P4 |
| `/admin` | `AdminDashboardView.vue` | admin | P4 |
| `/admin/users` | `AdminUsersView.vue` | admin | P4 |
| `/admin/layers` | `AdminLayersView.vue` | admin | P4 |
| `/admin/logs` | `AdminOperationLogsView.vue` | admin | P4 |
| ~~`/design/*`~~ | ~~design 预览树~~ | — | **P7 已删除** |

### 3.2 高耦合自研 UI（须被设计系统替换或收编）

| 现有模块 | 职责 | 目标替代方向 |
|----------|------|----------------|
| `App.vue` 壳层 | 侧栏/顶栏/移动导航 | `Sidebar` + `Sheet` + 布局 primitives |
| `components/ui/ToastViewport.vue` | Toast | `Sonner` / Toast  primitive |
| `components/workorder/BaseDialog.vue` | 对话框底座 | `Dialog` |
| `components/workorder/ConfirmDialog.vue` | 确认框 | `AlertDialog` |
| `components/workorder/RecordTable.vue` | 表格 | `Table` + 业务列封装 |
| `components/workorder/RecordDetailModal.vue` | 详情 | `Dialog`/`Sheet` |
| `components/workorder/ExcelImportDialog.vue` 等 | 导入流 | Dialog + Form 控件 |
| `components/workorder/ImageUploader.vue` | 上传 | 自研逻辑 + 新视觉 |
| `components/map/MapToolbar.vue` | 筛选工具 | Card/Popover/Select + 保留地图逻辑 |
| `components/map/LeafletMap.vue` | 地图引擎 | **逻辑保留**；外壳与 popup 皮肤化 |

### 3.3 尽量冻结不动（除非阶段需要）

- `frontend/src/api/*`、`auth/permissions.js`、`composables/useAuthSession.js`（除 UI 调用方式）
- `composables/workorder/*` 业务逻辑
- `router/index.js` 权限模型（仅允许 meta/壳相关小改）
- 后端全部

---

## 4. 关键决策（P0 · 已冻结）

> 2026-07-19 用户确认。实施以本表为准。

| # | 决策项 | 已决 | 说明 |
|---|--------|------|------|
| D1 | 主色策略 | **A · 完全使用 Claude 原样配色** | 暖橙 primary、暖纸色背景等，**不**改回林业绿 |
| D2 | 暗色模式 | **A · 仅 light** | 不实现 dark 切换；主题 CSS 只落地 light 变量 |
| D3 | Vue 组件方案 | **A · shadcn-vue** | 官方/文档推荐脚手架接入 |
| D4 | `/design` 预览 | **删除** | 路由、views/design、components/design、fixtures/design、styles/design-*.css、相关测试与文档描述一并移除 |
| D5 | 分支策略 | **C · 长驻 feature 分支，完成后才合 main**（2026-07-19 修订） | 分支名 `ui-shadcn-rebuild`；阶段用 commit 隔离；`main` 重构完成前不动 |
| D6 | 图标 | **继续 `@lucide/vue`** | 与 shadcn 生态一致 |

### P0 任务

- [x] P0.1 确认 D1～D5，填入上表「已决」  
  - 完成日期: 2026-07-19  
  - 备注: 用户对话确认，见变更记录
- [x] P0.2 截图冻结  
  - 完成日期: 2026-07-19  
  - 备注: **skipped**（可选；全量换 Claude 皮后基线对比价值低）
- [x] P0.3 从 [claude registry](https://tweakcn.com/r/themes/claude.json) 导出 **light** 主题快照到仓库  
  - 完成日期: 2026-07-19  
  - 备注: 已写入 `frontend/src/styles/themes/claude.json` + `claude-light.css`；原样 Claude，未改 primary

---

## 5. 阶段计划（按顺序执行）

### P1 · 工程基建（已完成）

**目标**: 项目可编译运行，Tailwind + 主题变量生效，旧样式暂时并存。

- [x] P1.1 安装 Tailwind v4（`tailwindcss` + `@tailwindcss/vite`）与 `clsx` / `tailwind-merge` / `class-variance-authority`  
  - 完成日期: 2026-07-19
- [x] P1.2 配置 Vite：`@` 别名 + `@tailwindcss/vite`；`main.js` 引入 `styles/shadcn.css`  
  - 完成日期: 2026-07-19
- [x] P1.3 `components.json`（JS、new-york、cssVariables）+ `src/lib/utils.js` 的 `cn()` + `jsconfig.json`  
  - 完成日期: 2026-07-19
- [x] P1.4 Claude light 主题：`styles/themes/claude-light.css`（`:root` + `@theme inline`）；无 `.dark`  
  - 完成日期: 2026-07-19
- [x] P1.5 共存：仅 theme + utilities（**无 preflight**）；旧 `styles.css` 仍加载  
  - 完成日期: 2026-07-19
- [x] P1.6 冒烟：`npm test` 246 通过；`npm run build` 成功；产物含 `.bg-background` / `.bg-primary`  
  - 完成日期: 2026-07-19

**验收**: 语义 utility 已进构建；旧测试全绿（无 preflight 打爆）。

**落地备注**:
- 入口：`src/styles/shadcn.css` → `themes/claude-light.css`
- 快照：`src/styles/themes/claude.json`
- CLI：`npx shadcn-vue@latest add <component>` 可识别项目（`shadcn-vue info` 已验证）
- P2 起用 CLI 添加 Button 等组件到 `src/components/ui/`（与现有 `ToastViewport.vue` 共存）

---

### P2 · 设计系统与基础组件（已完成）

**目标**: 业务页重构时只组合 primitives，不再复制 scoped 色值。

| 批次 | 组件 | 主要消费者 |
|------|------|------------|
| 2a | Button, Input, Label, Textarea, Checkbox, Select | 表单全站 |
| 2b | Card, Separator, Badge, Skeleton | 列表/概览 |
| 2c | Dialog, AlertDialog, Sheet | 确认/详情/移动侧栏 |
| 2d | Table, DropdownMenu, Popover, Tabs | 表格与筛选 |
| 2e | Sidebar, ScrollArea, Tooltip | 应用壳 |
| 2f | Sonner | 反馈（旧 ToastViewport 并存） |
| 2g | Switch, Pagination | 管理页 |

- [x] P2.1 批次 2a 接入 + 用法记录 `docs/ui-components-usage.md`  
  - 完成日期: 2026-07-19
- [x] P2.2 批次 2b～2c  
  - 完成日期: 2026-07-19
- [x] P2.3 批次 2d～2e（Sidebar CLI 因 TS 失败，已手动 JS 适配）  
  - 完成日期: 2026-07-19
- [x] P2.4 批次 2f～2g；Toast：**新旧并存**，P3 壳层可选用 Sonner，旧 `ToastViewport` 暂留  
  - 完成日期: 2026-07-19
- [x] P2.5 目录约定：`src/components/ui/<name>/` + smoke 测试；用法见 `docs/ui-components-usage.md`  
  - 完成日期: 2026-07-19

**验收**: `npm test` 含 primitives smoke；可 `import { Button } from '@/components/ui/button'`。

**附带依赖**: `reka-ui`、`@vueuse/core`、`vue-sonner`、`@tanstack/vue-table`、`tw-animate-css`。

---

### P3 · 应用壳与登录

**目标**: 全局导航/布局先切换到新系统，后续页面自然落入新壳。

- [ ] P3.1 用 Sidebar + Header 模式重写 `App.vue` 壳（保留：角色过滤导航、`hideShell`/`fullBleed`、登出、移动端菜单）  
  - 完成日期:
- [ ] P3.2 导航配置抽离（可选 `config/navigation.js`），与 `auth/permissions` 对齐  
  - 完成日期:
- [ ] P3.3 重写 `LoginView.vue`（Card + Form 控件；逻辑仍走 `useAuthSession`）  
  - 完成日期:
- [ ] P3.4 更新 `AppShell.spec.js` / `LoginView` 相关测试选择器（优先 `data-testid` 稳定）  
  - 完成日期:
- [ ] P3.5 手测：admin / investigator 默认落地路由、无权限回退、退出登录  
  - 完成日期:

**验收**: 登录全流程可用；壳层无旧侧栏 CSS 依赖（或旧 CSS 仅服务未迁页面且不污染壳）。

---

### P4 · 管理与数据轻页

**目标**: 低业务复杂度页面先完成，验证表格/表单模式。

建议顺序（由易到难）：

1. `DataExportView`
2. `DataStatisticsView`
3. `AdminDashboardView`
4. `AdminOperationLogsView`
5. `AdminUsersView`
6. `AdminLayersView`

- [ ] P4.1 DataExport  
  - 完成日期:
- [ ] P4.2 DataStatistics  
  - 完成日期:
- [ ] P4.3 AdminDashboard  
  - 完成日期:
- [ ] P4.4 AdminOperationLogs  
  - 完成日期:
- [ ] P4.5 AdminUsers  
  - 完成日期:
- [ ] P4.6 AdminLayers  
  - 完成日期:
- [ ] P4.7 对应 `views/__tests__/*` 与构建  
  - 完成日期:

**验收**: admin 数据链路功能等价；页面级 scoped 样式删除或近空。

---

### P5 · 工单域

**目标**: 核心 admin 业务 UI 现代化，逻辑复用 composables。

建议顺序：

1. 替换 `ConfirmDialog` / `BaseDialog` 为全局 AlertDialog/Dialog 封装（兼容旧调用点）
2. `RecordTable`
3. `ImageUploader` 视觉
4. `SurveyImportDialog` / `ExcelImportDialog`
5. `RecordDetailModal`
6. `WorkOrderView` 主页面编排
7. `PointScreenshotView`

- [ ] P5.1 Dialog/Confirm 统一封装与替换  
  - 完成日期:
- [ ] P5.2 RecordTable  
  - 完成日期:
- [ ] P5.3 导入类 Dialog  
  - 完成日期:
- [ ] P5.4 RecordDetail + ImageUploader  
  - 完成日期:
- [ ] P5.5 WorkOrderView  
  - 完成日期:
- [ ] P5.6 PointScreenshotView  
  - 完成日期:
- [ ] P5.7 工单相关单测全绿；手测：调查导入 → 选记录 → 补图 → 生成下载  
  - 完成日期:

**验收**: 工单主路径无回归；旧 workorder scoped 大块 CSS 移除。

---

### P6 · 地图域

**目标**: 地图工作区视觉对齐新系统；Leaflet 引擎稳定。

- [ ] P6.1 `MapView` 布局改为 full-bleed + 浮层面板（Card/Sheet），接入新 token  
  - 完成日期:
- [ ] P6.2 `MapToolbar` 筛选 UI 组件化（逻辑与 `mapStore` 可保留）  
  - 完成日期:
- [ ] P6.3 `LeafletMap`：popup/控件皮肤、容器圆角边框；**保留** `.leaflet-*` 必要覆盖于 `map-leaflet.css`  
  - 完成日期:
- [ ] P6.4 删除点确认等与 AlertDialog 对齐  
  - 完成日期:
- [ ] P6.5 地图单测与手测：图层切换、筛选、弹窗字段、移动端  
  - 完成日期:

**验收**: investigator 仅地图权限体验完整；性能与点位加载不劣于基线。

---

### P7 · 删除 `/design` 预览体系（已完成）

> **时机**: 已作为实施第一步完成（先于 P1）。  
> **范围**: 删预览体系，并剥离正式页上的 design mock 耦合。

删除清单：

- [x] P7.1 路由：移除 `router/index.js` 中 `/design` 及 children；删 design 相关 import  
  - 完成日期: 2026-07-19
- [x] P7.2 视图：删除 `views/design/*`  
  - 完成日期: 2026-07-19
- [x] P7.3 组件：删除 `components/design/**`  
  - 完成日期: 2026-07-19
- [x] P7.4 fixtures：删除 `fixtures/design/**`（含 `workorderMock`）  
  - 完成日期: 2026-07-19
- [x] P7.5 样式：删除 `styles/design-*.css`、`tokens.css`、`primitives.css`、`reset.css`（仅 design 引用）；空 `src/styles/` 目录已移除  
  - 完成日期: 2026-07-19
- [x] P7.6 测试：删除 Design* 测试；修正 `router/__tests__/index.spec.js`  
  - 完成日期: 2026-07-19
- [x] P7.7 文档：`AGENTS.md` 去掉「设计预览」小节；README 无相关描述  
  - 完成日期: 2026-07-19
- [x] P7.8 验证：`npm test` 245 通过；`npm run build` 成功；`src` 内无 design 路由/模块引用  
  - 完成日期: 2026-07-19

**附带清理（工单 preview 耦合）**:

- `WorkOrderView.vue`：移除 `previewMode` / mock 数据 / 预览横幅与禁用逻辑
- `useWorkorderExport.js`：移除 `isPreview` 参数与模拟导出分支
- 仓库根 `design-preview/` 空目录已删

---

### P8 · 清理与收尾

- [ ] P8.1 删除未引用的旧 CSS（`styles.css` 中死代码、`primitives` 重复、旧 token）  
  - 完成日期:
- [ ] P8.2 统一只保留一套语义 token（shadcn 名）；业务色（风险等级、地图边界）映射到 chart/扩展变量  
  - 完成日期:
- [ ] P8.3 全局搜索残留旧 class 命名体系，清理  
  - 完成日期:
- [ ] P8.4 更新 `README.md` / `AGENTS.md` 前端技术栈描述（Vue + Tailwind + shadcn-vue）  
  - 完成日期:
- [ ] P8.5 全量 `npm test` + `npm run build`；关键路径回归清单打勾（§6）  
  - 完成日期:
- [ ] P8.6 将本计划状态改为 `done`，写总结段落  
  - 完成日期:

---

## 6. 关键路径回归清单（P8 / 每大阶段可选）

| # | 路径 | 通过 |
|---|------|------|
| R1 | 登录成功 / 失败提示 | [ ] |
| R2 | 退出登录回登录页 | [ ] |
| R3 | admin 见全部导航；investigator 仅地图相关 | [ ] |
| R4 | 工单：调查导入 | [ ] |
| R5 | 工单：Excel 导入（若仍支持） | [ ] |
| R6 | 工单：生成并下载 | [ ] |
| R7 | 点位截图上传/替换/删除 | [ ] |
| R8 | 地图：视图切换、筛选、popup | [ ] |
| R9 | 数据导出下载 | [ ] |
| R10 | 数据统计展示 | [ ] |
| R11 | 管理：用户/图层/日志/概览 | [ ] |
| R12 | 401 / 会话过期跳转 | [ ] |

---

## 7. 目录与约定（目标态）

```
frontend/
  components.json                 # shadcn-vue
  src/
    assets/ / styles/
      themes/claude.json          # 主题快照（可选）
      shadcn.css / index.css      # Tailwind + CSS 变量
    components/
      ui/                         # shadcn 生成 primitives（尽量不手改或最小补丁）
      map/                        # 业务地图组件
      workorder/                  # 业务工单组件（薄封装 ui）
      layout/                     # AppSidebar, AppHeader 等（新建）
    lib/utils.js                  # cn()
    views/                        # 页面，样式以 Tailwind class 为主
    api/ auth/ composables/       # 默认冻结
```

**约定**:

1. 业务组件可以包一层 `ui/*`，但不要复制一套颜色系统。
2. 测试优先 `data-testid`，减少对 DOM 结构 class 的依赖。
3. 每完成一页，删除该页大块 `<style scoped>` 中已无用规则。
4. 新依赖必须写入 `package.json`；不引入与 shadcn-vue 冲突的第二套 UI 库。

---

## 8. 主题接入要点（Claude · 原样 light）

来源：`https://tweakcn.com/r/themes/claude.json`

- **只使用 `cssVars.light` + `cssVars.theme`**，不落地 `cssVars.dark`
- 语义变量：`background` `foreground` `primary` `secondary` `muted` `accent` `destructive` `border` `input` `ring` `card` `popover` `sidebar-*` `chart-*`
- 圆角基准：`radius: 0.5rem`
- 字体：Claude 提供的系统栈；可叠加中文回退（`PingFang SC` / `Noto Sans SC`），**不改变色板**
- **禁止**把 `--primary` 改回林业绿；旧 `--color-forest` 等在页面迁完后删除（P8）

业务专用色（地图/风险，不在 Claude 默认集）仍可扩展，但应与 Claude 暖色纸面协调：

| 用途 | 建议变量 |
|------|----------|
| 风险等级 | `--risk-*` 或复用 `chart-*` |
| 地图边界 | `--map-boundary` |
| 地图地貌 | `--map-land` / `--map-water` |

---

## 9. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| Preflight 打爆旧页 | 并存期布局错乱 | 分阶段替换；控制 preflight；先迁壳再迁页 |
| shadcn-vue 与 Vue 版本不兼容 | 阻塞 P1 | P1 先 spike 半日；不行则评估备用 headless |
| 测试脆弱（class 选择器） | 重构失败率高 | 同步改测；推广 testid |
| Leaflet z-index 与 Sidebar/Dialog | 地图被遮罩 | 统一 z-index 量表 |
| 范围膨胀（顺手改业务） | 失控 | 非目标清单；API 默认冻结 |
| 双 token 并存 | 颜色不一致 | P8 强制收敛 |

---

## 10. 工作量粗估（1 人参考）

| 阶段 | 粗估 |
|------|------|
| P0 | 0.5 天 |
| P1 | 1～2 天 |
| P2 | 2～3 天 |
| P3 | 1～2 天 |
| P4 | 2～3 天 |
| P5 | 3～5 天 |
| P6 | 2～4 天 |
| P7 | 0.5～1 天 |
| P8 | 1～2 天 |
| **合计** | **约 2～3 周**（含联调与回归，视决策与测试债浮动） |

---

## 11. 执行节奏建议

1. ~~先 P0 决策~~ **已完成**。
2. ~~P7 删 `/design`~~ **已完成**（在 `ui-shadcn-rebuild` 上独立 commit）。
3. ~~P1 基建~~ **已完成**。
3b. ~~P2 组件~~ **已完成** → 下一步 **P3 壳/登录** → P4 → P5 → P6 → P8。
4. **D5（修订）**: 全程在 `ui-shadcn-rebuild` 开发与调试；**勿合 main**，直至重构完成。
5. 每天结束更新本文进度；阻塞超过 1 天写入变更记录。
6. 地图（P6）不要与工单（P5）同一 commit 混改。
7. 需要旧版对照：`git checkout main`；继续重构：`git checkout ui-shadcn-rebuild`。

---

## 12. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-07-19 | 初版计划落盘；路径 C；主题参考 tweakcn Claude；实施未开始 |
| 2026-07-19 | **P0 冻结**: D1=Claude 原样配色；D2=仅 light；D3=shadcn-vue；D4=删除 `/design`；D5=小步合 main。P0 标 done；焦点转 P1；P7 改为可提前删除 |
| 2026-07-19 | **P7 完成**: 删除 `/design` 全树；剥离 WorkOrder preview；`npm test`/`build` 通过。焦点 → P1 |
| 2026-07-19 | **P1 完成**: Tailwind v4 + Claude light 主题 + shadcn-vue 基建；无 preflight 并存；焦点 → P2 |
| 2026-07-19 | **D5 修订**: 取消「小步合 main」；改为长驻 `ui-shadcn-rebuild`，全部完成后再合 main；P7/P1 在该分支分 commit 落盘 |
| 2026-07-19 | **P2 完成**: shadcn-vue 2a～2g；Sidebar JS 适配；Sonner 与旧 Toast 并存；焦点 → P3 |

---

## 13. 阶段完成摘要

### 摘要 · P7
- 日期: 2026-07-19
- 完成任务: P7.1～P7.8 全部；附带清理工单 `previewMode` 与 mock 依赖
- 主要改动:
  - 删除: `views/design/`、`components/design/`、`fixtures/design/`、`styles/design-*`、`tokens.css`、`primitives.css`、`reset.css`、Design* 测试、`design-preview/`
  - 修改: `router/index.js`、`router/__tests__/index.spec.js`、`WorkOrderView.vue`、`useWorkorderExport.js`、`AGENTS.md`、本计划
- 验证: `npm test` 27 files / 245 tests 通过；`npm run build` 成功
- 遗留: `docs/DESIGN.md` 仍为旧林业绿设计规范文稿（非 `/design` 路由），未动；P8 再处理旧 token/文档
- 下一步: P1 工程基建（Tailwind + shadcn-vue + Claude light 主题）

### 摘要 · P1
- 日期: 2026-07-19
- 完成任务: P0.3 + P1.1～P1.6
- 主要改动:
  - 依赖: `tailwindcss` `@tailwindcss/vite` `clsx` `tailwind-merge` `class-variance-authority`
  - 配置: `vite.config.js`（alias + tailwind 插件）、`jsconfig.json`、`components.json`
  - 样式: `src/styles/shadcn.css`、`src/styles/themes/claude-light.css`、`claude.json`
  - 工具: `src/lib/utils.js`（`cn`）+ 单测
  - 入口: `main.js` 先 shadcn.css 再 styles.css
- 验证: `npm test` 28 files / 246 tests；`npm run build` 含 `.bg-background` `.bg-primary`
- 遗留: 尚未添加任何 shadcn 组件（P2）；旧林业绿 token 仍在 `styles.css`
- 下一步: P2 用 `npx shadcn-vue@latest add` 分批接入 primitives

### 摘要 · P2
- 日期: 2026-07-19
- 完成任务: P2.1～P2.5
- 主要改动:
  - `src/components/ui/*`：button/input/label/textarea/checkbox/select/card/separator/badge/skeleton/dialog/alert-dialog/sheet/table/dropdown-menu/popover/tabs/scroll-area/tooltip/sidebar/sonner/switch/pagination
  - Sidebar：CLI TS 失败 → 从 registry 手写 JS 适配
  - `tw-animate-css` 接入动画类
  - 用法：`docs/ui-components-usage.md`；smoke：`components/ui/__tests__/primitives.smoke.spec.js`
  - 旧 `ToastViewport.vue` 保留
- 验证: `npm test` 29 files / 250 tests；`npm run build` 成功
- 遗留: 业务页尚未改用新组件；Form 未单独接入
- 下一步: P3 用 Sidebar + 相关 primitives 重写 App 壳与 Login

<!-- 后续摘要往下追加 -->
