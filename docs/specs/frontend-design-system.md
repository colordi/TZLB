# 林业调查工作台 · 前端设计规范

版本：v1.0（2026-07-22）　适用：`frontend/` 全部页面与组件
地位：本文件是前端 UI 的唯一现行规范。旧《DESIGN.md》（森林绿宋体方案）与《ui-shadcn-vue-rebuild-plan》（Claude 暖橙方案）均已作废。

---

## 1. 设计原则

1. **领域优先**：这是一个林业有害生物调查与防治的政务 GIS 工作台。视觉语言取"深林绿 + 暖灰"，沉稳、克制、信息密度优先，不追求营销感。
2. **唯一来源**：每种 UI 元素只有一个实现（见 §6 组件规范）。禁止平行造第二套按钮、弹窗、分页、空态。
3. **语义 token 优先**：任何颜色必须来自语义 token（§2），业务代码禁止出现裸 hex/rgb 颜色与 Tailwind 调色板直色（如 `bg-emerald-500`、`text-amber-800`）。
4. **浅色单主题**：仅 light。token 结构预留未来扩展暗色的可能，但当前不实现、不预留半成品代码。
5. **可访问性内建**：交互控件可键盘到达、焦点可见；弹窗焦点管理由 reka-ui 承担；测试钩子统一 `data-testid`，样式类不做测试选择器。

技术底座：Vue 3 + Tailwind CSS v4（**不启用 preflight**）+ shadcn-vue（new-york 风格）+ reka-ui + Leaflet + vue-sonner。

---

## 2. 色彩系统

### 2.1 主题文件与加载

- 主题定义：`frontend/src/styles/themes/forestry-light.css`（`:root` oklch 变量 + `@theme inline` 映射）。
- 入口：`frontend/src/styles/shadcn.css`（Tailwind theme/utilities + 主题）。
- `frontend/src/styles.css`：仅盒模型重置、滚动条、入场动画等基础层，**不再承担颜色 token 桥接**。

### 2.2 核心语义 token（light）

| token | 值（oklch） | 用途 |
|---|---|---|
| `--background` / `--foreground` | `0.982 0.004 150` / `0.28 0.02 155` | 页面底色（近白微绿）/ 主文字（深绿灰墨） |
| `--card` / `--card-foreground` | `1 0 0` / 同 foreground | 卡片面（纯白） |
| `--popover` / `--popover-foreground` | `1 0 0` / 同 foreground | 浮层面 |
| `--primary` / `--primary-foreground` | `0.52 0.09 155` / `0.985 0.004 150` | 主品牌绿：主按钮、激活态、链接强调（白字对比度 ≥ 4.5:1） |
| `--secondary` / `--secondary-foreground` | `0.94 0.012 150` / `0.36 0.03 155` | 次级面：次按钮、弱强调 |
| `--muted` / `--muted-foreground` | `0.955 0.008 150` / `0.52 0.015 155` | 弱底 / 次要文字、占位符 |
| `--accent` / `--accent-foreground` | `0.93 0.018 150` / `0.32 0.03 155` | hover/选中弱底色 |
| `--destructive` / `--destructive-foreground` | `0.577 0.215 27.3` / `0.985 0.004 150` | **真红**。删除等危险操作、错误文字 |
| `--border` / `--input` / `--ring` | `0.905 0.008 150` / `0.86 0.01 150` / 同 primary | 边框 / 控件边框 / 焦点环 |
| `--radius` | `0.5rem` | 基准圆角 |

### 2.3 反馈语义 token

| token | 值 | 用途 |
|---|---|---|
| `--success` / `--success-foreground` | `oklch(0.55 0.11 150)` / 近白 | 成功（toast 图标、校验通过、完成态） |
| `--warning` / `--warning-foreground` | `oklch(0.75 0.14 85)` / `oklch(0.32 0.04 80)` | 警告条、需注意状态 |
| `--info` / `--info-foreground` | `oklch(0.55 0.11 250)` / 近白 | 信息提示（toast 图标） |

