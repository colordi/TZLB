<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { Download, RefreshCw, Bug, Database, CalendarDays, Layers } from "@lucide/vue";

import { listPestExportTypes, downloadPestTypeExport } from "../api/dataExport.js";
import { isUnauthorizedError } from "../api/http.js";
import { useToast } from "../composables/useToast.js";
import { downloadBlob } from "../utils/download.js";

const PEST_CARD_STYLES = Object.freeze({
  "美国白蛾": { color: "var(--color-danger)" },
  "国槐尺蠖": { color: "var(--color-success)" },
  "春尺蠖": { color: "var(--color-warning)" },
  "其他害虫": { color: "var(--color-muted)" },
});

const TABLE_TYPE_LABELS = Object.freeze({
  table: "数据表",
  view: "视图",
});

const { error, success } = useToast();
const pestTypes = ref([]);
const loading = ref(false);
const downloadingPest = ref("");
const selectedPest = ref("");
const pestFilters = reactive({});

const iconColors = computed(() => {
  const colors = {};
  for (const pt of pestTypes.value) {
    const style = PEST_CARD_STYLES[pt.pest_type];
    colors[pt.pest_type] = style ? style.color : "var(--color-primary)";
  }
  return colors;
});

const currentPest = computed(() => {
  return pestTypes.value.find((pt) => pt.pest_type === selectedPest.value) || pestTypes.value[0] || null;
});

function formatNumber(value) {
  return Number(value || 0).toLocaleString("zh-CN");
}

function tableLabel(objectType) {
  return TABLE_TYPE_LABELS[objectType] || objectType;
}

function initFilters(pest) {
  if (!pestFilters[pest.pest_type]) {
    pestFilters[pest.pest_type] = { year: "", generation: "" };
  }
}

function hasActiveFilter(pestType) {
  const f = pestFilters[pestType];
  return f && (f.year || f.generation);
}

function filterLabel(pestType) {
  const f = pestFilters[pestType];
  if (!f || (!f.year && !f.generation)) return "";
  const parts = [];
  if (f.year) parts.push(`${f.year}年`);
  if (f.generation) parts.push(`第${f.generation}代`);
  return parts.join(" ");
}

async function loadPestTypes() {
  loading.value = true;
  try {
    pestTypes.value = await listPestExportTypes();
    for (const pest of pestTypes.value) {
      initFilters(pest);
    }
    if (
      !selectedPest.value ||
      !pestTypes.value.some((pt) => pt.pest_type === selectedPest.value)
    ) {
      selectedPest.value = pestTypes.value[0]?.pest_type || "";
    }
  } catch (loadError) {
    pestTypes.value = [];
    selectedPest.value = "";
    if (isUnauthorizedError(loadError)) {
      return;
    }
    error(`${loadError.message || loadError}`, "读取虫种信息失败");
  } finally {
    loading.value = false;
  }
}

async function handleDownloadPest(pestType) {
  if (downloadingPest.value) {
    return;
  }

  downloadingPest.value = pestType;
  const filters = pestFilters[pestType] || {};
  try {
    const result = await downloadPestTypeExport(pestType, {
      year: filters.year || undefined,
      generation: filters.generation || undefined,
    });
    await downloadBlob(result.blob, result.filename);
    const label = filterLabel(pestType) || "全部";
    success(`${pestType}（${label}）已开始下载。`, "导出成功");
  } catch (downloadError) {
    if (isUnauthorizedError(downloadError)) {
      return;
    }
    error(`${downloadError.message || downloadError}`, "导出失败");
  } finally {
    downloadingPest.value = "";
  }
}

onMounted(loadPestTypes);
</script>

