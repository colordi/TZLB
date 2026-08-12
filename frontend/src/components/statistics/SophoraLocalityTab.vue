<script setup>
import {
  AlertTriangle,
  CheckCircle2,
  MapPinned,
  Percent,
  ShieldAlert,
} from "@lucide/vue";
import { computed, onMounted, ref, watch } from "vue";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/native-select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getSophoraLocalitySummary } from "../../api/statistics.js";
import { useToast } from "../../composables/useToast.js";
import StatisticsYearFilter from "./StatisticsYearFilter.vue";
import { buildYearOptions, handleStatisticsLoadError } from "./statisticsShared.js";

const EMPTY = {
  year: null,
  generation: null,
  totals: {
    surveyed_points: 0,
    damaged_points: 0,
    damage_rate: null,
    severe_points: 0,
    ledger_points: 0,
    closed_points: 0,
    closure_rate: null,
  },
  localities: [],
};

const { error } = useToast();
const loading = ref(false);
const summary = ref({ ...EMPTY });

const YEAR_OPTIONS = buildYearOptions();
const GENERATION_OPTIONS = ["", "第一代", "第二代", "第三代"];

const selectedYear = ref(new Date().getFullYear());
const selectedGeneration = ref("");

watch([selectedYear, selectedGeneration], () => {
  loadSummary();
});

const totals = computed(() => summary.value.totals || EMPTY.totals);
const localities = computed(() =>
  Array.isArray(summary.value.localities) ? summary.value.localities : [],
);

const activeLocalities = computed(() =>
  localities.value.filter(
    (item) =>
      (item.surveyed_points || 0) > 0 ||
      (item.ledger_points || 0) > 0 ||
      (item.monitor_points || 0) > 0,
  ),
);

const severeSites = computed(() =>
  localities.value.flatMap((item) =>
    (item.severe_sites || []).map((site) => ({
      ...site,
      locality: item.locality,
    })),
  ),
);

const kpiItems = computed(() => [
  {
    key: "surveyed_points",
    label: "调查点数",
    value: totals.value.surveyed_points,
    unit: "个",
    icon: MapPinned,
    hint: "定级后去重点位",
  },
  {
    key: "damaged_points",
    label: "受害点数",
    value: totals.value.damaged_points,
    unit: "个",
    icon: ShieldAlert,
    hint: "危害程度为轻/中/重",
  },
  {
    key: "damage_rate",
    label: "受害率",
    value: totals.value.damage_rate,
    unit: "%",
    icon: Percent,
    hint: "受害 / 调查",
    isRate: true,
  },
  {
    key: "severe_points",
    label: "严重点位",
    value: totals.value.severe_points,
    unit: "个",
    icon: AlertTriangle,
    hint: "危害程度 = 重",
  },
  {
    key: "closure_rate",
    label: "闭环率",
    value: totals.value.closure_rate,
    unit: "%",
    icon: CheckCircle2,
    hint: `${formatNumber(totals.value.closed_points)} / ${formatNumber(totals.value.ledger_points)} 已闭环`,
    isRate: true,
  },
]);

function formatNumber(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  return Number(value || 0).toLocaleString("zh-CN");
}

function formatRate(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  return `${Number(value).toFixed(1)}%`;
}

function formatAvg(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  return Number(value).toFixed(1);
}

async function loadSummary() {
  loading.value = true;
  try {
    const result = await getSophoraLocalitySummary({
      year: selectedYear.value,
      generation: selectedGeneration.value || undefined,
    });
    summary.value = {
      year: result.year ?? null,
      generation: result.generation ?? null,
      totals: { ...EMPTY.totals, ...(result.totals || {}) },
      localities: Array.isArray(result.localities) ? result.localities : [],
    };
  } catch (loadError) {
    summary.value = { ...EMPTY, year: selectedYear.value };
    handleStatisticsLoadError(error, loadError);
  } finally {
    loading.value = false;
  }
}

