<script setup>
import { computed, ref, watch } from "vue";
import {
  CalendarDays,
  ChevronDown,
  LoaderCircle,
  Lock,
  Search,
  SearchX,
  X,
} from "@lucide/vue";

import { isUnauthorizedError } from "../../api/http.js";
import { fetchSurveyCandidates } from "../../api/survey.js";
import { useToast } from "../../composables/useToast.js";
import { useWorkorderTaskConfig } from "../../composables/workorder/useWorkorderTaskConfig.js";
import { getSurveyImportConfig, getTodayDate } from "./fieldConfig.js";
import BaseDialog from "./BaseDialog.vue";
import { DatePickerField } from "@/components/ui/date-picker";

const props = defineProps({
  busy: {
    type: Boolean,
    default: false,
  },
  open: {
    type: Boolean,
    default: false,
  },
  /** 页面已锁定的任务；有值时弹窗只读展示并沿用 */
  lockedTask: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(["close", "import"]);
const { error, info } = useToast();

const taskConfig = useWorkorderTaskConfig();
const {
  PEST_OPTIONS,
  pestType,
  year,
  taskName,
  generation,
  taskOptions,
  yearOptions,
  canImportSurvey,
} = taskConfig;

const selectedDate = ref(getTodayDate());
const loading = ref(false);
const queried = ref(false);
const candidates = ref([]);
const selectedCandidateKeys = ref([]);

const taskLocked = computed(() => Boolean(props.lockedTask));
const totalCount = computed(() => candidates.value.length);
const selectedCount = computed(() => selectedCandidateKeys.value.length);
const hasCandidates = computed(() => totalCount.value > 0);
const allSelected = computed(() => hasCandidates.value && selectedCount.value === totalCount.value);
const canImport = computed(
  () =>
    !props.busy &&
    !loading.value &&
    selectedCount.value > 0 &&
    canImportSurvey.value &&
    Boolean(taskName.value),
);
const surveyImportConfig = computed(() => getSurveyImportConfig(pestType.value));
const dialogDescription = computed(() => surveyImportConfig.value.description);
const idleHint = computed(() => surveyImportConfig.value.idleHint);
const candidateColumns = computed(() => surveyImportConfig.value.columns);

function getCandidateKey(candidate) {
  return surveyImportConfig.value.candidateKeyFields
    .map((key) => candidate[key] || "")
    .join("-");
}

function isCandidateSelected(candidate) {
  return selectedCandidateKeys.value.includes(getCandidateKey(candidate));
}

function formatCandidateValue(candidate, column) {
  const value = candidate[column.key];
  if (value === null || value === undefined) {
    return column.fallback;
  }

  const text = `${value}`.trim();
  return text === "" ? column.fallback : text;
}

function applyLockedTask() {
  if (!props.lockedTask) {
    return;
  }
  pestType.value = props.lockedTask.pestType;
  year.value = props.lockedTask.year;
  taskName.value = props.lockedTask.taskName;
}

function resetDialogState() {
  selectedDate.value = getTodayDate();
  loading.value = false;
  queried.value = false;
  candidates.value = [];
  selectedCandidateKeys.value = [];
  if (props.lockedTask) {
    applyLockedTask();
  } else {
    taskConfig.resetTaskName();
  }
}

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      resetDialogState();
    }
  },
);

watch([pestType, year, taskName], () => {
  if (!props.open) {
    return;
  }
  queried.value = false;
  candidates.value = [];
  selectedCandidateKeys.value = [];
});

async function handleQuery() {
  if (!selectedDate.value) {
    info("请先选择调查日期。", "缺少查询条件");
    return;
  }

  loading.value = true;

  try {
    const result = await fetchSurveyCandidates({
      date: selectedDate.value,
      pestType: pestType.value,
      year: year.value,
      generation: generation.value,
    });
    candidates.value = Array.isArray(result) ? result : [];
    selectedCandidateKeys.value = candidates.value.map((candidate) => getCandidateKey(candidate));
    queried.value = true;

    if (candidates.value.length === 0) {
      info("所选日期没有可导入的调查记录。", "暂无数据");
    }
  } catch (queryError) {
    if (isUnauthorizedError(queryError)) {
      return;
    }
    error(`${queryError.message || queryError}`, "查询调查记录失败");
  } finally {
    loading.value = false;
  }
}

