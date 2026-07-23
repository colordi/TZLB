<script setup>
/**
 * 统一页头（规范 §5.1）：标题 + 描述 + 右侧操作区。
 * 用法：
 *   <PageHeader title="数据导出" description="…">
 *     <template #actions><Button … /></template>
 *   </PageHeader>
 */
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: "" },
});
</script>

<template>
  <header class="flex flex-wrap items-end justify-between gap-3">
    <div class="min-w-0 space-y-1">
      <h1 class="text-2xl font-semibold tracking-tight">{{ title }}</h1>
      <p v-if="description" class="text-sm text-muted-foreground">
        {{ description }}
      </p>
    </div>
    <div v-if="$slots.actions" class="flex shrink-0 items-center gap-2">
      <slot name="actions" />
    </div>
  </header>
</template>
