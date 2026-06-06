<script setup>
import { computed, onMounted, ref } from "vue";
import { Database, Download, RefreshCw, Table2 } from "@lucide/vue";

import {
  downloadAllDataExportTables,
  downloadDataExportTable,
  listDataExportTables,
} from "../api/dataExport.js";
import { isUnauthorizedError } from "../api/http.js";
import { useToast } from "../composables/useToast.js";
import { downloadBlob } from "../utils/download.js";

const SCHEMA_LABELS = Object.freeze({
  survey: "survey 调查数据",
  ledger: "ledger 台账数据",
});

const { error, success } = useToast();
const tables = ref([]);
const loading = ref(false);
const downloadingAll = ref(false);
const downloadingTableKey = ref("");

const groupedTables = computed(() =>
  ["survey", "ledger"]
    .map((schemaName) => ({
      schemaName,
      label: SCHEMA_LABELS[schemaName] || schemaName,
      tables: tables.value.filter((table) => table.schema_name === schemaName),
    }))
    .filter((group) => group.tables.length > 0),
);

const totalTableCount = computed(() => tables.value.length);
const totalRowCount = computed(() =>
  tables.value.reduce((total, table) => total + Number(table.row_count || 0), 0),
);
const viewCount = computed(
  () => tables.value.filter((table) => table.object_type === "view").length,
);

function formatNumber(value) {
  return Number(value || 0).toLocaleString("zh-CN");
}

function formatObjectType(type) {
  return type === "view" ? "视图" : "表";
}

function buildTableKey(table) {
  return `${table.schema_name}.${table.table_name}`;
}

async function loadTables() {
  loading.value = true;
  try {
    tables.value = await listDataExportTables();
  } catch (loadError) {
    tables.value = [];
    if (isUnauthorizedError(loadError)) {
      return;
    }
    error(`${loadError.message || loadError}`, "读取表和视图失败");
  } finally {
    loading.value = false;
  }
}

async function deliverDownload(result, label) {
  await downloadBlob(result.blob, result.filename);
  success(`${label}已开始下载。`, "导出成功");
}

async function handleDownloadAll() {
  if (downloadingAll.value || totalTableCount.value === 0) {
    return;
  }

  downloadingAll.value = true;
  try {
    await deliverDownload(await downloadAllDataExportTables(), "全部表和视图");
  } catch (downloadError) {
    if (isUnauthorizedError(downloadError)) {
      return;
    }
    error(`${downloadError.message || downloadError}`, "导出失败");
  } finally {
    downloadingAll.value = false;
  }
}

async function handleDownloadTable(table) {
  const tableKey = buildTableKey(table);
  if (downloadingTableKey.value) {
    return;
  }

  downloadingTableKey.value = tableKey;
  try {
    await deliverDownload(
      await downloadDataExportTable({
        schemaName: table.schema_name,
        tableName: table.table_name,
      }),
      tableKey,
    );
  } catch (downloadError) {
    if (isUnauthorizedError(downloadError)) {
      return;
    }
    error(`${downloadError.message || downloadError}`, "导出失败");
  } finally {
    downloadingTableKey.value = "";
  }
}

onMounted(loadTables);
</script>

