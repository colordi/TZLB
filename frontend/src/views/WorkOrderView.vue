<script setup>
import { computed, ref, watch } from "vue";

import { isUnauthorizedError } from "../api/http.js";
import { generateWorkorder } from "../api/workorder.js";
import RecordTable from "../components/workorder/RecordTable.vue";
import RecordDetailModal from "../components/workorder/RecordDetailModal.vue";
import SurveyImportDialog from "../components/workorder/SurveyImportDialog.vue";
import {
  CONTROL_TYPE_OPTIONS,
  PEST_OPTIONS,
  createEmptyRecord,
  getDefaultControlType,
  getDefaultTask,
  getTaskOptions,
  hasValidationErrors,
  normalizeRecordForPest,
  toPayloadRecord,
  validateRecords,
} from "../components/workorder/fieldConfig.js";
import { useToast } from "../composables/useToast.js";
import { downloadBlob } from "../utils/download.js";

const { error, info, success } = useToast();

const pestType = ref("春尺蠖");
const taskType = ref(getDefaultControlType(pestType.value));
const taskName = ref(getDefaultTask(pestType.value));
const records = ref([]);
const generating = ref(false);
const exportProgress = ref({
  current: 0,
  total: 0,
});
const showValidationErrors = ref(false);
const surveyImportOpen = ref(false);

const selectedIndexes = ref([]);
const activeRecordIndex = ref(-1);
const showDetailModal = ref(false);

const taskOptions = computed(() => getTaskOptions(pestType.value));
const canImportSurvey = computed(() => pestType.value === "春尺蠖");
const validationErrors = computed(() =>
  showValidationErrors.value ? validateRecords(records.value, pestType.value) : [],
);
const totalImages = computed(() =>
  records.value.reduce((count, record) => count + (record.images?.length || 0), 0),
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
  taskType.value = getDefaultControlType(nextType);
  taskName.value = getDefaultTask(nextType);
  showValidationErrors.value = false;
  if (nextType !== "春尺蠖") {
    surveyImportOpen.value = false;
  }
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

function updateRecords(nextRecords) {
  records.value = nextRecords.map((record) => normalizeRecordForPest(record, pestType.value));
}

function hasMeaningfulRecordContent(record) {
  const normalized = normalizeRecordForPest(record, pestType.value);
  return Boolean(
    `${normalized.town_or_street || ""}`.trim() ||
      `${normalized.location_id || ""}`.trim() ||
      `${normalized.location_name || ""}`.trim() ||
      `${normalized.description || ""}`.trim() ||
      `${normalized.note || ""}`.trim() ||
      Array.isArray(normalized.images) && normalized.images.length > 0,
  );
}

function openSurveyImportDialog() {
  if (!canImportSurvey.value || generating.value) {
    return;
  }
  surveyImportOpen.value = true;
}

function closeSurveyImportDialog() {
  surveyImportOpen.value = false;
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
    const payloadRecords = records.value.map((record) => toPayloadRecord(record, pestType.value));
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
    <div class="page-content-grid">
      <aside class="page-sidebar">
        <div class="status-bento">
          <div class="status-bento-hero">
            <div class="status-bento-hero-head">
              <span class="icon-badge-glass" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M4 7.75A2.75 2.75 0 0 1 6.75 5h10.5A2.75 2.75 0 0 1 20 7.75v8.5A2.75 2.75 0 0 1 17.25 19H6.75A2.75 2.75 0 0 1 4 16.25v-8.5Zm2.75-1.25c-.69 0-1.25.56-1.25 1.25v8.5c0 .69.56 1.25 1.25 1.25h10.5c.69 0 1.25-.56 1.25-1.25v-8.5c0-.69-.56-1.25-1.25-1.25H6.75Zm.5 2.25a.75.75 0 0 1 .75-.75h3a.75.75 0 0 1 0 1.5H8a.75.75 0 0 1-.75-.75Zm0 3.5A.75.75 0 0 1 8 11.5h8a.75.75 0 0 1 0 1.5H8a.75.75 0 0 1-.75-.75Zm0 3.5A.75.75 0 0 1 8 15h5a.75.75 0 0 1 0 1.5H8a.75.75 0 0 1-.75-.75Z" />
                </svg>
              </span>
              <span class="pulse-tag">Real-time</span>
            </div>
            <div class="status-value-hero">{{ records.length }}</div>
            <div class="status-label-hero">当前记录</div>
          </div>
          
          <div class="status-card">
            <div class="status-value-sub text-primary">{{ totalImages }}</div>
            <div class="status-label-sub">图片总数</div>
            <div class="status-trend">
              <span class="trend-icon">📈</span>
              当前任务: {{ taskName || "待设置" }}
            </div>
          </div>
          
          <div class="status-card">
            <div class="status-value-sub text-warning">{{ pestType }}</div>
            <div class="status-label-sub">害虫类型</div>
            <div class="status-trend text-danger">需人工确认</div>
          </div>
        </div>

        <section class="panel-card sidebar-panel">
          <div class="panel-head">
            <span class="icon-badge" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                <path
                  d="M4.8 4.8A2.8 2.8 0 0 1 7.6 2h8.8a2.8 2.8 0 0 1 2.8 2.8v2.06a3.24 3.24 0 0 1 1.66 4.68l-2.7 5.41A3.25 3.25 0 0 1 15.19 19H8.81a3.25 3.25 0 0 1-2.91-1.97L3.2 11.62A3.24 3.24 0 0 1 4.8 6.96V4.8Zm2.8-1.3c-.72 0-1.3.58-1.3 1.3v1.84c.24-.04.48-.06.72-.06h10c.24 0 .48.02.72.06V4.8c0-.72-.58-1.3-1.3-1.3H7.6Zm-.74 4.58a1.73 1.73 0 0 0-1.55 2.49l2.7 5.41c.29.58.88.95 1.53.95h6.38c.65 0 1.24-.37 1.53-.95l2.7-5.41a1.73 1.73 0 0 0-1.55-2.49H6.86Z"
                />
              </svg>
            </span>
            <div class="panel-head-copy">
              <h2>任务配置</h2>
              <p>先设定任务，再开始录入。</p>
            </div>
          </div>

          <div class="sidebar-field-stack">
            <div class="field-block">
              <label for="pest-type">害虫类型</label>
              <select id="pest-type" v-model="pestType" :disabled="generating">
                <option v-for="option in PEST_OPTIONS" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>

            <div class="field-block">
              <label for="task-type">统防统治类型</label>
              <select id="task-type" v-model="taskType" :disabled="generating">
                <option
                  v-for="option in CONTROL_TYPE_OPTIONS"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </select>
            </div>

            <div class="field-block">
              <label for="task-name">统防统治任务</label>
              <select
                id="task-name"
                v-model="taskName"
                :disabled="generating || !taskOptions.length"
              >
                <option v-if="!taskOptions.length" value="">暂无预设任务</option>
                <option
                  v-for="option in taskOptions"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </select>
            </div>
          </div>
        </section>

      </aside>

      <div class="page-main-column workorder-main-column">
        <div class="panel-card action-toolbar-glass">
          <div class="tb-headings">
            <h1 class="page-title-display">工作单录入工作台</h1>
            <p class="tb-subtitle">复核现场数据后提交。</p>
          </div>
          <div class="action-toolbar-buttons">
            <button
              v-if="selectedIndexes.length > 0"
              type="button"
              class="button-danger"
              :disabled="generating"
              @click="handleBatchDelete"
            >
              删除所选 ({{ selectedIndexes.length }})
            </button>
            <button
              v-if="canImportSurvey"
              type="button"
              class="button-secondary"
              :disabled="generating"
              data-testid="survey-import-button"
              @click="openSurveyImportDialog"
            >
              导入调查数据
            </button>
            <button type="button" :disabled="generating" @click="handleGenerate">
              {{ generateButtonLabel }}
            </button>
          </div>
        </div>

        <RecordTable
          v-model:selectedIndexes="selectedIndexes"
          :records="records"
          :pest-type="pestType"
          :busy="generating"
          :errors="validationErrors"
          @row-click="handleRowClick"
        />

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
          @close="closeSurveyImportDialog"
          @import="handleSurveyImport"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.workorder-page {
  gap: 2rem;
}

.status-bento {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.status-bento-hero {
  grid-column: 1 / -1;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-container));
  padding: 1.5rem;
  border-radius: var(--radius-md);
  color: #fff;
  box-shadow: 0 10px 24px rgba(15, 82, 56, 0.2);
}

.status-bento-hero-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.icon-badge-glass {
  background: rgba(255, 255, 255, 0.2);
  padding: 0.5rem;
  border-radius: var(--radius-xs);
  display: inline-flex;
}

.icon-badge-glass svg {
  width: 1.5rem;
  height: 1.5rem;
}

.pulse-tag {
  font-size: 0.75rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  background: rgba(255, 255, 255, 0.1);
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-xs);
}

