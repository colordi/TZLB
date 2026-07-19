<script setup>
import { computed, ref, watch } from "vue";
import { Archive, FileSpreadsheet, FolderUp } from "@lucide/vue";

import { useWorkorderTaskConfig } from "../composables/workorder/useWorkorderTaskConfig.js";
import { useWorkorderRecords } from "../composables/workorder/useWorkorderRecords.js";
import { useRecordSelection } from "../composables/workorder/useRecordSelection.js";
import { useWorkorderExport } from "../composables/workorder/useWorkorderExport.js";
import { useDateFolderUpload } from "../composables/workorder/useDateFolderUpload.js";
import { useRecordDetailModal } from "../composables/workorder/useRecordDetailModal.js";
import { useToast } from "../composables/useToast.js";
import ExcelImportDialog from "../components/workorder/ExcelImportDialog.vue";
import RecordTable from "../components/workorder/RecordTable.vue";
import RecordDetailModal from "../components/workorder/RecordDetailModal.vue";
import SurveyImportDialog from "../components/workorder/SurveyImportDialog.vue";
import ConfirmDialog from "../components/workorder/ConfirmDialog.vue";

const toast = useToast();

const taskConfig = useWorkorderTaskConfig();
const {
  PEST_OPTIONS, pestType, year, taskName,
  generation, taskOptions, yearOptions, canImportSurvey,
} = taskConfig;

const recCtrl = useWorkorderRecords(pestType);
const {
  records, validationErrors,
  normalizeAll, handleSurveyImport: importRecords,
  handleUpdateRecord: updateRecord,
  handleBatchDelete: batchDelete,
} = recCtrl;

const selection = useRecordSelection(records, validationErrors);
const {
  selectedUids, searchQuery, recordFilter,
  currentPage, totalPages, serialOffset,
  filteredRecords, pagedRecords, pagedValidationErrors,
  clearSelection, goToPrevPage, goToNextPage,
} = selection;

