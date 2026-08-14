<script setup>
import { onMounted, ref, watch } from "vue";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getYangshuShiyeSummary } from "../../api/statistics.js";
import { useToast } from "../../composables/useToast.js";
import StatisticsYearFilter from "./StatisticsYearFilter.vue";
import { buildYearOptions, handleStatisticsLoadError } from "./statisticsShared.js";

const { error } = useToast();

const EMPTY_SUMMARY = {
  year: null,
  totals: {
    survey_records: 0,
    surveyed_points: 0,
    problem_records: 0,
    no_problem_records: 0,
    problem_points: 0,
    problem_rate: 0,
    last_survey_date: null,
    ledger_points: 0,
    status_counts: [],
  },
  pest_types: [],
};

const summary = ref({ ...EMPTY_SUMMARY });

const YEAR_OPTIONS = buildYearOptions();
const selectedYear = ref(new Date().getFullYear());

watch(selectedYear, () => {
  loadSummary();
});

async function loadSummary() {
  try {
    const result = await getYangshuShiyeSummary({ year: selectedYear.value });
    summary.value = {
      year: result.year || null,
      totals: { ...EMPTY_SUMMARY.totals, ...(result.totals || {}) },
      pest_types: Array.isArray(result.pest_types) ? result.pest_types : [],
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

function formatRate(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  return `${Number(value).toFixed(1)}%`;
}

onMounted(loadSummary);
</script>

<template>
  <div class="flex flex-col gap-4">
    <StatisticsYearFilter
      v-model="selectedYear"
      :year-options="YEAR_OPTIONS"
      testid="data-statistics-yangshu-shiye-year-filter"
    />

    <Card data-testid="data-statistics-yangshu-shiye-totals">
      <CardHeader class="pb-3">
        <CardTitle class="text-base">
          {{ summary.year || selectedYear }} 年整体情况
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div class="rounded-lg border p-4" data-testid="data-statistics-yangshu-shiye-kpi-survey">
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
          <div class="rounded-lg border p-4" data-testid="data-statistics-yangshu-shiye-kpi-problem">
            <p class="text-sm text-muted-foreground">发现问题</p>
            <p class="mt-1 text-2xl font-bold tracking-tight tabular-nums">
              {{ formatNumber(summary.totals.problem_records) }}
              <span class="text-sm font-normal text-muted-foreground">条</span>
            </p>
            <p class="mt-0.5 text-xs text-muted-foreground">
              未发现问题 {{ formatNumber(summary.totals.no_problem_records) }} 条 · 涉及
              {{ formatNumber(summary.totals.problem_points) }} 个点位
            </p>
          </div>
          <div class="rounded-lg border p-4" data-testid="data-statistics-yangshu-shiye-kpi-rate">
            <p class="text-sm text-muted-foreground">问题发现率</p>
            <p class="mt-1 text-2xl font-bold tracking-tight tabular-nums">
              {{ formatRate(summary.totals.problem_rate) }}
            </p>
            <p class="mt-0.5 text-xs text-muted-foreground">发现问题记录 / 调查记录</p>
          </div>
          <div class="rounded-lg border p-4" data-testid="data-statistics-yangshu-shiye-kpi-ledger">
            <p class="text-sm text-muted-foreground">台账问题点位</p>
            <p class="mt-1 text-2xl font-bold tracking-tight tabular-nums">
              {{ formatNumber(summary.totals.ledger_points) }}
              <span class="text-sm font-normal text-muted-foreground">个</span>
            </p>
            <div
              v-if="summary.totals.status_counts.length"
              class="mt-1.5 flex flex-wrap gap-1.5"
            >
              <Badge
                v-for="item in summary.totals.status_counts"
                :key="item.status"
                variant="secondary"
                class="font-normal"
              >
                {{ item.status }} {{ formatNumber(item.count) }}
              </Badge>
            </div>
            <p v-else class="mt-0.5 text-xs text-muted-foreground">暂无台账记录</p>
          </div>
        </div>
      </CardContent>
    </Card>

    <Card data-testid="data-statistics-yangshu-shiye-types">
      <CardHeader class="pb-3">
        <CardTitle class="text-base">虫害类型计数</CardTitle>
      </CardHeader>
      <CardContent>
        <Table v-if="summary.pest_types.length">
          <TableHeader>
            <TableRow>
              <TableHead>虫害类型</TableHead>
              <TableHead class="text-right">调查记录数</TableHead>
              <TableHead class="text-right">发现问题数</TableHead>
              <TableHead class="text-right">问题点位数</TableHead>
              <TableHead class="text-right">最近调查日期</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="item in summary.pest_types"
              :key="item.pest_type"
              :data-testid="`data-statistics-yangshu-shiye-row-${item.pest_type}`"
            >
              <TableCell class="font-medium">{{ item.pest_type }}</TableCell>
              <TableCell class="text-right tabular-nums">
                {{ formatNumber(item.survey_records) }}
              </TableCell>
              <TableCell class="text-right tabular-nums">
                {{ formatNumber(item.problem_records) }}
              </TableCell>
              <TableCell class="text-right tabular-nums">
                {{ formatNumber(item.problem_points) }}
              </TableCell>
              <TableCell class="text-right tabular-nums">
                {{ item.last_survey_date || "--" }}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
        <p v-else class="py-6 text-center text-sm text-muted-foreground">
          暂无杨树食叶害虫调查数据。
        </p>
      </CardContent>
    </Card>
  </div>
</template>
