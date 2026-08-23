<script setup>
import { onMounted, ref, watch } from "vue";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getPoplarInchwormSummary } from "../../api/statistics.js";
import { useToast } from "../../composables/useToast.js";
import StatisticsYearFilter from "./StatisticsYearFilter.vue";
import { handleStatisticsLoadError, useStatisticsYearOptions } from "./statisticsShared.js";

const { error } = useToast();

const EMPTY_SECTION = {
  survey_records: 0,
  surveyed_points: 0,
  avg_insect_count: null,
  total_insect_count: 0,
  last_survey_date: null,
  damage_levels: [],
};

const EMPTY_SUMMARY = {
  year: null,
  adult: { ...EMPTY_SECTION },
  larva: { ...EMPTY_SECTION },
  ring_wrap: {
    survey_records: 0,
    surveyed_points: 0,
    repair_count: 0,
    adult_count: 0,
    last_survey_date: null,
  },
  ledger: {
    ledger_points: 0,
    status_counts: [],
  },
};

const summary = ref({ ...EMPTY_SUMMARY });

const { yearOptions, selectedYear } = useStatisticsYearOptions("poplar-inchworm");

watch(selectedYear, () => {
  loadSummary();
});

async function loadSummary() {
  try {
    const result = await getPoplarInchwormSummary({ year: selectedYear.value });
    summary.value = {
      year: result.year || null,
      adult: { ...EMPTY_SECTION, ...(result.adult || {}) },
      larva: { ...EMPTY_SECTION, ...(result.larva || {}) },
      ring_wrap: { ...EMPTY_SUMMARY.ring_wrap, ...(result.ring_wrap || {}) },
      ledger: { ...EMPTY_SUMMARY.ledger, ...(result.ledger || {}) },
    };
  } catch (loadError) {
    summary.value = { ...EMPTY_SUMMARY };
    handleStatisticsLoadError(error, loadError);
  }
}

function formatNumber(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  return Number(value || 0).toLocaleString("zh-CN");
}

onMounted(loadSummary);
</script>

<template>
  <div class="flex flex-col gap-4">
    <StatisticsYearFilter
      v-model="selectedYear"
      :year-options="yearOptions"
      testid="data-statistics-poplar-inchworm-year-filter"
    />

    <div class="grid gap-4 lg:grid-cols-3">
      <Card data-testid="data-statistics-poplar-inchworm-adult">
        <CardHeader class="pb-3">
          <CardTitle class="text-base">成虫调查</CardTitle>
        </CardHeader>
        <CardContent>
          <p class="text-2xl font-bold tracking-tight tabular-nums">
            {{ formatNumber(summary.adult.survey_records) }}
            <span class="text-sm font-normal text-muted-foreground">条</span>
          </p>
          <p class="mt-0.5 text-xs text-muted-foreground">
            覆盖 {{ formatNumber(summary.adult.surveyed_points) }} 个点位 · 最近调查
            {{ summary.adult.last_survey_date || "暂无" }}
          </p>
          <p class="mt-2 text-sm tabular-nums">
            平均虫口数 {{ formatNumber(summary.adult.avg_insect_count) }} · 总虫口数
            {{ formatNumber(summary.adult.total_insect_count) }}
          </p>
          <div
            v-if="summary.adult.damage_levels.length"
            class="mt-1.5 flex flex-wrap gap-1.5"
            data-testid="data-statistics-poplar-inchworm-adult-levels"
          >
            <Badge
              v-for="item in summary.adult.damage_levels"
              :key="item.damage_level"
              variant="secondary"
              class="font-normal"
            >
              {{ item.damage_level }} {{ formatNumber(item.count) }}
            </Badge>
          </div>
        </CardContent>
      </Card>

      <Card data-testid="data-statistics-poplar-inchworm-larva">
        <CardHeader class="pb-3">
          <CardTitle class="text-base">幼虫调查</CardTitle>
        </CardHeader>
        <CardContent>
          <p class="text-2xl font-bold tracking-tight tabular-nums">
            {{ formatNumber(summary.larva.survey_records) }}
            <span class="text-sm font-normal text-muted-foreground">条</span>
          </p>
          <p class="mt-0.5 text-xs text-muted-foreground">
            覆盖 {{ formatNumber(summary.larva.surveyed_points) }} 个点位 · 最近调查
            {{ summary.larva.last_survey_date || "暂无" }}
          </p>
          <p class="mt-2 text-sm tabular-nums">
            平均虫口数 {{ formatNumber(summary.larva.avg_insect_count) }} · 总虫口数
            {{ formatNumber(summary.larva.total_insect_count) }}
          </p>
          <div
            v-if="summary.larva.damage_levels.length"
            class="mt-1.5 flex flex-wrap gap-1.5"
            data-testid="data-statistics-poplar-inchworm-larva-levels"
          >
            <Badge
              v-for="item in summary.larva.damage_levels"
              :key="item.damage_level"
              variant="secondary"
              class="font-normal"
            >
              {{ item.damage_level }} {{ formatNumber(item.count) }}
            </Badge>
          </div>
        </CardContent>
      </Card>

      <Card data-testid="data-statistics-poplar-inchworm-ring">
        <CardHeader class="pb-3">
          <CardTitle class="text-base">围环调查</CardTitle>
        </CardHeader>
        <CardContent>
          <p class="text-2xl font-bold tracking-tight tabular-nums">
            {{ formatNumber(summary.ring_wrap.survey_records) }}
            <span class="text-sm font-normal text-muted-foreground">条</span>
          </p>
          <p class="mt-0.5 text-xs text-muted-foreground">
            覆盖 {{ formatNumber(summary.ring_wrap.surveyed_points) }} 个点位 · 最近围环
            {{ summary.ring_wrap.last_survey_date || "暂无" }}
          </p>
          <p class="mt-2 text-sm tabular-nums">
            补环数量 {{ formatNumber(summary.ring_wrap.repair_count) }} · 成虫数量
            {{ formatNumber(summary.ring_wrap.adult_count) }}
          </p>
        </CardContent>
      </Card>
    </div>

    <Card data-testid="data-statistics-poplar-inchworm-ledger">
      <CardHeader class="pb-3">
        <CardTitle class="text-base">台账问题点位</CardTitle>
      </CardHeader>
      <CardContent>
        <p class="text-2xl font-bold tracking-tight tabular-nums">
          {{ formatNumber(summary.ledger.ledger_points) }}
          <span class="text-sm font-normal text-muted-foreground">个</span>
        </p>
        <div
          v-if="summary.ledger.status_counts.length"
          class="mt-1.5 flex flex-wrap gap-1.5"
          data-testid="data-statistics-poplar-inchworm-ledger-status"
        >
          <Badge
            v-for="item in summary.ledger.status_counts"
            :key="item.status"
            variant="secondary"
            class="font-normal"
          >
            {{ item.status }} {{ formatNumber(item.count) }}
          </Badge>
        </div>
        <p v-else class="mt-0.5 text-xs text-muted-foreground">暂无台账记录</p>
      </CardContent>
    </Card>
  </div>
</template>
