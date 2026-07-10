<script setup>
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { Archive, FileSpreadsheet, FolderUp, ShieldCheck } from "@lucide/vue";

import { useWorkorderTaskConfig } from "../composables/workorder/useWorkorderTaskConfig.js";
import { useWorkorderRecords } from "../composables/workorder/useWorkorderRecords.js";
import { useRecordSelection } from "../composables/workorder/useRecordSelection.js";
import { useWorkorderExport } from "../composables/workorder/useWorkorderExport.js";
import { useDateFolderUpload } from "../composables/workorder/useDateFolderUpload.js";
import { useRecordDetailModal } from "../composables/workorder/useRecordDetailModal.js";
import { MOCK_WORKORDER_RECORDS } from "../fixtures/design/workorderMock.js";
import { isUnauthorizedError } from "../api/http.js";
import { useToast } from "../composables/useToast.js";
import ExcelImportDialog from "../components/workorder/ExcelImportDialog.vue";
import RecordTable from "../components/workorder/RecordTable.vue";
import RecordDetailModal from "../components/workorder/RecordDetailModal.vue";
import SurveyImportDialog from "../components/workorder/SurveyImportDialog.vue";
import ConfirmDialog from "../components/workorder/ConfirmDialog.vue";
import {
  getDefaultTask,
  normalizeRecordForPest,
} from "../components/workorder/fieldConfig.js";

const toast = useToast();
const route = useRoute();
const isPreview = computed(() => route.meta?.previewMode === true);

const taskConfig = useWorkorderTaskConfig();
const {
  PEST_OPTIONS, pestType, year, taskType, taskName,
  generation, taskOptions, yearOptions, canImportSurvey,
} = taskConfig;

const recCtrl = useWorkorderRecords(pestType);
const {
  records, validationErrors,
  normalizeAll, handleSurveyImport: importRecords,
  handleUpdateRecord: updateRecord,
  handleDeleteRecord: deleteRecord,
  handleBatchDelete: batchDelete,
} = recCtrl;

if (isPreview.value) {
  pestType.value = "美国白蛾";
  records.value = MOCK_WORKORDER_RECORDS.map((r) => ({ ...r }));
}

const selection = useRecordSelection(records, validationErrors);
const {
  selectedUids, searchQuery, recordFilter,
  filteredRecords, filteredRecordUids, filteredValidationErrors,
  allVisibleSelected, toggleFilteredSelection, clearSelection,
} = selection;

const exportCtrl = useWorkorderExport(
  taskConfig, records, isPreview,
);
const { generating, exportProgress, generateButtonLabel } = exportCtrl;

const dateFolder = useDateFolderUpload();
const { dateFolderInput, dateFolderUploading } = dateFolder;

const surveyImportOpen = ref(false);
const excelImportOpen = ref(false);
const pendingDelete = ref(null);
const showConfirmDialog = ref(false);

const detailModal = useRecordDetailModal(records, validationErrors, pestType);
const {
  activeRecordUid, showDetailModal, activeRecord, activeRecordError,
  openDetail, closeDetail,
} = detailModal;

const confirmDialogTitle = computed(() =>
  pendingDelete.value?.scope === "batch"
    ? "删除选中记录"
    : "删除该条记录",
);
const confirmDialogMessage = computed(() => {
  const count = pendingDelete.value?.uids.length || 0;
  if (pendingDelete.value?.scope === "batch") {
    return `确认删除选中的 ${count} 条记录吗？此操作不可撤销。`;
  }
  return "确认删除当前记录吗？此操作不可撤销。";
});

function resetWorkspace() {
  taskConfig.resetTaskName();
  surveyImportOpen.value = false;
  excelImportOpen.value = false;
  selectedUids.value = [];
  normalizeAll();
}

watch(pestType, resetWorkspace);

function openSurveyImportDialog() {
  if (!canImportSurvey.value || generating.value) {
    return;
  }
  surveyImportOpen.value = true;
}

function openExcelImportDialog() {
  if (generating.value) {
    return;
  }
  excelImportOpen.value = true;
}

