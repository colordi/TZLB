# 视觉层接入现有行为层计划

## 1. 背景与目标

`/design/*` 静态预览已经完成 OpenDesign 高保真 HTML/CSS 原型到 Vue 3 + Vite 的第一阶段迁移。下一阶段目标不是继续复制静态页面，而是将已还原的视觉语言逐步接入正式 `/login`、`/workorder`、`/map` 和应用壳层。

核心约束：

- 保留正式页面现有业务行为、API、store、权限、路由守卫和测试契约。
- 不用静态预览组件整体替换正式页面。
- 不把 design fixture 作为正式业务数据源。
- `/design/*` 继续作为视觉回归对照入口保留。
- 每次只接入一个正式页面或一个明确视觉层，不并行改多个行为面。

本计划由主代理结合当前代码审阅和子代理 Goodall 的只读分析整理，子代理未修改文件、未运行测试。

## 2. 不可破坏的正式行为契约

### 2.1 路由与权限

关键文件：

- `frontend/src/router/index.js`
- `frontend/src/auth/permissions.js`
- `frontend/src/composables/useAuthSession.js`

必须保留：

- `/login` 免登录。
- `/workorder` 仅管理员可访问。
- `/map` 是正式全宽地图页。
- `beforeEach` 中的 `ensureSessionLoaded()`、未登录重定向、已登录访问登录页跳转、角色 fallback。
- `/design/*` 的 `hideShell: true`、`requiresAuth: false`、`skipSessionLoad: true` 隔离契约。

禁止：

- 为了适配视觉层绕过认证或权限判断。
- 让正式页面读取 design fixture。
- 让 `/design/*` 读取正式 session、API 或 store。

### 2.2 登录页

关键文件：

- `frontend/src/views/LoginView.vue`
- `frontend/src/views/design/DesignLoginView.vue`
- `frontend/src/views/__tests__/LoginView.spec.js`

必须保留：

- `username`、`password`、`rememberMe`、`submitting` 状态。
- 空值校验和 toast。
- `signIn()` 调用。
- `tzlb.rememberedUsername` 本地存储 key。
- `redirect` 或 `/map` 跳转逻辑。
- 表单 `autocomplete`、禁用态和提交中状态。

禁止：

- 直接替换成 `DesignLoginView.vue` 的静态提交逻辑。
- 删除真实错误提示或成功跳转。
- 改动认证 API 契约。

### 2.3 应用壳层

关键文件：

- `frontend/src/App.vue`
- `frontend/src/components/design/DesignAppShell.vue`
- `frontend/src/__tests__/AppShell.spec.js`

必须保留：

- `hideShell` 和 `fullBleed` route meta。
- 顶部导航按角色过滤。
- 移动抽屉开关、遮罩关闭和路由切换自动关闭。
- 用户下拉和 `signOut()` 退出流程。
- 地图页顶部工具栏通过 `mapStore/mapActions` 读取地图上下文。
- 现有 `data-testid`，特别是导航和地图工具相关测试定位点。

禁止：

- 把 design 预览导航中的“统计分析”“基础配置”等占位入口接入正式壳层。
- 断开 `App.vue` 与 `mapStore` 的地图工具栏桥接。

### 2.4 工单页

关键文件：

- `frontend/src/views/WorkOrderView.vue`
- `frontend/src/components/workorder/RecordTable.vue`
- `frontend/src/components/workorder/RecordDetailModal.vue`
- `frontend/src/components/workorder/SurveyImportDialog.vue`
- `frontend/src/components/workorder/fieldConfig.js`
- `frontend/src/api/workorder.js`
- `frontend/src/views/__tests__/WorkOrderView.spec.js`

必须保留：

- 害虫类型、任务类型、任务名称联动。
- 调查导入入口和 `SurveyImportDialog`。
- `normalizeRecordForPest()`、`validateRecords()`、`toPayloadRecord()`。
- 行点击详情、编辑、删除、批量删除。
- 图片字段和模板字段。
- `generateWorkorder()` 逐条导出，每次只传单条记录。
- 认证失效时中断后续导出。

