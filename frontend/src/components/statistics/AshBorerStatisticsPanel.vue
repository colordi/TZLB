<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { Activity, Bug, MapPinned, Percent } from "@lucide/vue";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import BaseChart from "@/components/charts/BaseChart.vue";
import { Skeleton } from "@/components/ui/skeleton";
import { getAshBorerSummary } from "../../api/statistics.js";
import { useToast } from "../../composables/useToast.js";
import StatisticsYearFilter from "./StatisticsYearFilter.vue";
import { handleStatisticsLoadError, useStatisticsYearOptions } from "./statisticsShared.js";
import {
  ASH_BORER_TREES_PER_POINT,
  buildDamageLevelLocalityOption,
  buildDamageLevelOverallOption,
  buildLocalityRateBarOption,
  buildMortalityRankingOption,
  formatNumber,
  formatRate,
  rankingChartHeight,
} from "./ashBorerChartOptions.js";

const { error } = useToast();

const EMPTY_SUMMARY = {
  year: null,
  trees_per_point: ASH_BORER_TREES_PER_POINT,
  totals: {
    survey_records: 0,
    surveyed_points: 0,
    surveyed_trees: 0,
    excluded_points: 0,
    agrilus_damaged_plants: 0,
    agrilus_holes: 0,
    cossus_damaged_plants: 0,
    dead_plants: 0,
    felled_plants: 0,
    mortality_rate: null,
    agrilus_infestation_rate: null,
    cossus_infestation_rate: null,
    agrilus_damage_levels: { none: 0, light: 0, medium: 0, high: 0 },
    cossus_damage_levels: { none: 0, light: 0, medium: 0, high: 0 },
    last_survey_date: null,
  },
  localities: [],
};

const loading = ref(false);
const summary = ref({ ...EMPTY_SUMMARY, totals: { ...EMPTY_SUMMARY.totals } });

const { yearOptions, selectedYear } = useStatisticsYearOptions("ash-borer");

watch(selectedYear, () => {
  loadSummary();
});

const totals = computed(() => summary.value?.totals || EMPTY_SUMMARY.totals);
const localities = computed(() =>
  Array.isArray(summary.value?.localities) ? summary.value.localities : [],
);
const treesPerPoint = computed(
  () => summary.value?.trees_per_point || ASH_BORER_TREES_PER_POINT,
);

const kpiItems = computed(() => [
  {
    key: "survey",
    label: "有效调查点位",
    value: formatNumber(totals.value.surveyed_points),
    unit: "个",
    icon: MapPinned,
    hint: `已排除换植 ${formatNumber(totals.value.excluded_points)} 个 · 最近调查 ${totals.value.last_survey_date || "暂无"}`,
  },
  {
    key: "mortality",
    label: "死亡率",
    value: formatRate(totals.value.mortality_rate),
    unit: "",
    icon: Activity,
    hint: `目测死亡 ${formatNumber(totals.value.dead_plants)} + 伐除 ${formatNumber(totals.value.felled_plants)} 株 / ${formatNumber(totals.value.surveyed_trees)} 株`,
  },
  {
    key: "agrilus",
    label: "窄吉丁有虫株率",
    value: formatRate(totals.value.agrilus_infestation_rate),
    unit: "",
    icon: Bug,
    hint: `受害 ${formatNumber(totals.value.agrilus_damaged_plants)} 株 · 孔数 ${formatNumber(totals.value.agrilus_holes)} 个`,
  },
  {
    key: "cossus",
    label: "木蠹蛾有虫株率",
    value: formatRate(totals.value.cossus_infestation_rate),
    unit: "",
    icon: Percent,
    hint: `受害 ${formatNumber(totals.value.cossus_damaged_plants)} 株`,
  },
]);

const rateBarOption = computed(() => buildLocalityRateBarOption(localities.value));
const rankingOption = computed(() => buildMortalityRankingOption(localities.value));
const rankingHeight = computed(() => rankingChartHeight(localities.value.length));
const damageOverallOption = computed(() => buildDamageLevelOverallOption(totals.value));
const agrilusDamageOption = computed(() =>
  buildDamageLevelLocalityOption(localities.value, "agrilus_damage_levels"),
);
const cossusDamageOption = computed(() =>
  buildDamageLevelLocalityOption(localities.value, "cossus_damage_levels"),
);

async function loadSummary() {
  loading.value = true;
  try {
    const result = await getAshBorerSummary({ year: selectedYear.value });
    summary.value = {
      year: result.year || null,
      trees_per_point: result.trees_per_point || ASH_BORER_TREES_PER_POINT,
      totals: { ...EMPTY_SUMMARY.totals, ...(result.totals || {}) },
      localities: Array.isArray(result.localities) ? result.localities : [],
    };
  } catch (loadError) {
    summary.value = { ...EMPTY_SUMMARY, totals: { ...EMPTY_SUMMARY.totals } };
    handleStatisticsLoadError(error, loadError);
  } finally {
    loading.value = false;
  }
}

onMounted(loadSummary);
</script>