function closeExcelImportDialog() {
  excelImportOpen.value = false;
}

function closeSurveyImportDialog() {
  surveyImportOpen.value = false;
}

function onDateFolderChange(event) {
  dateFolder.handleDateFolderChange(event, toast);
}

function onOpenDateFolderPicker() {
  dateFolder.openDateFolderPicker(generating.value);
}

function onSurveyImport(importedRecords) {
  if (!Array.isArray(importedRecords) || importedRecords.length === 0) {
    toast.info("请至少选择一条调查记录。", "没有可导入项");
    return;
  }
  const count = importRecords(importedRecords).length;
  surveyImportOpen.value = false;
  toast.success(`已导入 ${count} 条调查记录。`, "导入完成");
}

function handleRowClick(uid) {
  openDetail(uid);
}

function handleCloseDetailModal() {
  closeDetail();
}

function handleUpdateRecord(updatedRecord) {
  if (activeRecordUid.value) {
    updateRecord(activeRecordUid.value, updatedRecord);
    selectedUids.value = [];
    handleCloseDetailModal();
  }
}

function handleDeleteRecord() {
  if (!activeRecordUid.value) {
    return;
  }
  pendingDelete.value = {
    scope: "single",
    uids: [activeRecordUid.value],
  };
  showConfirmDialog.value = true;
}

function onBatchDelete() {
  if (!selectedUids.value.length) {
    return;
  }
  pendingDelete.value = {
    scope: "batch",
    uids: [...selectedUids.value],
  };
  showConfirmDialog.value = true;
}

function closeConfirmDialog() {
  showConfirmDialog.value = false;
  pendingDelete.value = null;
}

function confirmDelete() {
  if (!pendingDelete.value) {
    return;
  }
  batchDelete(pendingDelete.value.uids);
  selectedUids.value = selectedUids.value.filter(
    (uid) => !pendingDelete.value.uids.includes(uid),
  );
  const wasSingle = pendingDelete.value.scope === "single";
  closeConfirmDialog();
  if (wasSingle) {
    handleCloseDetailModal();
  }
}

function onGenerate() {
  exportCtrl.handleGenerate(toast);
}
</script>

