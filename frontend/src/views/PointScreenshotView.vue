<script setup>
import PointScreenshotPanel from "../components/workorder/PointScreenshotPanel.vue";
import PageHeader from "@/components/common/PageHeader.vue";
</script>

<template>
  <div class="mx-auto w-full max-w-6xl space-y-6">
    <PageHeader
      title="点位截图管理"
      description="该入口已并入「工单素材」。下方为点位截图管理面板。"
    />
    <PointScreenshotPanel />
  </div>
</template>
