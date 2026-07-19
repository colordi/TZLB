# shadcn-vue 组件用法速查（P2）

> 配套 `docs/ui-shadcn-vue-rebuild-plan-20260719.md`。  
> 组件目录：`frontend/src/components/ui/*`  
> 主题：Claude light（`src/styles/themes/claude-light.css`）

## 引入方式

```js
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
```

## 已接入清单

| 批次 | 组件 |
|------|------|
| 2a | button, input, label, textarea, checkbox, select |
| 2b | card, separator, badge, skeleton |
| 2c | dialog, alert-dialog, sheet |
| 2d | table, dropdown-menu, popover, tabs |
| 2e | scroll-area, tooltip, **sidebar**（JS 适配，CLI 原版为 TS） |
| 2f | sonner |
| 2g | switch, pagination |

**未替换**：`components/ui/ToastViewport.vue`（旧 Toast，与 sonner 并存，业务页迁壳时再统一）。

## 约定

1. 业务页优先用 `@/components/ui/*`，不写原始 hex。
2. 新增组件：`cd frontend && npx shadcn-vue@latest add <name> -y`
3. Sidebar 由 CLI TS 源适配为 JS；若 CLI 升级后可 `add sidebar --overwrite` 再按需改回 JS。
4. 旧页继续用现有 scoped CSS；新页用 Tailwind 语义类（`bg-background`、`text-foreground` 等）。

## 最小示例

```vue
<script setup>
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
</script>

<template>
  <Card class="max-w-sm">
    <CardHeader>
      <CardTitle>示例</CardTitle>
    </CardHeader>
    <CardContent>
      <Button>操作</Button>
    </CardContent>
  </Card>
</template>
```