<template>
  <section class="page-shell workorder-page">
    <div v-if="isPreview" class="workorder-preview-banner" data-testid="workorder-preview-banner">
      <strong>设计预览模式</strong>
      <span>当前展示的是静态 mock 数据，导入和上传功能已禁用。</span>
    </div>
    <header class="workorder-page-head">
      <div>
        <p class="workorder-eyebrow">WORK ORDER CONTROL DESK</p>
        <h1>调查工单</h1>
        <p>从数据库导入调查记录，逐条生成工单并导出标准化 Word 文档。</p>
      </div>
      <div class="workorder-page-actions" aria-label="工单操作">
        <button
          type="button"
          class="button-secondary"
          :disabled="generating || records.length === 0"
          data-testid="workorder-export-button"
          @click="onGenerate"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
            <path d="M7 3h7l5 5v13H7zM14 3v5h5M10 13h6m-6 4h6" />
          </svg>
          <span>{{ generateButtonLabel }}</span>
        </button>
        <button
          v-if="canImportSurvey"
          type="button"
          :disabled="generating || isPreview"
          data-testid="survey-import-button"
          @click="openSurveyImportDialog"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
            <path d="M12 16V4m-4 4 4-4 4 4M5 14v5h14v-5" />
          </svg>
          <span>从数据库追加工单记录</span>
        </button>
      </div>
    </header>

    <section class="workorder-controls" aria-label="任务配置">
      <label class="workorder-field" for="pest-type">
        <span>害虫类型</span>
        <select id="pest-type" v-model="pestType" :disabled="generating">
          <option v-for="option in PEST_OPTIONS" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>

      <label class="workorder-field" for="workorder-year">
        <span>年份</span>
        <select id="workorder-year" v-model="year" :disabled="generating">
          <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}</option>
        </select>
      </label>

      <label class="workorder-field is-task" for="task-name">
        <span>统防统治任务</span>
        <select id="task-name" v-model="taskName" :disabled="generating || !taskOptions.length">
          <option v-if="!taskOptions.length" value="">暂无预设任务</option>
          <option v-for="option in taskOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>
    </section>

    <section class="workorder-action-grid" aria-label="调查数据操作">
      <button
        type="button"
        class="workorder-action-card is-primary"
        :disabled="generating || isPreview"
        data-testid="survey-excel-import-button"
        @click="openExcelImportDialog"
      >
        <span class="workorder-action-icon"><FileSpreadsheet :size="21" /></span>
        <span class="workorder-action-copy">
          <strong>上传调查 Excel</strong>
          <small>预览校验后写入 survey / ledger 表</small>
        </span>
      </button>
      <button
        type="button"
        class="workorder-action-card"
        :disabled="generating || dateFolderUploading || isPreview"
        data-testid="date-image-folder-button"
        @click="onOpenDateFolderPicker"
      >
        <span class="workorder-action-icon"><FolderUp :size="21" /></span>
        <span class="workorder-action-copy">
          <strong>上传日期图片文件夹</strong>
          <small>{{ dateFolderUploading ? "正在上传…" : "文件夹名 YYYY-MM-DD" }}</small>
        </span>
      </button>
      <input
        ref="dateFolderInput"
        class="workorder-folder-input"
        type="file"
        multiple
        webkitdirectory
        directory
        data-testid="date-image-folder-input"
        @change="onDateFolderChange"
      />
      <router-link
        v-if="!isPreview"
        to="/workorder/point-screenshots"
        class="workorder-action-card"
        data-testid="point-screenshot-entry"
      >
        <span class="workorder-action-icon"><Archive :size="21" /></span>
        <span class="workorder-action-copy">
          <strong>点位截图管理</strong>
          <small>上传、替换、删除点位截图</small>
        </span>
      </router-link>
      <button v-else type="button" class="workorder-action-card" disabled>
        <span class="workorder-action-icon"><Archive :size="21" /></span>
        <span class="workorder-action-copy">
          <strong>点位截图管理</strong>
          <small>预览模式禁用</small>
        </span>
      </button>
      <button type="button" class="workorder-action-card" disabled>
        <span class="workorder-action-icon"><ShieldCheck :size="21" /></span>
        <span class="workorder-action-copy">
          <strong>占位功能三</strong>
          <small>暂未启用</small>
        </span>
      </button>
    </section>

    <section class="workorder-panel" aria-label="调查工单记录">
      <div class="workorder-toolbar">
        <label class="workorder-search">
          <span class="workorder-sr-only">搜索工单记录</span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="7" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <input
            v-model="searchQuery"
            type="search"
            placeholder="搜索点位名称、编号、乡镇…"
            data-testid="workorder-search"
          />
        </label>

        <div class="workorder-segmented" aria-label="记录筛选">
          <button
            type="button"
            :class="{ 'is-active': recordFilter === 'all' }"
            data-testid="workorder-filter-all"
            @click="recordFilter = 'all'"
          >
            全部
          </button>
          <button
            type="button"
            :class="{ 'is-active': recordFilter === 'errors' }"
            data-testid="workorder-filter-errors"
            @click="recordFilter = 'errors'"
          >
            有错误
          </button>
          <button
            type="button"
            :class="{ 'is-active': recordFilter === 'selected' }"
            data-testid="workorder-filter-selected"
            @click="recordFilter = 'selected'"
          >
            已选
          </button>
        </div>

        <span class="workorder-toolbar-separator" aria-hidden="true"></span>

        <button class="workorder-select-all" type="button" @click="toggleFilteredSelection">
          {{ allVisibleSelected ? "取消全选" : "全选" }}
        </button>
      </div>

      <RecordTable
        class="workorder-record-table"
        v-model:selectedUids="selectedUids"
        :records="filteredRecords"
        :pest-type="pestType"
        :busy="generating"
        :errors="filteredValidationErrors"
        @row-click="handleRowClick"
      />

      <div v-if="records.length > 0 && filteredRecords.length === 0" class="workorder-empty">
        当前筛选条件下没有工单记录。
      </div>

      <footer class="workorder-panel-foot">
        <span>共 <strong>{{ filteredRecords.length }}</strong> 条记录</span>
        <span>已选 <strong>{{ selectedUids.length }}</strong> 条</span>
      </footer>
    </section>

    <aside v-if="selectedUids.length" class="workorder-batch-bar" aria-label="已选工单摘要">
      <span>已选 <strong>{{ selectedUids.length }}</strong> 条记录</span>
      <div>
        <button type="button" :disabled="generating" @click="clearSelection">取消选择</button>
        <button type="button" :disabled="generating" @click="onBatchDelete">
          删除选中
        </button>
        <button
          type="button"
          :disabled="generating || records.length === 0"
          @click="onGenerate"
        >
          {{ generating ? generateButtonLabel : "逐条导出工作单" }}
        </button>
      </div>
    </aside>

    <RecordDetailModal
      :open="showDetailModal"
      :record="activeRecord"
      :pest-type="pestType"
      :busy="generating"
      :error="activeRecordError"
      @close="handleCloseDetailModal"
      @update="handleUpdateRecord"
      @delete="handleDeleteRecord"
    />

    <SurveyImportDialog
      :busy="generating"
      :open="surveyImportOpen"
      :pest-type="pestType"
      :year="year"
      :generation="generation"
      @close="closeSurveyImportDialog"
      @import="onSurveyImport"
    />

    <ExcelImportDialog
      :busy="generating"
      :open="excelImportOpen"
      @close="closeExcelImportDialog"
    />

    <ConfirmDialog
      :open="showConfirmDialog"
      :title="confirmDialogTitle"
      :message="confirmDialogMessage"
      :busy="generating"
      @close="closeConfirmDialog"
      @confirm="confirmDelete"
    />
  </section>
