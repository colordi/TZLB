<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { ChartColumn, ChevronLeft, ChevronRight, RefreshCw, Table2 } from "@lucide/vue";

import {
  getWhiteMothDailyStatistics,
  getWhiteMothGenerationSummary,
} from "../api/statistics.js";
import { isUnauthorizedError } from "../api/http.js";
import { useToast } from "../composables/useToast.js";

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
    "data-statistics-cell--date": column.type === "date",
    "data-statistics-cell--number": column.type === "number",
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
  <section class="page-shell data-statistics-page">
    <header class="data-statistics-head">
      <div>
        <p class="data-statistics-eyebrow">DATA STATISTICS</p>
        <h1>数据统计</h1>
        <p>查看各虫种的核心统计指标。</p>
      </div>
      <div class="data-statistics-actions" aria-label="数据统计操作">
        <button
          type="button"
          class="button-secondary"
          :disabled="loading"
          data-testid="data-statistics-refresh"
          @click="loadWhiteMothDailyStatistics"
        >
          <RefreshCw :size="18" :stroke-width="2" />
          <span>{{ loading ? "刷新中" : "刷新统计" }}</span>
        </button>
      </div>
    </header>

    <section class="data-statistics-tabs" aria-label="虫种统计">
      <button
        v-for="option in PEST_OPTIONS"
        :key="option.value"
        type="button"
        class="data-statistics-tab"
        :class="{ 'is-active': selectedPest === option.value }"
        :disabled="option.disabled"
        :data-testid="`data-statistics-pest-${option.value}`"
        @click="selectedPest = option.value"
      >
        <ChartColumn :size="16" :stroke-width="2" />
        <span>{{ option.label }}</span>
      </button>
    </section>

    <section
      class="data-statistics-panel data-statistics-summary-panel"
      data-testid="data-statistics-summary-panel"
    >
      <div class="data-statistics-summary-head">
        <h2>{{ generationSummary.year || selectedYear }} 年各世代累计情况</h2>
        <span v-if="generationSummary.as_of_date">截至 {{ generationSummary.as_of_date }}</span>
      </div>
      <div class="data-statistics-summaries" data-testid="data-statistics-generation-summary">
        <article
          v-for="item in generationSummary.generations"
          :key="item.generation"
          class="data-statistics-summary"
          :data-testid="`data-statistics-summary-${item.generation}`"
        >
          <h4>{{ item.generation }}</h4>
          <p>
            完成调查 <strong>{{ formatNumber(item.surveyed_points) }}</strong> 个点位
            <span>（城区 {{ formatNumber(item.urban_surveyed_points) }} 个、乡镇 {{ formatNumber(item.town_surveyed_points) }} 个）</span>
          </p>
          <p>
            发现受害点位 <strong>{{ formatNumber(item.damaged_points) }}</strong> 个
            <span>（城区 {{ formatNumber(item.urban_damaged_points) }} 个、乡镇 {{ formatNumber(item.town_damaged_points) }} 个）</span>
          </p>
          <p>共下发派单 <strong>{{ formatNumber(item.dispatch_count) }}</strong> 次</p>
          <p v-if="item.dispatch_frequency?.length" class="data-statistics-frequency">
            <span v-for="frequency in item.dispatch_frequency" :key="frequency.dispatch_times">
              {{ frequency.dispatch_times }} 次派单点位 {{ formatNumber(frequency.point_count) }} 个
            </span>
          </p>
          <p v-else class="data-statistics-frequency">暂无派单</p>
        </article>
      </div>
    </section>

    <section class="data-statistics-panel" data-testid="data-statistics-daily-panel">
      <div class="data-statistics-panel-head">
        <div>
          <h2>美国白蛾每日信息统计</h2>
          <p>{{ rows.length }} 条每日记录</p>
        </div>
        <div class="data-statistics-filters" aria-label="筛选条件">
          <label class="data-statistics-filter">
            <span>年份</span>
            <select v-model="selectedYear" data-testid="data-statistics-year-filter">
              <option v-for="year in YEAR_OPTIONS" :key="year" :value="year">
                {{ year }}
              </option>
            </select>
          </label>
          <label class="data-statistics-filter">
            <span>世代</span>
            <select v-model="selectedGeneration" data-testid="data-statistics-generation-filter">
              <option value="">全部</option>
              <option v-for="gen in GENERATION_OPTIONS.slice(1)" :key="gen" :value="gen">
                {{ gen }}
              </option>
            </select>
          </label>
        </div>
      </div>

      <div v-if="loading" class="data-statistics-empty">正在读取每日统计…</div>
      <div v-else-if="rows.length === 0" class="data-statistics-empty">
        暂无美国白蛾每日统计数据。
      </div>

      <div v-else class="data-statistics-table-wrap">
        <table>
          <thead>
            <tr class="data-statistics-group-row">
              <template v-for="group in groupedColumns" :key="group.label">
                <th
                  v-if="group.count === 1"
                  rowspan="2"
                  :class="[
                    'data-statistics-merged-header',
                    cellClass(group.columns[0]),
                    { 'group-start': group.start > 0 },
                  ]"
                >
                  {{ group.label }}
                </th>
                <th
                  v-else
                  :colspan="group.count"
                  :class="{ 'group-start': group.start > 0 }"
                >
                  {{ group.label }}
                </th>
              </template>
            </tr>
            <tr>
              <template v-for="(column, index) in columns" :key="column.key">
                <th
                  v-if="groupedColumns.find((g) => g.label === resolveColumnGroup(column.key)).count > 1"
                  :class="[cellClass(column), { 'group-start': groupStartIndices.has(index) }]"
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
              :class="{ 'is-latest': rowIndex === 0 && currentPage === 1 }"
              :data-testid="`data-statistics-row-${row.date}`"
            >
              <td
                v-for="(column, index) in columns"
                :key="column.key"
                :class="[cellClass(column), { 'group-start': groupStartIndices.has(index) }]"
              >
                <span v-if="column.key === 'date'" class="data-statistics-date">
                  <Table2 :size="16" :stroke-width="2" />
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
        class="data-statistics-pagination"
        aria-label="分页导航"
      >
        <button
          type="button"
          class="button-secondary"
          :disabled="currentPage === 1"
          data-testid="data-statistics-prev-page"
          @click="currentPage -= 1"
        >
          <ChevronLeft :size="18" :stroke-width="2" />
          <span>上一页</span>
        </button>
        <span class="data-statistics-page-info">
          第 {{ currentPage }} / {{ totalPages }} 页
        </span>
        <button
          type="button"
          class="button-secondary"
          :disabled="currentPage === totalPages"
          data-testid="data-statistics-next-page"
          @click="currentPage += 1"
        >
          <span>下一页</span>
          <ChevronRight :size="18" :stroke-width="2" />
        </button>
      </nav>
    </section>
  </section>