const exportCtrl = useWorkorderExport(
  taskConfig, records, selectedUids,
);
const {
  generating,
  generateButtonLabel,
  exportProgress,
  exportProgressPercent,
  exportProgressLabel,
} = exportCtrl;

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
    <header class="workorder-page-head">
      <div>
        <h1>调查工单</h1>
        <p>导入调查记录，检查点位信息并批量生成工单。</p>
      </div>
      <div class="workorder-page-actions" aria-label="工单操作">
        <button
          v-if="canImportSurvey"
          type="button"
          class="button-secondary"
          :disabled="generating"
          data-testid="survey-import-button"
          @click="openSurveyImportDialog"
        >
          从数据库追加
        </button>
      </div>
    </header>

    <section class="workorder-card workorder-card--accent" aria-label="任务配置">
      <h2 class="workorder-card-title">任务配置</h2>
      <div class="workorder-controls">
        <label class="workorder-field" for="pest-type">
          <span class="workorder-sr-only">害虫类型</span>
          <select id="pest-type" v-model="pestType" :disabled="generating">
            <option v-for="option in PEST_OPTIONS" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>

        <label class="workorder-field" for="workorder-year">
          <span class="workorder-sr-only">年份</span>
          <select id="workorder-year" v-model="year" :disabled="generating">
            <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}</option>
          </select>
        </label>

        <label class="workorder-field is-task" for="task-name">
          <span class="workorder-sr-only">统防统治任务</span>
          <select id="task-name" v-model="taskName" :disabled="generating || !taskOptions.length">
            <option v-if="!taskOptions.length" value="">暂无预设任务</option>
            <option v-for="option in taskOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
      </div>
    </section>

    <section class="workorder-card workorder-card--accent" aria-label="导入调查数据">
      <h2 class="workorder-card-title">导入调查数据</h2>
      <div class="workorder-import-actions">
        <button
          type="button"
          class="workorder-import-btn"
          :disabled="generating"
          data-testid="survey-excel-import-button"
          @click="openExcelImportDialog"
        >
          <FileSpreadsheet :size="16" />
          <span>Excel导入</span>
        </button>
        <button
          type="button"
          class="workorder-import-btn"
          :disabled="generating || dateFolderUploading"
          data-testid="date-image-folder-button"
          @click="onOpenDateFolderPicker"
        >
          <FolderUp :size="16" />
          <span>{{ dateFolderUploading ? "正在上传…" : "图片文件夹导入" }}</span>
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
          to="/workorder/point-screenshots"
          class="workorder-import-btn"
          data-testid="point-screenshot-entry"
        >
          <Archive :size="16" />
          <span>截图管理</span>
        </router-link>
      </div>
    </section>

    <section class="workorder-card workorder-list-card" aria-label="点位清单">
      <div class="workorder-list-head">
        <h2 class="workorder-card-title">点位清单</h2>
        <span class="workorder-list-count">共 {{ records.length }} 个点位</span>
      </div>

      <div class="workorder-toolbar">
        <label class="workorder-search">
          <span class="workorder-sr-only">搜索点位</span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="7" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <input
            v-model="searchQuery"
            type="search"
            placeholder="搜索点位……"
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
            错误
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
      </div>

      <RecordTable
        class="workorder-record-table"
        v-model:selectedUids="selectedUids"
        :records="pagedRecords"
        :pest-type="pestType"
        :busy="generating"
        :busy-label="exportProgressLabel"
        :busy-percent="exportProgressPercent"
        :errors="pagedValidationErrors"
        :serial-offset="serialOffset"
        @row-click="handleRowClick"
      />

      <div v-if="records.length > 0 && filteredRecords.length === 0" class="workorder-empty">
        当前筛选条件下没有工单记录。
      </div>

      <div
        v-if="generating"
        class="workorder-export-progress"
        data-testid="workorder-export-progress"
        aria-live="polite"
      >
        <div class="workorder-export-progress-head">
          <strong>{{ exportProgressLabel }}</strong>
          <span data-testid="workorder-export-progress-percent">{{ exportProgressPercent }}%</span>
        </div>
        <div
          class="workorder-export-progress-track"
          role="progressbar"
          :aria-valuenow="exportProgressPercent"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-label="exportProgressLabel"
        >
          <div
            class="workorder-export-progress-fill"
            :style="{ width: `${exportProgressPercent}%` }"
          />
        </div>
        <p v-if="exportProgress.total > 0" class="workorder-export-progress-meta">
          进度 {{ Math.min(exportProgress.current, exportProgress.total) }} / {{ exportProgress.total }}
        </p>
      </div>

      <div
        v-if="filteredRecords.length > 0"
        class="workorder-pagination"
        data-testid="workorder-pagination"
      >
        <button
          type="button"
          class="workorder-page-btn"
          :disabled="currentPage <= 1 || generating"
          data-testid="workorder-page-prev"
          @click="goToPrevPage"
        >
          上一页
        </button>
        <span class="workorder-page-status" data-testid="workorder-page-status">
          第 {{ currentPage }} / {{ totalPages }} 页
        </span>
        <button
          type="button"
          class="workorder-page-btn"
          :disabled="currentPage >= totalPages || generating"
          data-testid="workorder-page-next"
          @click="goToNextPage"
        >
          下一页
        </button>
      </div>

      <footer class="workorder-list-foot">
        <div class="workorder-list-foot-meta">
          <span>已选择 <strong>{{ selectedUids.length }}</strong> 个点位</span>
          <template v-if="selectedUids.length">
            <button type="button" class="workorder-text-btn" :disabled="generating" @click="clearSelection">
              取消选择
            </button>
            <button type="button" class="workorder-text-btn is-danger" :disabled="generating" @click="onBatchDelete">
              删除选中
            </button>
          </template>
        </div>
        <button
          type="button"
          class="workorder-export-btn"
          :disabled="generating || records.length === 0"
          data-testid="workorder-export-button"
          @click="onGenerate"
        >
          {{ generateButtonLabel }}
        </button>
      </footer>
    </section>

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
.workorder-page {
  position: relative;
  gap: var(--space-module);
}

