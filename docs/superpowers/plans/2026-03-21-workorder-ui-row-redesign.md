# 工作单页面记录行 UI 改进实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 改进工作单页面记录行的视觉协调性，统一输入框与图片区的高度，增大图片展示尺寸。

**Architecture:** 修改 `RecordTable.vue` 的样式系统，将输入框改为 textarea 以支持统一高度，将图片槽改为 2×2 网格布局，删除按钮改为与图片区等高的垂直按钮。

**Tech Stack:** Vue 3 + Scoped CSS

**参考设计:** `docs/superpowers/specs/2026-03-21-workorder-ui-row-redesign.md`

---

## 文件修改清单

- **Modify:** `frontend/src/components/workorder/RecordTable.vue`
  - 修改 `.table-stage` 的 grid 布局
  - 修改 `.table-textarea` 样式增加 min-height
  - 重构 `.row-tools` 为 flex 布局
  - 重构 `.thumb-strip` 为 2×2 网格
  - 修改 `.table-remove-icon` 为等高按钮

---

### Task 1: 调整表格整体布局宽度

**Files:**
- Modify: `frontend/src/components/workorder/RecordTable.vue:450`

- [ ] **Step 1: 修改 `.table-stage` 的 grid 列宽**

将右侧宽度从 128px 改为 160px，为更大的图片区留出空间：

```css
.table-stage {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 160px;  /* 从 128px 改为 160px */
  gap: 0.75rem;  /* 从 0.55rem 增大间距 */
  align-items: stretch;  /* 从 start 改为 stretch 实现等高 */
}
```

- [ ] **Step 2: 验证布局变化**

启动前端开发服务器，检查右侧列宽度是否正确增加到 160px。

---

### Task 2: 修改描述输入框为等高 textarea

**Files:**
- Modify: `frontend/src/components/workorder/RecordTable.vue:313-321, 560-590`

- [ ] **Step 1: 修改 textarea 标签的高度样式**

当前 textarea 使用 `rows="1"` 限制高度，需要移除并改用 CSS 控制：

```vue
<textarea
  v-else-if="field.type === 'textarea'"
  class="table-input table-textarea"
  :value="record[field.key]"
  :title="errors[index]?.[field.key] || ''"
  @input="updateCell(index, field, $event.target.value)"
  @paste="handleCellPaste(index, field, $event)"
/>
```

- [ ] **Step 2: 更新 `.table-textarea` 样式**

```css
.table-textarea {
  min-height: 4rem;  /* 新增：确保最小高度 */
  height: 100%;      /* 新增：填满单元格 */
  padding: 0.6rem 0.75rem;
  resize: none;      /* 从 vertical 改为 none，高度由内容决定 */
  overflow: auto;
  white-space: normal;  /* 从 nowrap 改为 normal 允许多行 */
  line-height: 1.4;
}
```

- [ ] **Step 3: 更新单元格样式确保撑满**

```css
.cell-description {
  width: 240px;
  min-width: 240px;
  min-height: 4rem;  /* 新增：单元格最小高度 */
}

.cell-body {
  padding: 0.35rem;
  border-bottom: 1px solid rgba(53, 67, 48, 0.08);
  vertical-align: middle;
  height: 100%;  /* 新增：确保单元格撑满 */
}
```

- [ ] **Step 4: 验证输入框高度**

在浏览器中检查"详细情况描述"输入框高度是否与图片区一致（约 4rem）。

---

### Task 3: 重构图片上传区为 2×2 网格

**Files:**
- Modify: `frontend/src/components/workorder/RecordTable.vue:338-389, 592-650`

- [ ] **Step 1: 重构 `.row-tools-rail` 布局**

```css
.row-tools-rail {
  display: flex;
  flex-direction: column;
  gap: 0;
}
```

- [ ] **Step 2: 重构 `.row-tools` 为 flex 布局**

```css
.row-tools {
  display: flex;
  gap: 0.5rem;
  align-items: stretch;  /* 等高 */
  min-height: 4rem;      /* 与输入框一致的最小高度 */
  padding: 0.35rem 0.4rem;
  border-bottom: 1px solid rgba(53, 67, 48, 0.08);
  background: rgba(255, 252, 247, 0.86);
}

.row-tools:nth-child(2n + 1) {
  background: rgba(248, 244, 233, 0.46);
}

.row-tools:hover,
.row-tools:focus {
  background: rgba(237, 241, 232, 0.62);
}
```

- [ ] **Step 3: 重构 `.thumb-strip` 为 2×2 网格**

```css
.thumb-strip {
  flex: 1;  /* 占据剩余空间 */
  display: grid;
  grid-template-columns: repeat(2, 1fr);  /* 2列 */
  grid-template-rows: repeat(2, 1fr);     /* 2行 */
  gap: 0.3rem;
  padding: 0.3rem;
  border-radius: 0.75rem;
  border: 1px solid rgba(53, 67, 48, 0.12);
  background: rgba(255, 251, 244, 0.9);
  outline: none;
}

.thumb-strip:focus {
  border-color: rgba(91, 109, 81, 0.28);
  box-shadow: 0 0 0 3px rgba(91, 109, 81, 0.08);
}
```

