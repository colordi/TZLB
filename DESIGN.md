# 林业调查工作台设计系统

> 类目：林业调查、地图作业、虫害监测  
> 设计理念：专业、清晰、可信、地图优先，让调查人员快速判断点位分布、风险等级和下一步操作

---

## 1. 设计理念与氛围

**核心理念**：以地图和调查数据为中心，界面保持克制，颜色只服务于导航、状态、风险和空间层级。

**视觉定位**：
- 专业稳重，适合政企、林业、应急和监测场景
- 地图优先，界面控件不抢占点位、边界和风险信息
- 低噪音，减少大面积高饱和色和装饰性背景
- 状态清晰，虫害风险、通用反馈和地图图层各有独立语义

**适用场景**：
- 林业调查点位管理
- 虫害发生情况监测
- 地图视图、筛选、图层切换
- 工单录入、记录审核、现场数据补录
- 风险研判、专题图和作业调度

---

## 2. 色彩系统

### 主色板

| 语义角色 | 色值 | 用途 |
|---------|------|------|
| Forest | `#14532D` | 主导航、关键选中态、主操作 |
| Leaf | `#2F7D46` | 次级强调、可点击状态、筛选激活 |
| Moss | `#6B8F3E` | 轻量强调、辅助图标、柔和状态 |
| Mist | `#F4F7F2` | 页面背景、地图外壳、低干扰区域 |
| Surface | `#FFFFFF` | 顶栏、卡片、浮层、输入框 |
| Ink | `#17231A` | 主文本、重要数字、标题 |
| Muted | `#637064` | 辅助文本、说明、禁用信息 |

### 地图与业务色

| 语义角色 | 色值 | 用途 |
|---------|------|------|
| Map Boundary | `#D97706` | 行政边界、区域轮廓、地图重点线 |
| Map Boundary Soft | `rgba(217, 119, 6, 0.46)` | 默认边界线、非选中区域 |
| Point Default | `#FFFFFF` | 普通调查点位 |
| Point Stroke | `#1F2933` | 点位描边，保证卫星底图可见 |
| Selected Point | `#2563EB` | 当前选中点位 |
| Active Area | `#C2410C` | 当前选中区域或重点范围 |

### 虫害风险分级

虫害风险色独立于通用 UI 状态色，避免“成功/错误”与“危害程度”混淆。

| 风险等级 | 色值 | 用途 |
|---------|------|------|
| Risk None | `#E7F3E8` | 无危害、低关注点位背景 |
| Risk Light | `#8BC34A` | 轻度危害 |
| Risk Medium | `#F2B705` | 中度危害、需要关注 |
| Risk High | `#D9480F` | 重度危害、重点处理 |
| Risk Critical | `#B42318` | 严重异常、阻断性风险 |

### 通用语义色

| 语义角色 | 色值 | 用途 |
|---------|------|------|
| Success | `#2F7D46` | 保存成功、完成、确认 |
| Warning | `#B7791F` | 待处理、提示、非阻断警告 |
| Danger | `#B42318` | 错误、删除、危险操作 |
| Info | `#2563EB` | 说明、定位、辅助信息 |

### 色彩使用规则

- **Forest (`#14532D`)**：用于主按钮、当前导航、核心选中态，不用于大面积背景。
- **Leaf (`#2F7D46`)**：用于筛选激活、次级行动、hover 状态。
- **Mist (`#F4F7F2`)**：用于页面背景和非地图区域，避免使用奶黄色、粉色或高饱和装饰色。
- **Map Boundary (`#D97706`)**：仅用于地图边界和空间范围，不作为品牌主色。
- **风险分级色**：只用于虫害等级、图例、专题图，不用于通用按钮。
- **白色浮层**：地图上的控件使用半透明白或纯白背景，并提供足够阴影和边框。
- **避免**：粉色主色、大面积亮橙、奶黄色背景、装饰性渐变、低对比度文字。

---

## 3. 字体系统

### 字体栈

```css
--font-display: Inter, "Noto Sans SC", system-ui, sans-serif;
--font-body: Inter, "Noto Sans SC", -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
--font-mono: "SF Mono", ui-monospace, Menlo, Consolas, monospace;
```