<template>
  <div class="flex flex-col gap-4">
    <StatisticsYearFilter
      v-model="selectedYear"
      :year-options="yearOptions"
      testid="data-statistics-ash-borer-year-filter"
    />

    <div
      class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
      data-testid="data-statistics-ash-borer-totals"
    >
      <template v-if="loading">
        <Skeleton v-for="index in 4" :key="index" class="h-24 rounded-xl" />
      </template>
      <article
        v-for="item in kpiItems"
        v-else
        :key="item.key"
        class="rounded-xl border bg-card p-4 shadow-sm"
        :data-testid="`data-statistics-ash-borer-kpi-${item.key}`"
      >
        <div class="flex items-center justify-between gap-2">
          <p class="text-sm text-muted-foreground">{{ item.label }}</p>
          <component :is="item.icon" class="size-4 text-muted-foreground" />
        </div>
        <div class="mt-2 flex items-baseline gap-1">
          <span class="text-2xl font-bold tracking-tight tabular-nums">{{ item.value }}</span>
          <span v-if="item.unit" class="text-sm text-muted-foreground">{{ item.unit }}</span>
        </div>
        <p class="mt-1 text-xs text-muted-foreground">{{ item.hint }}</p>
      </article>
    </div>

    <Card data-testid="data-statistics-ash-borer-locality-chart">
      <CardHeader class="pb-3">
        <CardTitle class="text-base">各属地危害率对比</CardTitle>
        <CardDescription>
          每个点位固定调查 {{ treesPerPoint }} 株。死亡率 =（目测死亡 + 伐除）/ {{ treesPerPoint }}，
          有虫株率 = 受害株 / {{ treesPerPoint }}。统计前已排除存在换植的点位。
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div
          v-if="!loading && localities.length === 0"
          class="rounded-xl border border-dashed px-4 py-16 text-center text-sm text-muted-foreground"
          data-testid="data-statistics-ash-borer-locality-empty"
        >
          暂无白蜡蛀干害虫调查数据。
        </div>
        <BaseChart v-else :option="rateBarOption" height="380px" :loading="loading" />
      </CardContent>
    </Card>

    <Card data-testid="data-statistics-ash-borer-mortality-ranking">
      <CardHeader class="pb-3">
        <CardTitle class="text-base">属地死亡率排行</CardTitle>
        <CardDescription>按死亡率从高到低排列，悬停可查看窄吉丁与木蠹蛾有虫株率</CardDescription>
      </CardHeader>
      <CardContent>
        <div
          v-if="!loading && localities.length === 0"
          class="rounded-xl border border-dashed px-4 py-16 text-center text-sm text-muted-foreground"
          data-testid="data-statistics-ash-borer-ranking-empty"
        >
          暂无白蜡蛀干害虫调查数据。
        </div>
        <BaseChart
          v-else
          :option="rankingOption"
          :height="rankingHeight"
          :loading="loading"
        />
      </CardContent>
    </Card>

    <Card data-testid="data-statistics-ash-borer-damage-overall">
      <CardHeader class="pb-3">
        <CardTitle class="text-base">各虫种危害程度构成</CardTitle>
        <CardDescription>
          按点位有虫株率分级：0 为无（白），≤10% 为轻，≤20% 为中，&gt;20% 为重。颜色为行业危害程度约定色。
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div
          v-if="!loading && localities.length === 0"
          class="rounded-xl border border-dashed px-4 py-16 text-center text-sm text-muted-foreground"
        >
          暂无白蜡蛀干害虫调查数据。
        </div>
        <BaseChart v-else :option="damageOverallOption" height="320px" :loading="loading" />
      </CardContent>
    </Card>

    <div class="grid gap-4 lg:grid-cols-2">
      <Card data-testid="data-statistics-ash-borer-damage-agrilus">
        <CardHeader class="pb-3">
          <CardTitle class="text-base">窄吉丁各属地危害程度</CardTitle>
          <CardDescription>按重度点位数排序，柱高为有效调查点位数</CardDescription>
        </CardHeader>
        <CardContent>
          <div
            v-if="!loading && localities.length === 0"
            class="rounded-xl border border-dashed px-4 py-16 text-center text-sm text-muted-foreground"
          >
            暂无白蜡蛀干害虫调查数据。
          </div>
          <BaseChart v-else :option="agrilusDamageOption" height="360px" :loading="loading" />
        </CardContent>
      </Card>

      <Card data-testid="data-statistics-ash-borer-damage-cossus">
        <CardHeader class="pb-3">
          <CardTitle class="text-base">木蠹蛾各属地危害程度</CardTitle>
          <CardDescription>按重度点位数排序，柱高为有效调查点位数</CardDescription>
        </CardHeader>
        <CardContent>
          <div
            v-if="!loading && localities.length === 0"
            class="rounded-xl border border-dashed px-4 py-16 text-center text-sm text-muted-foreground"
          >
            暂无白蜡蛀干害虫调查数据。
          </div>
          <BaseChart v-else :option="cossusDamageOption" height="360px" :loading="loading" />
        </CardContent>
      </Card>
    </div>
  </div>
</template>
