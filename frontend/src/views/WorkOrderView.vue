<script setup>
import { computed, ref, watch } from "vue";
import { Archive, FileSpreadsheet, FolderUp, ShieldCheck } from "@lucide/vue";

import { isUnauthorizedError } from "../api/http.js";
import { generateWorkorder, uploadDateImageFolder } from "../api/workorder.js";
import ExcelImportDialog from "../components/workorder/ExcelImportDialog.vue";
import RecordTable from "../components/workorder/RecordTable.vue";
import RecordDetailModal from "../components/workorder/RecordDetailModal.vue";
import SurveyImportDialog from "../components/workorder/SurveyImportDialog.vue";
import {
  PEST_OPTIONS,
  getDefaultControlType,
  getDefaultTask,
  getTaskOptions,
  hasValidationErrors,
  normalizeRecordForPest,
  supportsSurveyImport,
  toPayloadRecord,
  validateRecords,
} from "../components/workorder/fieldConfig.js";
import { useToast } from "../composables/useToast.js";
import { downloadBlob } from "../utils/download.js";

const { error, info, success } = useToast();

const pestType = ref("春尺蠖");
const taskType = computed(() => getDefaultControlType(pestType.value));
const taskName = ref(getDefaultTask(pestType.value));
const records = ref([]);
const generating = ref(false);
const exportProgress = ref({
  current: 0,
  total: 0,
});
const showValidationErrors = ref(false);
const surveyImportOpen = ref(false);
const excelImportOpen = ref(false);
const dateFolderInput = ref(null);
const dateFolderUploading = ref(false);

const selectedIndexes = ref([]);
const activeRecordIndex = ref(-1);
const showDetailModal = ref(false);
const searchQuery = ref("");
const recordFilter = ref("all");
const DATE_FOLDER_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

const taskOptions = computed(() => getTaskOptions(pestType.value));
const canImportSurvey = computed(() => supportsSurveyImport(pestType.value));
const validationErrors = computed(() =>
  showValidationErrors.value ? validateRecords(records.value, pestType.value) : [],
);
const filteredRecordItems = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase("zh-CN");

  return records.value
    .map((record, index) => ({
      record,
      index,
      errors: validationErrors.value[index] || {},
    }))
    .filter(({ record, index, errors }) => {
      if (recordFilter.value === "selected" && !selectedIndexes.value.includes(index)) {
        return false;
      }
      if (recordFilter.value === "errors" && Object.keys(errors).length === 0) {
        return false;
      }
      if (!query) {
        return true;
      }
      return [
        record.location_name,
        record.location_id,
        record.locality,
        record.description,
        record.note,
      ].some((value) => `${value || ""}`.toLocaleLowerCase("zh-CN").includes(query));
    });
});
const filteredRecords = computed(() => filteredRecordItems.value.map((item) => item.record));
const filteredRecordIndexes = computed(() => filteredRecordItems.value.map((item) => item.index));
const filteredValidationErrors = computed(() => filteredRecordItems.value.map((item) => item.errors));
const allVisibleSelected = computed(
  () =>
    filteredRecordIndexes.value.length > 0 &&
    filteredRecordIndexes.value.every((index) => selectedIndexes.value.includes(index)),
);
const generateButtonLabel = computed(() => {
  if (!generating.value) {
    return "生成工作单";
  }

  const total = exportProgress.value.total || records.value.length || 1;
  const current = exportProgress.value.current || 1;
  return `正在导出 ${current}/${total}…`;
});

watch(pestType, (nextType) => {
  taskName.value = getDefaultTask(nextType);
  showValidationErrors.value = false;
  surveyImportOpen.value = false;
  excelImportOpen.value = false;
  selectedIndexes.value = []; // Reset selections
  records.value = records.value.length
    ? records.value.map((record) => normalizeRecordForPest(record, nextType))
    : [];
});

watch(taskOptions, (options) => {
  if (!options.some((option) => option.value === taskName.value)) {
    taskName.value = options[0]?.value || "";
  }
});

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

function isValidDateFolderName(folderName) {
  if (!DATE_FOLDER_PATTERN.test(folderName)) {
    return false;
  }

  const [year, month, day] = folderName.split("-").map(Number);
  const parsedDate = new Date(Date.UTC(year, month - 1, day));
  return (
    parsedDate.getUTCFullYear() === year &&
    parsedDate.getUTCMonth() === month - 1 &&
    parsedDate.getUTCDate() === day
  );
}