禁止：

- 把 `DesignWorkOrderView.vue` 当正式页替换。
- 恢复原型里的静态“批量压缩导出”语义。
- 把 design fixture 的状态、统计、附件和审批字段混入正式记录模型。

### 2.5 地图页

关键文件：

- `frontend/src/views/MapView.vue`
- `frontend/src/components/map/LeafletMap.vue`
- `frontend/src/components/map/MapToolbar.vue`
- `frontend/src/components/map/popupFields.js`
- `frontend/src/stores/mapStore.js`
- `frontend/src/api/map.js`
- `frontend/src/views/__tests__/MapView.spec.js`
- `frontend/src/components/map/__tests__/LeafletMap.spec.js`

必须保留：

- `listMapViews()`、`fetchMapView()`、`fetchMapFilterOptions()`、`fetchAdminBoundary()`。
- GeoJSON 请求 token，防止旧请求覆盖当前 view。
- `LeafletMap.vue` 的真实底图、点位、聚合、编号、定位、图例和新增点位事件。
- 地图筛选字段来自后端动态配置。
- 美国白蛾点位新增、编号规则、乡镇识别和保存后刷新。
- `mapStore/mapActions` 与 App 顶部工具栏同步。

禁止：

- 用 `MapMockCanvas.vue` 替换 `LeafletMap.vue`。
- 使用 `DESIGN_MAP_MARKERS`、`DESIGN_MAP_CLUSTERS`、`DESIGN_MAP_POINT_DETAILS` 作为正式地图数据。
- 让静态“风险热力”“聚合详情”“区县点位”成为正式事实源。

## 3. 可复用资产与限制

### 3.1 可复用

- `frontend/src/styles/tokens.css`：颜色、字号、间距、圆角、阴影、动效等视觉 token，可作为正式 token 收敛参考。
- `frontend/src/styles/primitives.css`：按钮、输入、面板等基础视觉模式，可拆为正式基础样式。
- `frontend/src/views/design/DesignLoginView.vue`：登录页背景、品牌区、卡片结构和密码显示视觉，可借鉴模板结构。
- `frontend/src/components/design/DesignAppShell.vue`：预览壳层的侧栏密度、顶部栏和移动抽屉视觉，可借鉴。
- `frontend/src/components/design/workorder/*`：工单表格、卡片、筛选、统计、弹窗和抽屉视觉，可在改造成纯展示组件后接入。
- `frontend/src/components/design/map/MapDetailDrawer.vue`、`MapLayerPanel.vue`、`MobileMapBar.vue`：地图详情、图层和移动操作视觉，可在剥离 fixture 后接入正式状态。

### 3.2 必须改造后才可接入

以下组件不能直接进入正式页面，必须先移除 fixture import，改为只接收 props、只 emit 展示事件：

- `frontend/src/components/design/workorder/*`
- `frontend/src/components/design/map/*`

改造要求：

- 不在组件内读取 design fixture。
- 不在组件内调用正式 API。
- 组件只负责展示和用户事件。
- 业务状态、校验和副作用全部保留在正式页面或现有业务组件中。

### 3.3 只能参考，不能接入

- `frontend/src/fixtures/design/workorderRecords.js`：静态工单状态、审批、附件、统计、导出结构。
- `frontend/src/fixtures/design/mapWorkspace.js`：静态地图点位、聚合、热力、状态和详情。
- `frontend/src/fixtures/design/navigation.js`：预览侧栏、占位功能和用户摘要。
- `MapMockCanvas.vue`：只用于 `/design/map` 视觉预览，永不接入正式 `/map`。

## 4. 分阶段接入顺序

### 阶段 A：Token 与基础样式收敛

目标：

- 建立正式 `:root` 与 design token 的映射表。
- 只合入确定不会破坏正式页面的 spacing、radius、shadow、font、motion token。
- 保留正式地图风险色、Leaflet 点位色、控件高度和 focus ring。

实施边界：

