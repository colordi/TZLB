<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { Download, RefreshCw, Bug } from "@lucide/vue";

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
  table: "表",
  view: "视图",
});

const { error, success } = useToast();
const pestTypes = ref([]);
const loading = ref(false);
const downloadingPest = ref("");
const pestFilters = reactive({});

const iconColors = computed(() => {
  const colors = {};
  for (const pt of pestTypes.value) {
    const style = PEST_CARD_STYLES[pt.pest_type];
    colors[pt.pest_type] = style ? style.color : "var(--color-primary)";
  }
  return colors;
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
  } catch (loadError) {
    pestTypes.value = [];
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
    <header class="data-export-head">
      <div>
        <p class="data-export-eyebrow">DATA EXPORT</p>
        <h1>数据导出</h1>
        <p>按虫种导出调查数据和台账数据，可按年份/世代筛选。</p>
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

    <div v-if="loading" class="data-export-empty">正在读取虫种信息…</div>
    <div v-else-if="pestTypes.length === 0" class="data-export-empty">暂无可导出的虫种数据。</div>

    <div v-else class="data-export-pest-grid">
      <article
        v-for="pest in pestTypes"
        :key="pest.pest_type"
        class="data-export-pest-card"
        :style="{ '--pest-accent': iconColors[pest.pest_type] }"
        :data-testid="`pest-card-${pest.pest_type}`"
      >
        <div class="pest-card-head">
          <span class="pest-card-icon" aria-hidden="true">
            <Bug :size="22" :stroke-width="2" />
          </span>
          <div>
            <h2 class="pest-card-title">{{ pest.pest_type }}</h2>
            <p class="pest-card-subtitle">
              <strong>{{ formatNumber(pest.total_row_count) }}</strong> 条记录，<strong>{{ pest.tables.length }}</strong> 张表
            </p>
          </div>
        </div>

        <ul class="pest-card-tables">
          <li v-for="table in pest.tables" :key="`${table.schema_name}.${table.table_name}`">
            <span class="pest-table-badge" :class="`is-${table.object_type}`">
              {{ tableLabel(table.object_type) }}
            </span>
            <span class="pest-table-name">{{ table.table_name }}</span>
            <span class="pest-table-count">{{ formatNumber(table.row_count) }} 条</span>
          </li>
        </ul>

        <div v-if="pest.available_years?.length || pest.available_generations?.length" class="pest-card-filters">
          <label v-if="pest.available_years?.length" class="pest-filter-item">
            <span class="pest-filter-label">年份</span>
            <select
              v-model="pestFilters[pest.pest_type].year"
              class="pest-filter-select"
              @focus="initFilters(pest)"
            >
              <option value="">全部年份</option>
              <option
                v-for="y in pest.available_years"
                :key="y"
                :value="y"
              >{{ y }} 年</option>
            </select>
          </label>
          <label v-if="pest.available_generations?.length" class="pest-filter-item">
            <span class="pest-filter-label">世代</span>
            <select
              v-model="pestFilters[pest.pest_type].generation"
              class="pest-filter-select"
              @focus="initFilters(pest)"
            >
              <option value="">全部世代</option>
              <option
                v-for="g in pest.available_generations"
                :key="g"
                :value="g"
              >第{{ g }}代</option>
            </select>
          </label>
        </div>

        <div class="pest-card-action">
          <button
            type="button"
            class="pest-card-download-button"
            :class="{ 'is-filtered': hasActiveFilter(pest.pest_type) }"
            :disabled="Boolean(downloadingPest)"
            :data-testid="`pest-download-${pest.pest_type}`"
            @click="handleDownloadPest(pest.pest_type)"
          >
            <Download :size="18" :stroke-width="2" />
            <span>
              {{ downloadingPest === pest.pest_type ? "导出中" : filterLabel(pest.pest_type) || "导出全部数据" }}
            </span>
          </button>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.data-export-page {
  gap: 1.1rem;
}

.data-export-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.data-export-head h1 {
  margin-top: 0.2rem;
  font-size: clamp(1.7rem, 2.3vw, 2.35rem);
  line-height: 1.08;
}

.data-export-head p:last-child {
  color: var(--color-muted);
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
  padding: 2.4rem 1rem;
  color: var(--color-muted);
  text-align: center;
}

.data-export-pest-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(24rem, 1fr));
  gap: 1rem;
}

.data-export-pest-card {
  display: flex;
  flex-direction: column;
  padding: 1.25rem;
  border-radius: var(--radius-md);
  background: var(--color-surface-container-lowest);
  box-shadow: var(--shadow-card);
  border-top: 3px solid var(--pest-accent, var(--color-primary));
  gap: 0.85rem;
}

.pest-card-head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.pest-card-icon {
  width: 2.6rem;
  height: 2.6rem;
  display: grid;
  place-items: center;
  border-radius: var(--radius-sm);
  color: var(--pest-accent, var(--color-primary));
  background: color-mix(in srgb, var(--pest-accent, var(--color-primary)) 12%, transparent);
  flex: 0 0 auto;
}

.pest-card-title {
  margin: 0;
  font-size: var(--text-lg);
  line-height: 1.2;
}

.pest-card-subtitle {
  margin: 0.1rem 0 0;
  color: var(--color-muted);
  font-size: var(--text-sm);
}

.pest-card-subtitle strong {
  color: var(--color-on-surface);
}

.pest-card-tables {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.pest-card-tables li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: var(--text-sm);
  padding: 0.3rem 0;
  border-bottom: 1px solid var(--color-line);
}

.pest-card-tables li:last-child {
  border-bottom: none;
}

.pest-table-badge {
  display: inline-flex;
  align-items: center;
  min-height: 1.35rem;
  padding: 0 0.4rem;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: 700;
  flex: 0 0 auto;
  border: 1px solid var(--color-line);
  color: var(--color-muted);
  background: var(--color-surface-container);
}

.pest-table-badge.is-view {
  color: var(--color-primary);
  background: var(--color-primary-container);
  border-color: transparent;
}

.pest-table-name {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}

.pest-table-count {
  flex: 0 0 auto;
  color: var(--color-muted);
  white-space: nowrap;
}

.pest-card-filters {
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.pest-filter-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex: 1 1 auto;
  min-width: 0;
}

.pest-filter-label {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-muted);
  flex: 0 0 auto;
}

.pest-filter-select {
  flex: 1 1 auto;
  min-width: 0;
  padding: 0.3rem 0.5rem;
  border: 1px solid var(--color-line-strong);
  border-radius: var(--radius-sm);
  background: var(--color-surface-container);
  color: var(--color-ink);
  font-size: var(--text-sm);
  font-family: inherit;
  cursor: pointer;
}

.pest-filter-select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-mist);
}

.pest-card-action {
  margin-top: auto;
}

.pest-card-download-button {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  width: 100%;
  justify-content: center;
}

.pest-card-download-button.is-filtered {
  border-color: var(--pest-accent, var(--color-primary));
  color: var(--pest-accent, var(--color-primary));
}

@media (max-width: 760px) {
  .data-export-head {
    flex-direction: column;
  }

  .data-export-actions {
    width: 100%;
    justify-content: stretch;
  }

  .data-export-actions button {
    flex: 1;
    justify-content: center;
  }

  .data-export-pest-grid {
    grid-template-columns: 1fr;
  }
}
</style>