用法：`text-success`、`bg-warning/10`、`border-warning/30` 等（Tailwind 透明度修饰符可用）。

### 2.4 图表色

`--chart-1..5`：绿系为主、蓝橙辅：`oklch(0.52 0.09 155)`、`oklch(0.65 0.12 130)`、`oklch(0.72 0.13 90)`、`oklch(0.55 0.11 250)`、`oklch(0.60 0.13 30)`。

### 2.5 领域色（值锁定，属行业判读约定）

危害程度四色是调查行业的既定判读约定，**色值不可调整**，只允许纳入 token 管理：

| token | 值 | 含义 |
|---|---|---|
| `--severity-none` | `#ffffff` | 无危害 |
| `--severity-light` | `#0033ff` | 轻度 |
| `--severity-medium` | `#fbff05` | 中度 |
| `--severity-high` | `#ff0000` | 重度 |

其他领域 token：`--map-boundary: #D97706`（行政区边界）、`--map-boundary-soft: rgba(217,119,6,0.46)`。

Leaflet 运行时需要 JS 侧色值（circleMarker、图例、图层色板、地块状态色 调查红/伐除黑/其他白、定位蓝等）：唯一来源是 `frontend/src/config/map-palette.js`，其危害程度色值必须与上表一致；CSS 侧引用 `--severity-*` token。两侧注释互相指向。

### 2.6 颜色使用规则

- ✅ `bg-primary text-primary-foreground`、`text-muted-foreground`、`bg-destructive/10 text-destructive`、`border-warning/30 bg-warning/10 text-warning-foreground`
- ❌ 裸 hex/rgb（`#D97706`、`rgba(229,72,77,.08)`）、Tailwind 直色（`bg-emerald-500`、`text-amber-800`）、`style="{ color: ... }"` 内联色（Leaflet 图层色除外，且值必须来自 map-palette.js）
- 状态语义映射：**危险/错误=destructive 红；成功/可调查=success 绿；警告/待处理=warning 琥珀；普通信息=muted；主操作=primary**。不要再发明第五种状态色。

---

## 3. 字体与排版

- 字族：单一 sans 栈 `ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif`；标题与正文同族，不引入任何 Web 字体。等宽仅用于编号/代码：`--font-mono`。
- 字号档位（rem）：`0.75 / 0.8125 / 0.875 / 1 / 1.125 / 1.25 / 1.5 / 1.875`，对应 Tailwind `text-xs / sm / base / lg / xl / 2xl / 3xl`。
- 页面标题：`text-2xl font-semibold tracking-tight`（不随断点放大）；页面描述：`text-sm text-muted-foreground`。
- 表格正文 `text-sm`；辅助说明 `text-xs text-muted-foreground`；表单错误 `text-xs text-destructive`。
- 数字（统计值、计数）：`font-semibold` 起步，统计大数 `text-2xl font-bold tracking-tight`。

---

## 4. 间距、圆角、阴影、动效

- 间距：Tailwind 4px 基；页面模块间距 `space-y-6`（24px），卡片内部 `gap-4`，表单字段 `gap-3`，紧凑工具行 `gap-2`。不使用 `var(--space-*)` 旧 token。
- 圆角：`--radius: 0.5rem`；`rounded-md`(6px) 控件、`rounded-lg`(8px) 小面板、`rounded-xl`(12px) 卡片/表壳；徽章/状态点 `rounded-full`。
- 阴影：卡片 `shadow-sm`；浮层/下拉 `shadow-md`；弹窗 `shadow-lg`。不使用自绘彩色阴影。
- 动效：`120/180/240ms` + `cubic-bezier(0.2, 0, 0, 1)`。hover 只做颜色/阴影变化，**不做位移**（无 `translateY`）。页面入场动画 `fade-up` 仅保留在全局基础层。
- 焦点：所有可交互元素聚焦可见（组件库已带 `focus-visible` ring）；禁止 `outline-none` 后不给替代焦点样式。

---

## 5. 布局规范

### 5.1 页面骨架（唯一）