.status-value-hero {
  font-family: var(--font-display);
  font-size: 2.5rem;
  font-weight: 800;
  line-height: 1;
}

.status-label-hero {
  font-size: 0.875rem;
  opacity: 0.8;
  font-weight: 500;
  margin-top: 0.25rem;
}

.status-card {
  background: var(--color-surface-container-lowest);
  padding: 1.5rem;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
}

.status-value-sub {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 800;
  line-height: 1;
}

.text-primary { color: var(--color-primary); }
.text-warning { color: var(--color-warning); }
.text-danger { color: var(--color-danger); }

.status-label-sub {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-muted);
  margin-top: 0.25rem;
}

.status-trend {
  margin-top: 1rem;
  font-size: 0.75rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  color: var(--color-secondary);
}

.sidebar-panel {
  padding: 1.5rem;
}

.sidebar-panel .panel-head {
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--color-surface-container);
  margin-bottom: 1.5rem;
}

.sidebar-panel .panel-head-copy h2 {
  font-size: 1.2rem;
  font-family: var(--font-display);
}

.sidebar-field-stack {
  display: grid;
  gap: 1.25rem;
}

.sidebar-field-stack label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-muted);
  font-weight: 800;
}

.sidebar-field-stack select {
  background: var(--color-surface-container-low);
  border: none;
  font-weight: 600;
  color: var(--color-ink);
}

.action-toolbar-glass {
  padding: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.page-title-display {
  font-size: 1.75rem;
  font-weight: 800;
}

.tb-subtitle {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-muted);
  margin-top: 0.25rem;
}

.action-toolbar-buttons {
  display: flex;
  gap: 0.75rem;
}

@media (max-width: 980px) {
  .status-bento {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .status-bento {
    grid-template-columns: 1fr 1fr;
  }
  .action-toolbar-glass {
    flex-direction: column;
    align-items: stretch;
  }
  .action-toolbar-buttons {
    flex-wrap: wrap;
  }
  .action-toolbar-buttons button {
    flex: 1;
  }
}

@media (max-width: 520px) {
  .status-bento {
    grid-template-columns: 1fr;
  }
}

</style>