function resolveSelectedFolderName(files) {
  const folderNames = new Set();
  for (const file of files) {
    const relativePath = file.webkitRelativePath || "";
    const [folderName] = relativePath.split("/");
    if (folderName) {
      folderNames.add(folderName);
    }
  }

  if (folderNames.size !== 1) {
    throw new Error("请选择一个日期文件夹。");
  }

  const [folderName] = Array.from(folderNames);
  if (!isValidDateFolderName(folderName)) {
    throw new Error("文件夹名称必须是 YYYY-MM-DD 格式的有效日期。");
  }
  return folderName;
}

function openDateFolderPicker() {
  if (generating.value || dateFolderUploading.value) {
    return;
  }
  dateFolderInput.value?.click();
}

function summarizeDateFolderUpload(result) {
  const skippedParts = [];
  if (result.skipped_existing_count) {
    skippedParts.push(`同名跳过 ${result.skipped_existing_count}`);
  }
  if (result.skipped_non_image_count) {
    skippedParts.push(`非图片跳过 ${result.skipped_non_image_count}`);
  }
  if (result.skipped_nested_count) {
    skippedParts.push(`子目录跳过 ${result.skipped_nested_count}`);
  }
  return skippedParts.length ? `，${skippedParts.join("，")}` : "";
}

async function handleDateFolderChange(event) {
  const input = event.target;
  const files = Array.from(input.files || []);

  try {
    if (!files.length) {
      return;
    }

    const folderName = resolveSelectedFolderName(files);
    dateFolderUploading.value = true;
    const result = await uploadDateImageFolder({
      folderName,
      files,
    });
    const skippedSummary = summarizeDateFolderUpload(result);
    if (Number(result.saved_count || 0) > 0) {
      success(
        `已上传 ${result.saved_count} 张图片到 ${result.folder_name}${skippedSummary}。`,
        "日期文件夹已上传",
      );
    } else {
      info(`没有新增图片${skippedSummary}。`, "日期文件夹已处理");
    }
  } catch (uploadError) {
    if (isUnauthorizedError(uploadError)) {
      return;
    }
    error(`${uploadError.message || uploadError}`, "日期文件夹上传失败");
  } finally {
    dateFolderUploading.value = false;
    input.value = "";
  }
}

function handleSurveyImport(importedRecords) {
  if (!Array.isArray(importedRecords) || importedRecords.length === 0) {
    info("请至少选择一条调查记录。", "没有可导入项");
    return;
  }

  const normalizedRecords = importedRecords.map((record) =>
    normalizeRecordForPest(record, pestType.value)
  );

  records.value = records.value.concat(normalizedRecords);
  surveyImportOpen.value = false;
  showValidationErrors.value = false;
  success(`已导入 ${normalizedRecords.length} 条调查记录。`, "导入完成");
}

function resetExportProgress() {
  exportProgress.value = {
    current: 0,
    total: 0,
  };
}

const activeRecord = computed(() => {
  return activeRecordIndex.value >= 0 ? records.value[activeRecordIndex.value] : null;
});

const activeRecordError = computed(() => {
  if (activeRecordIndex.value < 0 || !showValidationErrors.value) return {};
  const currentRecord = records.value[activeRecordIndex.value];
  if (!currentRecord) return {};
  return validateRecords([currentRecord], pestType.value)[0] || {};
});

function handleRowClick(index) {
  activeRecordIndex.value = index;
  showDetailModal.value = true;
}

function handleCloseDetailModal() {
  showDetailModal.value = false;
  activeRecordIndex.value = -1;
}

function handleUpdateRecord(updatedRecord) {
  if (activeRecordIndex.value >= 0) {
    const next = records.value.slice();
    next[activeRecordIndex.value] = normalizeRecordForPest(updatedRecord, pestType.value);
    records.value = next;
    selectedIndexes.value = []; // Safety reset
    handleCloseDetailModal();
  }
}

function handleDeleteRecord() {
  if (activeRecordIndex.value >= 0) {
    const next = records.value.filter((_, idx) => idx !== activeRecordIndex.value);
    records.value = next;
    selectedIndexes.value = []; // Safety reset
    handleCloseDetailModal();
  }
}

function handleBatchDelete() {
  if (selectedIndexes.value.length === 0) return;
  const set = new Set(selectedIndexes.value);
  records.value = records.value.filter((_, idx) => !set.has(idx));
  selectedIndexes.value = [];
  handleCloseDetailModal(); // Just in case
}

function clearSelection() {
  selectedIndexes.value = [];
}

function toggleFilteredSelection() {
  if (allVisibleSelected.value) {
    selectedIndexes.value = selectedIndexes.value.filter(
      (index) => !filteredRecordIndexes.value.includes(index),
    );
    return;
  }
  selectedIndexes.value = Array.from(
    new Set([...selectedIndexes.value, ...filteredRecordIndexes.value]),
  );
}

