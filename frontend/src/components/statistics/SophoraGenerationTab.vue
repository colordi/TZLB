<script setup>
import { Calendar } from "@lucide/vue";
import { onMounted, ref, watch } from "vue";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getSophoraGenerationSummary } from "../../api/statistics.js";
import { useToast } from "../../composables/useToast.js";
import StatisticsYearFilter from "./StatisticsYearFilter.vue";
import { handleStatisticsLoadError, useStatisticsYearOptions } from "./statisticsShared.js";

const { error } = useToast();
const summary = ref({ as_of_date: "", year: null, generations: [] });

const { yearOptions, selectedYear } = useStatisticsYearOptions("sophora-inchworm");

watch(selectedYear, () => {
  loadSummary();
});

async function loadSummary() {
  try {
    const result = await getSophoraGenerationSummary({ year: selectedYear.value });
    summary.value = {
      as_of_date: result.as_of_date || "",
      year: result.year || null,
      generations: Array.isArray(result.generations) ? result.generations : [],
    };
  } catch (loadError) {
    summary.value = { as_of_date: "", year: null, generations: [] };
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

function formatAvg(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  return Number(value).toFixed(1);
}

function formatShortDate(value) {
  if (!value) {
    return "";
  }
  const text = String(value);
  return text.length >= 10 ? text.slice(5, 10) : text;
}

onMounted(loadSummary);
</script>

<template>
  <div class="flex flex-col gap-4">
    <StatisticsYearFilter
      v-model="selectedYear"
      :year-options="yearOptions"
      testid="data-statistics-sophora-generation-year-filter"
    />

    <Card data-testid="data-statistics-sophora-summary-panel">
      <CardHeader class="pb-3">
        <CardTitle class="text-base">
          {{ summary.year || selectedYear }} 年国槐尺蠖各世代累计情况
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div
          class="grid gap-3 md:grid-cols-3"
          data-testid="data-statistics-sophora-generation-summary"
        >
          <article
            v-for="item in summary.generations"
            :key="item.generation"
            class="rounded-lg border p-4"
            :data-testid="`data-statistics-sophora-summary-${item.generation}`"
          >
            <div class="flex items-baseline justify-between gap-2">
              <h4 class="text-sm font-medium text-muted-foreground">{{ item.generation }}</h4>
              <p class="flex items-center gap-1 text-xs text-muted-foreground/80 tabular-nums">
                <Calendar class="size-3" />
                <span v-if="item.start_date && item.end_date">
                  {{ formatShortDate(item.start_date) }} ~ {{ formatShortDate(item.end_date) }}
                </span>
                <span v-else>暂无调查日期</span>
              </p>
            </div>

            <div class="mt-2">
              <div class="flex items-baseline gap-1.5">
                <span class="text-2xl font-bold tracking-tight tabular-nums">
                  {{ formatNumber(item.surveyed_points) }}
                </span>
                <span class="text-sm text-muted-foreground">个点位完成调查</span>
              </div>
              <p class="mt-0.5 text-xs text-muted-foreground">
                受害 {{ formatNumber(item.damaged_points) }} · 受害率
                {{ formatRate(item.damage_rate) }}
              </p>
            </div>

            <dl class="mt-3 space-y-2 border-t pt-3 text-sm">
              <div class="flex items-baseline justify-between gap-2">
                <dt class="text-muted-foreground">轻 / 中 / 重</dt>
                <dd class="font-medium tabular-nums">
                  {{ formatNumber(item.light_points) }} /
                  {{ formatNumber(item.medium_points) }} /
                  {{ formatNumber(item.severe_points) }}
                </dd>
              </div>
              <div class="flex items-baseline justify-between gap-2">
                <dt class="text-muted-foreground">受害点平均虫口</dt>
                <dd class="font-medium tabular-nums">{{ formatAvg(item.avg_insect_count) }}</dd>
              </div>
              <div class="flex items-baseline justify-between gap-2">
                <dt class="text-muted-foreground">台账点数</dt>
                <dd class="font-medium tabular-nums">{{ formatNumber(item.ledger_points) }} 个</dd>
              </div>
              <div class="flex items-baseline justify-between gap-2">
                <dt class="text-muted-foreground">闭环率</dt>
                <dd class="font-medium tabular-nums">{{ formatRate(item.closure_rate) }}</dd>
              </div>
            </dl>

            <div class="mt-3 flex flex-wrap gap-1.5">
              <Badge variant="secondary" class="font-normal">
                待防治 {{ formatNumber(item.pending_treatment) }}
              </Badge>
              <Badge variant="secondary" class="font-normal">
                待复查 {{ formatNumber(item.pending_recheck) }}
              </Badge>
              <Badge variant="secondary" class="font-normal">
                复查异常 {{ formatNumber(item.recheck_abnormal) }}
              </Badge>
              <Badge variant="secondary" class="font-normal">
                已闭环 {{ formatNumber(item.closed_points) }}
              </Badge>
            </div>
          </article>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
