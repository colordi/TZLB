<script setup>
import { computed, ref } from "vue";

import { useToast } from "../../composables/useToast.js";
import ImageUploadDialog from "./ImageUploadDialog.vue";
import {
  createEmptyRecord,
  getVisibleFields,
  normalizeInputValue,
  normalizeRecordForPest,
  parseClipboardGrid,
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
const { success } = useToast();

const fields = computed(() => getVisibleFields(props.pestType));
const hasRows = computed(() => props.records.length > 0);
const activeImageRecordIndex = ref(-1);

const activeImageRecord = computed(() => props.records[activeImageRecordIndex.value] || null);

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

function duplicateRecord(index) {
  const source = normalizeRecordForPest(props.records[index], props.pestType);
  const next = props.records.slice();
  next.splice(index + 1, 0, {
    ...source,
    images: Array.isArray(source.images) ? source.images.slice() : [],
  });
  emitRecords(next);
  success(`已复制第 ${index + 1} 条记录。`, "记录已复制");
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

  const grid = parseClipboardGrid(text);
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

function openImageDialog(index) {
  activeImageRecordIndex.value = index;
}

function closeImageDialog() {
  activeImageRecordIndex.value = -1;
}

function updateImages(images) {
  if (activeImageRecordIndex.value < 0) {
    return;
  }

  updateRecord(activeImageRecordIndex.value, {
    ...props.records[activeImageRecordIndex.value],
    images,
  });
}
</script>

<template>
  <section class="record-workspace panel-card">
    <div v-if="hasRows" class="desktop-records">
      <div class="table-scroll">
        <table class="record-table">
          <thead>
            <tr>
              <th class="cell-serial">序号</th>
              <th
                v-for="field in fields"
                :key="field.key"
                :class="['cell-head', `cell-${field.key}`]"
              >
                {{ field.label }}
                <em v-if="field.required">*</em>
              </th>
              <th class="cell-images">现场图片</th>
              <th class="cell-actions">操作</th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="(record, index) in records" :key="index">
              <td class="cell-serial">
                <span class="serial-badge">{{ String(index + 1).padStart(2, "0") }}</span>
              </td>

              <td
                v-for="field in fields"
                :key="field.key"
                :class="['cell-body', { 'cell-error': errors[index]?.[field.key] }]"
              >
                <div class="cell-input-wrap">
                  <select
                    v-if="field.type === 'select'"
                    class="table-input"
                    :disabled="busy"
                    :value="record[field.key]"
                    @change="updateCell(index, field, $event.target.value)"
                    @paste="handleCellPaste(index, field, $event)"
                  >
                    <option value="">请选择</option>
                    <option v-for="option in field.options" :key="option" :value="option">
                      {{ option }}
                    </option>
                  </select>

                  <textarea
                    v-else-if="field.type === 'textarea'"
                    class="table-input table-textarea"
                    :disabled="busy"
                    :value="record[field.key]"
                    @input="updateCell(index, field, $event.target.value)"
                    @paste="handleCellPaste(index, field, $event)"
                  />

                  <input
                    v-else
                    class="table-input"
                    :disabled="busy"
                    :type="field.type"
                    :value="record[field.key]"
                    @input="updateCell(index, field, $event.target.value)"
                    @paste="handleCellPaste(index, field, $event)"
                  />

                  <span v-if="errors[index]?.[field.key]" class="cell-error-msg">
                    {{ errors[index][field.key] }}
                  </span>
                </div>
              </td>

              <td class="cell-images">
                <button
                  type="button"
                  class="image-trigger button-secondary"
                  :disabled="busy"
                  :title="`管理现场图片（${record.images?.length || 0}/4）`"
                  :data-testid="`open-image-dialog-${index}`"
                  @click="openImageDialog(index)"
                >
                  <span class="image-thumb-wrap">
                    <span v-if="record.images?.[0]" class="image-thumb">
                      <img :src="record.images[0]" alt="" />
                    </span>
                    <span v-else class="image-thumb is-empty">
                      <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                        <path d="M3.75 6A2.75 2.75 0 0 1 6.5 3.25h11A2.75 2.75 0 0 1 20.25 6v12A2.75 2.75 0 0 1 17.5 20.75h-11A2.75 2.75 0 0 1 3.75 18V6Zm2.75-1.25c-.69 0-1.25.56-1.25 1.25v8.69l3.22-3.22a.75.75 0 0 1 1.06 0l2.47 2.47 1.72-1.72a.75.75 0 0 1 1.06 0l2.97 2.97V6c0-.69-.56-1.25-1.25-1.25h-11Zm11 13.5c.69 0 1.25-.56 1.25-1.25v-.19l-3.5-3.5-1.72 1.72a.75.75 0 0 1-1.06 0l-2.47-2.47-3.75 3.75c.19.89.98 1.69 1.75 1.69h9.5Zm-6.5-8a1.5 1.5 0 1 0 3 0 1.5 1.5 0 0 0-3 0Z"/>
                      </svg>
                    </span>
                    <span v-if="record.images?.length" class="image-count-badge">
                      {{ record.images.length }}
                    </span>
                  </span>
                </button>
              </td>

              <td class="cell-actions">
                <button
                  type="button"
                  class="row-action button-secondary"
                  title="复制记录"
                  :disabled="busy"
                  :data-testid="`duplicate-record-${index}`"
                  @click="duplicateRecord(index)"
                >
                  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M8 4.25A2.75 2.75 0 0 0 5.25 7v9.25c0 .41.34.75.75.75s.75-.34.75-.75V7c0-.69.56-1.25 1.25-1.25h6.25a.75.75 0 0 0 0-1.5H8ZM10 8.75A2.75 2.75 0 0 0 7.25 11.5v5.75A2.75 2.75 0 0 0 10 20h6A2.75 2.75 0 0 0 18.75 17.25V11.5A2.75 2.75 0 0 0 16 8.75h-6Zm-1.25 2.75c0-.69.56-1.25 1.25-1.25h6c.69 0 1.25.56 1.25 1.25v5.75c0 .69-.56 1.25-1.25 1.25h-6c-.69 0-1.25-.56-1.25-1.25V11.5Z"/>
                  </svg>
                </button>
                <button
                  type="button"
                  class="row-action button-danger"
                  title="删除记录"
                  :disabled="busy"
                  :data-testid="`delete-record-${index}`"
                  @click="removeRecord(index)"
                >
                  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M10.25 4.75A.75.75 0 0 1 11 4h2a.75.75 0 0 1 .75.75V6h3.75a.75.75 0 0 1 0 1.5H6.5a.75.75 0 0 1 0-1.5h3.75v-1.25ZM7.28 9.25a.75.75 0 0 1 .79.71l.68 9H15.25l.68-9a.75.75 0 0 1 1.49.12l-.69 9A2.25 2.25 0 0 1 14.5 21h-5a2.25 2.25 0 0 1-2.24-2.13l-.69-9a.75.75 0 0 1 .71-.79Z"/>
                  </svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="hasRows" class="mobile-records">
      <article
        v-for="(record, index) in records"
        :key="`mobile-${index}`"
        class="mobile-card"
      >
        <header class="mobile-card-head">
          <div class="mobile-card-meta">
            <span class="serial-badge">{{ String(index + 1).padStart(2, "0") }}</span>
            <div>
              <strong>现场记录 {{ index + 1 }}</strong>
              <p>{{ record.images?.length || 0 }} 张图片</p>
            </div>
          </div>

          <div class="mobile-card-actions">
            <button
              type="button"
              class="row-action button-secondary"
              :disabled="busy"
              @click="duplicateRecord(index)"
            >
              复制
            </button>
            <button
              type="button"
              class="row-action button-danger"
              :disabled="busy"
              @click="removeRecord(index)"
            >
              删除
            </button>
          </div>
        </header>

        <div class="mobile-fields">
          <div
            v-for="field in fields"
            :key="field.key"
            class="field-block"
            :class="{ 'field-error': errors[index]?.[field.key] }"
          >
            <label>{{ field.label }}<span v-if="field.required">*</span></label>

            <select
              v-if="field.type === 'select'"
              :disabled="busy"
              :value="record[field.key]"
              @change="updateCell(index, field, $event.target.value)"
              @paste="handleCellPaste(index, field, $event)"
            >
              <option value="">请选择</option>
              <option v-for="option in field.options" :key="option" :value="option">
                {{ option }}
              </option>
            </select>

            <textarea
              v-else-if="field.type === 'textarea'"
              :disabled="busy"
              :value="record[field.key]"
              @input="updateCell(index, field, $event.target.value)"
              @paste="handleCellPaste(index, field, $event)"
            />

            <input
              v-else
              :disabled="busy"
              :type="field.type"
              :value="record[field.key]"
              @input="updateCell(index, field, $event.target.value)"
              @paste="handleCellPaste(index, field, $event)"
            />
          </div>
        </div>

        <button type="button" class="mobile-image-button button-secondary" @click="openImageDialog(index)">
          管理现场图片
        </button>
      </article>
    </div>

    <div v-if="!hasRows" class="empty-state">
      <strong>当前还没有记录</strong>
      <p>点击上方“新增记录”开始录入第一条现场信息。</p>
    </div>

    <ImageUploadDialog
      :busy="busy"
      :images="activeImageRecord?.images || []"
      :open="activeImageRecordIndex >= 0"
      :record-label="`记录 ${activeImageRecordIndex + 1}`"
      @close="closeImageDialog"
      @update:images="updateImages"
    />
  </section>
</template>

<style scoped>
.record-workspace {
  padding: 1rem;
}

.desktop-records,
.table-scroll {
  min-height: 0;
}

.table-scroll {
  overflow: auto;
  border: 1px solid rgba(46, 125, 50, 0.12);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.98);
}

.record-table {
  width: 100%;
  min-width: 1300px;
  border-collapse: separate;
  border-spacing: 0;
}

.record-table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: 1rem 0.8rem;
  background: linear-gradient(180deg, rgba(236, 249, 238, 0.98), rgba(228, 246, 230, 0.96));
  color: var(--color-primary-strong);
  text-align: left;
  font-size: var(--text-sm);
  font-weight: 800;
  white-space: nowrap;
  border-bottom: 1px solid var(--color-line);
}