- 优先修改 `frontend/src/styles.css` 或新增正式 token 文件。
- 不修改正式页面模板。
- 不解除 `.design-preview-root` 的作用域。

验收：

- `/login`、`/workorder`、`/map` 未出现全局按钮、输入框、Leaflet 控件串扰。
- `/design/*` 仍能作为视觉对照访问。

### 阶段 B：正式登录页视觉接入

目标：

- 用 OpenDesign 登录页视觉替换正式 `LoginView.vue` 的外观。
- 保留全部认证行为。

实施边界：

- 只改 `LoginView.vue` 和必要登录样式。
- 不改 `useAuthSession.js`、`api/auth`、router。
- 保留现有测试可定位元素，必要时只增不删 `data-testid`。

验收：

- 未填写用户名或密码仍提示错误。
- 登录成功仍保存 remembered username 并跳转目标路径。
- 登录失败仍显示真实错误。

### 阶段 C：正式应用壳层视觉接入

目标：

- 将 design 壳层的品牌、导航、用户区和移动抽屉视觉接入 `App.vue`。
- 保留正式权限和地图工具栏。

实施边界：

- 只改 `App.vue` 和壳层相关样式。
- 不改 `permissions.js` 和路由守卫。
- 地图工具栏仍读取 `mapStore/mapActions`。

验收：

- 管理员能看到工单和地图入口。
- 调查员不能看到工单入口。
- `/map` 仍使用满宽主内容区。
- 移动抽屉遮罩关闭和路由切换关闭仍正常。

### 阶段 D：正式工单页视觉接入

目标：

- 将工单页视觉密度、统计区、表格/卡片和抽屉样式接入正式 `WorkOrderView.vue`。
- 保留导入、校验、编辑、删除和逐条导出。

实施边界：

- 先改造 design 工单组件为 presentational 组件，再接入正式 props/events。
- 保留 `SurveyImportDialog`、`RecordDetailModal`、`fieldConfig` 和 `generateWorkorder` 调用链。
- 不改后端工单生成契约。

验收：

- 四类害虫均可导入调查记录。
- 导入后记录字段归一化正确。
- 单条和多条导出仍按现有逐条接口调用。
- 部分失败、认证失效和校验失败仍按现有行为处理。

### 阶段 E：正式地图页视觉接入

目标：

- 接入地图详情抽屉、图层面板、状态提示和移动底栏视觉。
- 保留 Leaflet、真实 API、动态筛选和新增点位逻辑。

实施边界：

- 不接入 `MapMockCanvas.vue`。
- 不使用 design map fixture。
- `LeafletMap.vue` 继续负责点位、聚合、定位、编号和图例。
- 详情抽屉数据来自 `selectedFeature` 和 `buildPopupRows()`，不是静态点位详情。

验收：

- 初始 view 加载、切换 view、筛选提交、防旧请求覆盖仍正常。
- Leaflet 聚合、编号、定位和图例测试仍通过。
- 新增美国白蛾点位流程仍正常。
- 移动端地图控件不遮挡核心操作。

### 阶段 F：清理、回归和文档

目标：

- 清理已经被正式组件吸收且确认无引用的重复样式。
- 保留 `/design/*` 对照入口，直到正式视觉全面验收。
- 更新计划文档和阶段记录。

实施边界：

- 不删除 design fixture，除非另有明确清理任务。
- 不一次性删除预览组件。
- 不合并后端或数据库改动。

验收：

- 全量前端测试和构建通过。
- `/design/*`、`/login`、`/workorder`、`/map` 均可访问。
- 浏览器桌面与移动视口无横向溢出。

## 5. 每阶段测试与回滚边界

