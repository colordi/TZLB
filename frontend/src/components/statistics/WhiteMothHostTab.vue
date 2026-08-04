<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { Bug, Crown, MapPinned, Trees } from "@lucide/vue";

import { getWhiteMothHostSummary } from "../../api/statistics.js";
import { useToast } from "../../composables/useToast.js";
import { NativeSelect } from "@/components/ui/native-select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import StatisticsYearFilter from "./StatisticsYearFilter.vue";
import HostGenerationComparePanel from "./host/HostGenerationComparePanel.vue";
import HostLocalityHeatmap from "./host/HostLocalityHeatmap.vue";
import HostRankingBar from "./host/HostRankingBar.vue";
import HostTreemap from "./host/HostTreemap.vue";
import { formatNumber, formatShare } from "./host/hostChartOptions.js";
import { buildYearOptions, handleStatisticsLoadError } from "./statisticsShared.js";

const EMPTY_SUMMARY = {
  totals: { host_species: 0, damaged_plants: 0, damaged_points: 0, top_host: null },
  hosts: [],
};

const { error } = useToast();
const loading = ref(false);
const summary = ref({ ...EMPTY_SUMMARY });
const compareGenerations = ref([]);

const YEAR_OPTIONS = buildYearOptions();
const GENERATION_OPTIONS = ["第一代", "第二代", "第三代"];

const viewMode = ref("single");
const selectedYear = ref(new Date().getFullYear());
const selectedGeneration = ref("");
const selectedMetric = ref("plants");

watch([viewMode, selectedYear, selectedGeneration], () => {
  loadSummary();
});

const totals = computed(() => summary.value?.totals || EMPTY_SUMMARY.totals);
const hosts = computed(() =>
  Array.isArray(summary.value?.hosts) ? summary.value.hosts : [],
);

const kpiItems = computed(() => [
  {
    key: "host_species",
    label: "寄主树种数",
    value: formatNumber(totals.value.host_species),
    unit: "种",
    icon: Trees,
    hint: "归一化后的树种数",
  },
  {
    key: "damaged_plants",
    label: "受害株总数",
    value: formatNumber(totals.value.damaged_plants),
    unit: "株",
    icon: Bug,
    hint: "台账危害寄主株数汇总",
  },
  {
    key: "damaged_points",
    label: "受害点位数",
    value: formatNumber(totals.value.damaged_points),
    unit: "个",
    icon: MapPinned,
    hint: "按点位编号去重",
  },
  {
    key: "top_host",
    label: "优势寄主",
    value: totals.value.top_host?.host || "--",
    unit: totals.value.top_host ? formatShare(totals.value.top_host.share) : "",
    icon: Crown,
    hint: totals.value.top_host
      ? `${formatNumber(totals.value.top_host.plants)} 株 · ${formatNumber(totals.value.top_host.points)} 个点位`
      : "暂无数据",
  },
]);

async function loadSummary() {
  loading.value = true;
  try {
    if (viewMode.value === "compare") {
      const result = await getWhiteMothHostSummary({
        year: selectedYear.value,
        byGeneration: true,
      });
      compareGenerations.value = Array.isArray(result.generations) ? result.generations : [];
    } else {
      const result = await getWhiteMothHostSummary({
        year: selectedYear.value,
        generation: selectedGeneration.value || undefined,
      });
      summary.value = {
        totals: { ...EMPTY_SUMMARY.totals, ...(result.totals || {}) },
        hosts: Array.isArray(result.hosts) ? result.hosts : [],
      };
    }
  } catch (loadError) {
    summary.value = { ...EMPTY_SUMMARY };
    compareGenerations.value = [];
    handleStatisticsLoadError(error, loadError);
  } finally {
    loading.value = false;
  }
}

function handleGenerationChange(event) {
  selectedGeneration.value = event.target.value;
}

onMounted(loadSummary);
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex flex-wrap items-center gap-2">
        <Tabs v-model="viewMode">
          <TabsList aria-label="视图模式">
            <TabsTrigger value="single" data-testid="data-statistics-host-view-single">
              单代
            </TabsTrigger>
            <TabsTrigger value="compare" data-testid="data-statistics-host-view-compare">
              分代对比
            </TabsTrigger>
          </TabsList>
        </Tabs>
        <Tabs v-model="selectedMetric">
          <TabsList aria-label="统计指标">
            <TabsTrigger value="plants" data-testid="data-statistics-host-metric-plants">
              按受害株数
            </TabsTrigger>
            <TabsTrigger value="points" data-testid="data-statistics-host-metric-points">
              按受害点位数
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>
      <div class="flex flex-wrap items-center gap-3">
        <label
          v-if="viewMode === 'single'"
          class="flex items-center gap-2 text-sm text-muted-foreground"
        >
          <span>世代</span>
          <NativeSelect
            :model-value="selectedGeneration"
            class="h-8 py-1"
            data-testid="data-statistics-host-generation-filter"
            @change="handleGenerationChange"
          >
            <option value="">全部</option>
            <option v-for="gen in GENERATION_OPTIONS" :key="gen" :value="gen">
              {{ gen }}
            </option>
          </NativeSelect>
        </label>
        <StatisticsYearFilter
          v-model="selectedYear"
          :year-options="YEAR_OPTIONS"
          testid="data-statistics-host-year-filter"
        />
      </div>
    </div>

    <HostGenerationComparePanel
      v-if="viewMode === 'compare'"
      :generations="compareGenerations"
      :metric="selectedMetric"
      :loading="loading"
    />

    <template v-else>
      <div
        class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
        data-testid="data-statistics-host-kpi"
      >
        <template v-if="loading">
          <Skeleton v-for="index in 4" :key="index" class="h-24 rounded-xl" />
        </template>
        <article
          v-for="item in kpiItems"
          v-else
          :key="item.key"
          class="rounded-xl border bg-card p-4 shadow-sm"
          :data-testid="`data-statistics-host-kpi-${item.key}`"
        >
          <div class="flex items-center justify-between gap-2">
            <p class="text-sm text-muted-foreground">{{ item.label }}</p>
            <component :is="item.icon" class="size-4 text-muted-foreground" />
          </div>
          <div class="mt-2 flex items-baseline gap-1">
            <span class="text-2xl font-bold tracking-tight tabular-nums">{{ item.value }}</span>
            <span class="text-sm text-muted-foreground">{{ item.unit }}</span>
          </div>
          <p class="mt-1 text-xs text-muted-foreground">{{ item.hint }}</p>
        </article>
      </div>

      <HostTreemap :hosts="hosts" :metric="selectedMetric" :loading="loading" />
      <div class="grid gap-4 lg:grid-cols-2">
        <HostRankingBar :hosts="hosts" :metric="selectedMetric" :loading="loading" />
        <HostLocalityHeatmap :hosts="hosts" :loading="loading" />
      </div>
    </template>
  </div>
</template>
