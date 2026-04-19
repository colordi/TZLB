<script setup>
import { computed, ref, watch } from "vue";

import { isUnauthorizedError } from "../../api/http.js";
import { fetchSurveyCandidates } from "../../api/survey.js";
import { useToast } from "../../composables/useToast.js";
import { getTodayDate } from "./fieldConfig.js";

const props = defineProps({
  busy: {
    type: Boolean,
    default: false,
  },
  pestType: {
    type: String,
    default: "春尺蠖",
  },
  open: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["close", "import"]);
const { error, info } = useToast();

const selectedDate = ref(getTodayDate());
const loading = ref(false);
const queried = ref(false);
const candidates = ref([]);
const selectedCandidateKeys = ref([]);

const totalCount = computed(() => candidates.value.length);
const selectedCount = computed(() => selectedCandidateKeys.value.length);
const hasCandidates = computed(() => totalCount.value > 0);
const allSelected = computed(() => hasCandidates.value && selectedCount.value === totalCount.value);
const canImport = computed(() => !props.busy && !loading.value && selectedCount.value > 0);
const isOtherPest = computed(() => props.pestType === "其他害虫");
const dialogDescription = computed(() =>
  isOtherPest.value
    ? "按调查日期查询其他害虫问题点位，并批量追加到当前工作单。"
    : "按调查日期查询春尺蠖受害点位，并批量追加到当前工作单。",
);
const idleHint = computed(() =>
  isOtherPest.value
    ? "当前支持按调查日期导入其他害虫调查数据。"
    : "当前仅支持导入春尺蠖幼虫调查数据。",
);
const candidateColumns = computed(() =>
  isOtherPest.value
    ? [
        { key: "location_id", label: "编号", fallback: "—" },
        { key: "town_or_street", label: "乡镇｜街道", fallback: "未匹配" },
        { key: "location_name", label: "点位名称", fallback: "未匹配" },
        { key: "pest_name", label: "虫害类型", fallback: "—" },
        { key: "host_plant", label: "寄主树种", fallback: "—" },
        { key: "survey_result", label: "调查结论", fallback: "—" },
      ]
    : [
        { key: "location_id", label: "编号", fallback: "—" },
        { key: "town_or_street", label: "乡镇｜街道", fallback: "未匹配" },
        { key: "location_name", label: "点位名称", fallback: "未匹配" },
        { key: "total_insect_count", label: "总虫口数", fallback: "—" },
        { key: "damage_level", label: "受害程度", fallback: "—" },
      ],
);

function getCandidateKey(candidate) {
  return [
    candidate.survey_date || "",
    candidate.location_id || "",
    candidate.pest_name || "",
  ].join("-");
}

function formatCandidateValue(candidate, column) {
  const value = candidate[column.key];
  if (value === null || value === undefined) {
    return column.fallback;
  }

  const text = `${value}`.trim();
  return text === "" ? column.fallback : text;
}

function resetDialogState() {
  selectedDate.value = getTodayDate();
  loading.value = false;
  queried.value = false;
  candidates.value = [];
  selectedCandidateKeys.value = [];
}

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      resetDialogState();
    }
  },
);

