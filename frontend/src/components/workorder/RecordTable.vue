<script setup>
import { computed, ref } from "vue";

import {
  CONTROL_TYPE_OPTIONS,
  PEST_OPTIONS,
  createEmptyRecord,
  getTaskOptions,
  getVisibleFields,
  normalizeInputValue,
  normalizeRecordForPest,
} from "./fieldConfig.js";

const props = defineProps({
  records: {
    type: Array,
    required: true,
  },
  pestType: {
    type: String,
    required: true,
  },
  taskType: {
    type: String,
    required: true,
  },
  taskName: {
    type: String,
    required: true,
  },
  busy: {
    type: Boolean,
    default: false,
  },
  errors: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits([
  "update:pestType",
  "update:taskType",
  "update:taskName",
  "update:records",
  "submit",
]);

const fields = computed(() => getVisibleFields(props.pestType));
const taskOptions = computed(() => getTaskOptions(props.pestType));
const hasRows = computed(() => props.records.length > 0);
const activeRowIndex = ref(null);

function emitRecords(records) {
  emit(
    "update:records",
    records.map((record) => normalizeRecordForPest(record, props.pestType)),
  );
}

function addRecord() {
  emitRecords([...props.records, createEmptyRecord(props.pestType)]);
}

function updateRecord(index, record) {
  const next = props.records.slice();
  next[index] = record;
  emitRecords(next);
}

function removeRecord(index) {
  const next = props.records.filter((_, currentIndex) => currentIndex !== index);
  emitRecords(next.length ? next : [createEmptyRecord(props.pestType)]);
}

function applyGridPaste({ rowIndex, fieldKey, grid }) {
  const startIndex = fields.value.findIndex((field) => field.key === fieldKey);
  if (startIndex < 0) {
    return;
  }

  const next = props.records.slice();
  grid.forEach((row, rowOffset) => {
    const targetIndex = rowIndex + rowOffset;
    while (targetIndex >= next.length) {
      next.push(createEmptyRecord(props.pestType));
    }

    const targetRecord = {
      ...next[targetIndex],
    };

    row.forEach((cellValue, columnOffset) => {
      const field = fields.value[startIndex + columnOffset];
      if (!field) {
        return;
      }
      targetRecord[field.key] = normalizeInputValue(field, cellValue);
    });

    next[targetIndex] = normalizeRecordForPest(targetRecord, props.pestType);
  });

  emitRecords(next);
}

function updateCell(index, field, value) {
  updateRecord(index, {
    ...props.records[index],
    [field.key]: normalizeInputValue(field, value),
  });
}

function handleCellPaste(index, field, event) {
  const text = event.clipboardData?.getData("text/plain") || "";
  if (!text.includes("\t") && !text.includes("\n")) {
    return;
  }

  const grid = text
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .split("\n")
    .filter((row, rowIndex, rows) => !(row === "" && rowIndex === rows.length - 1))
    .map((row) => row.split("\t"));

  if (grid.length <= 1 && (grid[0]?.length || 0) <= 1) {
    return;
  }

  event.preventDefault();
  applyGridPaste({
    rowIndex: index,
    fieldKey: field.key,
    grid,
  });
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function getImageSlots(images = []) {
  return Array.from({ length: 4 }, (_, index) => ({
    key: `slot-${index}`,
    src: images[index] || "",
    imageIndex: index,
  }));
}

async function handleImageChange(index, event) {
  const currentImages = props.records[index]?.images || [];
  const availableSlots = Math.max(0, 4 - currentImages.length);
  const files = Array.from(event.target.files || []).slice(0, availableSlots);
  if (!files.length) {
    event.target.value = "";
    return;
  }

  const encodedFiles = await Promise.all(files.map((file) => readFileAsBase64(file)));
  updateRecord(index, {
    ...props.records[index],
    images: currentImages.concat(encodedFiles),
  });
  event.target.value = "";
}

async function handleImagePaste(index, event) {
  const clipboardItems = Array.from(event.clipboardData?.items || []);
  const imageFiles = clipboardItems
    .filter((item) => item.kind === "file" && item.type.startsWith("image/"))
    .map((item) => item.getAsFile())
    .filter(Boolean);

  if (imageFiles.length === 0) {
    return;
  }

  event.preventDefault();
  const currentImages = props.records[index]?.images || [];
  const availableSlots = Math.max(0, 4 - currentImages.length);
  const filesToRead = imageFiles.slice(0, availableSlots);
  if (filesToRead.length === 0) {
    return;
  }

  const encodedFiles = await Promise.all(filesToRead.map((file) => readFileAsBase64(file)));
  updateRecord(index, {
    ...props.records[index],
    images: currentImages.concat(encodedFiles),
  });
}

function removeImage(index, imageIndex) {
  const currentImages = props.records[index]?.images || [];
  updateRecord(index, {
    ...props.records[index],
    images: currentImages.filter((_, currentIndex) => currentIndex !== imageIndex),
  });
}
</script>

<template>
  <section class="table-shell">
    <header class="table-head">
      <div class="table-heading">
        <div class="table-intro">
          <p class="ui-eyebrow">录入控制</p>
          <p class="table-note">
            支持直接粘贴二维表格数据，现场图片可点击上传或按 Ctrl/Cmd+V 粘贴。
          </p>
        </div>

        <div class="table-actions">
          <button type="button" class="ghost" @click="addRecord">
            新增记录
          </button>
          <button type="button" :disabled="busy" @click="emit('submit')">
            {{ busy ? "正在生成…" : "批量生成工作单" }}
          </button>
        </div>
      </div>

      <div class="table-toolbar">
        <label class="table-select">
          <span>害虫类型</span>
          <select :value="pestType" @change="emit('update:pestType', $event.target.value)">
            <option
              v-for="option in PEST_OPTIONS"
              :key="option.value"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </label>

        <label class="table-select">
          <span>统防统治类型</span>
          <select :value="taskType" @change="emit('update:taskType', $event.target.value)">
            <option
              v-for="option in CONTROL_TYPE_OPTIONS"
              :key="option.value"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </label>

        <label class="table-select">
          <span>统防统治任务</span>
          <select
            :value="taskName"
            :disabled="taskOptions.length === 0"
            @change="emit('update:taskName', $event.target.value)"
          >
            <option v-if="taskOptions.length === 0" value="">
              暂未配置
            </option>
            <option
              v-for="option in taskOptions"
              :key="option.value"
              :value="option.value"
            >
              {{ option.label }}
            </option>
          </select>
        </label>
      </div>
    </header>

    <div class="table-wrap">
      <div class="table-stage">
        <div class="table-scroll">
          <table class="survey-table">
            <thead>
              <tr>
                <th class="cell-rownum">序号</th>
                <th
                  v-for="field in fields"
                  :key="field.key"
                  :class="['cell-head', `cell-${field.key}`]"
                >
                  {{ field.label }}
                  <em v-if="field.required">*</em>
                </th>
              </tr>
            </thead>

            <tbody v-if="hasRows">
              <tr
                v-for="(record, index) in records"
                :key="index"
                :class="{ 'is-row-active': activeRowIndex === index }"
                @mouseenter="activeRowIndex = index"
                @mouseleave="activeRowIndex = null"
              >
                <td class="cell-rownum">
                  <span class="rownum-pill">{{ String(index + 1).padStart(2, "0") }}</span>
                </td>

                <td
                  v-for="field in fields"
                  :key="field.key"
                  :class="[
                    'cell-body',
                    `cell-${field.key}`,
                    { 'cell-error': errors[index]?.[field.key] },
                  ]"
                >
                  <select
                    v-if="field.type === 'select'"
                    class="table-input table-select-input"
                    :value="record[field.key]"
                    :title="errors[index]?.[field.key] || ''"
                    @change="updateCell(index, field, $event.target.value)"
                    @paste="handleCellPaste(index, field, $event)"
                  >
                    <option value="">请选择</option>
                    <option
                      v-for="option in field.options"
                      :key="option"
                      :value="option"
                    >
                      {{ option }}
                    </option>
                  </select>

                  <textarea
                    v-else-if="field.type === 'textarea'"
                    class="table-input table-textarea"
                    :value="record[field.key]"
                    :title="errors[index]?.[field.key] || ''"
                    @input="updateCell(index, field, $event.target.value)"
                    @paste="handleCellPaste(index, field, $event)"
                  />

                  <input
                    v-else
                    class="table-input"
                    :type="field.type"
                    :value="record[field.key]"
                    :title="errors[index]?.[field.key] || ''"
                    @input="updateCell(index, field, $event.target.value)"
                    @paste="handleCellPaste(index, field, $event)"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="hasRows" class="tools-pane">
          <table class="tools-table">
            <thead>
              <tr>
                <th class="cell-tools-head">
                  <span>现场图片 / 删除</span>
                  <small>每条最多 4 张</small>
                </th>
              </tr>
            </thead>

            <tbody>
              <tr
                v-for="(record, index) in records"
                :key="`tools-${index}`"
                :class="{ 'is-row-active': activeRowIndex === index }"
                @mouseenter="activeRowIndex = index"
                @mouseleave="activeRowIndex = null"
              >
                <td class="cell-tools-body">
                  <div class="row-tools">
                    <div
                      class="thumb-strip"
                      tabindex="0"
                      title="点击空位上传图片，或聚焦后按 Ctrl/Cmd+V 粘贴，单条记录最多 4 张"
                      @click="$event.currentTarget.focus()"
                      @paste="handleImagePaste(index, $event)"
                    >
                      <template v-for="slot in getImageSlots(record.images)" :key="slot.key">
                        <button
                          v-if="slot.src"
                          type="button"
                          class="thumb-slot thumb-filled"
                          :title="`第 ${slot.imageIndex + 1} 张图片，点击移除`"
                          @click.stop="removeImage(index, slot.imageIndex)"
                        >
                          <img :src="slot.src" alt="" />
                          <span class="thumb-remove-mark">×</span>
                        </button>

                        <label v-else class="thumb-slot thumb-empty" title="点击上传图片">
                          <input
                            type="file"
                            accept="image/*"
                            multiple
                            @change="handleImageChange(index, $event)"
                          />
                          <span>+</span>
                        </label>
                      </template>
                    </div>

                    <button
                      type="button"
                      class="table-remove-icon"
                      title="删除当前记录"
                      aria-label="删除当前记录"
                      @click="removeRecord(index)"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path
                          d="M9 3.75h6a1.5 1.5 0 0 1 1.5 1.5v.75h3a.75.75 0 0 1 0 1.5h-1.03l-.82 11.1A2.25 2.25 0 0 1 15.4 21H8.6a2.25 2.25 0 0 1-2.24-2.1L5.53 7.5H4.5a.75.75 0 0 1 0-1.5h3v-.75A1.5 1.5 0 0 1 9 3.75Zm6 2.25v-.75h-6V6h6ZM7.86 7.5l.8 10.98a.75.75 0 0 0 .74.69h6.2a.75.75 0 0 0 .74-.69l.8-10.98H7.86Zm2.39 2.25a.75.75 0 0 1 .75.75v5.25a.75.75 0 0 1-1.5 0V10.5a.75.75 0 0 1 .75-.75Zm3.5 0a.75.75 0 0 1 .75.75v5.25a.75.75 0 0 1-1.5 0V10.5a.75.75 0 0 1 .75-.75Z"
                        />
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="!hasRows" class="empty-table">
          当前没有记录，点击上方“新增记录”开始录入。
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.table-shell {
  --table-head-height: 4rem;
  --record-row-height: 5rem;
  --row-alt: rgba(247, 243, 235, 0.82);
  display: grid;
  gap: 0.9rem;
  padding: 1rem;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-lg);
  background: var(--surface-base);
  box-shadow: var(--shadow-card);
}

.table-head {
  display: grid;
  gap: 0.9rem;
}

.table-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.table-intro {
  display: grid;
  gap: 0.35rem;
  max-width: 38rem;
}

.table-note {
  color: var(--muted);
  line-height: 1.6;
}

.table-toolbar {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
}

.table-select {
  display: grid;
  gap: 0.42rem;
}

.table-select span {
  font-size: 0.72rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--muted-soft);
}