.record-table thead th em {
  margin-left: 0.15rem;
  color: var(--color-danger);
  font-style: normal;
}

.record-table tbody td {
  padding: 0.55rem 0.75rem;
  border-bottom: 1px solid rgba(46, 125, 50, 0.1);
  vertical-align: top;
  background: rgba(255, 255, 255, 0.94);
}

.record-table tbody tr:nth-child(2n) td {
  background: rgba(240, 249, 238, 0.9);
}

.cell-serial {
  width: 5rem;
  min-width: 5rem;
  padding-top: 0.8rem;
}

.cell-images {
  width: 4.5rem;
  min-width: 4.5rem;
  text-align: center;
}

.cell-actions {
  width: 6rem;
  min-width: 6rem;
  position: sticky;
  right: 0;
  z-index: 2;
  vertical-align: middle;
}

/* 字段列宽度定义 */
.cell-survey_date {
  width: 8.5rem;
  min-width: 8.5rem;
}

.cell-region {
  width: 6rem;
  min-width: 6rem;
}

.cell-town_or_street {
  width: 9rem;
  min-width: 9rem;
}

.cell-location_id {
  width: 7rem;
  min-width: 7rem;
}

.cell-location_name {
  width: 10rem;
  min-width: 10rem;
}

.cell-note {
  width: 9rem;
  min-width: 9rem;
}

