<script setup>
import { computed } from "vue";

import BaseChart from "@/components/charts/BaseChart.vue";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { buildTreemapOption, HOST_METRICS } from "./hostChartOptions.js";

const props = defineProps({
  hosts: {
    type: Array,
    default: () => [],
  },
  metric: {
    type: String,
    default: "plants",
  },
  loading: {
    type: Boolean,
    default: false,
  },
});

const option = computed(() => buildTreemapOption(props.hosts, props.metric));
const metricLabel = computed(() => HOST_METRICS[props.metric]?.label || "受害株数");
</script>

<template>
  <Card data-testid="data-statistics-host-treemap-panel">
    <CardHeader>
      <CardTitle class="text-base">寄主构成</CardTitle>
      <CardDescription>
        矩形面积按{{ metricLabel }}占比绘制，Top 12 之外的树种合并为「其他」（灰色）
      </CardDescription>
    </CardHeader>
    <CardContent>
      <div
        v-if="!props.loading && props.hosts.length === 0"
        class="rounded-xl border border-dashed px-4 py-16 text-center text-sm text-muted-foreground"
        data-testid="data-statistics-host-treemap-empty"
      >
        暂无寄主分布数据。
      </div>
      <BaseChart v-else :option="option" height="420px" :loading="props.loading" />
    </CardContent>
  </Card>
</template>