.table-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  justify-content: flex-end;
}

.table-wrap {
  overflow: hidden;
  border: 1px solid var(--line-soft);
  border-radius: calc(var(--radius-lg) - 0.15rem);
  background: rgba(255, 252, 247, 0.88);
}

.table-stage {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 236px;
  align-items: start;
}

.table-scroll {
  overflow-x: auto;
  overflow-y: hidden;
  border-right: 1px solid var(--line-soft);
}

.tools-pane {
  overflow: hidden;
  background: rgba(247, 243, 234, 0.9);
}

.survey-table {
  width: 100%;
  min-width: 1460px;
  border-collapse: separate;
  border-spacing: 0;
}

.tools-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
}

.survey-table thead th,
.tools-table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  height: var(--table-head-height);
  padding: 0.8rem 0.7rem;
  background: rgba(238, 232, 220, 0.94);
  color: var(--ink-soft);
  text-align: left;
  font-size: 0.76rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  border-bottom: 1px solid var(--line-strong);
}

.survey-table thead th em {
  color: var(--danger);
  font-style: normal;
  margin-left: 0.15rem;
}

.survey-table tbody td,
.tools-table tbody td {
  padding: 0.42rem 0.5rem;
  border-bottom: 1px solid var(--line-soft);
  vertical-align: middle;
  background: rgba(255, 252, 247, 0.56);
}

