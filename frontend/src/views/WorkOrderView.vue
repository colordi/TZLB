<script setup>
import { computed, ref, watch } from "vue";

import { generateWorkorder } from "../api/workorder.js";
import RecordTable from "../components/workorder/RecordTable.vue";
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
import { createWorkorderCsvFile } from "../utils/workorderCsv.js";

const { error, info, success } = useToast();

const pestType = ref("春尺蠖");
const taskType = ref(getDefaultControlType(pestType.value));
const taskName = ref(getDefaultTask(pestType.value));
const records = ref([createEmptyRecord(pestType.value)]);
const generating = ref(false);
const showValidationErrors = ref(false);

const taskOptions = computed(() => getTaskOptions(pestType.value));
const validationErrors = computed(() =>
  showValidationErrors.value ? validateRecords(records.value, pestType.value) : [],
);
const totalImages = computed(() =>
  records.value.reduce((count, record) => count + (record.images?.length || 0), 0),
);

watch(pestType, (nextType) => {
  taskType.value = getDefaultControlType(nextType);
  taskName.value = getDefaultTask(nextType);
  showValidationErrors.value = false;
  records.value = records.value.length
    ? records.value.map((record) => normalizeRecordForPest(record, nextType))
    : [createEmptyRecord(nextType)];
});

watch(taskOptions, (options) => {
  if (!options.some((option) => option.value === taskName.value)) {
    taskName.value = options[0]?.value || "";
  }
});

function updateRecords(nextRecords) {
  records.value = nextRecords.map((record) => normalizeRecordForPest(record, pestType.value));
}

function addRecord() {
  records.value = [...records.value, createEmptyRecord(pestType.value)];
  info("已新增一条空白记录。", "记录已创建");
}

function exportCsv() {
  const { blob, filename } = createWorkorderCsvFile({
    pestType: pestType.value,
    taskType: taskType.value,
    taskName: taskName.value,
    records: records.value,
  });
  downloadBlob(blob, filename);
  success("当前记录已导出为 CSV。", "导出完成");
}

async function handleGenerate() {
  const errors = validateRecords(records.value, pestType.value);
  if (hasValidationErrors(errors)) {
    showValidationErrors.value = true;
    error("请先补全所有必填项并修正错误字段。", "还有未完成的记录");
    return;
  }

  generating.value = true;

  try {
    const payload = {
      pest_type: pestType.value,
      task_type: taskType.value,
      task: taskName.value,
      records: records.value.map((record) => toPayloadRecord(record, pestType.value)),
    };
    const { blob, filename } = await generateWorkorder(payload);
    downloadBlob(blob, filename);
    showValidationErrors.value = false;
    success("工作单已生成并开始下载。", "导出成功");
  } catch (generateError) {
    console.error(generateError);
    error(`${generateError.message || generateError}`, "工作单生成失败");
  } finally {
    generating.value = false;
  }
}
</script>

