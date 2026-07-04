# 林业调查工作台前端设计规范

适用范围：`index.html`、`login.html`、`workorder.html`、`map.html` 后续拆分为 Vue 组件时的视觉与交互基础规范。整体方向为现代克制的森林绿政务 GIS 工作台：高信息密度、低装饰、清晰边界、状态色克制使用。

## 1. 颜色变量

基础变量建议放在全局样式，例如 `src/styles/tokens.css`。

```css
:root {
  --color-bg: oklch(97.8% 0.006 155);
  --color-surface: oklch(100% 0 0);
  --color-text: oklch(20% 0.036 158);
  --color-text-muted: oklch(50% 0.022 158);
  --color-border: oklch(89% 0.014 155);
  --color-primary: oklch(43% 0.105 155);
  --color-nav: oklch(25% 0.072 157);
  --color-nav-soft: oklch(31% 0.072 157);

  --color-info: oklch(57% 0.115 235);
  --color-warning: oklch(74% 0.14 84);
  --color-warning-text: oklch(55% 0.14 84);
  --color-danger: oklch(58% 0.16 28);

  --color-map-land: oklch(93% 0.025 145);
  --color-map-water: oklch(88% 0.055 225);
  --color-map-road: oklch(98% 0.005 145);

  --color-primary-soft: color-mix(in oklch, var(--color-primary) 8%, var(--color-surface));
  --color-info-soft: color-mix(in oklch, var(--color-info) 8%, var(--color-surface));
  --color-warning-soft: color-mix(in oklch, var(--color-warning) 12%, var(--color-surface));
  --color-danger-soft: color-mix(in oklch, var(--color-danger) 8%, var(--color-surface));
}
```

使用规则：
- 主背景使用 `--color-bg`，卡片、表格、弹窗、抽屉使用 `--color-surface`。
- 主操作、选中态、焦点态使用 `--color-primary`，不要再引入第二个主色。
- `--color-info` 表示待复核/进行中，`--color-warning` 表示中度风险，`--color-danger` 表示紧急处置/高风险。
- 地图底图只使用 `--color-map-*`，避免把业务卡片色直接套到地图区域。

## 2. 字体层级

```css
:root {
  --font-display: "Songti SC", "STSong", "Noto Serif CJK SC", "Iowan Old Style", Georgia, serif;
  --font-body: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  --font-mono: "SFMono-Regular", "JetBrains Mono", "Cascadia Code", ui-monospace, monospace;

  --text-2xs: 10px;
  --text-xs: 11px;
  --text-sm: 12px;
  --text-md: 13px;
  --text-base: 14px;
  --text-lg: 16px;
  --text-xl: 18px;
  --text-title: clamp(24px, 2.2vw, 32px);
  --text-hero: clamp(38px, 5vw, 62px);

  --line-body: 1.55;
  --line-title: 1.25;
  --line-hero: 1.08;
}
```

层级规则：
- 页面标题：`--font-display` + `--text-title`，用于工作台页头。
- 卡片标题/弹窗标题/抽屉标题：`--font-display` + `18px` 左右。
- 正文、表格、按钮：`--font-body`，默认 `14px`，表格可降至 `13px`。
- 编号、坐标、数量、表头、英文元信息：`--font-mono` + `font-variant-numeric: tabular-nums`。

## 3. 间距规则

```css
:root {
  --space-1: 4px;
  --space-2: 6px;
  --space-3: 8px;
  --space-4: 10px;
  --space-5: 12px;
  --space-6: 14px;
  --space-7: 16px;
  --space-8: 18px;
  --space-9: 20px;
  --space-10: 22px;
  --space-11: 24px;
  --space-12: 30px;
}
```

布局规则：
- 桌面内容区内边距：`22px`。
- 平板/窄屏内容区内边距：`16px`。
- 手机内容区内边距：`12px`。
- 卡片内部：`14px 16px` 或 `18px`。
- 表格单元格：`11px 14px`，表头 `10px 14px`。
- 表单网格间距：横向 `16px`，纵向 `14px`。