function toggleSelectAll() {
  selectedCandidateKeys.value = allSelected.value
    ? []
    : candidates.value.map((candidate) => getCandidateKey(candidate));
}

function updateCandidateSelection(candidate, checked) {
  const candidateKey = getCandidateKey(candidate);
  const selection = new Set(selectedCandidateKeys.value);

  if (checked) {
    selection.add(candidateKey);
  } else {
    selection.delete(candidateKey);
  }

  selectedCandidateKeys.value = Array.from(selection);
}

function handleImport() {
  const selectedKeySet = new Set(selectedCandidateKeys.value);
  const selectedRecords = candidates.value.filter((candidate) =>
    selectedKeySet.has(getCandidateKey(candidate)),
  );

  if (!selectedRecords.length) {
    info("请至少选择一条调查记录。", "没有可导入项");
    return;
  }

  emit("import", {
    records: selectedRecords,
    task: {
      pestType: pestType.value,
      year: year.value,
      taskName: taskName.value,
      generation: generation.value,
    },
  });
}
</script>

<template>
  <BaseDialog
    :open="open"
    aria-label="从数据库导入"
    mask-class="survey-import-mask"
    dialog-class="survey-import-dialog"
    @close="emit('close')"
  >
    <header class="sid-head">
      <div class="sid-head-copy">
        <h3>从数据库导入</h3>
        <p>{{ dialogDescription }}</p>
      </div>
      <button
        data-slot="icon-button"
        type="button"
        class="sid-icon-btn"
        aria-label="关闭"
        @click="emit('close')"
      >
        <X :size="14" />
      </button>
    </header>

    <div class="sid-body">
      <section class="sid-filters" data-testid="survey-import-task-panel" aria-label="任务配置">
        <label class="sid-field" for="survey-import-pest-type">
          <span class="sid-field-label">害虫类型</span>
          <span class="sid-select-wrap">
            <select
              data-slot="native-select"
              id="survey-import-pest-type"
              v-model="pestType"
              :disabled="loading || taskLocked"
              data-testid="survey-import-pest-type"
            >
              <option v-for="option in PEST_OPTIONS" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
            <ChevronDown class="sid-select-icon" :size="13" />
          </span>
        </label>
        <label class="sid-field" for="survey-import-year">
          <span class="sid-field-label">年份</span>
          <span class="sid-select-wrap">
            <select
              data-slot="native-select"
              id="survey-import-year"
              v-model="year"
              :disabled="loading || taskLocked"
              data-testid="survey-import-year"
            >
              <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}</option>
            </select>
            <ChevronDown class="sid-select-icon" :size="13" />
          </span>
        </label>
        <label class="sid-field" for="survey-import-task-name">
          <span class="sid-field-label">统防统治任务</span>
          <span class="sid-select-wrap">
            <select
              data-slot="native-select"
              id="survey-import-task-name"
              v-model="taskName"
              :disabled="loading || taskLocked || !taskOptions.length"
              data-testid="survey-import-task-name"
            >
              <option v-if="!taskOptions.length" value="">暂无预设任务</option>
              <option v-for="option in taskOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
            <ChevronDown class="sid-select-icon" :size="13" />
          </span>
        </label>
      </section>

      <p v-if="taskLocked" class="sid-lock-hint">
        <Lock :size="11" />
        任务已锁定。如需更换，请先清空点位清单后重新导入。
      </p>

      <section class="sid-main" aria-label="日期与查询结果">
        <aside class="sid-calendar-col">
          <span class="sid-pane-label">调查日期</span>
          <DatePickerField
            id="survey-import-date"
            v-model="selectedDate"
            :disabled="loading"
          />
          <button
            data-slot="button"
            type="button"
            class="sid-query-btn"
            :disabled="loading || !canImportSurvey || !taskName"
            data-testid="survey-query-button"
            @click="handleQuery"
          >
            <LoaderCircle v-if="loading" class="sid-spin" :size="13" />
            <Search v-else :size="13" />
            {{ loading ? "查询中…" : "查询" }}
          </button>
        </aside>

        <div class="sid-result-col">
          <div class="sid-result-toolbar">
            <p class="sid-result-summary">
              <template v-if="queried">共 {{ totalCount }} 条，已选 {{ selectedCount }} 条</template>
              <template v-else>选择日期后点击「查询」</template>
            </p>
            <button
              v-if="hasCandidates"
              data-slot="button"
              type="button"
              class="sid-text-btn"
              :disabled="loading"
              @click="toggleSelectAll"
            >
              {{ allSelected ? "取消全选" : "全选" }}
            </button>
          </div>

          <div class="sid-result-panel">
            <div v-if="loading" class="sid-result-state">
              <span class="sid-state-icon">
                <LoaderCircle class="sid-spin" :size="16" />
              </span>
              <strong>正在查询…</strong>
              <p>请稍候</p>
            </div>

            <div v-else-if="hasCandidates" class="sid-table-wrap">
              <table class="sid-table">
                <thead>
                  <tr>
                    <th class="cell-check">
                      <input
                        data-slot="checkbox"
                        :checked="allSelected"
                        :indeterminate.prop="selectedCount > 0 && !allSelected"
                        type="checkbox"
                        aria-label="全选调查记录"
                        @change="toggleSelectAll"
                      />
                    </th>
                    <th v-for="column in candidateColumns" :key="column.key">
                      {{ column.label }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="candidate in candidates"
                    :key="getCandidateKey(candidate)"
                    :class="{ 'is-selected': isCandidateSelected(candidate) }"
                    @click="updateCandidateSelection(candidate, !isCandidateSelected(candidate))"
                  >
                    <td class="cell-check">
                      <input
                        data-slot="checkbox"
                        :checked="isCandidateSelected(candidate)"
                        type="checkbox"
                        :aria-label="`选择 ${candidate.location_id}`"
                        @click.stop
                        @change="updateCandidateSelection(candidate, $event.target.checked)"
                      />
                    </td>
                    <td v-for="column in candidateColumns" :key="column.key">
                      {{ formatCandidateValue(candidate, column) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div v-else-if="queried" class="sid-result-state">
              <span class="sid-state-icon">
                <SearchX :size="16" />
              </span>
              <strong>未找到记录</strong>
              <p>请切换日期后重新查询</p>
            </div>

            <div v-else class="sid-result-state">
              <span class="sid-state-icon">
                <CalendarDays :size="16" />
              </span>
              <strong>等待查询</strong>
              <p>{{ idleHint }}</p>
            </div>
          </div>
        </div>
      </section>
    </div>

    <footer class="sid-footer">
      <p class="sid-footer-hint">导入后仍可在点位清单中继续编辑</p>
      <div class="sid-footer-actions">
        <button data-slot="button" type="button" class="sid-ghost-btn" @click="emit('close')">
          取消
        </button>
        <button
          data-slot="button"
          type="button"
          class="sid-primary-btn"
          :disabled="!canImport"
          data-testid="survey-import-confirm"
          @click="handleImport"
        >
          导入选中记录
        </button>
      </div>
    </footer>
  </BaseDialog>
</template>

<style>
/*
 * Notion 风弹窗：纯白底、发丝级描边、柔和三段阴影。
 * 控件统一走 --nx-* 局部变量，避免与全局遗留控件样式打架
 * （弹窗内按钮/选择框/勾选框均带 data-slot，已豁免 styles.css 中的原生控件样式）。
 */
.base-dialog-mask.survey-import-mask {
  z-index: 1600;
  background: rgb(15 15 15 / 32%);
  backdrop-filter: none;
}

.base-dialog-content.survey-import-dialog {
  --nx-line: color-mix(in oklch, var(--border) 78%, transparent);
  --nx-line-soft: color-mix(in oklch, var(--border) 55%, transparent);
  --nx-hover: color-mix(in oklch, var(--foreground) 5%, transparent);
  --nx-selected: color-mix(in oklch, var(--primary) 8%, transparent);
  --nx-text: var(--foreground);
  --nx-text-2: var(--muted-foreground);
  --nx-text-3: color-mix(in oklch, var(--muted-foreground) 72%, transparent);
  --nx-ring: 0 0 0 3px color-mix(in oklch, var(--ring) 16%, transparent);

  width: min(56rem, calc(100vw - 2rem)) !important;
  max-width: min(56rem, calc(100vw - 2rem)) !important;
  max-height: min(44rem, calc(100vh - 2rem));
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 0;
  overflow: hidden;
  border: 0;
  border-radius: 12px;
  background: var(--popover);
  box-shadow:
    0 0 0 1px rgb(15 15 15 / 4%),
    0 4px 8px rgb(15 15 15 / 6%),
    0 16px 48px rgb(15 15 15 / 18%);
}

@media (max-width: 860px) {
  .base-dialog-content.survey-import-dialog {
    width: min(100%, calc(100vw - 1rem)) !important;
    max-width: min(100%, calc(100vw - 1rem)) !important;
    max-height: calc(100vh - 1rem);
  }
}
</style>

<style scoped>
.sid-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.05rem 1.25rem 0.9rem;
  border-bottom: 1px solid var(--nx-line-soft);
}

.sid-head-copy {
  min-width: 0;
}

.sid-head-copy h3 {
  margin: 0;
  color: var(--nx-text);
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  line-height: 1.35;
}

.sid-head-copy p {
  margin: 0.22rem 0 0;
  color: var(--nx-text-2);
  font-size: 0.78rem;
  line-height: 1.5;
}

.sid-icon-btn {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  margin: -0.2rem -0.3rem 0 0;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--nx-text-2);
  cursor: pointer;
  transition:
    background-color 90ms ease,
    color 90ms ease;
}

.sid-icon-btn:hover {
  background: var(--nx-hover);
  color: var(--nx-text);
}

.sid-body {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 1rem;
  min-height: 0;
  padding: 1rem 1.25rem 1.1rem;
  overflow: auto;
}

/* 任务配置：Notion 属性行 */
.sid-filters {
  display: grid;
  grid-template-columns: minmax(0, 0.95fr) minmax(0, 0.6fr) minmax(0, 1.45fr);
  gap: 0.75rem;
}

.sid-field {
  display: grid;
  gap: 0.3rem;
  min-width: 0;
}

.sid-field-label {
  color: var(--nx-text-2);
  font-size: 0.72rem;
  font-weight: 500;
}

.sid-select-wrap {
  position: relative;
  display: block;
}

.sid-select-wrap select {
  width: 100%;
  height: 1.9rem;
  padding: 0 1.6rem 0 0.6rem;
  appearance: none;
  border: 1px solid var(--nx-line);
  border-radius: 6px;
  background: var(--popover);
  color: var(--nx-text);
  font-size: 0.8rem;
  line-height: 1;
  outline: none;
  cursor: pointer;
  transition:
    border-color 90ms ease,
    box-shadow 90ms ease,
    background-color 90ms ease;
}

.sid-select-wrap select:hover:not(:disabled) {
  background: color-mix(in oklch, var(--foreground) 3%, var(--popover));
}

.sid-select-wrap select:focus-visible {
  border-color: var(--input);
  box-shadow: var(--nx-ring);
}

.sid-select-wrap select:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.sid-select-icon {
  position: absolute;
  top: 50%;
  right: 0.55rem;
  color: var(--nx-text-3);
  pointer-events: none;
  transform: translateY(-50%);
}

.sid-lock-hint {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  margin: -0.45rem 0 0;
  color: var(--nx-text-2);
  font-size: 0.72rem;
}

.sid-lock-hint svg {
  flex-shrink: 0;
}

/* 主区：左日历右结果，中间发丝分隔线 */
.sid-main {
  display: grid;
  grid-template-columns: 14.25rem minmax(0, 1fr);
  gap: 1.1rem;
  align-items: stretch;
  min-height: 0;
}

.sid-calendar-col {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.55rem;
  padding-right: 1.1rem;
  border-right: 1px solid var(--nx-line-soft);
}

.sid-pane-label {
  color: var(--nx-text-2);
  font-size: 0.72rem;
  font-weight: 500;
}

.sid-query-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  height: 1.85rem;
  margin-top: 0.15rem;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: var(--primary);
  color: var(--primary-foreground);
  font-size: 0.78rem;
  font-weight: 500;
  cursor: pointer;
  transition:
    background-color 90ms ease,
    opacity 90ms ease;
}

