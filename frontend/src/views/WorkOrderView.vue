<script setup>
import { computed, ref, watch } from "vue";

import { generateWorkorder } from "../api/workorder.js";
import RecordTable from "../components/workorder/RecordTable.vue";
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
    <header class="hero-card">
      <div class="hero-copy">
        <p class="hero-kicker">Workorder Studio</p>
        <h2>工作单录入</h2>
      </div>

      <div class="hero-metrics">
        <div class="hero-metric">
          <span>当前记录数</span>
          <strong>{{ records.length }}</strong>
        </div>
        <div class="hero-metric">
          <span>图片总数</span>
          <strong>{{ totalImages }}</strong>
        </div>
        <div class="hero-metric">
          <span>统防统治类型</span>
          <strong>{{ taskType }}</strong>
        </div>
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

.hero-card {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
  gap: 1rem;
  padding: 1.15rem;
  border-radius: 1.55rem;
  background:
    radial-gradient(circle at top right, rgba(137, 165, 104, 0.22), transparent 36%),
    linear-gradient(135deg, rgba(251, 247, 235, 0.94), rgba(236, 230, 211, 0.88));
  border: 1px solid var(--line-strong);
  box-shadow: var(--panel-shadow);
}

.hero-copy {
  display: grid;
  align-content: center;
  gap: 0.35rem;
  padding: 1rem 1.1rem;
  border-radius: 1.25rem;
  background: linear-gradient(180deg, rgba(255, 252, 246, 0.76), rgba(250, 246, 236, 0.42));
  border: 1px solid rgba(53, 67, 48, 0.08);
}

.hero-kicker {
  margin: 0;
  font-size: 0.72rem;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: var(--accent);
}

.hero-copy h2 {
  margin: 0;
  font-size: clamp(1.4rem, 2.4vw, 2rem);
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
}

.hero-metric {
  display: grid;
  align-content: center;
  gap: 0.4rem;
  min-width: 0;
  padding: 1rem;
  border-radius: 1.2rem;
  background: linear-gradient(180deg, rgba(255, 252, 246, 0.92), rgba(246, 240, 226, 0.72));
  border: 1px solid rgba(53, 67, 48, 0.08);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.52);
}

.hero-metric span {
  font-size: 0.78rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--muted);
}

.hero-metric strong {
  font-size: clamp(1.25rem, 2vw, 1.6rem);
}

@media (max-width: 960px) {
  .hero-card {
    grid-template-columns: 1fr;
  }

  .hero-metrics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .hero-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