## 4. 圆角规则

```css
:root {
  --radius-xs: 6px;
  --radius-sm: 7px;
  --radius-md: 8px;
  --radius-lg: 10px;
  --radius-xl: 12px;
  --radius-2xl: 14px;
  --radius-sheet: 16px;
  --radius-pill: 999px;
  --radius-round: 50%;
}
```

使用规则：
- 输入框、下拉框、分段按钮内按钮：`--radius-sm`。
- 普通按钮、导航项、小卡片：`--radius-md`。
- 地图控件、统计卡、上传区：`--radius-lg`。
- 面板、表格容器：`--radius-xl`。
- 弹窗、登录卡片：`--radius-2xl`。
- 移动端底部抽屉顶部圆角：`16px 16px 0 0`。

## 5. 阴影规则

```css
:root {
  --shadow-sm: 0 4px 16px color-mix(in oklch, var(--color-text) 8%, transparent);
  --shadow-card: 0 1px 0 color-mix(in oklch, var(--color-text) 3%, transparent);
  --shadow-hover: 0 16px 40px color-mix(in oklch, var(--color-text) 9%, transparent);
  --shadow-popover: 0 12px 36px color-mix(in oklch, var(--color-text) 10%, transparent);
  --shadow-drawer: -14px 0 40px color-mix(in oklch, var(--color-text) 12%, transparent);
  --shadow-bottom-bar: 0 -8px 24px color-mix(in oklch, var(--color-text) 12%, transparent);
}
```

使用规则：
- 常规面板优先用边框，不使用重阴影。
- 悬浮图层、Toast、弹窗、抽屉才使用明显阴影。
- 地图控件使用 `--shadow-sm` + `backdrop-filter: blur(10px)`。

## 6. 按钮样式

```css
.btn {
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 9px 16px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  font-weight: 650;
  transition: background 160ms ease, border-color 160ms ease, transform 80ms ease;
}

.btn:active { transform: translateY(1px); }

.btn-primary {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-surface);
}

.btn-primary:hover {
  background: color-mix(in oklch, var(--color-primary) 88%, var(--color-text));
}

.btn-secondary {
  border-color: var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
}

.btn-secondary:hover {
  border-color: color-mix(in oklch, var(--color-primary) 45%, var(--color-border));
  background: color-mix(in oklch, var(--color-primary) 4%, var(--color-surface));
}

.btn-ghost {
  border-color: transparent;
  background: transparent;
  color: var(--color-text-muted);
}

.btn-danger {
  border-color: color-mix(in oklch, var(--color-danger) 24%, var(--color-border));
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

.icon-btn {
  width: 36px;
  height: 36px;
  display: inline-grid;
  place-items: center;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text);
}
```

交互规则：
- 桌面按钮最小高度 `40px`，登录/移动端主按钮最小 `44px`。
- 图标按钮常规 `36px`，表格行内操作 `30px`。
- 危险操作不能使用纯红实心按钮，优先使用浅红底 + 红色文字。

## 7. 输入框样式

```css
.input,
.textarea {
  width: 100%;
  min-height: 40px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  outline: none;
  background: var(--color-surface);
  color: var(--color-text);
  transition: border-color 160ms ease, box-shadow 160ms ease;
}

.input { padding: 0 11px; }

.textarea {
  min-height: 88px;
  padding: 9px 11px;
  resize: vertical;
}

.input:focus,
.textarea:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px color-mix(in oklch, var(--color-primary) 12%, transparent);
}
```

表单规则：
- 表单标签使用 `12px`、`600`、`--color-text-muted`。
- 必填星号使用 `--color-danger`。
- 密码显示按钮、辅助链接在移动端触控区域不小于 `44px`。

## 8. 下拉框样式

```css
.select {
  width: 100%;
  min-height: 40px;
  padding: 0 34px 0 11px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  outline: none;
  background-color: var(--color-surface);
  color: var(--color-text);
  transition: border-color 160ms ease, box-shadow 160ms ease;
}

.select:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px color-mix(in oklch, var(--color-primary) 12%, transparent);
}
```