.survey-table tbody tr:nth-child(2n) td,
.tools-table tbody tr:nth-child(2n) td {
  background: var(--row-alt);
}

.survey-table tbody tr:hover td,
.tools-table tbody tr:hover td,
.survey-table tbody tr.is-row-active td,
.tools-table tbody tr.is-row-active td {
  background: var(--hover-tint);
}

.survey-table tbody tr,
.tools-table tbody tr {
  height: var(--record-row-height);
}

.cell-rownum {
  width: 62px;
  min-width: 62px;
  text-align: center;
}

.rownum-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 2.1rem;
  padding: 0.22rem 0.42rem;
  border-radius: 999px;
  background: rgba(85, 106, 66, 0.1);
  color: var(--accent-strong);
  font-size: 0.72rem;
  font-weight: 700;
}

.cell-survey_date,
.cell-report_time {
  width: 120px;
  min-width: 120px;
}

.cell-region {
  width: 92px;
  min-width: 92px;
}

.cell-town_or_street,
.cell-location_name,
.cell-occurrence_position,
.cell-plot_type {
  width: 132px;
  min-width: 132px;
}

.cell-location_id {
  width: 98px;
  min-width: 98px;
}

.cell-total_insect_count,
.cell-damage_level {
  width: 96px;
  min-width: 96px;
}