| 阶段 | 目标测试 | 回滚边界 |
|---|---|---|
| A Token | `npm run test -- --run`、`npm run build` | 只回退 token/样式文件 |
| B 登录 | `src/views/__tests__/LoginView.spec.js`、`src/router/__tests__/index.spec.js`、`src/api/__tests__/auth.spec.js` | 只回退 `LoginView.vue` 和登录样式 |
| C 壳层 | `src/__tests__/AppShell.spec.js`、`src/router/__tests__/index.spec.js` | 只回退 `App.vue` 和壳层样式 |
| D 工单 | `src/views/__tests__/WorkOrderView.spec.js`、`src/components/workorder/__tests__/*`、`src/api/__tests__/http.spec.js` | 回退新接入展示组件，保留业务链路 |
| E 地图 | `src/views/__tests__/MapView.spec.js`、`src/components/map/__tests__/*`、`src/api/__tests__/map.spec.js`、`src/__tests__/AppShell.spec.js` | 回退地图外层视觉，不回退 `LeafletMap.vue` 行为 |
| F 收口 | `npm run test`、`npm run build` | 回退清理项，保留功能改动 |

若任何阶段涉及后端契约，必须另行评审并补跑后端测试；本计划默认不修改后端。

## 6. 高风险点

- 静态预览整体替换正式页会丢失真实行为。
- design fixture 误接正式页面会形成第二业务事实源。
- 解除 `.design-preview-root` 样式作用域可能污染所有按钮、输入框、Leaflet 控件和弹窗。
- `MapMockCanvas.vue` 进入正式 `/map` 会破坏真实 GeoJSON、Leaflet、定位、聚合、新增点位和筛选链路。
- 工单静态批量导出视觉若直接接入，会违背当前逐条生成工作单的接口契约。
- 壳层视觉拆分若打断 `mapStore/mapActions`，会造成顶部地图工具栏与地图页面状态不同步。
- 删除 `data-testid` 或可访问属性会破坏现有单测和回归定位能力。
- 在一个阶段同时修改多个正式页面，会导致回滚边界不清晰。

## 7. 当前状态

| 项目 | 状态 |
|---|---|
| 第一阶段 `/design/*` 静态 Vue 页面和样式还原 | 已完成 |
| 本计划文档 | 已创建 |
| 阶段 A：Token 与基础样式收敛 | 已完成 |
| 阶段 B：正式登录页视觉接入 | 已完成 |
| 阶段 C：正式应用壳层视觉接入 | 已完成 |
| 阶段 D：正式工单页视觉接入 | 已完成 |
| 阶段 E：正式地图页视觉接入 | 已完成 |
| 阶段 F：清理、回归和文档 | 已完成 |

正式视觉接入阶段 A-F 已完成；后续只在用户验收反馈明确后做针对性微调。

## 8. 执行记录

### 2026-06-05：阶段 A 完成

已完成：

- 启动子代理 Lorentz 对阶段 A 做只读核对，子代理未修改文件。
- 在正式全局 `:root` 中补充 OpenDesign 后续接入需要的语义别名 token。
- 新增别名只映射到现有正式 token，不覆盖正式 `--color-primary`、`--font-*`、`--focus-ring`、`--control-height`、`--risk-*` 等业务关键 token。
- 补充 `--color-text`、`--color-text-muted`、`--color-nav`、`--color-map-land/water/road`、`--radius-pill`、`--radius-round`、`--shadow-popover`、`--space-7` 至 `--space-12` 等后续复用所需变量。
- 未导入 `frontend/src/styles/tokens.css` 到正式入口。
- 未解除 `.design-preview-root` 作用域。
- 未修改正式登录、壳层、工单或地图页面模板。
- 清理 `frontend/src/styles.css` 中一处与实际取值不一致的英文临时注释。

验证结果：

- 阶段 A 目标测试：5 个测试文件、69 个测试通过。
- 完整前端测试：20 个测试文件、145 个测试通过。
- `npm run build` 通过。
- Browser 插件在本轮最终浏览器检查时返回 URL policy 拒绝；按插件规则未绕过该限制，浏览器视觉检查留待用户侧或后续可用浏览器会话补做。

下一步：

- 进入阶段 B 前，先确认正式 `/login` 视觉接入范围。
- 阶段 B 只改正式登录页视觉，不改认证、路由守卫或 API。

### 2026-06-05：阶段 B 完成

已完成：