.workorder-page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-form);
}

.workorder-page-head h1 {
  color: var(--color-text);
  font-size: var(--text-title);
  letter-spacing: 0.01em;
}

.workorder-page-head p {
  margin-top: var(--space-title);
  max-width: 46rem;
  color: var(--color-text-muted);
  font-size: var(--text-md);
}

.workorder-page-actions {
  display: flex;
  gap: var(--space-icon);
  flex-wrap: wrap;
  justify-content: flex-end;
}

.workorder-card {
  display: grid;
  gap: var(--space-form);
  padding: var(--space-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

/* 任务配置 / 导入区：右侧淡色装饰，缓解横向留白 */
.workorder-card--accent {
  position: relative;
  overflow: hidden;
  isolation: isolate;
  background:
    radial-gradient(
      120px 90px at calc(100% - 48px) 18%,
      color-mix(in oklch, var(--color-primary) 9%, transparent),
      transparent 72%
    ),
    radial-gradient(
      160px 120px at calc(100% - 8px) 88%,
      color-mix(in oklch, var(--color-secondary) 10%, transparent),
      transparent 70%
    ),
    linear-gradient(
      105deg,
      var(--color-surface) 0%,
      var(--color-surface) 58%,
      color-mix(in oklch, var(--color-primary-soft) 55%, var(--color-surface)) 100%
    );
}

.workorder-card--accent::before {
  content: "";
  position: absolute;
  top: -24px;
  right: -18px;
  z-index: 0;
  width: 120px;
  height: 120px;
  border-radius: 40% 60% 55% 45%;
  background: color-mix(in oklch, var(--color-primary) 6%, transparent);
  transform: rotate(18deg);
  pointer-events: none;
}

.workorder-card--accent::after {
  content: "";
  position: absolute;
  right: 28px;
  bottom: -28px;
  z-index: 0;
  width: 90px;
  height: 90px;
  border-radius: 50%;
  border: 1px solid color-mix(in oklch, var(--color-primary) 10%, transparent);
  background: color-mix(in oklch, var(--color-secondary) 5%, transparent);
  pointer-events: none;
}

.workorder-card--accent > * {
  position: relative;
  z-index: 1;
}

.workorder-card-title {
  margin: 0;
  color: var(--color-text);
  font-size: var(--text-base);
  font-weight: 700;
}

.workorder-controls {
  display: flex;
  align-items: center;
  gap: var(--space-form);
  flex-wrap: wrap;
}

.workorder-field {
  min-width: 0;
  display: grid;
  gap: var(--space-label);
}

.workorder-field > select {
  width: 160px;
  min-height: 36px;
}

.workorder-field.is-task > select {
  width: 240px;
}

#workorder-year {
  width: 100px;
}

.workorder-import-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-icon);
}

.workorder-import-btn {
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  gap: var(--space-icon);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: var(--text-sm);
  font-weight: 650;
  text-decoration: none;
}

.workorder-import-btn:focus-visible {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: var(--focus-ring);
}

.workorder-import-btn:not(:disabled):hover {
  border-color: color-mix(in oklch, var(--color-primary) 46%, var(--color-border));
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.workorder-import-btn:disabled {
  cursor: not-allowed;
  opacity: 0.68;
}

.workorder-folder-input {
  display: none;
}

.workorder-list-card {
  padding: 0;
  gap: 0;
  overflow: visible;
}

.workorder-list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-form);
  padding: var(--space-card) var(--space-card) 0;
}

.workorder-list-count {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  font-weight: 650;
}

.workorder-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-form);
  flex-wrap: wrap;
  padding: var(--space-form) var(--space-card);
}

.workorder-search {
  position: relative;
  min-width: 210px;
  flex: 1;
}

.workorder-search svg {
  position: absolute;
  top: 50%;
  left: var(--space-form);
  width: 14px;
  height: 14px;
  color: var(--color-text-muted);
  transform: translateY(-50%);
}

