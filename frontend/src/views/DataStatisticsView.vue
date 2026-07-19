<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { ChartColumn, ChevronLeft, ChevronRight, Table2 } from "@lucide/vue";

import {
  getWhiteMothDailyStatistics,
  getWhiteMothGenerationSummary,
} from "../api/statistics.js";
import { isUnauthorizedError } from "../api/http.js";
import { useToast } from "../composables/useToast.js";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const PEST_OPTIONS = Object.freeze([
  { value: "white-moth", label: "美国白蛾", disabled: false },
  { value: "poplar-inchworm", label: "春尺蠖", disabled: true },
  { value: "sophora-inchworm", label: "国槐尺蠖", disabled: true },
  { value: "other-pests", label: "其他害虫", disabled: true },
]);

const { error } = useToast();
const loading = ref(false);
const columns = ref([]);
const rows = ref([]);
const generationSummary = ref({ as_of_date: "", year: null, generations: [] });
const selectedPest = ref("white-moth");
const currentPage = ref(1);
const PAGE_SIZE = 7;

const currentYear = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: 5 }, (_, index) => currentYear - 2 + index);
const GENERATION_OPTIONS = ["", "第一代", "第二代", "第三代"];

const selectedYear = ref(currentYear);
const selectedGeneration = ref("");

const totalPages = computed(() => Math.max(1, Math.ceil(rows.value.length / PAGE_SIZE)));

const paginatedRows = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE;
  return rows.value.slice(start, start + PAGE_SIZE);
});

watch(rows, () => {
  currentPage.value = 1;
});

watch([selectedYear, selectedGeneration], () => {
  loadWhiteMothDailyStatistics();
});

function formatNumber(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  return Number(value || 0).toLocaleString("zh-CN");
}

function formatCell(row, column) {
  const value = row[column.key];
  return column.type === "number" ? formatNumber(value) : value || "--";
}

function resolveColumnGroup(columnKey) {
  if (columnKey === "date") {
    return "日期";
  }
  if (
    columnKey === "daily_treatment_plants" ||
    columnKey === "cumulative_completed_points"
  ) {
    return "汇总";
  }
  if (columnKey.startsWith("urban_")) {
    return "城区";
  }
  if (columnKey.startsWith("town_")) {
    return "乡镇";
  }
  if (columnKey === "daily_dispatch_points") {
    return "派单";
  }
  return "";
}

const groupedColumns = computed(() => {
  const groups = [];
  let current = null;
  columns.value.forEach((column, index) => {
    const label = resolveColumnGroup(column.key);
    if (!current || current.label !== label) {
      current = { label, start: index, count: 1, columns: [column] };
      groups.push(current);
    } else {
      current.count += 1;
      current.columns.push(column);
    }
  });
  return groups;
});

const groupStartIndices = computed(() => {
  return new Set(groupedColumns.value.filter((g) => g.start > 0).map((g) => g.start));
});

function cellClass(column) {
  return {
    "text-right tabular-nums": column.type === "number",
    "whitespace-nowrap": column.type === "date",
  };
}

async function loadWhiteMothDailyStatistics() {
  loading.value = true;
  try {
    const [result, summaryResult] = await Promise.all([
      getWhiteMothDailyStatistics({
        year: selectedYear.value,
        generation: selectedGeneration.value || undefined,
      }),
      getWhiteMothGenerationSummary(),
    ]);
    columns.value = Array.isArray(result.columns) ? result.columns : [];
    rows.value = Array.isArray(result.rows) ? result.rows : [];
    generationSummary.value = {
      as_of_date: summaryResult.as_of_date || "",
      year: summaryResult.year || null,
      generations: Array.isArray(summaryResult.generations) ? summaryResult.generations : [],
    };
    currentPage.value = 1;
  } catch (loadError) {
    columns.value = [];
    rows.value = [];
    generationSummary.value = { as_of_date: "", year: null, generations: [] };
    currentPage.value = 1;
    if (isUnauthorizedError(loadError)) {
      return;
    }
    error(`${loadError.message || loadError}`, "读取数据统计失败");
  } finally {
    loading.value = false;
  }
}

