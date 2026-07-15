<script setup>
import { computed, ref, watch } from "vue";

import { isUnauthorizedError } from "../../api/http.js";
import { downloadImportTemplate, uploadSurveyExcel } from "../../api/survey.js";
import { useToast } from "../../composables/useToast.js";
import { downloadBlob } from "../../utils/download.js";
import BaseDialog from "./BaseDialog.vue";

const props = defineProps({
  busy: {
    type: Boolean,
    default: false,
  },
  open: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["close", "imported"]);
const { error, info, success } = useToast();

const selectedFile = ref(null);
const previewResult = ref(null);
const loading = ref(false);
const committing = ref(false);
const downloadingTemplate = ref(false);

const totals = computed(() => previewResult.value?.totals || {});
const hasErrors = computed(() => Number(totals.value.error_count || 0) > 0);
const importableRows = computed(
  () =>
    Number(totals.value.valid_rows || 0) -
    Number(totals.value.skipped_duplicate_rows || 0),
);
const canConfirm = computed(
  () =>
    !props.busy &&
    !loading.value &&
    !committing.value &&
    previewResult.value &&
    !hasErrors.value &&
    importableRows.value > 0,
);

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      resetDialogState();
    }
  },
);

function resetDialogState() {
  selectedFile.value = null;
  previewResult.value = null;
  loading.value = false;
  committing.value = false;
}

function handleFileChange(event) {
  const file = event.target.files?.[0] || null;
  selectedFile.value = file;
  previewResult.value = null;
}

async function handleDownloadTemplate() {
  if (downloadingTemplate.value) {
    return;
  }

  downloadingTemplate.value = true;
  try {
    const { blob, filename } = await downloadImportTemplate();
    await downloadBlob(blob, filename);
    success("导入模板已下载。", "下载完成");
  } catch (downloadError) {
    if (isUnauthorizedError(downloadError)) {
      return;
    }
    error(`${downloadError.message || downloadError}`, "模板下载失败");
  } finally {
    downloadingTemplate.value = false;
  }
}

function formatSheetTarget(sheet) {
  if (!sheet?.schema_name || !sheet?.table_name) {
    return "未匹配可写表";
  }
  return `${sheet.schema_name}.${sheet.table_name}`;
}

async function handlePreview() {
  if (!selectedFile.value) {
    info("请先选择一个 .xlsx 文件。", "缺少文件");
    return;
  }

  loading.value = true;
  try {
    previewResult.value = await uploadSurveyExcel({
      file: selectedFile.value,
      dryRun: true,
    });
    if (hasErrors.value) {
      error("Excel 存在校验错误，暂未入库。", "预览失败");
    } else if (importableRows.value === 0) {
      info("没有可导入的新记录。", "预览完成");
    } else {
      success(`校验通过，可导入 ${importableRows.value} 条记录。`, "预览完成");
    }
  } catch (previewError) {
    if (isUnauthorizedError(previewError)) {
      return;
    }
    error(`${previewError.message || previewError}`, "Excel 预览失败");
  } finally {
    loading.value = false;
  }
}

async function handleConfirm() {
  if (!canConfirm.value || !selectedFile.value) {
    return;
  }

  committing.value = true;
  try {
    const result = await uploadSurveyExcel({
      file: selectedFile.value,
      dryRun: false,
    });
    previewResult.value = result;

    if (Number(result.totals?.error_count || 0) > 0) {
      error("确认导入前数据发生变化，已取消入库。", "导入失败");
      return;
    }

    success(`已导入 ${result.totals?.inserted_rows || 0} 条记录。`, "导入完成");
    emit("imported", result);
  } catch (commitError) {
    if (isUnauthorizedError(commitError)) {
      return;
    }
    error(`${commitError.message || commitError}`, "Excel 入库失败");
  } finally {
    committing.value = false;
  }
}
</script>