.cell-occurrence_position {
  width: 9rem;
  min-width: 9rem;
}

.cell-total_insect_count {
  width: 6.5rem;
  min-width: 6.5rem;
}

.cell-damage_level {
  width: 6rem;
  min-width: 6rem;
}

.cell-pest_name {
  width: 7rem;
  min-width: 7rem;
}

.cell-host_plant {
  width: 7rem;
  min-width: 7rem;
}

.cell-plot_type {
  width: 7rem;
  min-width: 7rem;
}

.cell-report_time {
  width: 8.5rem;
  min-width: 8.5rem;
}

.cell-description {
  width: 16rem;
  min-width: 16rem;
}

.serial-badge {
  width: 2.7rem;
  height: 2.7rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: rgba(46, 125, 50, 0.13);
  color: var(--color-primary-strong);
  font-weight: 800;
  letter-spacing: 0.02em;
}

.table-input {
  width: 100%;
  min-height: 2.85rem;
  padding: var(--space-3) 0.85rem;
  border: 1.5px solid var(--color-line);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.98);
  font-size: var(--text-sm);
  box-shadow: none;
  transition: all 200ms ease;
}

.table-input:hover {
  border-color: var(--color-line-strong);
  background: #ffffff;
}

.table-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(46, 125, 50, 0.15);
  background: #ffffff;
}