</template>

<style scoped>
.data-statistics-page {
  gap: 1.1rem;
}

.data-statistics-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.data-statistics-head h1 {
  margin-top: 0.2rem;
  font-size: clamp(1.7rem, 2.3vw, 2.35rem);
  line-height: 1.08;
}

.data-statistics-head p:last-child,
.data-statistics-panel-head p {
  color: var(--color-muted);
}

.data-statistics-eyebrow {
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 700;
  letter-spacing: 0.1em;
}

.data-statistics-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.65rem;
}

.data-statistics-actions button,
.data-statistics-tab {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}

.data-statistics-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.data-statistics-tab {
  min-height: 2.65rem;
  padding: 0.65rem 0.9rem;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  background: var(--color-surface-container-lowest);
  box-shadow: none;
  font-size: var(--text-sm);
}

.data-statistics-tab.is-active {
  color: var(--color-accent-on);
  border-color: var(--color-primary);
  background: var(--color-primary);
}

.data-statistics-tab:disabled {
  color: var(--color-muted-soft);
  background: var(--color-surface-container);
}

.data-statistics-panel {
  padding: 1.15rem;
  border-radius: var(--radius-md);
  background: var(--color-surface-container-lowest);
  box-shadow: var(--shadow-card);
}

.data-statistics-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.9rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.data-statistics-panel-head h2 {
  margin: 0;
}