onMounted(loadWhiteMothDailyStatistics);
</script>

<template>
  <section class="mx-auto flex w-full max-w-6xl flex-col gap-4">
    <header class="space-y-1">
      <p class="text-[10px] font-bold tracking-[0.12em] text-primary">DATA STATISTICS</p>
      <h1 class="text-2xl font-bold tracking-tight md:text-3xl">数据统计</h1>
      <p class="text-sm text-muted-foreground">查看各虫种的核心统计指标。</p>
    </header>

    <section class="flex flex-wrap gap-2" aria-label="虫种统计">
      <Button
        v-for="option in PEST_OPTIONS"
        :key="option.value"
        type="button"
        size="sm"
        :variant="selectedPest === option.value ? 'default' : 'outline'"
        :disabled="option.disabled"
        :data-testid="`data-statistics-pest-${option.value}`"
        @click="selectedPest = option.value"
      >
        <ChartColumn class="size-4" />
        <span>{{ option.label }}</span>
      </Button>
    </section>

    <Card data-testid="data-statistics-summary-panel">
      <CardHeader class="pb-3">
        <div class="flex flex-wrap items-baseline justify-between gap-2">
          <CardTitle class="text-lg">
            {{ generationSummary.year || selectedYear }} 年各世代累计情况
          </CardTitle>
          <span v-if="generationSummary.as_of_date" class="text-sm text-muted-foreground">
            截至 {{ generationSummary.as_of_date }}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <div
          class="grid gap-3 md:grid-cols-3"
          data-testid="data-statistics-generation-summary"
        >
          <article
            v-for="item in generationSummary.generations"
            :key="item.generation"
            class="rounded-lg border bg-card p-4 text-sm"
            :data-testid="`data-statistics-summary-${item.generation}`"
          >
            <h4 class="mb-2 font-semibold">{{ item.generation }}</h4>
            <p class="text-muted-foreground">
              完成调查 <strong class="text-foreground">{{ formatNumber(item.surveyed_points) }}</strong> 个点位
              <span>
                （城区 {{ formatNumber(item.urban_surveyed_points) }} 个、乡镇
                {{ formatNumber(item.town_surveyed_points) }} 个）
              </span>
            </p>
            <p class="mt-1 text-muted-foreground">
              发现受害点位 <strong class="text-foreground">{{ formatNumber(item.damaged_points) }}</strong> 个
              <span>
                （城区 {{ formatNumber(item.urban_damaged_points) }} 个、乡镇
                {{ formatNumber(item.town_damaged_points) }} 个）
              </span>
            </p>
            <p class="mt-1 text-muted-foreground">
              共下发派单 <strong class="text-foreground">{{ formatNumber(item.dispatch_count) }}</strong> 次
            </p>
            <p
              v-if="item.dispatch_frequency?.length"
              class="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground"
            >
              <span v-for="frequency in item.dispatch_frequency" :key="frequency.dispatch_times">
                {{ frequency.dispatch_times }} 次派单点位
                {{ formatNumber(frequency.point_count) }} 个
              </span>
            </p>
            <p v-else class="mt-2 text-xs text-muted-foreground">暂无派单</p>
          </article>
        </div>
      </CardContent>
    </Card>

    <Card data-testid="data-statistics-daily-panel">
      <CardHeader class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div class="space-y-1">
          <CardTitle class="text-lg">美国白蛾每日信息统计</CardTitle>
          <CardDescription>{{ rows.length }} 条每日记录</CardDescription>
        </div>
        <div class="flex flex-wrap items-center gap-2" aria-label="筛选条件">
          <label class="flex items-center gap-2 text-sm text-muted-foreground">
            <span>年份</span>
            <select
              v-model="selectedYear"
              class="h-9 rounded-md border border-input bg-background px-2 text-sm"
              data-testid="data-statistics-year-filter"
            >
              <option v-for="year in YEAR_OPTIONS" :key="year" :value="year">
                {{ year }}
              </option>
            </select>
          </label>
          <label class="flex items-center gap-2 text-sm text-muted-foreground">
            <span>世代</span>
            <select
              v-model="selectedGeneration"
              class="h-9 rounded-md border border-input bg-background px-2 text-sm"
              data-testid="data-statistics-generation-filter"
            >
              <option value="">全部</option>
              <option v-for="gen in GENERATION_OPTIONS.slice(1)" :key="gen" :value="gen">
                {{ gen }}
              </option>
            </select>
          </label>
        </div>
      </CardHeader>

      <CardContent class="space-y-4">
        <div v-if="loading" class="py-8 text-center text-muted-foreground">
          正在读取每日统计…
        </div>
        <div v-else-if="rows.length === 0" class="py-8 text-center text-muted-foreground">
          暂无美国白蛾每日统计数据。
        </div>

        <div v-else class="overflow-x-auto rounded-md border">
          <table class="w-full min-w-[48rem] border-collapse text-sm">
            <thead>
              <tr class="border-b bg-muted/50">
                <template v-for="group in groupedColumns" :key="group.label">
                  <th
                    v-if="group.count === 1"
                    rowspan="2"
                    class="px-3 py-2 text-left font-semibold text-muted-foreground"
                    :class="[cellClass(group.columns[0]), group.start > 0 ? 'border-l' : '']"
                  >
                    {{ group.label }}
                  </th>
                  <th
                    v-else
                    :colspan="group.count"
                    class="px-3 py-2 text-center font-semibold text-muted-foreground"
                    :class="group.start > 0 ? 'border-l' : ''"
                  >
                    {{ group.label }}
                  </th>
                </template>
              </tr>
              <tr class="border-b bg-muted/30">
                <template v-for="(column, index) in columns" :key="column.key">
                  <th
                    v-if="groupedColumns.find((g) => g.label === resolveColumnGroup(column.key)).count > 1"
                    class="px-3 py-2 text-left font-medium text-muted-foreground"
                    :class="[cellClass(column), groupStartIndices.has(index) ? 'border-l' : '']"
                  >
                    {{ column.label }}
                  </th>
                </template>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(row, rowIndex) in paginatedRows"
                :key="row.date"
                class="border-b last:border-0 hover:bg-muted/40"
                :class="{ 'bg-primary/5': rowIndex === 0 && currentPage === 1 }"
                :data-testid="`data-statistics-row-${row.date}`"
              >
                <td
                  v-for="(column, index) in columns"
                  :key="column.key"
                  class="px-3 py-2"
                  :class="[cellClass(column), groupStartIndices.has(index) ? 'border-l' : '']"
                >
                  <span
                    v-if="column.key === 'date'"
                    class="inline-flex items-center gap-1.5 font-medium"
                  >
                    <Table2 class="size-4 text-muted-foreground" />
                    <span>{{ formatCell(row, column) }}</span>
                  </span>
                  <span v-else>{{ formatCell(row, column) }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <nav
          v-if="totalPages > 1"
          class="flex items-center justify-center gap-3"
          aria-label="分页导航"
        >
          <Button
            type="button"
            variant="outline"
            size="sm"
            :disabled="currentPage === 1"
            data-testid="data-statistics-prev-page"
            @click="currentPage -= 1"
          >
            <ChevronLeft class="size-4" />
            <span>上一页</span>
          </Button>
          <span class="text-sm text-muted-foreground">
            第 {{ currentPage }} / {{ totalPages }} 页
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            :disabled="currentPage === totalPages"
            data-testid="data-statistics-next-page"
            @click="currentPage += 1"
          >
            <span>下一页</span>
            <ChevronRight class="size-4" />
          </Button>
        </nav>
      </CardContent>
    </Card>
  </section>
</template>
