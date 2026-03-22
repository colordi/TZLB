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
    <header class="summary-card">
      <div class="summary-copy">
        <p class="ui-eyebrow">工作单录入</p>
        <h2>批量生成工作单</h2>
        <p class="ui-note">
          集中维护调查记录、现场图片与统防统治信息，完成后直接导出标准工作单。
        </p>
      </div>

      <div class="summary-metrics">
        <article class="ui-stat">
          <span class="ui-stat-label">当前记录</span>
          <strong class="ui-stat-value">{{ records.length }}</strong>
        </article>
        <article class="ui-stat">
          <span class="ui-stat-label">图片总数</span>
          <strong class="ui-stat-value">{{ totalImages }}</strong>
        </article>
        <article class="ui-stat">
          <span class="ui-stat-label">统防类型</span>
          <strong class="ui-stat-value">{{ taskType }}</strong>
        </article>
      </div>
    </header>

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
  </section>
</template>

<style scoped>
.workorder-view {
  display: grid;
  gap: 1rem;
}

.summary-card {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
  gap: 0.9rem;
  padding: 1.15rem 1.2rem;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-lg);
  background: var(--surface-base);
  box-shadow: var(--shadow-card);
}

.summary-copy {
  display: grid;
  gap: 0.45rem;
  align-content: center;
  max-width: 42rem;
}

.summary-copy h2 {
  font-size: clamp(1.55rem, 2.3vw, 2.15rem);
  line-height: 1.12;
}

.summary-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.7rem;
}

@media (max-width: 920px) {
  .summary-card {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 680px) {
  .summary-card {
    padding: 1rem;
  }

  .summary-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