- 启动子代理 Kant 对阶段 B 做只读核对，子代理未修改文件。
- 将正式 `LoginView.vue` 接入 OpenDesign 登录页视觉结构，包括背景网格、等高线装饰、树形装饰、居中卡片、品牌区、安全提示和页脚。
- 保留正式登录行为：`signIn()`、空值校验、toast、`redirect`、`tzlb.rememberedUsername`、`remember_me`、忘记密码和申请加入按钮。
- 新增密码显示/隐藏按钮，并补充单元测试确保只改变本地输入框类型、不触发接口。
- 未修改路由守卫、认证 API、`useAuthSession.js` 或 design 预览路由。
- 未把 `DesignLoginView.vue` 的静态 `@submit.prevent` 逻辑接入正式页面。

验证结果：

- 阶段 B 目标测试：3 个测试文件、14 个测试通过。
- 完整前端测试：20 个测试文件、146 个测试通过。
- `npm run build` 通过。
- Browser 插件访问 `http://127.0.0.1:5174/login` 时返回 `net::ERR_BLOCKED_BY_CLIENT`；按插件安全规则未绕过该限制，浏览器视觉检查留待用户侧或后续可用浏览器会话补做。

下一步：

- 进入阶段 C 前，先确认正式应用壳层视觉接入范围。
- 阶段 C 只改 `App.vue` 壳层视觉和相关样式，不改权限、路由守卫、退出登录或地图 store 工具栏桥接。

### 2026-06-05：阶段 C 完成

已完成：

- 启动子代理 Ohm 对阶段 C 做只读核对，子代理未修改文件。
- 将正式 `App.vue` 桌面壳层接入 OpenDesign 的左侧深色侧栏、业务导航、用户摘要、顶栏标题和内容区布局。
- 保留正式导航数据来源：`visibleNavItems`、`userHasAnyRole`、`homePath` 和 `currentUserName`。
- 保留退出登录流程：`signOut()`、关闭菜单、toast、跳转 `/login` 和 `loggingOut` 防重复点击。
- 保留移动抽屉行为：触发按钮 testid、遮罩关闭、路由切换关闭、Escape 关闭和 body overflow 锁定。
- 保留地图工具栏 store 桥接：视图选择、筛选、图层和显示编号仍全部通过 `mapStore/mapActions`。
- 保留 `hideShell` 与 `fullBleed` route meta；登录页仍不展示正式壳层，地图页仍满宽。
- 未接入 `DESIGN_NAV_GROUPS`、`DESIGN_PREVIEW_PROFILE`、`STATIC PREVIEW`、`迁移状态` 或 `/design/*` fixture。
- 补充 AppShell 测试，覆盖正式侧栏导航和调查员权限过滤。

验证结果：

- 阶段 C 目标测试：4 个测试文件、64 个测试通过。
- 完整前端测试：20 个测试文件、146 个测试通过。
- `npm run build` 通过。
- Browser 插件当前对本地页面返回 URL policy 拒绝；按插件安全规则未绕过该限制，浏览器视觉检查留待用户侧或后续可用浏览器会话补做。

下一步：

- 进入阶段 D 前，先确认正式工单页视觉接入范围。
- 阶段 D 只改工单页展示层，不改调查导入、字段归一化、校验、编辑、删除或逐条导出链路。

### 2026-06-05：阶段 D 完成

已完成：

- 启动子代理 Godel 对阶段 D 做只读核对，子代理未修改文件。
- 将正式 `WorkOrderView.vue` 接入 OpenDesign 工单页视觉结构，包括页头、控制台说明、统计卡、记录工作区工具栏和更紧凑的表格面板。
- 调整 `RecordTable.vue` 的正式表格和移动卡片展示密度，保留 props、events 和 selection 行为。
- 保留 `SurveyImportDialog`、`RecordDetailModal`、`fieldConfig`、`selectedIndexes`、`normalizeRecordForPest()`、`validateRecords()`、`toPayloadRecord()`、逐条 `generateWorkorder()` 和 `downloadBlob` 链路。
- 未接入 design workorder fixture、`selectedIds`、`activeOverlay`、静态状态机或静态导入/导出弹窗逻辑。
- 未修改后端、工单 API、认证或下载工具。

