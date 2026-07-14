<script setup>
import { computed, ref } from "vue";

import { getVisibleFields } from "./fieldConfig.js";
import { toggleUidSelection } from "../../composables/workorder/useRecordSelection.js";

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
  busyLabel: {
    type: String,
    default: "正在导出…",
  },
  busyPercent: {
    type: Number,
    default: 0,
  },
  errors: {
    type: Array,
    default: () => [],
  },
  selectedUids: {
    type: Array,
    default: () => [],
  },
  serialOffset: {
    type: Number,
    default: 0,
  },
});

const emit = defineEmits(["row-click", "update:selectedUids"]);

// We only show these four specific columns as requested by the user.
const ALLOWED_KEYS = ["survey_date", "locality", "location_id", "location_name"];

const fields = computed(() => {
  return getVisibleFields(props.pestType).filter((f) => ALLOWED_KEYS.includes(f.key));
});

const hasRows = computed(() => props.records.length > 0);

const isAllSelected = computed(() => {
  return (
    hasRows.value &&
    props.records.every((record) => props.selectedUids.includes(record.__uid))
  );
});

function toggleAll() {
  const visibleUids = props.records.map((record) => record.__uid);
  emit("update:selectedUids", toggleUidSelection(props.selectedUids, visibleUids));
}

function toggleSelection(uid) {
  const current = [...props.selectedUids];
  const pos = current.indexOf(uid);
  if (pos === -1) {
    current.push(uid);
  } else {
    current.splice(pos, 1);
  }
  emit("update:selectedUids", current);
}

function handleRowClick(uid) {
  emit("row-click", uid);
}
</script>

<template>
  <section class="record-workspace panel-card">
    <div v-if="busy" class="record-busy-overlay" aria-live="polite" data-testid="record-busy-overlay">
      <div class="record-busy-card">
        <span class="record-busy-spinner" aria-hidden="true"></span>
        <div class="record-busy-copy">
          <strong>{{ busyLabel || "正在导出…" }}</strong>
          <span v-if="busyPercent > 0" data-testid="record-busy-percent">{{ Math.round(busyPercent) }}%</span>
        </div>
        <div
          class="record-busy-track"
          role="progressbar"
          :aria-valuenow="Math.round(busyPercent)"
          aria-valuemin="0"
          aria-valuemax="100"
          data-testid="record-busy-progress"
        >
          <div class="record-busy-fill" :style="{ width: `${Math.max(0, Math.min(100, busyPercent))}%` }" />
        </div>
      </div>
    </div>
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
            <tr
              v-for="(record, index) in records"
              :key="record.__uid"
              class="clickable-row"
              @click="handleRowClick(record.__uid)"
            >
              <td class="cell-checkbox" @click.stop>
                <input
                  type="checkbox"
                  class="cb-custom"
                  :checked="selectedUids.includes(record.__uid)"
                  @change="toggleSelection(record.__uid)"
                />
              </td>
              <td class="cell-serial">
                <span class="serial-badge">{{ String(serialOffset + index + 1).padStart(2, "0") }}</span>
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
        :key="`mobile-${record.__uid}`"
        class="mobile-card"
        @click="handleRowClick(record.__uid)"
      >
        <header class="mobile-card-head">
          <div class="mobile-card-meta">
            <div @click.stop class="mobile-checkbox-wrap">
              <input
                type="checkbox"
                class="cb-custom"
                :checked="selectedUids.includes(record.__uid)"
                @change="toggleSelection(record.__uid)"
              />
            </div>
            <span class="serial-badge">{{ String(serialOffset + index + 1).padStart(2, "0") }}</span>
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
  position: relative;
  overflow: hidden;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.record-busy-overlay {
  position: absolute;
  inset: 0;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in oklch, var(--color-surface) 72%, transparent);
  backdrop-filter: blur(2px);
}

.record-busy-card {
  width: min(360px, calc(100% - 2rem));
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 8px 12px;
  align-items: center;
  padding: 14px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  color: var(--color-ink);
  font-size: var(--text-sm);
}

.record-busy-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid color-mix(in oklch, var(--color-primary) 24%, transparent);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: record-busy-spin 0.7s linear infinite;
}

.record-busy-copy {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
}

.record-busy-copy strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-busy-copy span {
  flex: 0 0 auto;
  color: var(--color-primary);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.record-busy-track {
  grid-column: 1 / -1;
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: color-mix(in oklch, var(--color-primary) 12%, var(--color-bg));
}

.record-busy-fill {
  height: 100%;
  border-radius: inherit;
  background: var(--color-primary);
  transition: width 160ms ease;
}

@keyframes record-busy-spin {
  to { transform: rotate(360deg); }
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
  min-width: 920px;
  border-collapse: collapse;
  font-size: var(--text-md);
}

.record-table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--color-border);
  background: color-mix(in oklch, var(--color-bg) 60%, var(--color-surface));
  color: var(--color-muted);
  text-align: left;
  font-family: var(--font-mono);
  font-size: var(--text-2xs);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 700;
  white-space: nowrap;
}

.record-table thead th em {
  margin-left: 0.15rem;
  color: var(--color-danger);
  font-style: normal;
}

.record-table tbody tr {
  cursor: pointer;
  transition:
    background var(--motion-base) ease,
    transform var(--motion-base) ease;
}

.record-table tbody tr:hover {
  transform: none;
  box-shadow: none;
}

.record-table tbody td {
  padding: 11px var(--space-6);
  border-bottom: 1px solid color-mix(in oklch, var(--color-border) 60%, transparent);
  vertical-align: middle;
  background: var(--color-surface);
  transition: background-color 0.2s;
}

.record-table tbody tr:hover td {
  background: color-mix(in oklch, var(--color-primary) 3%, var(--color-surface));
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
  width: 14px;
  min-width: 14px;
  height: 14px;
  min-height: 14px;
  padding: 0;
  accent-color: var(--color-accent);
  cursor: pointer;
  margin: 0;
  box-shadow: none;
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

.cell-locality {
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
  min-width: 2.35rem;
  height: 2rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 var(--space-3);
  border-radius: var(--radius-pill);
  background: var(--color-primary-soft);
  color: var(--color-muted);
  font-weight: 700;
  font-size: var(--text-xs);
  letter-spacing: 0.02em;
}

.cell-text-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  min-height: 2rem;
  padding: 0;
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
  padding: var(--space-6);
  border-bottom: 1px solid var(--color-border);
  border-radius: 0;
  background: var(--color-surface);
  box-shadow: none;
  cursor: pointer;
  transition: transform var(--motion-fast) var(--ease-standard), box-shadow var(--motion-fast) var(--ease-standard);
}

.mobile-card:hover {
  transform: none;
  box-shadow: none;
  background: color-mix(in oklch, var(--color-primary) 3%, var(--color-surface));
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
    border-radius: var(--radius-lg);
  }

  .mobile-card-head {
    flex-direction: column;
  }


}
</style>