.workorder-search input {
  width: 100%;
  min-height: 34px;
  padding: 0 var(--space-form) 0 36px;
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

.workorder-record-table {
  border: 0;
  border-radius: 0;
  box-shadow: none;
}

/* 表格随内容撑开，由右侧主内容区整页滚动，不在清单内部锁高度 */
.workorder-record-table :deep(.record-workspace) {
  overflow: visible;
  border: 0;
  border-radius: 0;
  box-shadow: none;
}

.workorder-record-table :deep(.desktop-records),
.workorder-record-table :deep(.table-scroll) {
  min-height: unset;
  overflow: visible;
}

.workorder-record-table :deep(.table-scroll) {
  overflow-x: auto;
  overflow-y: visible;
}

.workorder-empty {
  padding: 48px var(--space-card);
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  text-align: center;
}

.workorder-export-progress {
  display: grid;
  gap: 8px;
  padding: var(--space-form) var(--space-card);
  border-top: 1px solid var(--color-border);
  background: color-mix(in oklch, var(--color-primary) 4%, var(--color-surface));
}

.workorder-export-progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: var(--color-text);
  font-size: var(--text-sm);
}

.workorder-export-progress-head strong {
  font-weight: 700;
}

.workorder-export-progress-head span {
  color: var(--color-primary);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.workorder-export-progress-track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: color-mix(in oklch, var(--color-primary) 12%, var(--color-bg));
}

.workorder-export-progress-fill {
  height: 100%;
  border-radius: inherit;
  background: var(--color-primary);
  transition: width 160ms ease;
}

.workorder-export-progress-meta {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--text-xs);
}

.workorder-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-form);
  padding: var(--space-form) var(--space-card);
  border-top: 1px solid var(--color-border);
}

.workorder-page-status {
  min-width: 7rem;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  font-weight: 650;
  text-align: center;
}

.workorder-page-btn {
  min-height: 32px;
  padding: 0 var(--space-form);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: var(--text-sm);
  font-weight: 650;
}

.workorder-page-btn:hover:not(:disabled) {
  border-color: color-mix(in oklch, var(--color-primary) 46%, var(--color-border));
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.workorder-page-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.workorder-list-foot {
  min-height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-form);
  flex-wrap: wrap;
  padding: var(--space-form) var(--space-card);
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
}

.workorder-list-foot-meta {
  display: flex;
  align-items: center;
  gap: var(--space-form);
  flex-wrap: wrap;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.workorder-list-foot-meta strong {
  color: var(--color-text);
}

.workorder-text-btn {
  min-height: 28px;
  padding: 0 var(--space-icon);
  border: 0;
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  font-weight: 650;
}

.workorder-text-btn:hover:not(:disabled) {
  color: var(--color-primary);
}

.workorder-text-btn.is-danger:hover:not(:disabled) {
  color: var(--color-danger);
}

.workorder-text-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.workorder-export-btn {
  min-height: 36px;
  padding: 0 var(--space-form);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: var(--color-surface);
  font-size: var(--text-sm);
  font-weight: 650;
}

.workorder-export-btn:hover:not(:disabled) {
  filter: brightness(1.05);
}

.workorder-export-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

@media (max-width: 760px) {
  .workorder-page-head {
    flex-direction: column;
    align-items: stretch;
  }

  .workorder-page-actions {
    justify-content: stretch;
  }

  .workorder-page-actions button {
    width: 100%;
  }

  .workorder-card {
    padding: var(--space-form);
  }

  .workorder-list-head,
  .workorder-toolbar,
  .workorder-list-foot,
  .workorder-pagination {
    padding-left: var(--space-form);
    padding-right: var(--space-form);
  }

  .workorder-list-foot {
    flex-direction: column;
    align-items: stretch;
  }

  .workorder-export-btn {
    width: 100%;
  }
}

@media (max-width: 520px) {
  .workorder-field,
  .workorder-field > select,
  .workorder-field.is-task > select,
  .workorder-search {
    width: 100%;
  }

  .workorder-import-actions {
    flex-direction: column;
  }

  .workorder-import-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