```html
<div class="mx-auto w-full max-w-6xl space-y-6">
  <PageHeader title="…" description="…">
    <template #actions>…</template>
  </PageHeader>
  …
</div>
```

- 宽度三档：默认 `max-w-6xl`；数据密集页（数据管理）`max-w-[90rem]`；地图页 `full-bleed`（meta.fullBleed）。
- 页头统一用共享组件 `components/common/PageHeader.vue`（标题 + 描述 + actions 插槽），不再手写页头，不使用 overline 装饰文字。

### 5.2 卡片

统一 `ui/card`（`rounded-xl border bg-card shadow-sm`）。卡片头：`CardHeader` + `CardTitle`（`text-base font-semibold`）+ `CardDescription`。统计数值卡直接复用 Card，不另造 summary-card。

### 5.3 响应式

- 断点用 Tailwind 默认（sm/md/lg）。表单栅格 `grid gap-4 md:grid-cols-2`；统计卡 `sm:grid-cols-2 lg:grid-cols-4`。
- 移动端（<768px）：侧边栏走 Sheet 抽屉（已有）；表格允许 `overflow-x-auto` 横向滚动，关键操作页提供卡片式替代（工单记录已有移动卡片视图，保留）。

---

## 6. 组件规范（每类元素的唯一实现）

| 元素 | 唯一实现 | 已废弃（不得新增使用） |
|---|---|---|
| 按钮 | `ui/button`：variant `default/destructive/outline/secondary/ghost/link`；size `default(h-9)/xs/sm/lg/icon/icon-xs/icon-sm/icon-lg` | 原生 `<button>`、全局 `button:not([data-slot])` 样式、`.button-secondary`、`.button-danger`、一切自绘按钮类 |
| 危险操作 | 主确认按钮 `variant="destructive"`；列表内危险项 `variant="ghost" size="icon-sm"` + `text-destructive` | 手贴 `bg-destructive` 类、描边红钮、原生 `confirm()` |
| 弹窗 | `ui/dialog`（内容型，含 `DialogHeader/Title/Description/Footer`）；确认型一律 `ui/alert-dialog` | `BaseDialog`、`ConfirmDialog`、原生 `confirm()`、手写 teleport 弹层 |
| 全局提示 | vue-sonner，经 `useToast()` 调用：`success(message, title?) / error(...) / info(...)` | `ToastViewport`、行内自制通知条 |
| 输入 | `ui/input`（h-9） | 原生 `<input>`、全局 `input:not([data-slot])` 样式 |
| 选择 | `ui/native-select`（简单场景）；`ui/select`（需要搜索/自定义展现时） | 裸 `<select>`、自绘下拉 |
| 多行文本 | `ui/textarea` | 裸 `<textarea>` |
| 勾选/开关 | `ui/checkbox`；互斥开启用 `ui/switch` | CSS 画勾、checkbox 当开关 |
| 日期 | `ui/date-picker`（DatePickerField） | `<Input type="date">`（仅原生兼容兜底时允许） |
| 标签徽章 | `ui/badge`：variant `default/secondary/destructive/outline` | 自绘 chip/角标 |
| 状态点 | `<span class="size-2 rounded-full bg-success">` + `text-sm` 文字 | 各色自绘圆点 |
| 表格 | `ui/table` + 统一表壳（见下） | 手写 `<table>` 与自绘表样式 |
| 分页 | `ui/pagination` | 自绘上一页/下一页 |
| 视图切换 | `ui/tabs` | 自绘分段控件 |
| 值选择（虫种/表选择等单选值） | 一排 `ui/button`：选中 `default`、未选 `outline`，`size="sm"` | 其他自绘单选排 |
| 加载 | 卡片/区块初载：`ui/skeleton`；表格加载：加载行；按钮内加载：`Loader2`/`RefreshCw` + `animate-spin` | 自绘 spinner CSS |
| 空态 | 共享 `components/common/EmptyState.vue` | 各种自绘空态 |
| 图标 | `@lucide/vue` 按需引入，尺寸 `size-4` 为基准 | 内联手写 SVG（组件库内部除外） |

### 6.1 表格范式

