<script setup>
import { computed } from "vue";

import BaseChart from "@/components/charts/BaseChart.vue";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { buildHeatmapOption, HEATMAP_HOST_LIMIT } from "./hostChartOptions.js";

const props = defineProps({
  hosts: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
});

const option = computed(() => buildHeatmapOption(props.hosts));
</script>

<template>
  <Card data-testid="data-statistics-host-heatmap-panel">
    <CardHeader>
      <CardTitle class="text-base">寄主 × 属地热力</CardTitle>
      <CardDescription>
        Top {{ HEATMAP_HOST_LIMIT }} 寄主在各属地的受害株数分布，颜色越深受害越重
      </CardDescription>
    </CardHeader>
    <CardContent>
      <div
        v-if="!props.loading && props.hosts.length === 0"
        class="rounded-xl border border-dashed px-4 py-16 text-center text-sm text-muted-foreground"
        data-testid="data-statistics-host-heatmap-empty"
      >
        暂无寄主分布数据。
      </div>
      <BaseChart v-else :option="option" height="460px" :loading="props.loading" />
    </CardContent>
  </Card>
</template>
