<script setup>
import { computed } from "vue";

import BaseChart from "@/components/charts/BaseChart.vue";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  buildGenerationCompareBarOption,
  buildGenerationHeatmapOption,
  formatNumber,
  formatShare,
  GENERATION_COMPARE_HOST_LIMIT,
} from "./hostChartOptions.js";

const props = defineProps({
  generations: {
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

const isEmpty = computed(() => !props.loading && props.generations.length === 0);

const barOption = computed(() => buildGenerationCompareBarOption(props.generations, props.metric));
const heatmapOption = computed(() => buildGenerationHeatmapOption(props.generations));

function topHostText(generation) {
  const topHost = generation.totals?.top_host;
  if (!topHost) {
    return "--";
  }
  return `${topHost.host}（${formatShare(topHost.share)}）`;
}
</script>

<template>
  <div class="flex flex-col gap-4" data-testid="data-statistics-host-compare">
    <Card>
      <CardHeader>
        <CardTitle class="text-base">各世代概览对比</CardTitle>
        <CardDescription>按世代汇总的寄主受害核心指标</CardDescription>
      </CardHeader>
      <CardContent>
        <div
          v-if="isEmpty"
          class="rounded-xl border border-dashed px-4 py-10 text-center text-sm text-muted-foreground"
          data-testid="data-statistics-host-compare-empty"
        >
          暂无分代寄主数据。
        </div>
        <div v-else class="overflow-hidden rounded-xl border" data-testid="data-statistics-host-compare-kpi">
          <Table>
            <TableHeader>
              <TableRow class="hover:bg-transparent">
                <TableHead>指标</TableHead>
                <TableHead
                  v-for="generation in props.generations"
                  :key="generation.generation"
                  class="text-right"
                >
                  {{ generation.generation }}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell class="text-muted-foreground">受害株数</TableCell>
                <TableCell
                  v-for="generation in props.generations"
                  :key="generation.generation"
                  class="text-right font-medium tabular-nums"
                >
                  {{ formatNumber(generation.totals?.damaged_plants) }} 株
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell class="text-muted-foreground">受害点位</TableCell>
                <TableCell
                  v-for="generation in props.generations"
                  :key="generation.generation"
                  class="text-right font-medium tabular-nums"
                >
                  {{ formatNumber(generation.totals?.damaged_points) }} 个
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell class="text-muted-foreground">寄主树种数</TableCell>
                <TableCell
                  v-for="generation in props.generations"
                  :key="generation.generation"
                  class="text-right font-medium tabular-nums"
                >
                  {{ formatNumber(generation.totals?.host_species) }} 种
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell class="text-muted-foreground">优势寄主（株数占比）</TableCell>
                <TableCell
                  v-for="generation in props.generations"
                  :key="generation.generation"
                  class="text-right font-medium"
                  :data-testid="`data-statistics-host-compare-top-${generation.generation}`"
                >
                  {{ topHostText(generation) }}
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>

    <Card data-testid="data-statistics-host-compare-bar-panel">
      <CardHeader>
        <CardTitle class="text-base">分代寄主对比</CardTitle>
        <CardDescription>
          各世代寄主并集 Top {{ GENERATION_COMPARE_HOST_LIMIT }}（按株数合计排序，不含「其他」合并桶）
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div
          v-if="isEmpty"
          class="rounded-xl border border-dashed px-4 py-16 text-center text-sm text-muted-foreground"
        >
          暂无分代寄主数据。
        </div>
        <BaseChart v-else :option="barOption" height="380px" :loading="props.loading" />
      </CardContent>
    </Card>

    <Card data-testid="data-statistics-host-compare-heatmap-panel">
      <CardHeader>
        <CardTitle class="text-base">寄主 × 世代热力</CardTitle>
        <CardDescription>颜色越深受害株数越多，直观呈现优势寄主随世代的变化</CardDescription>
      </CardHeader>
      <CardContent>
        <div
          v-if="isEmpty"
          class="rounded-xl border border-dashed px-4 py-16 text-center text-sm text-muted-foreground"
        >
          暂无分代寄主数据。
        </div>
        <BaseChart v-else :option="heatmapOption" height="420px" :loading="props.loading" />
      </CardContent>
    </Card>
  </div>
</template>