<template>
  <section class="page-shell workorder-page">
    <div class="page-content-grid">
      <aside class="page-sidebar">
        <section class="panel-card sidebar-panel">
          <div class="panel-head">
            <span class="icon-badge" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                <path
                  d="M4 7.75A2.75 2.75 0 0 1 6.75 5h10.5A2.75 2.75 0 0 1 20 7.75v8.5A2.75 2.75 0 0 1 17.25 19H6.75A2.75 2.75 0 0 1 4 16.25v-8.5Zm2.75-1.25c-.69 0-1.25.56-1.25 1.25v8.5c0 .69.56 1.25 1.25 1.25h10.5c.69 0 1.25-.56 1.25-1.25v-8.5c0-.69-.56-1.25-1.25-1.25H6.75Zm.5 2.25a.75.75 0 0 1 .75-.75h3a.75.75 0 0 1 0 1.5H8a.75.75 0 0 1-.75-.75Zm0 3.5A.75.75 0 0 1 8 11.5h8a.75.75 0 0 1 0 1.5H8a.75.75 0 0 1-.75-.75Zm0 3.5A.75.75 0 0 1 8 15h5a.75.75 0 0 1 0 1.5H8a.75.75 0 0 1-.75-.75Z"
                />
              </svg>
            </span>
            <div class="panel-head-copy">
              <h2>录入概览</h2>
              <p>记录数、图片数与当前任务一屏掌握。</p>
            </div>
          </div>

          <div class="compact-summary-grid">
            <article class="compact-summary is-highlight">
              <span class="compact-summary-value">{{ records.length }}</span>
              <span class="compact-summary-label">当前记录</span>
            </article>
            <article class="compact-summary">
              <span class="compact-summary-value">{{ totalImages }}</span>
              <span class="compact-summary-label">图片总数</span>
            </article>
            <article class="compact-summary">
              <span class="compact-summary-value compact-summary-text">{{ pestType }}</span>
              <span class="compact-summary-label">害虫类型</span>
            </article>
            <article class="compact-summary">
              <span class="compact-summary-value compact-summary-text">
                {{ taskName || "待设置" }}
              </span>
              <span class="compact-summary-label">当前任务</span>
            </article>
          </div>
        </section>

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
        <div class="panel-card action-toolbar">
          <div class="action-toolbar-buttons">
            <button type="button" :disabled="generating" @click="handleGenerate">
              {{ generating ? "正在生成工作单…" : "生成工作单" }}
            </button>
            <button type="button" class="button-secondary" :disabled="generating" @click="addRecord">新增记录</button>
            <button type="button" class="button-secondary" @click="exportCsv">导出数据</button>
          </div>
          <p class="muted-note action-toolbar-note">支持表格粘贴，图片通过单条记录弹窗统一管理。</p>
        </div>

        <RecordTable
          :records="records"
          :pest-type="pestType"
          :busy="generating"
          :errors="validationErrors"
          @update:records="updateRecords"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.workorder-page {
  gap: 0.95rem;
}

.sidebar-panel {
  padding: 1rem;
}

.sidebar-panel .panel-head {
  margin-bottom: 0.9rem;
}

.sidebar-panel .panel-head-copy h2 {
  font-size: 1.12rem;
  line-height: 1.15;
  letter-spacing: -0.02em;
}

.compact-summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
}

.compact-summary {
  min-height: 6.9rem;
  padding: 0.95rem 1rem;
  border-radius: 20px;
  border: 1px solid rgba(46, 125, 50, 0.12);
  background: rgba(245, 251, 244, 0.88);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 0.6rem;
}

.compact-summary.is-highlight {
  background:
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.18), transparent 34%),
    linear-gradient(135deg, #6dbb90, #2e7d32);
  color: #fff;
}

.compact-summary-value {
  font-size: clamp(1.5rem, 2vw, 2rem);
  line-height: 1;
  letter-spacing: -0.04em;
  font-weight: 800;
}

.compact-summary-text {
  font-size: 1.1rem;
  line-height: 1.25;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.compact-summary-label {
  color: var(--color-muted);
  font-size: 0.9rem;
  font-weight: 700;
}

.compact-summary.is-highlight .compact-summary-label {
  color: rgba(255, 255, 255, 0.84);
}

.sidebar-field-stack {
  display: grid;
  gap: 0.85rem;
}

.workorder-main-column {
  gap: 0.9rem;
}

.action-toolbar {
  padding: 0.7rem 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.action-toolbar-buttons {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  flex-wrap: wrap;
}

.action-toolbar-note {
  margin-left: auto;
  white-space: nowrap;
}

@media (max-width: 980px) {
  .compact-summary-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .compact-summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .action-toolbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .action-toolbar-note {
    margin-left: 0;
    white-space: normal;
  }
}

@media (max-width: 520px) {
  .compact-summary-grid {
    grid-template-columns: 1fr;
  }

  .compact-summary {
    min-height: 6.2rem;
  }
}

@media (max-width: 760px) {
  .sidebar-panel {
    padding: 1.05rem;
  }
}

</style>
