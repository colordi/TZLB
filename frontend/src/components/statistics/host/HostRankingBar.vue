<script setup>
import { computed } from "vue";

import BaseChart from "@/components/charts/BaseChart.vue";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { buildRankingOption, HOST_METRICS, RANKING_LIMIT } from "./hostChartOptions.js";

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

const option = computed(() => buildRankingOption(props.hosts, props.metric));
const metricLabel = computed(() => HOST_METRICS[props.metric]?.label || "受害株数");
</script>

<template>
  <Card data-testid="data-statistics-host-ranking-panel">
    <CardHeader>
      <CardTitle class="text-base">寄主受害排行</CardTitle>
      <CardDescription>按{{ metricLabel }}排序的 Top {{ RANKING_LIMIT }} 树种；「其他」为多树种合并桶，不参与排名，灰色置于榜尾作参照</CardDescription>
    </CardHeader>
    <CardContent>
      <div
        v-if="!props.loading && props.hosts.length === 0"
        class="rounded-xl border border-dashed px-4 py-16 text-center text-sm text-muted-foreground"
        data-testid="data-statistics-host-ranking-empty"
      >
        暂无寄主分布数据。
      </div>
      <BaseChart v-else :option="option" height="460px" :loading="props.loading" />
    </CardContent>
  </Card>
</template>
