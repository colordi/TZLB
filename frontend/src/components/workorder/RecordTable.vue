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
const { info, success } = useToast();

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
  info(`第 ${index + 1} 条记录已删除。`, "记录已更新");
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
                <select
                  v-if="field.type === 'select'"
                  class="table-input"
                  :disabled="busy"
                  :value="record[field.key]"
                  :title="errors[index]?.[field.key] || ''"
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
                  :title="errors[index]?.[field.key] || ''"
                  @input="updateCell(index, field, $event.target.value)"
                  @paste="handleCellPaste(index, field, $event)"
                />

                <input
                  v-else
                  class="table-input"
                  :disabled="busy"
                  :type="field.type"
                  :value="record[field.key]"
                  :title="errors[index]?.[field.key] || ''"
                  @input="updateCell(index, field, $event.target.value)"
                  @paste="handleCellPaste(index, field, $event)"
                />
              </td>

              <td class="cell-images">
                <button
                  type="button"
                  class="image-trigger button-secondary"
                  :disabled="busy"
                  :data-testid="`open-image-dialog-${index}`"
                  @click="openImageDialog(index)"
                >
                  <span v-if="record.images?.[0]" class="image-thumb">
                    <img :src="record.images[0]" alt="" />
                  </span>
                  <span v-else class="image-thumb is-empty">+</span>
                  <span class="image-copy">
                    <strong>{{ record.images?.length || 0 }}/4</strong>
                    <small>上传 / 预览</small>
                  </span>
                </button>
              </td>

              <td class="cell-actions">
                <button
                  type="button"
                  class="row-action button-secondary"
                  :disabled="busy"
                  :data-testid="`duplicate-record-${index}`"
                  @click="duplicateRecord(index)"
                >
                  复制
                </button>
                <button
                  type="button"
                  class="row-action button-danger"
                  :disabled="busy"
                  :data-testid="`delete-record-${index}`"
                  @click="removeRecord(index)"
                >
                  删除
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
  min-width: 1100px;
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
  padding: 0.6rem 0.5rem;
  border-bottom: 1px solid rgba(46, 125, 50, 0.1);
  vertical-align: middle;
  background: rgba(255, 255, 255, 0.94);
}

.record-table tbody tr:nth-child(2n) td {
  background: rgba(248, 252, 247, 0.95);
}

.cell-serial {
  width: 5rem;
  min-width: 5rem;
}

.cell-images {
  width: 8.5rem;
  min-width: 8.5rem;
}

.cell-actions {
  width: 8rem;
  min-width: 8rem;
}

/* 字段列宽度定义 */
.cell-survey_date {
  width: 7.5rem;
  min-width: 7.5rem;
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
  width: 7.5rem;
  min-width: 7.5rem;
}

.cell-description {
  width: 12rem;
  min-width: 12rem;
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
  min-height: 2.85rem;
  height: 2.85rem;
  resize: none;
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

.image-trigger {
  width: 100%;
  min-height: 2.85rem;
  height: 2.85rem;
  justify-content: flex-start;
  padding: 0.4rem 0.52rem;
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
  font-size: 1.4rem;
  font-weight: 700;
  transition: transform 200ms ease;
}

.image-trigger:hover .image-thumb {
  transform: scale(1.05);
}

.image-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.image-copy strong {
  color: var(--color-ink);
  font-size: 0.92rem;
}

.image-copy small {
  color: var(--color-muted);
  font-size: 0.78rem;
}

.row-action {
  width: 100%;
  min-height: 2.85rem;
  border-radius: 14px;
  font-size: 0.84rem;
}

.cell-actions {
  display: grid;
  gap: 0.55rem;
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