<template>
  <section class="page-shell data-export-page">
    <header class="page-heading">
      <div>
        <p class="data-export-eyebrow">DATA EXPORT</p>
        <h1>数据导出</h1>
        <p>按虫种导出调查数据和台账数据，选择虫种后可按年份/世代筛选并下载。</p>
      </div>
      <div class="data-export-actions" aria-label="数据导出操作">
        <button
          type="button"
          class="button-secondary"
          :disabled="loading"
          data-testid="data-export-refresh"
          @click="loadPestTypes"
        >
          <RefreshCw :size="18" :stroke-width="2" />
          <span>{{ loading ? "刷新中" : "刷新列表" }}</span>
        </button>
      </div>
    </header>

    <section v-if="!loading && pestTypes.length > 0" class="data-export-tabs" aria-label="虫种选择">
      <button
        v-for="pest in pestTypes"
        :key="pest.pest_type"
        type="button"
        class="data-export-tab"
        :class="{ 'is-active': selectedPest === pest.pest_type }"
        :data-testid="`data-export-pest-${pest.pest_type}`"
        @click="selectedPest = pest.pest_type"
      >
        <Bug :size="16" :stroke-width="2" />
        <span>{{ pest.pest_type }}</span>
      </button>
    </section>

    <div v-if="loading" class="data-export-empty">
      <RefreshCw :size="28" :stroke-width="2" class="empty-icon is-spinning" />
      <p>正在读取虫种信息…</p>
    </div>
    <div v-else-if="pestTypes.length === 0" class="data-export-empty">
      <Database :size="28" :stroke-width="2" class="empty-icon" />
      <p>暂无可导出的虫种数据。</p>
    </div>

    <section
      v-else-if="currentPest"
      class="data-export-panel"
      :style="{ '--pest-accent': iconColors[currentPest.pest_type] }"
      :data-testid="`pest-panel-${currentPest.pest_type}`"
    >
      <div class="data-export-panel-head">
        <div class="panel-head-main">
          <span class="panel-icon" aria-hidden="true">
            <Bug :size="22" :stroke-width="2" />
          </span>
          <div>
            <h2>{{ currentPest.pest_type }}</h2>
            <p>
              <strong>{{ formatNumber(currentPest.total_row_count) }}</strong> 条记录，
              <strong>{{ currentPest.tables.length }}</strong> 张表 / 视图
            </p>
          </div>
        </div>

        <div class="panel-head-tools">
          <div v-if="currentPest.available_years?.length || currentPest.available_generations?.length" class="panel-filters">
            <label v-if="currentPest.available_years?.length" class="panel-filter-item">
              <span class="panel-filter-label">
                <CalendarDays :size="13" :stroke-width="2" />
                年份
              </span>
              <select
                v-model="pestFilters[currentPest.pest_type].year"
                class="panel-filter-select"
                @focus="initFilters(currentPest)"
              >
                <option value="">全部年份</option>
                <option
                  v-for="y in currentPest.available_years"
                  :key="y"
                  :value="y"
                >{{ y }} 年</option>
              </select>
            </label>
            <label v-if="currentPest.available_generations?.length" class="panel-filter-item">
              <span class="panel-filter-label">
                <Layers :size="13" :stroke-width="2" />
                世代
              </span>
              <select
                v-model="pestFilters[currentPest.pest_type].generation"
                class="panel-filter-select"
                @focus="initFilters(currentPest)"
              >
                <option value="">全部世代</option>
                <option
                  v-for="g in currentPest.available_generations"
                  :key="g"
                  :value="g"
                >第{{ g }}代</option>
              </select>
            </label>
          </div>

          <button
            type="button"
            class="panel-download-button"
            :class="{ 'is-filtered': hasActiveFilter(currentPest.pest_type) }"
            :disabled="Boolean(downloadingPest)"
            :data-testid="`pest-download-${currentPest.pest_type}`"
            @click="handleDownloadPest(currentPest.pest_type)"
          >
            <Download :size="18" :stroke-width="2" />
            <span>
              {{ downloadingPest === currentPest.pest_type ? "导出中" : filterLabel(currentPest.pest_type) || "导出全部数据" }}
            </span>
          </button>
        </div>
      </div>

      <div class="data-export-table-wrap">
        <table>
          <thead>
            <tr>
              <th>对象名称</th>
              <th>类型</th>
              <th>记录数</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="table in currentPest.tables"
              :key="`${table.schema_name}.${table.table_name}`"
            >
              <td>
                <span class="table-name">
                  <Layers :size="15" :stroke-width="2" />
                  {{ table.table_name }}
                </span>
              </td>
              <td>
                <span class="table-badge" :class="`is-${table.object_type}`">
                  {{ tableLabel(table.object_type) }}
                </span>
              </td>
              <td class="table-count">{{ formatNumber(table.row_count) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>

<style scoped>
.data-export-page {
  gap: 1.25rem;
}

.data-export-eyebrow {
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 700;
  letter-spacing: 0.1em;
}

.data-export-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.65rem;
}

.data-export-actions button {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}

.data-export-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 3rem 1rem;
  color: var(--color-muted);
  text-align: center;
  background: var(--color-surface-container-lowest);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
}

.empty-icon {
  color: var(--color-line-strong);
}

.empty-icon.is-spinning {
  animation: slow-spin 1.4s linear infinite;
}

@keyframes slow-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.data-export-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.data-export-tab {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  min-height: 2.65rem;
  padding: 0.65rem 0.9rem;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  background: var(--color-surface-container-lowest);
  box-shadow: none;
  font-size: var(--text-sm);
  font-weight: 700;
  cursor: pointer;
  transition:
    background-color var(--motion-fast) ease,
    border-color var(--motion-fast) ease,
    color var(--motion-fast) ease;
}

.data-export-tab:hover {
  border-color: var(--color-line-strong);
  color: var(--color-ink);
}

.data-export-tab.is-active {
  color: var(--color-accent-on);
  border-color: var(--color-primary);
  background: var(--color-primary);
}

.data-export-panel {
  padding: 1.25rem;
  border-radius: var(--radius-md);
  background: var(--color-surface-container-lowest);
  box-shadow: var(--shadow-card);
  border: 1px solid var(--color-border);
  border-top: 3px solid var(--pest-accent, var(--color-primary));
}

