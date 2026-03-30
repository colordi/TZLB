<script setup>
import { computed, ref, watch } from "vue";

import RecordTable from "../components/workorder/RecordTable.vue";
import { generateWorkorder } from "../api/workorder.js";
import {
  createEmptyRecord,
  getDefaultControlType,
  getDefaultTask,
  hasValidationErrors,
  normalizeRecordForPest,
  toPayloadRecord,
  validateRecords,
} from "../components/workorder/fieldConfig.js";

const pestType = ref("春尺蠖");
const taskType = ref(getDefaultControlType(pestType.value));
const taskName = ref(getDefaultTask(pestType.value));
const records = ref([createEmptyRecord(pestType.value)]);
const generating = ref(false);
const showValidationErrors = ref(false);

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

function updateRecords(nextRecords) {
  records.value = nextRecords.map((record) => normalizeRecordForPest(record, pestType.value));
}

function addRecord() {
  records.value = [...records.value, createEmptyRecord(pestType.value)];
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function handleGenerate() {
  const errors = validateRecords(records.value, pestType.value);
  if (hasValidationErrors(errors)) {
    showValidationErrors.value = true;
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
  } catch (error) {
    console.error(error);
  } finally {
    generating.value = false;
  }
}
</script>

<template>
  <section class="workorder-view">
    <aside class="workorder-sidebar">
      <!-- 统计指标 -->
      <div class="sidebar-section metrics-section">
        <div class="metric-item">
          <span class="metric-value">{{ records.length }}</span>
          <span class="metric-label">当前记录</span>
        </div>
        <div class="metric-item">
          <span class="metric-value">{{ totalImages }}</span>
          <span class="metric-label">图片总数</span>
        </div>
        <div class="metric-item">
          <span class="metric-value text-accent">{{ taskType }}</span>
          <span class="metric-label">统防类型</span>
        </div>
      </div>

      <!-- 配置选项 -->
      <div class="sidebar-section">
        <label class="field-label">害虫类型</label>
        <select v-model="pestType" class="field-select">
          <option value="春尺蠖">春尺蠖</option>
          <option value="国槐尺蠖">国槐尺蠖</option>
          <option value="其他害虫">其他害虫</option>
        </select>

        <label class="field-label">统防统治类型</label>
        <select v-model="taskType" class="field-select">
          <option value="春尺蠖防治">春尺蠖防治</option>
          <option value="国槐尺蠖防治">国槐尺蠖防治</option>
          <option value="美国白蛾防治">美国白蛾防治</option>
        </select>

        <label class="field-label">统防统治任务</label>
        <select v-model="taskName" class="field-select">
          <option value="2026春尺蠖防治">2026春尺蠖防治</option>
          <option value="2026国槐尺蠖防治">2026国槐尺蠖防治</option>
          <option value="2026美国白蛾防治">2026美国白蛾防治</option>
        </select>
      </div>

      <!-- 操作按钮 -->
      <div class="sidebar-section actions-section">
        <button type="button" class="btn-primary" :disabled="generating" @click="handleGenerate">
          {{ generating ? "生成中…" : "生成工作单" }}
        </button>
        <button type="button" class="btn-ghost" @click="addRecord">
          + 新增记录
        </button>
      </div>

      <!-- 提示信息 -->
      <div class="sidebar-section hint-section">
        <p class="hint-text">
          支持直接粘贴二维表格数据，现场图片可点击上传或按 Ctrl/Cmd+V 粘贴。
        </p>
      </div>
    </aside>

    <div class="workorder-main">
      <RecordTable
        :records="records"
        :pest-type="pestType"
        :task-type="taskType"
        :task-name="taskName"
        :busy="generating"
        :errors="validationErrors"
        @update:pest-type="pestType = $event"
        @update:task-type="taskType = $event"
        @update:task-name="taskName = $event"
        @update:records="updateRecords"
        @submit="handleGenerate"
      />
    </div>
  </section>
</template>

<style scoped>
.workorder-view {
  display: flex;
  flex: 1;
  gap: 1rem;
  min-height: 0;
}

/* 左侧边栏 */
.workorder-sidebar {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  overflow-y: auto;
  padding-right: 0.5rem;
}

.sidebar-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.875rem;
  background: var(--surface-base);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-soft);
}

.metrics-section {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  padding: 0.75rem;
}

.metric-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0.25rem;
}

.metric-value {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--ink);
  line-height: 1;
}

.metric-value.text-accent {
  font-size: 0.875rem;
  color: var(--accent);
}

.metric-label {
  font-size: 0.6875rem;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.field-label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--muted);
}

.field-select {
  width: 100%;
  min-height: 2.25rem;
  padding: 0.5rem 0.625rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-strong);
  color: var(--ink);
  font-size: 0.8125rem;
}

.field-select:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--focus-ring);
}

.actions-section {
  gap: 0.5rem;
}

.btn-primary {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 2.5rem;
  padding: 0 1rem;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--accent);
  color: #fff;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 150ms ease;
}

.btn-primary:hover:not(:disabled) {
  background: var(--accent-strong);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-ghost {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 2.25rem;
  padding: 0 1rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-strong);
  color: var(--ink-soft);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 150ms ease;
}

.btn-ghost:hover {
  background: var(--hover-tint);
  border-color: var(--border-strong);
}

.hint-section {
  background: var(--bg);
  border-style: dashed;
}

.hint-text {
  font-size: 0.75rem;
  color: var(--muted);
  line-height: 1.5;
  margin: 0;
}

/* 主内容区 */
.workorder-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

/* 响应式 */
@media (max-width: 1024px) {
  .workorder-view {
    flex-direction: column;
  }

  .workorder-sidebar {
    width: 100%;
    flex-direction: row;
    flex-wrap: wrap;
    padding-right: 0;
  }

  .sidebar-section {
    flex: 1;
    min-width: 200px;
  }

  .metrics-section {
    flex: 1;
    min-width: 200px;
  }

  .hint-section {
    flex: 2;
    min-width: 300px;
  }
}

@media (max-width: 640px) {
  .workorder-sidebar {
    flex-direction: column;
  }

  .sidebar-section,
  .metrics-section,
  .hint-section {
    flex: none;
    min-width: auto;
    width: 100%;
  }
}
</style>