.sid-query-btn:hover:not(:disabled) {
  background: color-mix(in oklch, var(--primary) 90%, black);
}

.sid-query-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.sid-spin {
  animation: sid-spin 0.9s linear infinite;
}

@keyframes sid-spin {
  to {
    transform: rotate(360deg);
  }
}

/* 结果列 */
.sid-result-col {
  display: flex;
  min-width: 0;
  min-height: 19rem;
  flex-direction: column;
  gap: 0.4rem;
}

.sid-result-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  min-height: 1.4rem;
}

.sid-result-summary {
  margin: 0;
  color: var(--nx-text-2);
  font-size: 0.75rem;
}

.sid-text-btn {
  padding: 0.15rem 0.4rem;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: var(--nx-text-2);
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition:
    background-color 90ms ease,
    color 90ms ease;
}

.sid-text-btn:hover:not(:disabled) {
  background: var(--nx-hover);
  color: var(--nx-text);
}

.sid-text-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sid-result-panel {
  display: flex;
  flex: 1 1 auto;
  min-height: 17rem;
  flex-direction: column;
  overflow: hidden;
  border-top: 1px solid var(--nx-line-soft);
}

/* Notion 数据库式表格：无外框，仅发丝行线 */
.sid-table-wrap {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}

.sid-table {
  width: 100%;
  min-width: 30rem;
  border-collapse: collapse;
}