</template>

<style scoped>
.workorder-preview-banner {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-5);
  border: 1px solid color-mix(in oklch, var(--color-primary) 40%, var(--color-border));
  border-radius: var(--radius-md);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: var(--text-sm);
}

.workorder-preview-banner strong {
  font-weight: 700;
  white-space: nowrap;
}

.workorder-page {
  position: relative;
  gap: var(--space-8);
  padding-bottom: var(--space-8);
}

.workorder-page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-9);
}

.workorder-page-actions {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
  justify-content: flex-end;
}

.workorder-page-actions button,
.workorder-batch-bar button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
}

.workorder-page-actions svg,
.workorder-batch-bar svg {
  width: 16px;
  height: 16px;
}

.workorder-eyebrow {
  margin-bottom: var(--space-2);
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: var(--text-2xs);
  font-weight: 700;
  letter-spacing: 0.12em;
}

.workorder-page-head h1 {
  color: var(--color-text);
  font-size: var(--text-title);
  letter-spacing: 0.01em;
}

.workorder-page-head p:last-child {
  margin-top: var(--space-2);
  max-width: 46rem;
  color: var(--color-text-muted);
  font-size: var(--text-md);
}

.workorder-controls {
  display: flex;
  align-items: flex-end;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.workorder-field {
  min-width: 0;
  display: grid;
  gap: var(--space-1);
}

.workorder-field > span:first-child {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: 650;
}

.workorder-field > select {
  width: 180px;
}

.workorder-field.is-task > select {
  width: 260px;
}

#workorder-year {
  width: 100px;
}

.workorder-action-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-5);
}

.workorder-action-card {
  min-height: 112px;
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text);
  text-align: left;
  text-decoration: none;
  box-shadow: var(--shadow-card);
}

.workorder-action-card:focus-visible {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: var(--focus-ring);
}

.workorder-action-card:not(:disabled):hover {
  border-color: color-mix(in oklch, var(--color-primary) 46%, var(--color-border));
  background: var(--color-primary-soft);
}

.workorder-action-card:disabled {
  cursor: not-allowed;
  opacity: 0.68;
}

.workorder-action-card.is-primary {
  border-color: color-mix(in oklch, var(--color-primary) 44%, var(--color-border));
}