async function handleQuery() {
  if (!selectedDate.value) {
    info("请先选择调查日期。", "缺少查询条件");
    return;
  }

  loading.value = true;

  try {
    const result = await fetchSurveyCandidates({
      date: selectedDate.value,
      pestType: props.pestType,
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

  emit("import", selectedRecords);
}
</script>

<template>
  <teleport to="body">
    <div
      v-if="open"
      class="survey-import-mask"
      role="presentation"
      @click.self="emit('close')"
      @keydown.esc.prevent="emit('close')"
    >
      <section
        class="survey-import-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="导入调查数据"
        tabindex="0"
      >
        <header class="dialog-head">
          <div>
            <h3>导入调查数据</h3>
            <p>{{ dialogDescription }}</p>
          </div>
          <button type="button" class="dialog-close button-secondary" @click="emit('close')">
            关闭
          </button>
        </header>

        <div class="query-panel">
          <div class="query-field">
            <label for="survey-import-date">调查日期</label>
            <input id="survey-import-date" v-model="selectedDate" :disabled="loading" type="date" />
          </div>
          <button
            type="button"
            :disabled="loading"
            data-testid="survey-query-button"
            @click="handleQuery"
          >
            {{ loading ? "查询中…" : "查询记录" }}
          </button>
        </div>

        <div class="result-toolbar">
          <p class="result-summary">
            <template v-if="queried">
              共 {{ totalCount }} 条记录，已选择 {{ selectedCount }} 条
            </template>
            <template v-else>
              选择调查日期后点击“查询记录”。
            </template>
          </p>
          <button
            v-if="hasCandidates"
            type="button"
            class="button-secondary"
            :disabled="loading"
            @click="toggleSelectAll"
          >
            {{ allSelected ? "取消全选" : "全选记录" }}
          </button>
        </div>

        <div class="result-panel">
          <div v-if="loading" class="result-state">
            <strong>正在查询调查记录…</strong>
            <p>请稍候，系统正在读取符合条件的点位。</p>
          </div>

          <div v-else-if="hasCandidates" class="result-table-wrap">
            <table class="result-table">
              <thead>
                <tr>
                  <th class="cell-check">
                    <input
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
                <tr v-for="candidate in candidates" :key="getCandidateKey(candidate)">
                  <td class="cell-check">
                    <input
                      :checked="selectedCandidateKeys.includes(getCandidateKey(candidate))"
                      type="checkbox"
                      :aria-label="`选择 ${candidate.location_id}`"
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

          <div v-else-if="queried" class="result-state">
            <strong>未找到可导入的调查记录</strong>
            <p>请切换日期后重新查询。</p>
          </div>

          <div v-else class="result-state">
            <strong>尚未开始查询</strong>
            <p>{{ idleHint }}</p>
          </div>
        </div>

        <footer class="dialog-footer">
          <p class="footer-hint">导入后仍可在下方工作单表格中继续编辑。</p>
          <div class="footer-actions">
            <button type="button" class="button-secondary" @click="emit('close')">取消</button>
            <button
              type="button"
              :disabled="!canImport"
              data-testid="survey-import-confirm"
              @click="handleImport"
            >
              导入选中记录
            </button>
          </div>
        </footer>
      </section>
    </div>
  </teleport>
</template>

<style scoped>
.survey-import-mask {
  position: fixed;
  inset: 0;
  z-index: 1600;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(18, 36, 25, 0.36);
  backdrop-filter: blur(8px);
}

.survey-import-dialog {
  width: min(72rem, 100%);
  max-height: min(46rem, calc(100vh - 2rem));
  display: flex;
  flex-direction: column;
  gap: 1rem;
  overflow: hidden;
  padding: 1.25rem;
  border: 1px solid rgba(46, 125, 50, 0.16);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 30px 60px rgba(12, 35, 20, 0.18);
}

.dialog-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.dialog-head h3 {
  font-size: 1.4rem;
  line-height: 1.15;
}

.dialog-head p {
  margin-top: 0.32rem;
  color: var(--color-muted);
  font-size: 0.92rem;
}

.dialog-close {
  flex-shrink: 0;
}

.query-panel {
  display: flex;
  align-items: flex-end;
  gap: 1rem;
  padding: 1rem 1.1rem;
  border: 1px solid rgba(46, 125, 50, 0.14);
  border-radius: 24px;
  background:
    linear-gradient(135deg, rgba(46, 125, 50, 0.07), rgba(46, 125, 50, 0.03)),
    rgba(245, 250, 243, 0.94);
}

.query-field {
  min-width: 0;
  flex: 1;
}

.query-field label {
  display: block;
  margin-bottom: 0.35rem;
  color: var(--color-primary-strong);
  font-size: 0.88rem;
  font-weight: 700;
}

.result-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.result-summary {
  color: var(--color-muted);
  font-size: 0.92rem;
  font-weight: 600;
}

.result-panel {
  flex: 0 1 auto;
  min-height: 18rem;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(46, 125, 50, 0.12);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  overflow: hidden;
}

.result-table-wrap {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}

.result-table {
  width: 100%;
  min-width: 42rem;
  border-collapse: collapse;
}

.result-table th,
.result-table td {
  padding: 0.9rem 0.85rem;
  border-bottom: 1px solid rgba(46, 125, 50, 0.08);
  text-align: left;
}

.result-table thead th {
  position: sticky;
  top: 0;
  background: linear-gradient(180deg, rgba(236, 249, 238, 0.98), rgba(228, 246, 230, 0.96));
  color: var(--color-primary-strong);
  font-size: var(--text-sm);
  font-weight: 800;
}

.result-table tbody tr:nth-child(2n) td {
  background: rgba(240, 249, 238, 0.55);
}

.cell-check {
  width: 3rem;
  text-align: center;
}

.cell-check input {
  width: 1.1rem;
  min-height: 1.1rem;
  height: 1.1rem;
  padding: 0;
}

.result-state {
  flex: 1 1 auto;
  min-height: 18rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  padding: 1.5rem;
  text-align: center;
}

.result-state strong {
  font-size: 1rem;
}

.result-state p {
  color: var(--color-muted);
}

.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.footer-hint {
  color: var(--color-muted);
  font-size: 0.9rem;
}

.footer-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

@media (max-width: 760px) {
  .survey-import-dialog {
    width: 100%;
    max-height: calc(100vh - 1rem);
    padding: 1rem;
  }

  .dialog-head,
  .query-panel,
  .result-toolbar,
  .dialog-footer {
    flex-direction: column;
    align-items: stretch;
  }

  .result-table {
    min-width: 34rem;
  }

  .footer-actions {
    justify-content: stretch;
  }

  .footer-actions button {
    flex: 1;
  }
}
</style>