.sid-table th,
.sid-table td {
  padding: 0.42rem 0.65rem;
  text-align: left;
  font-size: 0.78rem;
}

.sid-table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  border-bottom: 1px solid var(--nx-line);
  background: var(--popover);
  color: var(--nx-text-2);
  font-size: 0.72rem;
  font-weight: 500;
  white-space: nowrap;
}

.sid-table tbody td {
  max-width: 11rem;
  overflow: hidden;
  border-bottom: 1px solid var(--nx-line-soft);
  color: var(--nx-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sid-table tbody tr {
  cursor: pointer;
  transition: background-color 60ms ease;
}

.sid-table tbody tr:hover td {
  background: var(--nx-hover);
}

.sid-table tbody tr.is-selected td {
  background: var(--nx-selected);
}

.cell-check {
  width: 2.1rem;
  text-align: center;
}

.cell-check input {
  width: 0.85rem;
  height: 0.85rem;
  margin: 0;
  padding: 0;
  accent-color: var(--primary);
  cursor: pointer;
  vertical-align: middle;
}

/* 空态 / 加载态 */
.sid-result-state {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.3rem;
  min-height: 16rem;
  padding: 1.5rem;
  text-align: center;
}

.sid-state-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.1rem;
  height: 2.1rem;
  margin-bottom: 0.25rem;
  border-radius: 8px;
  background: var(--nx-hover);
  color: var(--nx-text-2);
}

.sid-result-state strong {
  color: var(--nx-text);
  font-size: 0.82rem;
  font-weight: 500;
}

.sid-result-state p {
  margin: 0;
  color: var(--nx-text-2);
  font-size: 0.74rem;
}

/* 底部操作条 */
.sid-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.75rem 1.25rem;
  border-top: 1px solid var(--nx-line-soft);
}