- [ ] **Step 4: 修改 `.thumb-slot` 样式**

```css
.thumb-slot,
.table-remove-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;  /* 从 aspect-ratio 改为 100% 高度 */
  padding: 0;
  border-radius: 0.55rem;
  overflow: hidden;
}

.thumb-slot {
  position: relative;
  cursor: pointer;
  border: 1px dashed rgba(53, 67, 48, 0.2);  /* 虚线边框 */
  background: rgba(255, 252, 247, 0.94);
  transition: all 0.2s ease;
}

.thumb-slot:hover {
  border-color: var(--accent);
  background: rgba(123, 107, 51, 0.05);
}

.thumb-empty {
  color: var(--muted);
  font-size: 0.8rem;
  font-weight: 600;
}

.thumb-filled {
  border-style: solid;
  border-color: rgba(53, 67, 48, 0.12);
}

.thumb-filled img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.thumb-remove-mark {
  position: absolute;
  top: 0.14rem;
  right: 0.14rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 0.8rem;
  height: 0.8rem;
  border-radius: 999px;
  background: rgba(28, 34, 23, 0.68);
  color: rgba(255, 252, 247, 0.95);
  font-size: 0.6rem;
  line-height: 1;
}
```

- [ ] **Step 5: 更新删除按钮样式**

```css
.table-remove-icon {
  width: 2.5rem;  /* 固定宽度 */
  flex-shrink: 0;
  cursor: pointer;
  border: 1px solid rgba(180, 62, 37, 0.2);  /* 红色边框 */
  background: rgba(255, 252, 247, 0.94);
  color: var(--danger);
  transition: all 0.2s ease;
}

.table-remove-icon:hover,
.table-remove-icon:focus-visible {
  background: rgba(180, 62, 37, 0.08);
  border-color: rgba(180, 62, 37, 0.3);
}

.table-remove-icon svg {
  width: 1rem;
  height: 1rem;
  fill: currentColor;
}
```

- [ ] **Step 6: 验证图片区布局**

检查图片区是否为 2×2 网格，每个槽位尺寸是否足够大。

---

### Task 4: 更新移动端响应式样式

**Files:**
- Modify: `frontend/src/components/workorder/RecordTable.vue:739-773`

- [ ] **Step 1: 更新移动端 `.row-tools` 样式**

```css
@media (max-width: 900px) {
  .table-toolbar {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .table-stage {
    grid-template-columns: 1fr;
  }

  .row-tools-rail {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));  /* 增大最小宽度 */
    gap: 0.45rem;
    padding: 0.45rem;
  }

  .row-tools-header {
    display: none;
  }

  .row-tools {
    border: 1px solid rgba(53, 67, 48, 0.08);
    border-radius: 0.85rem;
    min-height: auto;  /* 移动端取消固定高度 */
    padding: 0.5rem;
  }

  .thumb-strip {
    min-height: 6rem;  /* 移动端保持足够高度 */
  }
}
```

- [ ] **Step 2: 在移动设备宽度测试**

调整浏览器窗口到 900px 以下，检查布局是否正常切换。

---

### Task 5: 最终验证与提交

- [ ] **Step 1: 完整功能测试**

1. 添加多条记录，检查每行高度是否一致
2. 上传图片，检查缩略图是否清晰可见
3. 测试删除图片功能
4. 测试删除整行功能
5. 测试 Excel 粘贴功能
6. 测试响应式布局

- [ ] **Step 2: 代码审查**

- 检查是否有未使用的 CSS 类
- 检查样式覆盖是否正确
- 检查浏览器控制台是否有 CSS 警告

- [ ] **Step 3: 提交更改**

```bash
git add frontend/src/components/workorder/RecordTable.vue
git commit -m "feat: 改进工作单记录行 UI，统一高度并增大图片展示

- 输入框与图片区统一使用 4rem 最小高度
- 图片槽改为 2×2 网格布局，尺寸增大
- 删除按钮改为与图片区等高的垂直按钮
- 统一边框风格，消除视觉断层"
```

---

## 常见问题排查

**Q: 输入框和图片区高度不一致？**
A: 检查 `.table-stage` 的 `align-items: stretch` 是否生效，以及 `.row-tools` 的 `min-height` 是否与 `.table-textarea` 一致。

**Q: 图片区没有变成 2×2 网格？**
A: 检查 `.thumb-strip` 的 `grid-template-columns` 和 `grid-template-rows` 是否正确设置为 `repeat(2, 1fr)`。

**Q: 删除按钮高度不对？**
A: 检查 `.table-remove-icon` 是否设置了 `height: 100%`，以及父元素 `.row-tools` 是否设置了 `align-items: stretch`。