<template>
  <BaseDialog
    :open="open"
    aria-label="上传调查 Excel"
    mask-class="excel-import-mask"
    dialog-class="excel-import-dialog"
    @close="emit('close')"
  >
    <header class="excel-dialog-head">
      <div>
        <h3>上传调查 Excel</h3>
        <p>sheet 名必须与 survey 或 ledger 下的可写表名完全一致，预览确认后才会写入数据库。</p>
      </div>
      <button type="button" class="button-secondary excel-dialog-close" @click="emit('close')">
        关闭
      </button>
    </header>

    <div class="excel-dialog-body">
      <div class="excel-import-picker">
        <div class="excel-import-field">
          <label for="survey-excel-file">本地 Excel 文件</label>
          <input
            id="survey-excel-file"
            type="file"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            :disabled="loading || committing"
            data-testid="survey-excel-file"
            @change="handleFileChange"
          />
        </div>
        <button
          type="button"
          :disabled="!selectedFile || loading || committing"
          data-testid="survey-excel-preview"
          @click="handlePreview"
        >
          {{ loading ? "校验中…" : "预览校验" }}
        </button>
      </div>

      <div class="excel-template-hint">
        <p>请先下载导入模板，按模板表头填写后再上传。</p>
        <button
          type="button"
          class="button-secondary"
          :disabled="downloadingTemplate"
          data-testid="survey-excel-download-template"
          @click="handleDownloadTemplate"
        >
          {{ downloadingTemplate ? "正在下载模板…" : "下载导入模板" }}
        </button>
      </div>

      <div v-if="previewResult" class="excel-result-panel" data-testid="excel-import-result">
        <div class="excel-result-summary">
          <span>sheet {{ totals.sheet_count || 0 }}</span>
          <span>总行数 {{ totals.row_count || 0 }}</span>
          <span>可导入 {{ importableRows }}</span>
          <span>跳过重复 {{ totals.skipped_duplicate_rows || 0 }}</span>
          <span :class="{ 'is-error': hasErrors }">错误 {{ totals.error_count || 0 }}</span>
        </div>

        <div class="excel-sheet-list">
          <article
            v-for="sheet in previewResult.sheets"
            :key="sheet.sheet_name"
            class="excel-sheet-item"
          >
            <div class="excel-sheet-head">
              <strong>{{ sheet.sheet_name }}</strong>
              <span>{{ formatSheetTarget(sheet) }}</span>
            </div>
            <p>
              总行数 {{ sheet.row_count }} / 有效 {{ sheet.valid_rows }} / 已导入
              {{ sheet.inserted_rows }} / 跳过 {{ sheet.skipped_duplicate_rows }}
            </p>
            <ul v-if="sheet.warnings?.length" class="excel-message-list">
              <li v-for="warning in sheet.warnings" :key="warning">{{ warning }}</li>
            </ul>
            <ul v-if="sheet.errors?.length" class="excel-message-list is-error">
              <li v-for="sheetError in sheet.errors" :key="sheetError">{{ sheetError }}</li>
            </ul>
          </article>
        </div>
      </div>

      <div v-else class="excel-empty-state">
        选择 .xlsx 文件后先预览，系统会校验 sheet 名、列名、必填项和重复记录。
      </div>
    </div>

    <footer class="excel-dialog-foot">
      <button type="button" class="button-secondary" @click="emit('close')">取消</button>
      <button
        type="button"
        :disabled="!canConfirm"
        data-testid="survey-excel-confirm"
        @click="handleConfirm"
      >
        {{ committing ? "正在入库…" : "确认入库" }}
      </button>
    </footer>
  </BaseDialog>
</template>

<style>
.base-dialog-mask.excel-import-mask {
  z-index: 1600;
  display: grid;
  place-items: center;
  padding: var(--space-5);
  background: color-mix(in oklch, var(--color-nav) 44%, transparent);
  backdrop-filter: blur(8px);
}

.base-dialog-content.excel-import-dialog {
  width: min(760px, calc(100vw - 2rem));
  max-height: min(46rem, calc(100vh - 2rem));
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-modal);
}
</style>

<style scoped>
.excel-dialog-head,
.excel-dialog-foot {
  display: flex;
  flex-shrink: 0;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-5);
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.excel-dialog-foot {
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-3);
  border-top: 1px solid var(--color-border);
  border-bottom: 0;
  background: var(--color-surface-container-low, var(--color-bg));
}

.excel-dialog-close {
  flex-shrink: 0;
}

.excel-dialog-head h3 {
  margin: 0;
  color: var(--color-text);
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 700;
  line-height: 1.15;
}

.excel-dialog-head p {
  margin-top: var(--space-2);
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.excel-dialog-body {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: var(--space-4);
  min-height: 0;
  overflow: auto;
  padding: var(--space-5) var(--space-6);
}

.excel-import-picker {
  display: flex;
  flex-shrink: 0;
  align-items: flex-end;
  gap: var(--space-4);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-container-low, var(--color-bg));
}

.excel-import-field {
  min-width: 0;
  flex: 1;
}

.excel-import-field label {
  display: block;
  margin-bottom: var(--space-2);
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  font-weight: 600;
}

.excel-import-field input {
  display: block;
  width: 100%;
  min-width: 0;
}

.excel-import-picker > button {
  flex-shrink: 0;
  white-space: nowrap;
}

.excel-template-hint {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
}

.excel-template-hint p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.excel-template-hint > button {
  flex-shrink: 0;
  white-space: nowrap;
}

.excel-result-panel {
  flex: 1 1 auto;
  min-height: 12rem;
}

.excel-empty-state {
  display: grid;
  flex: 1 1 auto;
  min-height: 12rem;
  place-items: center;
  padding: var(--space-6);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  text-align: center;
}

.excel-result-summary {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.excel-result-summary span {
  padding: 4px var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: 650;
}

.excel-result-summary .is-error {
  border-color: var(--color-danger);
  color: var(--color-danger);
}

.excel-sheet-list {
  display: grid;
  gap: var(--space-3);
}

.excel-sheet-item {
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
}

.excel-sheet-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-4);
}

.excel-sheet-head strong {
  color: var(--color-text);
  font-size: var(--text-sm);
}

.excel-sheet-head span,
.excel-sheet-item p,
.excel-message-list {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
}

.excel-sheet-item p {
  margin-top: var(--space-2);
}

.excel-message-list {
  margin: var(--space-2) 0 0;
  padding-left: 1.1rem;
}

.excel-message-list.is-error {
  color: var(--color-danger);
}

@media (max-width: 640px) {
  .excel-dialog-head,
  .excel-dialog-foot,
  .excel-dialog-body {
    padding: var(--space-4) var(--space-5);
  }

  .excel-import-picker {
    flex-direction: column;
    align-items: stretch;
  }

  .excel-import-picker > button,
  .excel-template-hint {
    flex-direction: column;
    align-items: stretch;
  }

  .excel-template-hint > button {
    width: 100%;
  }
}
</style>
