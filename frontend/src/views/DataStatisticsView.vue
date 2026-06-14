<script setup>
import { computed, onMounted, ref } from "vue";
import { ChartColumn, RefreshCw, Table2 } from "@lucide/vue";

import { getWhiteMothDailyStatistics } from "../api/statistics.js";
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
const selectedPest = ref("white-moth");

const latestRow = computed(() => rows.value[0] || null);

const summaryCards = computed(() => [
  {
    label: "最新日期",
    value: latestRow.value?.date || "--",
    footnote: "按每日统计结果取最新一日",
    highlight: true,
  },
  {
    label: "当日除治量",
    value: formatNumber(latestRow.value?.daily_treatment_plants),
    footnote: "单位：株",
  },
  {
    label: "累积完成点数",
    value: formatNumber(latestRow.value?.cumulative_completed_points),
    footnote: "截至最新日期",
  },
  {
    label: "当日派单数",
    value: formatNumber(latestRow.value?.daily_dispatch_points),
    footnote: "受害株数大于 0 的点位",
  },
]);

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

async function loadWhiteMothDailyStatistics() {
  loading.value = true;
  try {
    const result = await getWhiteMothDailyStatistics();
    columns.value = Array.isArray(result.columns) ? result.columns : [];
    rows.value = Array.isArray(result.rows) ? result.rows : [];
  } catch (loadError) {
    columns.value = [];
    rows.value = [];
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

    <section class="summary-grid" aria-label="美国白蛾每日统计摘要">
      <article
        v-for="card in summaryCards"
        :key="card.label"
        class="summary-card"
        :class="{ 'is-highlight': card.highlight }"
      >
        <span class="summary-label">{{ card.label }}</span>
        <strong class="summary-value">{{ card.value }}</strong>
        <span class="summary-footnote">{{ card.footnote }}</span>
      </article>
    </section>

    <section class="data-statistics-panel">
      <div class="data-statistics-panel-head">
        <div>
          <h2>美国白蛾每日信息统计</h2>
          <p>{{ rows.length }} 条每日记录</p>
        </div>
      </div>

      <div v-if="loading" class="data-statistics-empty">正在读取每日统计…</div>
      <div v-else-if="rows.length === 0" class="data-statistics-empty">
        暂无美国白蛾每日统计数据。
      </div>

      <div v-else class="data-statistics-table-wrap">
        <table>
          <thead>
            <tr>
              <th v-for="column in columns" :key="column.key">
                {{ column.label }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in rows"
              :key="row.date"
              :data-testid="`data-statistics-row-${row.date}`"
            >
              <td v-for="column in columns" :key="column.key">
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
}

.data-statistics-panel-head h2 {
  margin: 0;
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
  text-align: left;
  vertical-align: middle;
  white-space: nowrap;
}

.data-statistics-table-wrap th {
  color: var(--color-muted);
  font-size: var(--text-xs);
  font-weight: 700;
  background: var(--color-surface-container);
}

.data-statistics-table-wrap tbody tr:last-child td {
  border-bottom: none;
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
}
</style>
