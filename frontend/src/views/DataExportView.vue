<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { Download, RefreshCw, Bug, Database, Layers } from "@lucide/vue";

import { listPestExportTypes, getPestExportMeta, downloadPestTypeExport } from "../api/dataExport.js";
import { isUnauthorizedError } from "../api/http.js";
import { useToast } from "../composables/useToast.js";
import { downloadBlob } from "../utils/download.js";

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
const currentPestMeta = ref(null);

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

async function loadCurrentPestMeta() {
  if (!currentPest.value) {
    currentPestMeta.value = null;
    return;
  }
  const pest = currentPest.value;
  const filters = pestFilters[pest.pest_type] || {};
  try {
    currentPestMeta.value = await getPestExportMeta(pest.pest_type, {
      year: filters.year || undefined,
      generation: filters.generation || undefined,
    });
  } catch (metaError) {
    if (isUnauthorizedError(metaError)) {
      return;
    }
    error(`${metaError.message || metaError}`, "读取筛选后记录数失败");
  }
}

function selectPest(pest) {
  selectedPest.value = pest.pest_type;
  initFilters(pest);
  const filters = pestFilters[pest.pest_type];
  if (filters.year && !pest.available_years?.includes(filters.year)) {
    filters.year = "";
  }
  if (filters.generation && !pest.available_generations?.includes(filters.generation)) {
    filters.generation = "";
  }
  loadCurrentPestMeta();
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
  if (f.generation) parts.push(f.generation);
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
    currentPestMeta.value = currentPest.value;
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
    <header class="data-export-head">
      <div>
        <p class="data-export-eyebrow">DATA EXPORT</p>
        <h1>数据导出</h1>
        <p>按虫种导出调查数据和台账数据，选择虫种后可按年份/世代筛选并下载。</p>
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
        @click="selectPest(pest)"
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
      v-else-if="currentPestMeta"
      class="data-export-panel"
      :data-testid="`pest-panel-${currentPestMeta.pest_type}`"
    >
      <div class="data-export-panel-head">
        <div>
          <h2>{{ currentPestMeta.pest_type }}</h2>
          <p>
            <strong>{{ formatNumber(currentPestMeta.total_row_count) }}</strong> 条记录，
            <strong>{{ currentPestMeta.tables.length }}</strong> 张表 / 视图
          </p>
        </div>

        <div class="data-export-filters" aria-label="导出筛选条件">
          <label v-if="currentPestMeta.available_years?.length" class="data-export-filter">
            <span>年份</span>
            <select
              v-model="pestFilters[currentPestMeta.pest_type].year"
              @focus="initFilters(currentPestMeta)"
              @change="loadCurrentPestMeta"
            >
              <option value="">全部年份</option>
              <option
                v-for="y in currentPestMeta.available_years"
                :key="y"
                :value="y"
              >{{ y }}</option>
            </select>
          </label>
          <label v-if="currentPestMeta.available_generations?.length" class="data-export-filter">
            <span>世代</span>
            <select
              v-model="pestFilters[currentPestMeta.pest_type].generation"
              @focus="initFilters(currentPestMeta)"
              @change="loadCurrentPestMeta"
            >
              <option value="">全部世代</option>
              <option
                v-for="g in currentPestMeta.available_generations"
                :key="g"
                :value="g"
              >{{ g }}</option>
            </select>
          </label>

          <button
            type="button"
            class="data-export-download"
            :disabled="Boolean(downloadingPest)"
            :data-testid="`pest-download-${currentPestMeta.pest_type}`"
            @click="handleDownloadPest(currentPestMeta.pest_type)"
          >
            <Download :size="18" :stroke-width="2" />
            <span>
              {{ downloadingPest === currentPestMeta.pest_type ? "导出中" : filterLabel(currentPestMeta.pest_type) || "导出全部数据" }}
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
              v-for="table in currentPestMeta.tables"
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

.data-export-head p:last-child,
.data-export-panel-head p {
  color: var(--color-muted);
}

.data-export-eyebrow {
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 700;
  letter-spacing: 0.1em;
}

.data-export-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.data-export-tab {
  min-height: 2.65rem;
  padding: 0.65rem 0.9rem;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  background: var(--color-surface-container-lowest);
  box-shadow: none;
  font-size: var(--text-sm);
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}

.data-export-tab.is-active {
  color: var(--color-accent-on);
  border-color: var(--color-primary);
  background: var(--color-primary);
}

.data-export-tab:disabled {
  color: var(--color-muted-soft);
  background: var(--color-surface-container);
}

.data-export-empty {
  padding: 2.4rem 1rem;
  color: var(--color-muted);
  text-align: center;
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

.data-export-panel {
  padding: 1.15rem;
  border-radius: var(--radius-md);
  background: var(--color-surface-container-lowest);
  box-shadow: var(--shadow-card);
}

.data-export-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.9rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.data-export-panel-head h2 {
  margin: 0;
}

.data-export-filters {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.data-export-filter {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--color-muted);
  font-size: var(--text-sm);
}

.data-export-filter select {
  width: auto;
  min-width: 6.5rem;
  min-height: 2.4rem;
  padding: 0.45rem 0.75rem;
}

.data-export-download {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  min-height: 2.65rem;
  padding: 0 1rem;
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: var(--color-accent-on);
  font-size: var(--text-sm);
  font-weight: 700;
  border: none;
  white-space: nowrap;
}

.data-export-download:disabled {
  opacity: 0.55;
  cursor: not-allowed;
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
  padding: 0.8rem 0.9rem;
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
  text-align: right;
  color: var(--color-muted);
  font-weight: 600;
  white-space: nowrap;
}

@media (max-width: 760px) {
  .data-export-head {
    flex-direction: column;
  }

  .data-export-filters {
    width: 100%;
  }

  .data-export-filter {
    flex: 1 1 auto;
    min-width: 0;
  }

  .data-export-filter select {
    width: 100%;
  }

  .data-export-download {
    flex: 1 1 auto;
    justify-content: center;
  }
}
</style>