下拉规则：
- 与输入框同高、同圆角、同焦点环。
- 筛选型下拉应放在工具栏或控制栏中，不单独使用大面积卡片包裹。
- 表格筛选下拉文案要使用业务字段，例如“害虫类型”“统防统治任务”。

## 9. 表格样式

```css
.table-panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  background: var(--color-surface);
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-md);
}

.data-table th {
  padding: 10px 14px;
  border-bottom: 1px solid var(--color-border);
  background: color-mix(in oklch, var(--color-bg) 60%, var(--color-surface));
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: var(--text-2xs);
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  text-align: left;
  white-space: nowrap;
}

.data-table td {
  padding: 11px 14px;
  border-bottom: 1px solid color-mix(in oklch, var(--color-border) 60%, transparent);
  vertical-align: middle;
}

.data-table tr:hover td {
  background: color-mix(in oklch, var(--color-primary) 3%, var(--color-surface));
}
```

表格规则：
- 桌面端保留表格以保证信息密度。
- `920px` 以下切换为卡片列表，不横向压缩表格。
- 数值、坐标、编号单元格使用 `--font-mono`。
- 表头不使用深色底，保持轻量政务系统质感。

## 10. 弹窗样式

```css
.dialog {
  width: min(520px, calc(100vw - 28px));
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-2xl);
  background: var(--color-surface);
  color: var(--color-text);
  box-shadow: var(--shadow-popover);
}

.dialog::backdrop {
  background: color-mix(in oklch, var(--color-text) 42%, transparent);
  backdrop-filter: blur(3px);
}

.dialog-head,
.dialog-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 14px 16px;
}

.dialog-head { border-bottom: 1px solid var(--color-border); }
.dialog-body { padding: 16px; }
.dialog-foot { justify-content: flex-end; border-top: 1px solid var(--color-border); }
```

弹窗规则：
- 用于导入确认、批量生成确认、风险提示等短流程。
- 弹窗宽度默认 `520px`，不要超过 `640px`。
- 弹窗内表格预览最大高度建议 `240px` 并允许内部滚动。

## 11. 抽屉样式

```css
.drawer {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 51;
  width: min(520px, calc(100vw - 40px));
  display: flex;
  flex-direction: column;
  border-left: 1px solid var(--color-border);
  background: var(--color-surface);
  box-shadow: var(--shadow-drawer);
  transform: translateX(100%);
  transition: transform 220ms ease;
}

.drawer.open { transform: translateX(0); }
.drawer-head { padding: 16px 20px; border-bottom: 1px solid var(--color-border); }
.drawer-scroll { flex: 1; overflow: auto; padding: 20px; }
.drawer-foot { padding: 14px 20px; border-top: 1px solid var(--color-border); }
```

抽屉规则：
- 地图点位详情抽屉桌面宽度约 `390px`，工单编辑抽屉约 `520px`。
- `920px` 以下地图详情改为底部抽屉，高度 `min(62vh, 560px)`。
- 抽屉内信息使用分组区块，分组之间用 `border-top`，不要堆叠重卡片。

## 12. Toast 样式

```css
.toast {
  position: fixed;
  right: 22px;
  bottom: 22px;
  z-index: 80;
  max-width: min(360px, calc(100vw - 28px));
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border: 1px solid color-mix(in oklch, var(--color-primary) 20%, var(--color-border));
  border-radius: 9px;
  background: var(--color-surface);
  box-shadow: var(--shadow-popover);
  transform: translateY(20px);
  opacity: 0;
  pointer-events: none;
  transition: opacity 180ms ease, transform 180ms ease;
}

.toast.show {
  transform: translateY(0);
  opacity: 1;
}

.toast-dot {
  width: 9px;
  height: 9px;
  border-radius: var(--radius-round);
  background: var(--color-primary);
}
```