.table-textarea {
  min-height: 5rem;
  height: 5rem;
  resize: vertical;
}

.cell-error :is(.table-input, input, select, textarea),
.field-error :is(input, select, textarea) {
  border-color: var(--color-danger);
  background: rgba(211, 84, 48, 0.05);
}

.cell-error :is(.table-input, input, select, textarea):focus,
.field-error :is(input, select, textarea):focus {
  box-shadow: 0 0 0 3px rgba(211, 84, 48, 0.15);
}

.cell-input-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.cell-error-msg {
  color: var(--color-danger);
  font-size: 0.72rem;
  font-weight: 600;
  line-height: 1;
  padding-left: 0.15rem;
}

.image-trigger {
  width: 2.85rem;
  height: 2.85rem;
  min-height: 0;
  padding: 0.3rem;
  justify-content: center;
}

.image-thumb-wrap {
  position: relative;
  display: inline-flex;
  flex-shrink: 0;
}

.image-thumb {
  width: 2.2rem;
  height: 2.2rem;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  overflow: hidden;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(46, 125, 50, 0.1);
  color: var(--color-primary);
  transition: transform 200ms ease;
}

.image-thumb svg {
  width: 1.1rem;
  height: 1.1rem;
}

.image-trigger:hover .image-thumb {
  transform: scale(1.08);
}

.image-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-count-badge {
  position: absolute;
  top: -0.3rem;
  right: -0.3rem;
  min-width: 1rem;
  height: 1rem;
  padding: 0 0.2rem;
  border-radius: 999px;
  background: var(--color-primary);
  color: #fff;
  font-size: 0.62rem;
  font-weight: 800;
  line-height: 1rem;
  text-align: center;
  pointer-events: none;
}

.row-action {
  width: 2.5rem;
  height: 2.5rem;
  min-height: 0;
  padding: 0;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.row-action svg {
  width: 1rem;
  height: 1rem;
  pointer-events: none;
}

.cell-actions {
  display: flex;
  flex-direction: row;
  gap: 0.4rem;
  align-items: center;
  justify-content: center;
}

.record-table thead th.cell-actions {
  background: linear-gradient(180deg, #ecf9ee, #e4f6e6);
  box-shadow: -1px 0 0 var(--color-line);
}

.record-table tbody td.cell-actions {
  background: #ffffff;
  box-shadow: -1px 0 0 rgba(46, 125, 50, 0.1);
}

.record-table tbody tr:nth-child(2n) td.cell-actions {
  background: #f0f9ee;
}

.mobile-records {
  display: none;
}

.mobile-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid rgba(46, 125, 50, 0.12);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
}

.mobile-card-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.mobile-card-meta {
  display: flex;
  gap: 0.8rem;
  align-items: center;
}

.mobile-card-meta strong {
  display: block;
}

.mobile-card-meta p {
  color: var(--color-muted);
  font-size: 0.84rem;
}

.mobile-card-actions {
  display: flex;
  gap: 0.5rem;
}

.mobile-fields {
  display: grid;
  gap: 0.9rem;
}

.mobile-fields label {
  color: var(--color-muted);
  font-size: 0.86rem;
  font-weight: 700;
}

.mobile-fields label span {
  margin-left: 0.15rem;
  color: var(--color-danger);
}

.mobile-image-button {
  width: 100%;
}

.empty-state {
  min-height: 15rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  text-align: center;
  color: var(--color-muted);
}

@media (max-width: 900px) {
  .desktop-records {
    display: none;
  }

  .mobile-records {
    display: grid;
    gap: 0.9rem;
  }
}

@media (max-width: 640px) {
  .record-workspace {
    padding: 0.85rem;
  }

  .mobile-card-head {
    flex-direction: column;
  }

  .mobile-card-actions {
    width: 100%;
  }

  .mobile-card-actions .row-action {
    flex: 1;
  }
}
</style>