### 字号层级

| 角色 | 字号 | 行高 | 用途 |
|-----|------|------|------|
| H1 | 32px | 1.2 | 页面主标题、报表标题 |
| H2 | 24px | 1.25 | 章节标题、面板标题 |
| H3 | 18px | 1.35 | 卡片标题、表单分组 |
| Body | 16px | 1.52 | 正文、表单、列表 |
| Compact | 14px | 1.45 | 顶栏、地图控件、表格 |
| Caption | 12px | 1.35 | 图例、辅助标签、元信息 |
| Map Label | 11px | 1.2 | 地图点位编号、空间标注 |

### 字重

- **标题**：650-750，用于建立清晰层级。
- **正文**：400-500，保证长表单和表格可读。
- **控件**：600，用于按钮、标签、筛选项。
- **地图标签**：700，并带描边或浅色底，确保复杂底图上可读。

### 字体应用规则

- 不使用营销型超大标题，业务系统默认保持紧凑。
- 数字、编号、经纬度、工单号使用等宽字体或 tabular numbers。
- 地图标签只在必要缩放级别显示，避免标签堆叠。
- 中文界面优先保证字形清晰，不使用装饰性衬线字体。

---

## 4. 间距与网格

### 间距系统

```css
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
--space-10: 40px;
--space-12: 48px;
```

### 圆角系统

```css
--radius-xs: 6px;      /* 地图点位标签、小徽章 */
--radius-sm: 8px;      /* 按钮、输入框、菜单项 */
--radius-md: 12px;     /* 浮层、卡片、筛选面板 */
--radius-lg: 16px;     /* 模态框、大面板 */
--radius-pill: 9999px; /* 状态标签、计数徽章 */
```

### 间距使用原则

- 地图页控件使用紧凑间距，避免遮挡地图。
- 表单和工单页面使用 4px 网格，保持字段对齐。
- 浮层与屏幕边缘至少保持 12px 安全距离。
- 不使用大面积留白制造“营销感”，优先服务扫读效率。

---

## 5. 布局与构成

### 核心原则

1. **地图优先**：地图页第一视觉焦点是点位、边界和图例，导航与工具栏保持低干扰。
2. **任务清晰**：筛选、图层、定位、新增点位等操作要分组明确。
3. **状态可见**：当前视图、筛选数量、风险图例和选中点位必须清楚。
4. **密度可控**：点位、编号和边界应随缩放级别逐步展示，避免全量堆叠。

### 推荐布局

#### 地图作业布局
```text
┌──────────────────────────────────────────────┐
│ 顶栏：品牌 / 当前视图 / 筛选 / 用户           │
├──────────────────────────────────────────────┤
│                                              │
│ 地图画布                                     │
│   右上：图层、底图、编号、聚合控制            │
│   左下：图例                                 │
│   右下：定位、新增点位                       │
│                                              │
└──────────────────────────────────────────────┘
```

#### 工单录入布局
```text
┌──────────────┬───────────────────────────────┐
│ 导入与筛选区 │ 表格 / 表单 / 详情             │
│              │ 图片、字段校验、生成文档       │
└──────────────┴───────────────────────────────┘
```

### 响应式断点

| 断点 | 宽度 | 布局策略 |
|-----|------|---------|
| Mobile | < 768px | 地图控件收进底部或右侧浮层，表单单列 |
| Tablet | 768px - 1024px | 顶栏压缩，筛选以抽屉展示 |
| Desktop | > 1024px | 完整地图工具、浮层菜单、双栏工单布局 |

---

## 6. 组件规范

### 按钮

**主要按钮**
```css
.btn-primary {
  background: #14532D;
  color: #FFFFFF;
  border: 1px solid #14532D;
  border-radius: 8px;
  padding: 10px 16px;
  font-weight: 650;
}
```

**次要按钮**
```css
.btn-secondary {
  background: #FFFFFF;
  color: #14532D;
  border: 1px solid #B7C9B2;
  border-radius: 8px;
  padding: 10px 16px;
  font-weight: 600;
}
```

**地图浮动按钮**
```css
.map-tool-button {
  background: rgba(255, 255, 255, 0.94);
  color: #17231A;
  border: 1px solid rgba(20, 83, 45, 0.16);
  border-radius: 12px;
  box-shadow: 0 10px 28px rgba(23, 35, 26, 0.16);
}
```

