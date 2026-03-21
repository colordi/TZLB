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

const emit = defineEmits(["update:pestType", "update:taskType", "update:taskName", "update:records", "submit"]);

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

        <div class="table-actions">
          <button type="button" class="ghost" @click="addRecord">
            新增记录
          </button>
          <button type="button" :disabled="busy" @click="emit('submit')">
            {{ busy ? "正在生成…" : "批量生成工作单" }}
          </button>
        </div>
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
  --table-head-height: 4.25rem;
  --record-row-height: 5.15rem;
  --row-alt: rgba(247, 242, 229, 0.72);
  display: grid;
  gap: 0.85rem;
  padding: 1.15rem;
  border-radius: 1.65rem;
  background:
    radial-gradient(circle at top right, rgba(147, 170, 106, 0.12), transparent 28%),
    linear-gradient(180deg, rgba(249, 245, 235, 0.92), rgba(242, 236, 221, 0.84));
  border: 1px solid rgba(53, 67, 48, 0.11);
  box-shadow: var(--panel-shadow);
}

.table-head {
  display: block;
}

.table-toolbar {
  display: grid;
  grid-template-columns: minmax(160px, 1fr) minmax(190px, 1fr) minmax(210px, 1fr) auto;
  gap: 0.75rem;
  align-items: end;
  padding: 0.95rem;
  border-radius: 1.3rem;
  background: linear-gradient(180deg, rgba(255, 252, 246, 0.78), rgba(247, 242, 229, 0.6));
  border: 1px solid rgba(53, 67, 48, 0.08);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.48);
}

.table-select {
  display: grid;
  gap: 0.35rem;
}

.table-select span {
  font-size: 0.7rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
}

.table-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  justify-content: flex-end;
  padding-left: 0.3rem;
}

.table-actions button {
  min-height: 3.1rem;
}

.table-wrap {
  overflow: hidden;
  border-radius: 1.35rem;
  border: 1px solid rgba(53, 67, 48, 0.08);
  background: rgba(255, 252, 247, 0.82);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.5),
    0 10px 24px rgba(25, 32, 22, 0.05);
}

.table-stage {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 236px;
  gap: 0;
  align-items: start;
}

.table-scroll {
  overflow-x: auto;
  overflow-y: hidden;
  border-right: 1px solid rgba(53, 67, 48, 0.08);
}

.tools-pane {
  overflow: hidden;
  background: rgba(252, 249, 241, 0.78);
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
  background: linear-gradient(180deg, rgba(239, 233, 216, 0.96), rgba(233, 226, 208, 0.9));
  color: var(--ink);
  text-align: left;
  font-size: 0.76rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  border-bottom: 1px solid rgba(53, 67, 48, 0.12);
  backdrop-filter: blur(12px);
}

.survey-table thead th em {
  color: var(--danger);
  font-style: normal;
  margin-left: 0.15rem;
}

.survey-table tbody td,
.tools-table tbody td {
  padding: 0.45rem 0.5rem;
  border-bottom: 1px solid rgba(53, 67, 48, 0.08);
  vertical-align: middle;
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
  min-width: 2.15rem;
  padding: 0.24rem 0.42rem;
  border-radius: 999px;
  background: rgba(123, 107, 51, 0.12);
  color: var(--accent-strong);
  font-size: 0.72rem;
  font-weight: 600;
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
  gap: 0.18rem;
}

.cell-tools-head span {
  display: block;
}

.cell-tools-head small {
  font-size: 0.68rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}

.cell-body {
  height: 100%;
}

.table-input {
  width: 100%;
  min-width: 0;
  min-height: 3.15rem;
  padding: 0.72rem 0.82rem;
  border: 1px solid rgba(53, 67, 48, 0.12);
  border-radius: 0.95rem;
  background: rgba(255, 254, 251, 0.95);
  color: var(--ink);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.42);
  font-size: 0.84rem;
  line-height: 1.3;
}