.cell-description {
  width: 240px;
  min-width: 240px;
}

.cell-tools-head {
  display: grid;
  align-content: center;
  gap: 0.2rem;
}

.cell-tools-head small {
  font-size: 0.66rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted-soft);
}

.cell-body {
  height: 100%;
}

.table-input {
  width: 100%;
  min-width: 0;
  min-height: 3rem;
  padding: 0.72rem 0.82rem;
  border: 1px solid rgba(65, 83, 50, 0.12);
  border-radius: 0.85rem;
  background: rgba(255, 254, 251, 0.96);
  color: var(--ink);
  box-shadow: none;
  font-size: 0.84rem;
  line-height: 1.35;
}

.table-textarea {
  min-height: calc(var(--record-row-height) - 0.95rem);
  height: calc(var(--record-row-height) - 0.95rem);
  padding: 0.78rem 0.9rem;
  resize: none;
  overflow: hidden auto;
  white-space: normal;
}

.table-select-input {
  appearance: none;
}

.cell-error .table-input {
  border-color: rgba(176, 75, 49, 0.45);
  box-shadow: 0 0 0 3px rgba(176, 75, 49, 0.08);
}

.row-tools {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 2.95rem;
  gap: 0.5rem;
  align-items: stretch;
  height: calc(var(--record-row-height) - 0.9rem);
}

.thumb-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-template-rows: repeat(2, minmax(0, 1fr));
  gap: 0.35rem;
  height: 100%;
  padding: 0.35rem;
  border: 1px solid var(--line-soft);
  border-radius: 0.95rem;
  background: rgba(255, 252, 247, 0.9);
  outline: none;
}

.thumb-strip:focus {
  border-color: rgba(85, 106, 66, 0.3);
  box-shadow: 0 0 0 3px rgba(85, 106, 66, 0.08);
}

.thumb-slot,
.table-remove-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  min-height: 0;
  padding: 0;
  border-radius: 0.75rem;
  overflow: hidden;
}

.thumb-slot {
  position: relative;
  cursor: pointer;
  border: 1px dashed rgba(65, 83, 50, 0.18);
  background: rgba(255, 252, 247, 0.96);
  color: var(--ink);
  box-shadow: none;
}

.thumb-slot input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.thumb-empty {
  color: var(--muted-soft);
  font-size: 1.05rem;
  font-weight: 700;
}

.thumb-slot:hover {
  transform: none;
  border-color: rgba(85, 106, 66, 0.34);
  background: rgba(250, 246, 238, 0.98);
}

.thumb-filled {
  border-style: solid;
}

.thumb-filled img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-remove-mark {
  position: absolute;
  top: 0.22rem;
  right: 0.24rem;
  width: 1.1rem;
  height: 1.1rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: rgba(24, 31, 25, 0.68);
  color: #fff;
  font-size: 0.72rem;
}

.table-remove-icon {
  align-self: stretch;
  border: 1px solid rgba(176, 75, 49, 0.14);
  background: rgba(252, 235, 231, 0.74);
  color: var(--danger);
  box-shadow: none;
}

.table-remove-icon:hover {
  transform: none;
  background: rgba(249, 226, 221, 0.9);
}

.table-remove-icon svg {
  width: 1rem;
  height: 1rem;
  fill: currentColor;
}

.empty-table {
  padding: 1.8rem 1rem;
  text-align: center;
  color: var(--muted);
}

@media (max-width: 1024px) {
  .table-heading {
    flex-direction: column;
    align-items: stretch;
  }

  .table-actions {
    justify-content: flex-start;
  }

  .table-toolbar {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .table-shell {
    padding: 0.9rem;
  }

  .table-stage {
    grid-template-columns: minmax(0, 1fr);
  }

  .table-scroll {
    border-right: 0;
    border-bottom: 1px solid var(--line-soft);
  }
}
</style>