**状态**
- Hover：使用 `#2F7D46` 或浅灰绿背景，不使用高饱和橙色。
- Focus：使用深林绿半透明 focus ring。
- Disabled：降低透明度并保持文字对比度，不只依赖颜色表达。

### 输入框

```css
.input {
  background: #FFFFFF;
  border: 1px solid #B7C9B2;
  border-radius: 8px;
  color: #17231A;
  padding: 10px 12px;
  font-size: 14px;
}

.input:focus {
  border-color: #2F7D46;
  box-shadow: 0 0 0 3px rgba(47, 125, 70, 0.22);
}
```

### 卡片与面板

```css
.panel {
  background: #FFFFFF;
  border: 1px solid #D8E2D2;
  border-radius: 12px;
  box-shadow: 0 14px 34px rgba(23, 35, 26, 0.10);
}
```

### 标签与徽章

```css
.badge {
  background: #E7F3E8;
  color: #14532D;
  border-radius: 9999px;
  padding: 3px 10px;
  font-size: 12px;
  font-weight: 650;
}
```

### 地图图例

- 图例默认使用白色或半透明白浮层，放在地图左下或左侧安全区域。
- 图例项必须和点位、面状图层使用同一套风险色。
- 图例可收起，但收起按钮对比度必须高于卫星底图。
- 图例不使用浅粉、浅橙等与业务无关的装饰色。

### 筛选与图层菜单

- 筛选菜单用于数据条件，图层菜单用于底图、边界、编号、聚合等空间显示控制。
- 两类菜单视觉可相似，但文案和分组必须区分。
- 地图图层菜单优先放在地图画布右上角浮层，而不是和账号信息混在一起。
- 激活状态使用 Forest 或 Leaf，计数徽章可使用 Danger 或 Warning。

---

## 7. 动效与交互

### 过渡规范

```css
--motion-fast: 120ms;
--motion-base: 180ms;
--motion-slow: 240ms;
--ease-standard: cubic-bezier(0.2, 0, 0, 1);
```

### 动效原则

1. **克制**：动效只用于反馈、展开、定位和状态切换。
2. **快速**：地图操作反馈优先，避免等待。
3. **稳定**：面板、菜单和点位选中不使用弹跳动画。

### 推荐动效

- 菜单展开：轻微淡入和 4px 位移。
- 点位选中：描边、尺寸或阴影变化，不使用闪烁。
- 图层切换：显示加载状态，避免底图空白时无反馈。
- 表单校验：错误文本即时出现，字段边框变为 Danger。

### 避免

- 装饰性背景动画
- 大面积渐变切换
- 过度弹性动画
- 地图点位持续闪烁

---

## 8. 语音与品牌

### 文案调性

- **专业**：使用准确业务词汇，如“调查点位”“虫害等级”“行政边界”“工单记录”。
- **简洁**：按钮和提示不超过一行动作描述。
- **中性**：优先使用客观说明，避免过度口语化。
- **尊重**：面向管理端或政企场景时使用“您”或省略主语。

### 品牌表达

- 标题强调工作台属性，不使用营销式口号。
- 成功提示说明结果，错误提示说明原因和下一步。
- 地图控件文案必须直指操作，如“切换图层”“显示编号”“新增点位”。
- 风险文案避免情绪化，使用“轻度 / 中度 / 重度 / 严重异常”。

### 避免

- 消费级亲昵语气
- 过度营销语言
- 模糊占位文案
- 将虫害风险描述成通用成功或失败状态

---

## 9. 禁用模式

### 绝对禁止

- 使用粉色作为主色或选中态
- 使用奶黄色作为页面大背景
- 使用亮橙作为品牌主强调色
- 用渐变、色块或装饰图形抢占地图注意力
- 全缩放级别强制显示所有点位编号
- 风险色、通用状态色和图层色混用

### 需要谨慎

- 卫星底图：适合核查现场环境，不一定适合作为默认分析底图。
- 橙色边界：只用于地图空间边界，默认透明度要低。
- 阴影：用于浮层从地图中抬起，不用于普通装饰。
- 圆角：地图工具可保持 8-12px，避免过度圆润造成消费级气质。