function joinDeliveryLabel(label, message) {
  return /^[A-Za-z0-9_.-]+$/.test(label) ? `${label} ${message}` : `${label}${message}`;
}

function buildDeliveryMessage(result, label) {
  if (result?.delivery === "share") {
    return joinDeliveryLabel(label, "已打开系统分享。");
  }

  if (result?.delivery === "preview") {
    return joinDeliveryLabel(label, "已打开预览，请在新页面中保存文件。");
  }

  return joinDeliveryLabel(label, "已开始下载。");
}

async function handleGenerate() {
  const errors = validateRecords(records.value, pestType.value);
  if (hasValidationErrors(errors)) {
    showValidationErrors.value = true;
    error("请先补全所有必填项并修正错误字段。", "还有未完成的记录");
    return;
  }

  generating.value = true;
  exportProgress.value = {
    current: 0,
    total: records.value.length,
  };

  try {
    const payload = {
      pest_type: pestType.value,
      task_type: taskType.value,
      task: taskName.value,
    };
    const payloadRecords = records.value.map((record, index) => ({
      ...toPayloadRecord(record, pestType.value),
      serial_number: index + 1,
    }));
    let completedCount = 0;
    let lastDelivery = null;

    showValidationErrors.value = false;

    for (const [index, record] of payloadRecords.entries()) {
      exportProgress.value = {
        current: index + 1,
        total: payloadRecords.length,
      };

      const { blob, filename } = await generateWorkorder({
        ...payload,
        records: [record],
      });
      lastDelivery = await downloadBlob(blob, filename);
      completedCount += 1;
    }

    if (completedCount === 1) {
      success(buildDeliveryMessage(lastDelivery, "工作单"), "导出成功");
      return;
    }

    success(`已依次导出 ${completedCount} 份工作单。`, "导出成功");
  } catch (generateError) {
    if (isUnauthorizedError(generateError)) {
      return;
    }

    const completedCount = Math.max(exportProgress.value.current - 1, 0);
    if (completedCount > 0) {
      error(
        `已导出 ${completedCount}/${exportProgress.value.total} 份工作单，剩余导出失败：${generateError.message || generateError}`,
        "部分导出失败",
      );
      return;
    }

    error(`${generateError.message || generateError}`, "工作单生成失败");
  } finally {
    generating.value = false;
    resetExportProgress();
  }
}
</script>

<template>
  <section class="page-shell workorder-page">
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
          @click="handleGenerate"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
            <path d="M7 3h7l5 5v13H7zM14 3v5h5M10 13h6m-6 4h6" />
          </svg>
          <span>{{ generating ? generateButtonLabel : "逐条导出工作单" }}</span>
        </button>
        <button
          v-if="canImportSurvey"
          type="button"
          :disabled="generating"
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
        :disabled="generating"
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
        :disabled="generating || dateFolderUploading"
        data-testid="date-image-folder-button"
        @click="openDateFolderPicker"
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
        @change="handleDateFolderChange"
      />
      <button type="button" class="workorder-action-card" disabled>
        <span class="workorder-action-icon"><Archive :size="21" /></span>
        <span class="workorder-action-copy">
          <strong>占位功能二</strong>
          <small>暂未启用</small>
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
        v-model:selectedIndexes="selectedIndexes"
        :records="filteredRecords"
        :row-indexes="filteredRecordIndexes"
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
        <span>已选 <strong>{{ selectedIndexes.length }}</strong> 条</span>
      </footer>
    </section>

    <aside v-if="selectedIndexes.length" class="workorder-batch-bar" aria-label="已选工单摘要">
      <span>已选 <strong>{{ selectedIndexes.length }}</strong> 条记录</span>
      <div>
        <button type="button" :disabled="generating" @click="clearSelection">取消选择</button>
        <button type="button" :disabled="generating" @click="handleBatchDelete">
          删除选中
        </button>
        <button
          type="button"
          :disabled="generating || records.length === 0"
          @click="handleGenerate"
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
      @close="closeSurveyImportDialog"
      @import="handleSurveyImport"
    />

    <ExcelImportDialog
      :busy="generating"
      :open="excelImportOpen"
      @close="closeExcelImportDialog"
    />
  </section>
</template>

<style scoped>
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
  box-shadow: var(--shadow-card);
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
  position: sticky;
  bottom: calc(var(--space-10) * -1);
  z-index: 16;
  display: flex;
  align-items: center;
  gap: var(--space-5);
  margin: var(--space-7) calc(var(--space-10) * -1) calc(var(--space-8) * -1);
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
    bottom: 0;
    margin: var(--space-7) calc(var(--space-10) * -1) calc(var(--space-8) * -1);
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