.workorder-folder-input {
  display: none;
}

.workorder-action-icon {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: var(--radius-sm);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.workorder-action-card:disabled .workorder-action-icon {
  background: var(--color-bg);
  color: var(--color-text-muted);
}

.workorder-action-copy {
  min-width: 0;
  display: grid;
  gap: var(--space-1);
}

.workorder-action-copy strong,
.workorder-action-copy small {
  display: block;
}

.workorder-action-copy strong {
  color: var(--color-text);
  font-size: var(--text-md);
}

.workorder-action-copy small {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  line-height: 1.45;
}

.workorder-panel {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.workorder-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex-wrap: wrap;
  padding: var(--space-5) var(--space-7);
  border-bottom: 1px solid var(--color-border);
}

.workorder-search {
  position: relative;
  min-width: 210px;
  flex: 1;
}

.workorder-search svg {
  position: absolute;
  top: 50%;
  left: var(--space-4);
  width: 14px;
  height: 14px;
  color: var(--color-text-muted);
  transform: translateY(-50%);
}

.workorder-search input {
  width: 100%;
  min-height: 34px;
  padding: 0 var(--space-4) 0 31px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  outline: none;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: var(--text-sm);
}

.workorder-search input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px color-mix(in oklch, var(--color-primary) 10%, transparent);
}

.workorder-sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.workorder-segmented {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 3px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
}

.workorder-segmented button {
  min-height: 26px;
  padding: 0 var(--space-4);
  border: 0;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: 650;
}

.workorder-segmented button.is-active {
  background: var(--color-surface);
  color: var(--color-primary);
  box-shadow: 0 1px 4px color-mix(in oklch, var(--color-text) 8%, transparent);
}

.workorder-toolbar-separator {
  width: 1px;
  height: 20px;
  background: var(--color-border);
}

.workorder-select-all {
  min-height: 32px;
  padding: 0 var(--space-4);
  border: 0;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  font-weight: 650;
}

.workorder-select-all:hover {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.workorder-record-table {
  border: 0;
  border-radius: 0;
  box-shadow: none;
}

.workorder-empty {
  padding: 54px var(--space-7);
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  text-align: center;
}

.workorder-panel-foot {
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  padding: 0 var(--space-7);
  border-top: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.workorder-batch-bar {
  position: fixed;
  bottom: 0;
  inset-inline: 0;
  z-index: 16;
  display: flex;
  align-items: center;
  gap: var(--space-5);
  margin: 0;
  padding: var(--space-5) var(--space-9);
  border-top: 1px solid color-mix(in oklch, var(--color-surface) 18%, transparent);
  background: var(--color-nav);
  color: var(--color-surface);
  box-shadow: var(--shadow-bottom-bar);
}

.workorder-batch-bar > div {
  display: flex;
  gap: var(--space-3);
  margin-left: auto;
}

.workorder-batch-bar button {
  min-height: 34px;
  padding: 0 var(--space-5);
  border: 1px solid color-mix(in oklch, var(--color-surface) 22%, transparent);
  border-radius: var(--radius-md);
  background: color-mix(in oklch, var(--color-surface) 7%, transparent);
  color: var(--color-surface);
  font-size: var(--text-sm);
  font-weight: 650;
}

.workorder-batch-bar button:first-child {
  border-color: transparent;
  background: transparent;
}

.workorder-batch-bar button:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

@media (max-width: 760px) {
  .workorder-page-head,
  .workorder-batch-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .workorder-page-actions,
  .workorder-batch-bar > div {
    margin-left: 0;
  }

  .workorder-action-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .workorder-toolbar {
    padding: var(--space-5);
  }

  .workorder-toolbar-separator {
    display: none;
  }

  .workorder-batch-bar {
    margin: 0;
    padding: var(--space-5);
  }
}

@media (max-width: 520px) {
  .workorder-field,
  .workorder-field > select,
  .workorder-field.is-task > select,
  .workorder-search {
    width: 100%;
  }

  .workorder-action-grid {
    grid-template-columns: 1fr;
  }
}
</style>
