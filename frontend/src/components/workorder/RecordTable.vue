<script setup>
import { computed, ref } from "vue";

import { getVisibleFields } from "./fieldConfig.js";

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
  selectedIndexes: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(["row-click", "update:selectedIndexes"]);

// We only show these four specific columns as requested by the user.
const ALLOWED_KEYS = ["survey_date", "town_or_street", "location_id", "location_name"];

const fields = computed(() => {
  return getVisibleFields(props.pestType).filter((f) => ALLOWED_KEYS.includes(f.key));
});

const hasRows = computed(() => props.records.length > 0);

const isAllSelected = computed(() => {
  return hasRows.value && props.selectedIndexes.length === props.records.length;
});

function toggleAll() {
  if (isAllSelected.value) {
    emit("update:selectedIndexes", []);
  } else {
    emit("update:selectedIndexes", props.records.map((_, i) => i));
  }
}

function toggleSelection(index) {
  const current = [...props.selectedIndexes];
  const pos = current.indexOf(index);
  if (pos === -1) {
    current.push(index);
  } else {
    current.splice(pos, 1);
  }
  emit("update:selectedIndexes", current);
}

function handleRowClick(index) {
  emit("row-click", index);
}
</script>

<template>
  <section class="record-workspace panel-card">
    <div v-if="hasRows" class="desktop-records">
      <div class="table-scroll">
        <table class="record-table">
          <thead>
            <tr>
              <th class="cell-checkbox">
                <input type="checkbox" class="cb-custom" :checked="isAllSelected" @change="toggleAll" />
              </th>
              <th class="cell-serial">序号</th>
              <th
                v-for="field in fields"
                :key="field.key"
                :class="['cell-head', `cell-${field.key}`]"
              >
                {{ field.label }}
              </th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="(record, index) in records" :key="index" @click="handleRowClick(index)" class="clickable-row">
              <td class="cell-checkbox" @click.stop>
                <input type="checkbox" class="cb-custom" :checked="selectedIndexes.includes(index)" @change="toggleSelection(index)" />
              </td>
              <td class="cell-serial">
                <span class="serial-badge">{{ String(index + 1).padStart(2, "0") }}</span>
              </td>

              <td
                v-for="field in fields"
                :key="field.key"
                :class="['cell-body', { 'cell-error': errors[index]?.[field.key] }]"
              >
                <div class="cell-text-wrap" :class="{ 'has-error': errors[index]?.[field.key] }">
                  <span class="readonly-text">{{ record[field.key] || '-' }}</span>
                  <span v-if="errors[index]?.[field.key]" class="cell-error-indicator">
                    <!-- show exclamation icon if error -->
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="var(--color-danger)">
                      <circle cx="12" cy="12" r="10" opacity="0.2"/>
                      <path d="M12 7v5M12 16h.01" stroke="var(--color-danger)" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                  </span>
                </div>
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
        @click="handleRowClick(index)"
      >
        <header class="mobile-card-head">
          <div class="mobile-card-meta">
            <div @click.stop class="mobile-checkbox-wrap">
              <input type="checkbox" class="cb-custom" :checked="selectedIndexes.includes(index)" @change="toggleSelection(index)"/>
            </div>
            <span class="serial-badge">{{ String(index + 1).padStart(2, "0") }}</span>
            <div>
              <strong>{{ record.location_name || `现场记录 ${index + 1}` }}</strong>
              <p>{{ record.survey_date || '未填写日期' }}</p>
            </div>
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
            <div class="readonly-text">{{ record[field.key] || '-' }}</div>
          </div>
        </div>
      </article>
    </div>

    <div v-if="!hasRows" class="empty-state">
      <strong>当前单子为空</strong>
      <p>请点击“导入调查数据”选取记录导入工作单。</p>
    </div>
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
  border: none;
  background: transparent;
}

.record-table {
  width: 100%;
  min-width: 1100px; /* Reduced min-width slightly since columns are removed */
  border-collapse: separate;
  border-spacing: 0 4px; /* Reduced vertical spacing to make it more compact */
}

.record-table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: 1rem 0.8rem;
  background: var(--color-surface-container);
  color: var(--color-muted);
  text-align: left;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 700;
  white-space: nowrap;
  border: none;
}

.record-table thead th em {
  margin-left: 0.15rem;
  color: var(--color-danger);
  font-style: normal;
}

.record-table tbody tr {
  cursor: pointer;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s;
}

.record-table tbody tr:hover {
  transform: translateY(-1px);
  box-shadow: var(--elev-ring);
}

.record-table tbody td {
  padding: 0.5rem 0.75rem; /* Reduced padding for compactness */
  vertical-align: middle; /* Center vertically for cleaner rows */
  background: var(--color-surface-container-lowest);
  border: none;
  transition: background-color 0.2s;
}

.record-table tbody tr:hover td {
  background: var(--color-surface-container-low);
}

/* Rounded corners for the row segments */
.record-table tbody td:first-child {
  border-top-left-radius: var(--radius-sm);
  border-bottom-left-radius: var(--radius-sm);
}

.record-table tbody td:last-child {
  border-top-right-radius: var(--radius-sm);
  border-bottom-right-radius: var(--radius-sm);
}

.cell-serial {
  width: 4.5rem;
  min-width: 4.5rem;
}

.cell-checkbox {
  width: 3rem;
  min-width: 3rem;
  padding-left: 1rem !important; /* Visual spacing for checkbox */
}

.cb-custom {
  width: 1.15rem;
  height: 1.15rem;
  accent-color: var(--color-accent);
  cursor: pointer;
  margin: 0;
}

.mobile-checkbox-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 0.25rem;
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
  border-radius: var(--radius-pill);
  background: var(--color-surface-container);
  color: var(--color-muted);
  font-weight: 700;
  font-size: var(--text-sm);
  letter-spacing: 0.02em;
}

.cell-text-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  min-height: 2rem;
  padding: var(--space-2) 0.5rem;
}

.readonly-text {
  font-family: var(--font-body);
  font-size: var(--text-sm);
  color: var(--color-ink);
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cell-error-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
}



.mobile-records {
  display: none;
}

.mobile-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.25rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--elev-ring);
  cursor: pointer;
  transition: transform var(--motion-fast) var(--ease-standard), box-shadow var(--motion-fast) var(--ease-standard);
}

.mobile-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--elev-raised);
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


}
</style>