.data-export-panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.panel-head-main {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  min-width: 0;
}

.panel-icon {
  width: 2.8rem;
  height: 2.8rem;
  display: grid;
  place-items: center;
  border-radius: var(--radius-md);
  color: var(--pest-accent, var(--color-primary));
  background: color-mix(in srgb, var(--pest-accent, var(--color-primary)) 12%, transparent);
  flex: 0 0 auto;
}

.panel-head-main h2 {
  margin: 0;
  font-size: var(--text-xl);
  line-height: 1.2;
}

.panel-head-main p {
  margin: 0.15rem 0 0;
  color: var(--color-muted);
  font-size: var(--text-sm);
}

.panel-head-main p strong {
  color: var(--color-ink);
}

.panel-head-tools {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  flex-wrap: wrap;
}

.panel-filters {
  display: flex;
  align-items: flex-end;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.panel-filter-item {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 8rem;
}

.panel-filter-label {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: var(--text-xs);
  font-weight: 700;
  color: var(--color-muted);
}

.panel-filter-select {
  width: 100%;
  min-height: 2.5rem;
  padding: 0 0.65rem;
  border: 1px solid var(--color-line-strong);
  border-radius: var(--radius-sm);
  background: var(--color-surface-container-lowest);
  color: var(--color-ink);
  font-size: var(--text-sm);
  font-family: inherit;
  cursor: pointer;
  transition:
    border-color var(--motion-fast) ease,
    box-shadow var(--motion-fast) ease,
    background-color var(--motion-fast) ease;
}

.panel-filter-select:hover {
  border-color: var(--color-primary);
  background: var(--color-surface);
}

.panel-filter-select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: var(--focus-ring);
}

.panel-download-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 2.65rem;
  padding: 0 1.1rem;
  border-radius: var(--radius-sm);
  background: var(--pest-accent, var(--color-primary));
  color: var(--color-accent-on);
  font-size: var(--text-sm);
  font-weight: 700;
  border: none;
  box-shadow: 0 4px 14px color-mix(in srgb, var(--pest-accent, var(--color-primary)) 32%, transparent);
  transition:
    transform var(--motion-fast) var(--ease-standard),
    box-shadow var(--motion-fast) var(--ease-standard),
    background-color var(--motion-fast) var(--ease-standard);
}

.panel-download-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px color-mix(in srgb, var(--pest-accent, var(--color-primary)) 40%, transparent);
  background: color-mix(in srgb, var(--pest-accent, var(--color-primary)) 90%, black);
}

.panel-download-button:active:not(:disabled) {
  transform: translateY(0);
}

.panel-download-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.panel-download-button.is-filtered {
  background: var(--color-surface);
  color: var(--pest-accent, var(--color-primary));
  border: 1.5px solid var(--pest-accent, var(--color-primary));
  box-shadow: none;
}

.panel-download-button.is-filtered:hover:not(:disabled) {
  background: color-mix(in srgb, var(--pest-accent, var(--color-primary)) 8%, transparent);
}

.data-export-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
}

.data-export-table-wrap table {
  width: 100%;
  min-width: 36rem;
  border-collapse: collapse;
}

.data-export-table-wrap th,
.data-export-table-wrap td {
  padding: 0.85rem 0.95rem;
  border-bottom: 1px solid var(--color-line);
  text-align: left;
  vertical-align: middle;
}

.data-export-table-wrap th {
  color: var(--color-muted);
  font-size: var(--text-xs);
  font-weight: 700;
  background: var(--color-surface-container);
  white-space: nowrap;
}

.data-export-table-wrap tbody tr:last-child td {
  border-bottom: none;
}

.data-export-table-wrap tbody tr:hover td {
  background: var(--color-surface-container-low);
}

.table-name {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-weight: 600;
  color: var(--color-ink);
}

.table-name svg {
  flex: 0 0 auto;
  color: var(--color-muted);
}

.table-badge {
  display: inline-flex;
  align-items: center;
  min-height: 1.35rem;
  padding: 0 0.45rem;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: 700;
  border: 1px solid var(--color-line);
  color: var(--color-muted);
  background: var(--color-surface-container);
}

.table-badge.is-view {
  color: var(--color-primary);
  background: var(--color-primary-container);
  border-color: transparent;
}

.table-count {
  color: var(--color-muted);
  font-weight: 600;
  white-space: nowrap;
}

@media (max-width: 760px) {
  .page-heading {
    flex-direction: column;
    align-items: flex-start;
  }

  .data-export-actions {
    width: 100%;
    justify-content: stretch;
  }

  .data-export-actions button {
    flex: 1;
    justify-content: center;
  }

  .data-export-panel-head {
    flex-direction: column;
  }

  .panel-head-tools {
    width: 100%;
  }

  .panel-filters {
    width: 100%;
  }

  .panel-filter-item {
    flex: 1 1 auto;
    min-width: 0;
  }

  .panel-download-button {
    flex: 1 1 auto;
    width: 100%;
  }
}
</style>