onMounted(loadSummary);
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-end gap-3">
      <StatisticsYearFilter
        v-model="selectedYear"
        :year-options="YEAR_OPTIONS"
        testid="data-statistics-sophora-locality-year-filter"
      />
      <label class="flex flex-col gap-1 text-sm">
        <span class="text-muted-foreground">世代</span>
        <NativeSelect
          v-model="selectedGeneration"
          class="w-36"
          data-testid="data-statistics-sophora-locality-generation-filter"
        >
          <option value="">全部世代</option>
          <option v-for="gen in GENERATION_OPTIONS.filter(Boolean)" :key="gen" :value="gen">
            {{ gen }}
          </option>
        </NativeSelect>
      </label>
    </div>

    <Card data-testid="data-statistics-sophora-locality-panel">
      <CardHeader class="pb-3">
        <CardTitle class="text-base">
          {{ summary.year || selectedYear }} 年属地受害汇总
        </CardTitle>
        <CardDescription>
          点位定级取最新调查；受害含轻/中/重；严重 = 重。
        </CardDescription>
      </CardHeader>
      <CardContent class="space-y-4">
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <div
            v-for="kpi in kpiItems"
            :key="kpi.key"
            class="rounded-lg border p-4"
            :data-testid="`data-statistics-sophora-locality-kpi-${kpi.key}`"
          >
            <div class="flex items-center gap-2 text-sm text-muted-foreground">
              <component :is="kpi.icon" class="size-4" />
              {{ kpi.label }}
            </div>
            <p class="mt-1 text-2xl font-bold tracking-tight tabular-nums">
              <template v-if="kpi.isRate">{{ formatRate(kpi.value) }}</template>
              <template v-else>
                {{ formatNumber(kpi.value) }}
                <span class="text-sm font-normal text-muted-foreground">{{ kpi.unit }}</span>
              </template>
            </p>
            <p class="mt-0.5 text-xs text-muted-foreground">{{ kpi.hint }}</p>
          </div>
        </div>

        <div v-if="loading" class="space-y-2">
          <Skeleton class="h-8 w-full" />
          <Skeleton class="h-8 w-full" />
          <Skeleton class="h-8 w-full" />
        </div>

        <div v-else class="overflow-x-auto rounded-lg border" data-testid="data-statistics-sophora-locality-list">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>属地</TableHead>
                <TableHead class="text-right">监测</TableHead>
                <TableHead class="text-right">调查</TableHead>
                <TableHead class="text-right">覆盖率</TableHead>
                <TableHead class="text-right">受害</TableHead>
                <TableHead class="text-right">轻/中/重</TableHead>
                <TableHead class="text-right">平均虫口</TableHead>
                <TableHead class="text-right">台账</TableHead>
                <TableHead class="text-right">状态</TableHead>
                <TableHead class="text-right">闭环率</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow
                v-for="item in activeLocalities"
                :key="item.locality"
                :data-testid="`data-statistics-sophora-locality-row-${item.locality}`"
              >
                <TableCell class="font-medium">{{ item.locality }}</TableCell>
                <TableCell class="text-right tabular-nums">{{ formatNumber(item.monitor_points) }}</TableCell>
                <TableCell class="text-right tabular-nums">{{ formatNumber(item.surveyed_points) }}</TableCell>
                <TableCell class="text-right tabular-nums">{{ formatRate(item.coverage_rate) }}</TableCell>
                <TableCell class="text-right tabular-nums">{{ formatNumber(item.damaged_points) }}</TableCell>
                <TableCell class="text-right tabular-nums text-xs">
                  {{ formatNumber(item.light_points) }}/{{ formatNumber(item.medium_points) }}/{{ formatNumber(item.severe_points) }}
                </TableCell>
                <TableCell class="text-right tabular-nums">{{ formatAvg(item.avg_insect_count) }}</TableCell>
                <TableCell class="text-right tabular-nums">{{ formatNumber(item.ledger_points) }}</TableCell>
                <TableCell class="text-right text-xs text-muted-foreground">
                  防{{ formatNumber(item.pending_treatment) }}
                  ·复{{ formatNumber(item.pending_recheck) }}
                  ·异{{ formatNumber(item.recheck_abnormal) }}
                  ·闭{{ formatNumber(item.closed_points) }}
                </TableCell>
                <TableCell class="text-right tabular-nums">{{ formatRate(item.closure_rate) }}</TableCell>
              </TableRow>
              <TableRow v-if="!activeLocalities.length">
                <TableCell colspan="10" class="py-8 text-center text-muted-foreground">
                  暂无属地统计数据
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>

        <div v-if="severeSites.length" class="space-y-2" data-testid="data-statistics-sophora-severe-list">
          <h4 class="text-sm font-medium">严重点位清单（危害程度 = 重）</h4>
          <div class="flex flex-wrap gap-2">
            <Badge
              v-for="site in severeSites"
              :key="`${site.locality}-${site.code}`"
              variant="outline"
              class="font-normal"
              :data-testid="`data-statistics-sophora-severe-${site.code}`"
            >
              {{ site.code }}
              · {{ site.locality }}
              · {{ site.name }}
              · 虫口 {{ formatNumber(site.avg_insect_count) }}
              <span v-if="site.ledger_status"> · {{ site.ledger_status }}</span>
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