验证结果：

- 阶段 D 目标测试：5 个测试文件、36 个测试通过。
- 完整前端测试：20 个测试文件、146 个测试通过。
- `npm run build` 通过。
- Browser 插件此前对本地页面返回 URL policy/`ERR_BLOCKED_BY_CLIENT`；本阶段未绕过该限制，浏览器视觉检查留待用户侧或后续可用浏览器会话补做。

下一步：

- 进入阶段 E 前，先确认正式地图页视觉接入范围。
- 阶段 E 只接入地图外层视觉，不用 `MapMockCanvas` 替换 `LeafletMap`，不改地图 API、store 或新增点位流程。

### 2026-06-05：阶段 E 完成

已完成：

- 将正式 `MapView.vue` 接入 OpenDesign 地图页外层视觉，包括沉浸式地图工作区、背景纹理、状态提示、右侧详情抽屉、新增点位抽屉和移动端底部操作条。
- 保留正式 `LeafletMap.vue`，继续由它负责真实底图、点位、聚合、编号、定位、图例和新增点位地图点击事件。
- 保留 `listMapViews()`、`fetchMapView()`、`fetchMapFilterOptions()`、`fetchAdminBoundary()`、`fetchWhiteMothSiteCodeRules()` 和 `createWhiteMothSite()` 调用链。
- 保留 `mapStore/mapActions` 与 `App.vue` 顶部地图工具栏桥接，视图选择、筛选、图层和编号开关仍走正式 store。
- 保留 GeoJSON 请求 token、旧请求丢弃、保存美国白蛾点位后刷新并切换视图、保存后不自动缩放等行为。
- 未接入 `MapMockCanvas.vue`、`DESIGN_MAP_MARKERS`、`DESIGN_MAP_CLUSTERS`、`DESIGN_MAP_POINT_DETAILS` 或静态图层 fixture。
- 未修改地图 API、后端、认证、路由守卫或 `App.vue` 壳层工具栏。

验证结果：

- 阶段 E 目标测试：4 个测试文件、60 个测试通过。
- 完整前端测试：20 个测试文件、146 个测试通过。
- `npm run build` 通过。
- `MapView.vue` 正式样式未使用未定义的 design-only `--color-surface-soft` token。
- Browser 插件此前对本地页面返回 URL policy/`ERR_BLOCKED_BY_CLIENT`；本阶段未绕过该限制，浏览器视觉检查留待用户侧或后续可用浏览器会话补做。

下一步：

- 进入阶段 F 前，先确认是否开始收口清理。
- 阶段 F 只做重复样式、阶段文档和最终回归收口，不新增页面、不连接新 API、不改正式业务行为。

### 2026-06-05：阶段 F 完成

已完成：

- 审查正式视觉接入累计改动，重点核对 design fixture、design-only token、地图 store 桥接和旧样式残留。
- 删除 `MapView.vue` 中已经不再被模板使用的旧筛选抽屉 CSS 和 `filterHint` 计算属性。
- 保留 `App.vue` 顶部地图筛选、图层、视图和编号工具栏，未改 `mapStore/mapActions`。
- 保留 `/design/*` 对照入口、design fixture 和预览组件，未做批量删除。
- 更新本计划状态，标记阶段 A-F 完成。

验证结果：

- 完整前端测试：20 个测试文件、146 个测试通过。
- `npm run build` 通过。
- `git diff --check` 通过。
- `MapView.vue` 不再残留旧筛选抽屉选择器或 `filterHint`。
- Browser 插件此前对本地页面返回 URL policy/`ERR_BLOCKED_BY_CLIENT`；本阶段未绕过该限制，浏览器视觉检查留待用户侧补做。

后续边界：

- 若继续调整，应基于用户实际预览反馈做单点视觉修正。
- 不建议在未验收前删除 `/design/*` 预览资产。
