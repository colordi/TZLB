<script setup>
import { computed, ref } from "vue";

import {
  createEmptyRecord,
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
  busy: {
    type: Boolean,
    default: false,
  },
  errors: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(["update:records"]);

const fields = computed(() => getVisibleFields(props.pestType));
const hasRows = computed(() => props.records.length > 0);
const activeRowIndex = ref(null);

function emitRecords(records) {
  emit(
    "update:records",
    records.map((record) => normalizeRecordForPest(record, props.pestType)),
  );
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
                  <span>现场图片</span>
                  <small>最多4张</small>
                </th>
                <th class="cell-tools-delete">
                  <span>操作</span>
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
                  <div
                    class="thumb-strip"
                    tabindex="0"
                    title="点击空位上传图片，或聚焦后按 Ctrl/Cmd+V 粘贴"
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
                </td>
                <td class="cell-delete">
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
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="!hasRows" class="empty-table">
          当前没有记录，点击左侧"新增记录"开始录入。
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.table-shell {
  --table-head-height: 2.75rem;
  --record-row-height: 3.75rem;
  --row-alt: #f8fafc;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  padding: 0.75rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface-base);
  box-shadow: var(--shadow-card);
}

.table-wrap {
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface-strong);
  flex: 1;
  min-height: 0;
}

.table-stage {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 200px 56px;
  align-items: start;
  height: 100%;
}

.table-scroll {
  overflow-x: auto;
  overflow-y: auto;
  height: 100%;
  border-right: 1px solid var(--border);
}

.tools-pane {
  overflow-y: auto;
  height: 100%;
  background: var(--bg);
  border-right: 1px solid var(--border);
}

.survey-table,
.tools-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}

.survey-table {
  min-width: 1200px;
}

.tools-table {
  table-layout: fixed;
}

.survey-table thead th,
.tools-table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  height: var(--table-head-height);
  padding: 0.625rem 0.5rem;
  background: #f1f5f9;
  color: var(--ink-soft);
  text-align: left;
  font-size: 0.75rem;
  font-weight: 600;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

.survey-table thead th em {
  color: var(--danger);
  font-style: normal;
  margin-left: 0.125rem;
}

.survey-table tbody td,
.tools-table tbody td {
  padding: 0.375rem 0.5rem;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
  background: var(--surface-strong);
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
  width: 56px;
  min-width: 56px;
  text-align: center;
}

.rownum-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 0.75rem;
  font-weight: 600;
}

.cell-tools-head {
  width: 140px;
}

.cell-tools-delete {
  width: 56px;
  text-align: center;
}

.cell-tools-head small {
  display: block;
  font-size: 0.6875rem;
  font-weight: normal;
  color: var(--muted);
}

.cell-tools-body {
  padding: 0.375rem;
}

.cell-delete {
  text-align: center;
  padding: 0.375rem;
}

.table-input {
  width: 100%;
  min-width: 0;
  min-height: 2.25rem;
  padding: 0.4375rem 0.5rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-strong);
  color: var(--ink);
  box-shadow: none;
  font-size: 0.8125rem;
  line-height: 1.4;
}

.table-input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--focus-ring);
}

.table-textarea {
  min-height: calc(var(--record-row-height) - 0.75rem);
  height: calc(var(--record-row-height) - 0.75rem);
  padding: 0.5rem;
  resize: none;
  overflow: hidden auto;
  white-space: normal;
}

.cell-error .table-input {
  border-color: rgba(220, 38, 38, 0.4);
  box-shadow: 0 0 0 2px rgba(220, 38, 38, 0.08);
}

.thumb-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-template-rows: repeat(2, minmax(0, 1fr));
  gap: 0.25rem;
  height: 52px;
  padding: 0.25rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-strong);
  outline: none;
}

.thumb-strip:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--focus-ring);
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
  border-radius: calc(var(--radius-sm) - 1px);
  overflow: hidden;
}

.thumb-slot {
  position: relative;
  cursor: pointer;
  border: 1px dashed var(--border-strong);
  background: var(--bg);
  color: var(--muted);
  box-shadow: none;
}

.thumb-slot input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.thumb-empty {
  color: var(--muted);
  font-size: 0.875rem;
  font-weight: 600;
}

.thumb-slot:hover {
  transform: none;
  border-color: var(--accent);
  background: var(--hover-tint);
}

.thumb-filled {
  border-style: solid;
  border-color: var(--border);
}

.thumb-filled img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-remove-mark {
  position: absolute;
  top: 0.0625rem;
  right: 0.0625rem;
  width: 0.875rem;
  height: 0.875rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: calc(var(--radius-sm) - 1px);
  background: rgba(15, 23, 42, 0.7);
  color: #fff;
  font-size: 0.625rem;
}

.table-remove-icon {
  width: 2rem;
  height: 2rem;
  border: 1px solid rgba(220, 38, 38, 0.15);
  background: rgba(220, 38, 38, 0.05);
  color: var(--danger);
  box-shadow: none;
  cursor: pointer;
  transition: all 150ms ease;
}

.table-remove-icon:hover {
  background: rgba(220, 38, 38, 0.1);
  border-color: rgba(220, 38, 38, 0.25);
}

.table-remove-icon svg {
  width: 1rem;
  height: 1rem;
  fill: currentColor;
}

.empty-table {
  padding: 2rem;
  text-align: center;
  color: var(--muted);
  font-size: 0.875rem;
  grid-column: 1 / -1;
}

@media (max-width: 1024px) {
  .table-stage {
    grid-template-columns: minmax(0, 1fr) 180px 48px;
  }

  .cell-tools-head {
    width: 120px;
  }

  .cell-tools-delete {
    width: 48px;
  }
}

@media (max-width: 760px) {
  .table-shell {
    padding: 0.5rem;
  }

  .table-stage {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto auto;
  }

  .tools-pane {
    border-right: 0;
    border-top: 1px solid var(--border);
  }
}
</style>