.table-textarea {
  min-height: calc(var(--record-row-height) - 1rem);
  height: calc(var(--record-row-height) - 1rem);
  padding: 0.78rem 0.9rem;
  resize: none;
  overflow: hidden auto;
  white-space: normal;
  line-height: 1.4;
}

.table-select-input {
  appearance: none;
}

.cell-error .table-input {
  border-color: rgba(180, 62, 37, 0.42);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.42),
    0 0 0 3px rgba(180, 62, 37, 0.08);
}

.row-tools {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 3rem;
  gap: 0.55rem;
  align-items: stretch;
  height: calc(var(--record-row-height) - 0.9rem);
  min-height: calc(var(--record-row-height) - 0.9rem);
  max-height: calc(var(--record-row-height) - 0.9rem);
  padding: 0;
  outline: none;
  overflow: hidden;
}

.thumb-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-template-rows: repeat(2, minmax(0, 1fr));
  gap: 0.35rem;
  align-items: stretch;
  min-width: 0;
  height: 100%;
  min-height: 0;
  max-height: 100%;
  padding: 0.35rem;
  border-radius: 1rem;
  border: 1px solid rgba(53, 67, 48, 0.1);
  background: rgba(255, 251, 244, 0.9);
  outline: none;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.44);
  overflow: hidden;
}

.thumb-strip:focus {
  border-color: rgba(91, 109, 81, 0.28);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.44),
    0 0 0 3px rgba(91, 109, 81, 0.08);
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
  border-radius: 0.8rem;
  overflow: hidden;
  align-self: stretch;
}

.thumb-slot {
  position: relative;
  cursor: pointer;
  border: 1px dashed rgba(53, 67, 48, 0.18);
  background: rgba(255, 252, 247, 0.94);
  color: var(--ink);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.42);
  transition:
    border-color 180ms ease,
    background 180ms ease,
    transform 180ms ease;
}

.thumb-slot input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.thumb-empty {
  color: var(--muted);
  font-size: 1.1rem;
  font-weight: 600;
}

.thumb-slot:hover {
  border-color: rgba(123, 107, 51, 0.45);
  background: rgba(250, 244, 231, 0.96);
  transform: translateY(-1px);
}

.thumb-filled {
  border-style: solid;
  border-color: rgba(53, 67, 48, 0.12);
}

.thumb-filled img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.thumb-remove-mark {
  position: absolute;
  top: 0.14rem;
  right: 0.14rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 0.92rem;
  height: 0.92rem;
  border-radius: 999px;
  background: rgba(28, 34, 23, 0.68);
  color: rgba(255, 252, 247, 0.95);
  font-size: 0.66rem;
  line-height: 1;
}

.table-remove-icon {
  min-height: calc(var(--record-row-height) - 1rem);
  border: 1px solid rgba(180, 62, 37, 0.16);
  background: linear-gradient(180deg, rgba(255, 249, 246, 0.96), rgba(247, 226, 221, 0.9));
  color: rgba(137, 43, 29, 0.92);
  cursor: pointer;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.48);
}

.table-remove-icon svg {
  width: 1rem;
  height: 1rem;
  fill: currentColor;
}

.table-remove-icon:hover,
.table-remove-icon:focus-visible {
  border-color: rgba(180, 62, 37, 0.3);
  background: linear-gradient(180deg, rgba(249, 232, 227, 0.96), rgba(243, 214, 207, 0.92));
  color: var(--danger);
}

.empty-table {
  grid-column: 1 / -1;
  padding: 1.4rem;
  color: var(--muted);
  text-align: center;
  font-size: 0.9rem;
}

@media (max-width: 1080px) {
  .table-heading {
    display: grid;
    align-items: start;
  }

  .table-toolbar {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .table-stage {
    grid-template-columns: minmax(0, 1fr) 236px;
  }
}

@media (max-width: 640px) {
  .table-toolbar {
    grid-template-columns: 1fr;
  }

  .table-actions {
    justify-content: flex-start;
  }
}
</style>
