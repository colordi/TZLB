<script setup>
import PointScreenshotPanel from "../components/workorder/PointScreenshotPanel.vue";
</script>

<template>
  <section class="point-screenshot-page mx-auto flex w-full max-w-6xl flex-col gap-4">
    <header class="space-y-1">
      <h1 class="text-2xl font-bold tracking-tight md:text-3xl">点位截图管理</h1>
      <p class="text-sm text-muted-foreground">
        该入口已并入「工单素材」。下方为点位截图管理面板。
      </p>
    </header>
    <PointScreenshotPanel />
  </section>
</template>