<template>
  <section class="page-shell data-export-page">
    <header class="data-export-head">
      <div>
        <p class="data-export-eyebrow">DATA EXPORT</p>
        <h1>数据导出</h1>
        <p>导出当前数据库中 survey 和 ledger 下的最新表和视图。</p>
      </div>
      <div class="data-export-actions" aria-label="数据导出操作">
        <button
          type="button"
          class="button-secondary"
          :disabled="loading || downloadingAll"
          data-testid="data-export-refresh"
          @click="loadTables"
        >
          <RefreshCw :size="18" :stroke-width="2" />
          <span>{{ loading ? "刷新中" : "刷新列表" }}</span>
        </button>
        <button
          type="button"
          :disabled="loading || downloadingAll || totalTableCount === 0"
          data-testid="data-export-download-all"
          @click="handleDownloadAll"
        >
          <Download :size="18" :stroke-width="2" />
          <span>{{ downloadingAll ? "导出中" : "导出全部" }}</span>
        </button>
      </div>
    </header>

    <section class="summary-grid" aria-label="导出数据概览">
      <article class="summary-card is-highlight">
        <span class="summary-label">可导出对象</span>
        <strong class="summary-value">{{ formatNumber(totalTableCount) }}</strong>
        <span class="summary-footnote">survey / ledger 表和视图</span>
      </article>
      <article class="summary-card">
        <span class="summary-label">总记录数</span>
        <strong class="summary-value">{{ formatNumber(totalRowCount) }}</strong>
        <span class="summary-footnote">按当前数据库实时统计</span>
      </article>
      <article class="summary-card">
        <span class="summary-label">视图数</span>
        <strong class="summary-value">{{ formatNumber(viewCount) }}</strong>
        <span class="summary-footnote">已纳入全量导出</span>
      </article>
      <article class="summary-card">
        <span class="summary-label">导出格式</span>
        <strong class="summary-value">XLSX</strong>
        <span class="summary-footnote">全量导出包含导出说明 sheet</span>
      </article>
    </section>

    <section class="data-export-panel">
      <div class="data-export-panel-head">
        <div>
          <h2>表和视图</h2>
          <p>仅显示允许导出的 survey 和 ledger 表及视图。</p>
        </div>
      </div>

      <div v-if="loading" class="data-export-empty">正在读取表和视图列表…</div>
      <div v-else-if="tables.length === 0" class="data-export-empty">暂无可导出的表或视图。</div>

      <div v-else class="data-export-groups">
        <section
          v-for="group in groupedTables"
          :key="group.schemaName"
          class="data-export-group"
        >
          <header class="data-export-group-head">
            <span class="data-export-group-icon" aria-hidden="true">
              <Database :size="18" :stroke-width="2" />
            </span>
            <div>
              <h3>{{ group.label }}</h3>
              <p>{{ formatNumber(group.tables.length) }} 个对象</p>
            </div>
          </header>

          <div class="data-export-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>名称</th>
                  <th>类型</th>
                  <th>字段数</th>
                  <th>记录数</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="table in group.tables"
                  :key="buildTableKey(table)"
                  :data-testid="`data-export-row-${buildTableKey(table)}`"
                >
                  <td>
                    <span class="data-export-table-name">
                      <Table2 :size="16" :stroke-width="2" />
                      <span>{{ table.table_name }}</span>
                    </span>
                  </td>
                  <td>
                    <span
                      class="data-export-type-badge"
                      :class="{ 'is-view': table.object_type === 'view' }"
                    >
                      {{ formatObjectType(table.object_type) }}
                    </span>
                  </td>
                  <td>{{ formatNumber(table.column_count) }}</td>
                  <td>{{ formatNumber(table.row_count) }}</td>
                  <td>
                    <button
                      type="button"
                      class="button-secondary data-export-table-button"
                      :disabled="Boolean(downloadingTableKey)"
                      :data-testid="`data-export-download-${buildTableKey(table)}`"
                      @click="handleDownloadTable(table)"
                    >
                      <Download :size="16" :stroke-width="2" />
                      <span>
                        {{ downloadingTableKey === buildTableKey(table) ? "导出中" : "导出" }}
                      </span>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
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
.data-export-panel-head p,
.data-export-group-head p {
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

.data-export-actions button,
.data-export-table-button {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}

.data-export-panel {
  padding: 1.15rem;
  border-radius: var(--radius-md);
  background: var(--color-surface-container-lowest);
  box-shadow: var(--shadow-card);
}

.data-export-panel-head,
.data-export-group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.9rem;
}

.data-export-panel-head {
  margin-bottom: 1rem;
}

.data-export-panel-head h2,
.data-export-group-head h3 {
  margin: 0;
}

.data-export-groups {
  display: grid;
  gap: 1rem;
}

.data-export-group {
  display: grid;
  gap: 0.75rem;
}

.data-export-group-head {
  justify-content: flex-start;
}

.data-export-group-icon {
  width: 2.25rem;
  height: 2.25rem;
  display: grid;
  place-items: center;
  border-radius: var(--radius-sm);
  color: var(--color-primary);
  background: var(--color-primary-container);
}

.data-export-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
}

.data-export-table-wrap table {
  width: 100%;
  min-width: 38rem;
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
}

.data-export-table-wrap tbody tr:last-child td {
  border-bottom: none;
}

.data-export-table-name {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-weight: 700;
}

.data-export-table-name svg {
  color: var(--color-primary);
  flex: 0 0 auto;
}

.data-export-type-badge {
  display: inline-flex;
  align-items: center;
  min-height: 1.65rem;
  padding: 0 0.55rem;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-sm);
  color: var(--color-muted);
  background: var(--color-surface-container);
  font-size: var(--text-xs);
  font-weight: 700;
}

.data-export-type-badge.is-view {
  color: var(--color-primary);
  background: var(--color-primary-container);
}

.data-export-empty {
  padding: 2.4rem 1rem;
  color: var(--color-muted);
  text-align: center;
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
}
</style>