.sid-footer-hint {
  margin: 0;
  color: var(--nx-text-3);
  font-size: 0.72rem;
}

.sid-footer-actions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.sid-ghost-btn,
.sid-primary-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 1.8rem;
  padding: 0 0.75rem;
  border: 0;
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 500;
  cursor: pointer;
  transition:
    background-color 90ms ease,
    opacity 90ms ease;
}

.sid-ghost-btn {
  background: transparent;
  color: var(--nx-text);
}

.sid-ghost-btn:hover {
  background: var(--nx-hover);
}

.sid-primary-btn {
  background: var(--primary);
  color: var(--primary-foreground);
}

.sid-primary-btn:hover:not(:disabled) {
  background: color-mix(in oklch, var(--primary) 90%, black);
}

.sid-primary-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.sid-icon-btn:focus-visible,
.sid-query-btn:focus-visible,
.sid-text-btn:focus-visible,
.sid-ghost-btn:focus-visible,
.sid-primary-btn:focus-visible {
  outline: none;
  box-shadow: var(--nx-ring);
}

@media (max-width: 860px) {
  .sid-filters {
    grid-template-columns: 1fr;
  }

  .sid-main {
    grid-template-columns: 1fr;
  }

  .sid-calendar-col {
    align-items: stretch;
    padding-right: 0;
    padding-bottom: 1rem;
    border-right: 0;
    border-bottom: 1px solid var(--nx-line-soft);
  }

  .sid-calendar-col :deep(.inline-calendar) {
    width: 100%;
    max-width: 16rem;
    margin-inline: auto;
  }

  .sid-result-col {
    min-height: 14rem;
  }

  .sid-footer {
    flex-direction: column;
    align-items: stretch;
  }

  .sid-footer-hint {
    text-align: center;
  }

  .sid-footer-actions {
    justify-content: stretch;
  }

  .sid-footer-actions button {
    flex: 1;
  }
}
</style>
