<script setup>
import { onMounted, ref, watch } from "vue";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getAshBorerSummary } from "../../api/statistics.js";
import { useToast } from "../../composables/useToast.js";
import StatisticsYearFilter from "./StatisticsYearFilter.vue";
import { handleStatisticsLoadError, useStatisticsYearOptions } from "./statisticsShared.js";

const { error } = useToast();

const EMPTY_SUMMARY = {
  year: null,
  totals: {
    survey_records: 0,
    surveyed_points: 0,
    agrilus_damaged_plants: 0,
    agrilus_holes: 0,
    cossus_damaged_plants: 0,
    dead_plants: 0,
    felled_plants: 0,
    replanted_plants: 0,
    last_survey_date: null,
  },
  localities: [],
};

const summary = ref({ ...EMPTY_SUMMARY });

const { yearOptions, selectedYear } = useStatisticsYearOptions("ash-borer");

watch(selectedYear, () => {
  loadSummary();
});

async function loadSummary() {
  try {
    const result = await getAshBorerSummary({ year: selectedYear.value });
    summary.value = {
      year: result.year || null,
      totals: { ...EMPTY_SUMMARY.totals, ...(result.totals || {}) },
      localities: Array.isArray(result.localities) ? result.localities : [],
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
      testid="data-statistics-ash-borer-year-filter"
    />

    <Card data-testid="data-statistics-ash-borer-totals">
      <CardHeader class="pb-3">
        <CardTitle class="text-base">
          {{ summary.year || selectedYear }} 年整体情况
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div class="rounded-lg border p-4" data-testid="data-statistics-ash-borer-kpi-survey">
            <p class="text-sm text-muted-foreground">调查记录</p>
            <p class="mt-1 text-2xl font-bold tracking-tight tabular-nums">
              {{ formatNumber(summary.totals.survey_records) }}
              <span class="text-sm font-normal text-muted-foreground">条</span>
            </p>
            <p class="mt-0.5 text-xs text-muted-foreground">
              覆盖 {{ formatNumber(summary.totals.surveyed_points) }} 个点位 · 最近调查
              {{ summary.totals.last_survey_date || "暂无" }}
            </p>
          </div>
          <div class="rounded-lg border p-4" data-testid="data-statistics-ash-borer-kpi-agrilus">
            <p class="text-sm text-muted-foreground">窄吉丁危害</p>
            <p class="mt-1 text-2xl font-bold tracking-tight tabular-nums">
              {{ formatNumber(summary.totals.agrilus_damaged_plants) }}
              <span class="text-sm font-normal text-muted-foreground">株</span>
            </p>
            <p class="mt-0.5 text-xs text-muted-foreground">
              窄吉丁孔数 {{ formatNumber(summary.totals.agrilus_holes) }} 个
            </p>
          </div>
          <div class="rounded-lg border p-4" data-testid="data-statistics-ash-borer-kpi-cossus">
            <p class="text-sm text-muted-foreground">木蠹蛾危害</p>
            <p class="mt-1 text-2xl font-bold tracking-tight tabular-nums">
              {{ formatNumber(summary.totals.cossus_damaged_plants) }}
              <span class="text-sm font-normal text-muted-foreground">株</span>
            </p>
            <p class="mt-0.5 text-xs text-muted-foreground">
              目测死亡 {{ formatNumber(summary.totals.dead_plants) }} 株
            </p>
          </div>
          <div class="rounded-lg border p-4" data-testid="data-statistics-ash-borer-kpi-disposal">
            <p class="text-sm text-muted-foreground">伐除换植</p>
            <p class="mt-1 text-2xl font-bold tracking-tight tabular-nums">
              {{ formatNumber(summary.totals.felled_plants + summary.totals.replanted_plants) }}
              <span class="text-sm font-normal text-muted-foreground">株</span>
            </p>
            <p class="mt-0.5 text-xs text-muted-foreground">
              伐除 {{ formatNumber(summary.totals.felled_plants) }} · 换植
              {{ formatNumber(summary.totals.replanted_plants) }}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>

    <Card data-testid="data-statistics-ash-borer-localities">
      <CardHeader class="pb-3">
        <CardTitle class="text-base">各属地危害情况</CardTitle>
      </CardHeader>
      <CardContent>
        <Table v-if="summary.localities.length">
          <TableHeader>
            <TableRow>
              <TableHead>属地</TableHead>
              <TableHead class="text-right">调查记录数</TableHead>
              <TableHead class="text-right">窄吉丁危害（株）</TableHead>
              <TableHead class="text-right">木蠹蛾危害（株）</TableHead>
              <TableHead class="text-right">目测死亡（株）</TableHead>
              <TableHead class="text-right">伐除（株）</TableHead>
              <TableHead class="text-right">换植（株）</TableHead>
              <TableHead class="text-right">最近调查日期</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="item in summary.localities"
              :key="item.locality"
              :data-testid="`data-statistics-ash-borer-row-${item.locality}`"
            >
              <TableCell class="font-medium">{{ item.locality }}</TableCell>
              <TableCell class="text-right tabular-nums">
                {{ formatNumber(item.survey_records) }}
              </TableCell>
              <TableCell class="text-right tabular-nums">
                {{ formatNumber(item.agrilus_damaged_plants) }}
              </TableCell>
              <TableCell class="text-right tabular-nums">
                {{ formatNumber(item.cossus_damaged_plants) }}
              </TableCell>
              <TableCell class="text-right tabular-nums">
                {{ formatNumber(item.dead_plants) }}
              </TableCell>
              <TableCell class="text-right tabular-nums">
                {{ formatNumber(item.felled_plants) }}
              </TableCell>
              <TableCell class="text-right tabular-nums">
                {{ formatNumber(item.replanted_plants) }}
              </TableCell>
              <TableCell class="text-right tabular-nums">
                {{ item.last_survey_date || "--" }}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
        <p v-else class="py-6 text-center text-sm text-muted-foreground">
          暂无白蜡蛀干害虫调查数据。
        </p>
      </CardContent>
    </Card>
  </div>
</template>