.data-statistics-filters {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.data-statistics-summary-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.data-statistics-summary-head h2 {
  margin: 0;
}

.data-statistics-summary-head span {
  color: var(--color-muted);
  font-size: var(--text-sm);
}

.data-statistics-summaries {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.8rem;
}

.data-statistics-summary-panel {
  padding-bottom: 0.35rem;
}

.data-statistics-summary {
  margin-bottom: 1rem;
  padding: 0.9rem 1rem;
  border: 1px solid var(--color-line);
  border-left: 4px solid var(--color-primary);
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  background: var(--color-primary-soft);
  line-height: 1.8;
}

.data-statistics-summary h4,
.data-statistics-summary p {
  margin: 0;
}

.data-statistics-summary h4 {
  color: var(--color-text);
  font-size: var(--text-lg);
}

.data-statistics-summary p span {
  display: block;
}

.data-statistics-summary strong {
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: 1.1em;
}

.data-statistics-frequency {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 0.8rem;
  padding-top: 0.35rem;
  border-top: 1px solid var(--color-line);
}

.data-statistics-frequency span {
  display: inline;
}

.data-statistics-filter {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--color-muted);
  font-size: var(--text-sm);
}

.data-statistics-filter select {
  width: auto;
  min-width: 6.5rem;
  min-height: 2.4rem;
  padding: 0.45rem 0.75rem;
}

.data-statistics-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
}

.data-statistics-table-wrap table {
  width: 100%;
  min-width: 72rem;
  border-collapse: collapse;
}

.data-statistics-table-wrap th,
.data-statistics-table-wrap td {
  padding: 0.8rem 0.9rem;
  border-bottom: 1px solid var(--color-line);
  vertical-align: middle;
  white-space: nowrap;
}

.data-statistics-table-wrap thead th {
  color: var(--color-muted);
  font-size: var(--text-xs);
  font-weight: 700;
  background: var(--color-surface-container);
}

.data-statistics-table-wrap thead th.group-start {
  border-left: 2px solid var(--color-line-strong);
}

.data-statistics-table-wrap tbody td.group-start {
  border-left: 2px solid var(--color-line);
}

.data-statistics-group-row th {
  padding-top: 0.5rem;
  padding-bottom: 0.5rem;
  text-align: center;
  letter-spacing: 0.08em;
  background: var(--color-bg-strong);
}

.data-statistics-merged-header {
  background: var(--color-surface-container);
  vertical-align: middle;
}

.data-statistics-cell--date {
  text-align: left;
}

.data-statistics-cell--number {
  text-align: right;
}

.data-statistics-table-wrap tbody tr:last-child td {
  border-bottom: none;
}

.data-statistics-table-wrap tbody tr.is-latest td {
  background: var(--color-primary-soft);
}

.data-statistics-table-wrap tbody tr.is-latest .data-statistics-date {
  color: var(--color-primary);
}

.data-statistics-date {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-weight: 700;
}

.data-statistics-date svg {
  color: var(--color-primary);
  flex: 0 0 auto;
}

.data-statistics-empty {
  padding: 2.4rem 1rem;
  color: var(--color-muted);
  text-align: center;
}

.data-statistics-pagination {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1rem;
}

.data-statistics-pagination button {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.data-statistics-page-info {
  color: var(--color-muted);
  font-size: var(--text-sm);
}

@media (max-width: 760px) {
  .data-statistics-head {
    flex-direction: column;
  }

  .data-statistics-actions {
    width: 100%;
    justify-content: stretch;
  }

  .data-statistics-actions button {
    flex: 1;
    justify-content: center;
  }

  .data-statistics-summaries {
    grid-template-columns: 1fr;
  }

}
</style>