Toast 规则：
- 用于地图图层切换、定位、筛选结果、导入完成等轻反馈。
- 显示时长建议 `2200ms`。
- 不用于阻断性错误，阻断性错误用弹窗或表单校验。

## 13. 地图控件样式

```css
.map-workspace {
  position: relative;
  min-height: 0;
  flex: 1;
  overflow: hidden;
  background-color: var(--color-map-land);
}

.map-control-card {
  position: absolute;
  z-index: 8;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: color-mix(in oklch, var(--color-surface) 95%, transparent);
  box-shadow: var(--shadow-sm);
  backdrop-filter: blur(10px);
}

.map-filter-card {
  left: 14px;
  top: 14px;
  width: 292px;
}

.map-tool-stack {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 9;
  display: grid;
  gap: 8px;
}

.map-marker {
  position: absolute;
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border: 3px solid var(--color-surface);
  border-radius: var(--radius-round);
  background: var(--color-nav);
  box-shadow: var(--shadow-sm);
}

.map-cluster {
  width: 42px;
  height: 42px;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 700;
}
```

地图规则：
- 搜索/筛选面板左上，图层/定位/缩放工具右上。
- 搜索筛选面板必须支持收起，收起后保留搜索框，避免遮挡地图视线。
- 图层面板区分“基础图层”和“点位图层”。点位图层使用小圆点 + 名称 + 数量。
- 移动端底部操作栏固定在地图底部，按钮高度不低于 `42px`。

## 14. 响应式断点

```css
:root {
  --bp-mobile-compact: 430px;
  --bp-mobile: 680px;
  --bp-tablet: 920px;
  --bp-laptop: 1180px;
}
```

断点规则：
- `1180px`：侧边栏从 `228px` 收窄到 `196px`，右侧辅助栏收窄。
- `920px`：主布局从侧边栏 + 内容改为单列；侧边栏隐藏为移动抽屉；工单表格切换为卡片；地图详情抽屉改为底部抽屉。
- `680px`：页头操作纵向堆叠；表单双列改为单列；地图筛选面板默认隐藏筛选体，只保留搜索入口。
- `430px`：内容边距降至 `12px`；登录卡片降低阴影；保证所有可点击控件不小于 `42px`，关键操作不小于 `44px`。

## 15. 不应该使用的样式反例

- 不要使用大面积渐变背景替代当前森林绿政务底色。
- 不要使用紫色、粉色、橙棕色作为默认主色或页面洗底色。
- 不要把每个卡片都做成重阴影悬浮卡，当前系统以边框和留白表达层级。
- 不要在表格行使用彩色左边框作为状态表达，状态应使用徽标、圆点、浅色底。
- 不要在地图控件中加入“设计器控件”“视口选择器”“主题切换器”等非业务 UI。
- 不要把桌面表格强行压缩到手机宽度，移动端应切换为工单卡片。
- 不要用纯黑文本、纯灰边框、纯白背景组合成无品牌感界面，应使用 OKLch 变量。
- 不要在普通表单里使用 20px 以上大圆角，圆角应保持 7-14px 的克制范围。
- 不要使用大面积实心红色按钮表达危险操作，改用浅红底和红色文字。
- 不要用 emoji 作为功能图标，继续使用线性 SVG 图标。

## Vue 组件拆分建议

- `AppShell.vue`：侧边栏、主内容区、移动菜单状态。
- `BaseButton.vue` / `IconButton.vue`：封装按钮尺寸、状态、图标布局。
- `BaseInput.vue` / `BaseSelect.vue` / `BaseTextarea.vue`：共享焦点环与标签结构。
- `DataTable.vue`：桌面表格；移动端可通过 `WorkorderCardList.vue` 单独实现。
- `BaseDialog.vue`：导入确认、批量确认。
- `BaseDrawer.vue`：工单编辑抽屉、点位详情抽屉。
- `ToastProvider.vue`：统一消息队列和 2200ms 自动隐藏。
- `MapControls.vue`：搜索面板、图层面板、地图工具栈、移动端底部操作栏。