---

## 10. Tokens 引用

将以下 tokens 作为后续落地到项目 `:root` 的参考。现有前端变量可逐步映射到这些语义，不要求一次性替换。

```css
:root {
  --color-forest: #14532D;
  --color-leaf: #2F7D46;
  --color-moss: #6B8F3E;
  --color-earth: #8A5A2B;
  --color-map-boundary: #D97706;
  --color-map-boundary-soft: rgba(217, 119, 6, 0.46);

  --risk-none: #E7F3E8;
  --risk-light: #8BC34A;
  --risk-medium: #F2B705;
  --risk-high: #D9480F;
  --risk-critical: #B42318;

  --bg: #F4F7F2;
  --surface: #FFFFFF;
  --surface-muted: #EEF4EA;
  --surface-map-control: rgba(255, 255, 255, 0.94);
  --fg: #17231A;
  --fg-2: #2F3D32;
  --muted: #637064;
  --border: #D8E2D2;
  --border-soft: #E7EEE2;

  --accent: var(--color-forest);
  --accent-on: #FFFFFF;
  --accent-hover: #2F7D46;
  --accent-active: #0F3D22;
  --success: #2F7D46;
  --warn: #B7791F;
  --danger: #B42318;
  --info: #2563EB;

  --font-display: Inter, "Noto Sans SC", system-ui, sans-serif;
  --font-body: Inter, "Noto Sans SC", system-ui, sans-serif;
  --font-mono: "SF Mono", ui-monospace, Menlo, Consolas, monospace;

  --text-xs: 12px;
  --text-sm: 14px;
  --text-base: 16px;
  --text-lg: 18px;
  --text-xl: 24px;
  --text-2xl: 32px;
  --leading-body: 1.52;
  --leading-tight: 1.2;
  --tracking-display: 0;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;

  --radius-xs: 6px;
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-pill: 9999px;

  --elev-flat: none;
  --elev-ring: 0 0 0 1px var(--border);
  --elev-raised: 0 14px 34px rgba(23, 35, 26, 0.10);
  --elev-map-control: 0 10px 28px rgba(23, 35, 26, 0.16);
  --focus-ring: 0 0 0 3px rgba(47, 125, 70, 0.22);

  --motion-fast: 120ms;
  --motion-base: 180ms;
  --motion-slow: 240ms;
  --ease-standard: cubic-bezier(0.2, 0, 0, 1);

  --container-max: 1180px;
  --container-gutter-desktop: 36px;
  --container-gutter-tablet: 24px;
  --container-gutter-phone: 16px;
}
```

### 与现有前端变量的映射建议

| 新语义 token | 可映射到现有变量 | 说明 |
|-------------|------------------|------|
| `--color-forest` | `--color-primary`, `--accent` | 主操作、导航选中 |
| `--color-leaf` | `--color-accent`, `--success` | 次级强调、成功状态 |
| `--bg` | `--color-bg` | 页面背景 |
| `--surface` | `--color-surface` | 卡片和浮层 |
| `--surface-muted` | `--color-surface-container-low` | 次级背景 |
| `--border` | `--color-border` | 常规边框 |
| `--color-map-boundary` | 地图边界样式常量 | 行政边界 |
| `--risk-*` | 图例和点位分级色 | 虫害风险专题 |

---

## 附录：组件清单

| 类别 | 选择器 | 用途 |
|-----|-------|------|
| 按钮 | `.btn`, `.btn-primary`, `.btn-secondary`, `.map-tool-button` | 行动按钮与地图浮动工具 |
| 表单 | `.field`, `.input`, `label` | 工单录入、筛选、点位新增 |
| 卡片 | `.panel`, `.card`, `.detail-drawer` | 内容容器、详情面板 |
| 地图 | `.map-legend`, `.layer-menu`, `.filter-popover` | 图例、图层、筛选浮层 |
| 排版 | `.section-title`, `.caption`, `.map-label` | 文本层级与地图标注 |
| 布局 | `.container`, `.map-workspace`, `.shell-layout` | 页面结构 |

---

*最后更新：2026-06-03*