```html
<div class="overflow-hidden rounded-xl border bg-card shadow-sm">
  <div class="overflow-x-auto">
    <Table>
      <TableHeader><TableRow class="hover:bg-transparent">…</TableRow></TableHeader>
      <TableBody>
        <!-- 加载/空态：单行 -->
        <TableRow v-if="loading">
          <TableCell :colspan="N" class="h-24 text-center text-muted-foreground">加载中…</TableCell>
        </TableRow>
        <TableRow v-else-if="!rows.length">
          <TableCell :colspan="N" class="h-24 text-center text-muted-foreground">暂无数据</TableCell>
        </TableRow>
      </TableBody>
    </Table>
  </div>
</div>
```

- 列多需横滚时容器加 `min-w-[48rem]`（按内容定，取 48/56 两档之一）。
- 行 hover 用组件默认 `hover:bg-muted/50`；表头行固定 `hover:bg-transparent`。

### 6.2 弹窗范式

- 内容弹窗：`DialogContent` 宽度 `sm:max-w-md`（表单）/ `sm:max-w-xl`（宽表单）/ `sm:max-w-3xl`（导入、详情），高内容加 `max-h-[85vh] overflow-y-auto`。
- 副标题必须用 `DialogDescription`，不用裸 `<p>`。
- 确认弹窗固定结构：`AlertDialogTitle` 一句话说清后果 + `AlertDialogDescription` 补充 + 取消 `AlertDialogCancel` + 确认 `AlertDialogAction variant="destructive"`（危险时）。

### 6.3 Toast 使用

- 操作成功/失败/一般提示分别用 `success/error/info`；`error` 文案携带具体原因；不要在同一动作里 toast 与行内错误双发（表单校验错误放行内，操作结果走 toast）。

---

## 7. 地图域规范

- 色值唯一来源 `frontend/src/config/map-palette.js`：危害程度、地块状态、点位/参考图层色板、行政边界、定位标记。LeafletMap.vue、popupFields.js、MapView 图例全部引用它。
- 地图浮层（搜索面板、详情抽屉、图层面板、图例）：视觉 = 卡片语言（`bg-card/95 backdrop-blur rounded-xl border shadow-md`），控件一律 ui/*（button、native-select、checkbox、input）。
- Leaflet 自有 DOM（控件、tooltip）通过 `:deep()` 定制，颜色引用 token，不写裸色。
- 点位图层色板（6 色）与危害程度色职责分离：色板区分图层，程度色只在按危害渲染模式下使用，图例说明当前着色语义。

---

## 8. 工程规则

1. 新 UI 一律使用 `@/components/ui/*` 与共享组件（`@/components/common/*`）；缺组件时用 `npx shadcn-vue@latest add <x>` 添加，不从别库引入第二套组件。
2. 业务模板中的测试钩子用 `data-testid`；删除无用 class（无 CSS 定义、仅历史残留的类名一并清除）。
3. 样式写法优先级：Tailwind 语义类 > 共享组件 > 组件内 scoped 样式（仅地图等特殊场景）。 scoped 样式中颜色必须用 `var(--*)` token。
4. 不引入新的全局元素样式（`button {}`、`input {}` 这类）。元素级重置由 Tailwind preflight 承担（`styles/shadcn.css` 引入，`@layer base`）；全局基础层 `styles.css` 只放应用级文档样式（html/body）、滚动条、动画。层顺序由 `styles/shadcn.css` 顶部 `@layer theme, base, components, utilities;` 显式声明，base 必须始终低于 utilities。
5. 修改前端后必须 `npm run build` 验证通过；提交前 `npm test` 全绿。
6. 魔法值集中：分页大小、图片上限等写在对应模块顶部常量，并在规范相关处注明（图片上限 4 张以 `fieldConfig.js` 为准）。

## 9. 已知遗留风险（本规范不解决，记录在案）

- 天地图 tk key 明文硬编码于 `LeafletMap.vue`（应迁环境变量，另行处理）。
- `@tanstack/vue-table` 仅被 `ui/table/utils.js` 引用一个工具函数，保留观察。
