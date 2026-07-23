<script setup>
/**
 * 统一空态（规范 §6）：虚线框 + 图标 + 标题 + 描述 + 可选操作。
 * 用法：
 *   <EmptyState :icon="Inbox" title="暂无数据" description="…" />
 *   <EmptyState …><Button … /></EmptyState>
 */
import { Inbox } from "@lucide/vue";

defineProps({
  icon: { type: [Object, Function], default: () => Inbox },
  title: { type: String, required: true },
  description: { type: String, default: "" },
});
</script>

<template>
  <div
    class="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed px-6 py-12 text-center"
  >
    <component
      :is="icon"
      class="size-8 text-muted-foreground/60"
      :stroke-width="1.5"
      aria-hidden="true"
    />
    <p class="text-sm font-semibold">{{ title }}</p>
    <p v-if="description" class="max-w-md text-sm text-muted-foreground">
      {{ description }}
    </p>
    <div v-if="$slots.default" class="mt-2 flex items-center gap-2">
      <slot />
    </div>
  </div>
</template>
