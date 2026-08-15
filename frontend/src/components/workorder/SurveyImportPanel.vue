<script setup>
import { computed, ref, watch } from "vue";
import {
  CalendarDays,
  LoaderCircle,
  Lock,
  Search,
  SearchX,
} from "@lucide/vue";

import { isUnauthorizedError } from "../../api/http.js";
import { fetchSurveyCandidates } from "../../api/survey.js";
import { useToast } from "../../composables/useToast.js";
import { getSurveyImportConfig, getTodayDate } from "./fieldConfig.js";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { DatePickerField } from "@/components/ui/date-picker";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const props = defineProps({
  busy: {
    type: Boolean,
    default: false,
  },
  /** 页面已锁定任务（已有导入记录）：任务配置只读，仅可换日期继续导入 */
  taskLocked: {
    type: Boolean,
    default: false,
  },
  /** 视图持有的唯一任务配置实例，面板直接读写，不再自行创建 */
  taskConfig: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(["import"]);
const { error, info } = useToast();

const {
  PEST_OPTIONS,
  pestType,
  year,
  taskName,
  generation,
  taskOptions,
  yearOptions,
  canImportSurvey,
} = props.taskConfig;

const selectedDate = ref(getTodayDate());
const loading = ref(false);
const queried = ref(false);
const candidates = ref([]);
const selectedCandidateKeys = ref([]);

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
const panelDescription = computed(() => surveyImportConfig.value.description);
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

function resetQueryState() {
  selectedDate.value = getTodayDate();
  loading.value = false;
  queried.value = false;
  candidates.value = [];
  selectedCandidateKeys.value = [];
}

watch([pestType, year, taskName], () => {
  queried.value = false;
  candidates.value = [];
  selectedCandidateKeys.value = [];
});

watch(
  () => props.taskLocked,
  (locked, wasLocked) => {
    // 清空点位重新建单后，清掉上一单的查询结果
    if (wasLocked && !locked) {
      resetQueryState();
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
      pestType: pestType.value,
      year: year.value,
      generation: generation.value,
      // 列表仅需字段，不批量拉点位截图原图（生成时再按存储装配）
      includeImages: false,
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

  emit("import", { records: selectedRecords });
}
</script>

<template>
  <Card aria-label="从数据库导入" data-testid="survey-import-panel">
    <CardHeader class="pb-3">
      <CardTitle class="text-base">从数据库导入</CardTitle>
      <CardDescription>{{ panelDescription }}</CardDescription>
    </CardHeader>

    <CardContent class="space-y-4">
      <section class="survey-task-grid grid gap-3 md:grid-cols-[minmax(0,0.95fr)_minmax(0,0.6fr)_minmax(0,1.45fr)]" data-testid="survey-import-task-panel" aria-label="任务配置">
        <div class="grid gap-1.5">
          <Label for="survey-import-pest-type">害虫类型</Label>
          <NativeSelect
            id="survey-import-pest-type"
            v-model="pestType"
            class="w-full"
            :disabled="loading || taskLocked"
            data-testid="survey-import-pest-type"
          >
            <option v-for="option in PEST_OPTIONS" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </NativeSelect>
        </div>
        <div class="grid gap-1.5">
          <Label for="survey-import-year">年份</Label>
          <NativeSelect
            id="survey-import-year"
            v-model="year"
            class="w-full"
            :disabled="loading || taskLocked"
            data-testid="survey-import-year"
          >
            <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}</option>
          </NativeSelect>
        </div>
        <div class="grid gap-1.5">
          <Label for="survey-import-task-name">统防统治任务</Label>
          <NativeSelect
            id="survey-import-task-name"
            v-model="taskName"
            class="w-full"
            :disabled="loading || taskLocked || !taskOptions.length"
            data-testid="survey-import-task-name"
          >
            <option v-if="!taskOptions.length" value="">暂无预设任务</option>
            <option v-for="option in taskOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </NativeSelect>
        </div>
      </section>

      <p v-if="taskLocked" class="flex items-center gap-1 text-xs text-muted-foreground">
        <Lock class="size-3 shrink-0" />
        任务已锁定。如需更换，请先清空点位清单后重新导入。
      </p>

      <section class="grid gap-4 md:grid-cols-[14rem_minmax(0,1fr)]" aria-label="日期与查询结果">
        <div class="flex flex-col gap-2 md:border-r md:pr-4">
          <Label for="survey-import-date">调查日期</Label>
          <DatePickerField
            id="survey-import-date"
            v-model="selectedDate"
            :disabled="loading"
          />
          <Button
            type="button"
            :disabled="loading || !canImportSurvey || !taskName"
            data-testid="survey-query-button"
            @click="handleQuery"
          >
            <LoaderCircle v-if="loading" class="size-4 animate-spin" />
            <Search v-else class="size-4" />
            {{ loading ? "查询中…" : "查询" }}
          </Button>
        </div>

        <div class="flex min-w-0 flex-col gap-2">
          <div class="flex min-h-8 items-center justify-between gap-3">
            <p class="text-sm text-muted-foreground">
              <template v-if="queried">共 {{ totalCount }} 条，已选 {{ selectedCount }} 条</template>
              <template v-else>选择日期后点击「查询」</template>
            </p>
            <Button
              v-if="hasCandidates"
              type="button"
              variant="ghost"
              size="sm"
              :disabled="loading"
              @click="toggleSelectAll"
            >
              {{ allSelected ? "取消全选" : "全选" }}
            </Button>
          </div>

          <div class="flex min-h-[16rem] flex-col overflow-hidden rounded-xl border bg-card">
            <div v-if="loading" class="flex flex-1 flex-col items-center justify-center gap-1.5 p-6 text-center">
              <LoaderCircle class="size-4 animate-spin text-muted-foreground" />
              <p class="text-sm font-medium">正在查询…</p>
              <p class="text-xs text-muted-foreground">请稍候</p>
            </div>

            <div v-else-if="hasCandidates" class="survey-result-table">
              <Table class="min-w-[30rem]">
                <TableHeader>
                  <TableRow class="hover:bg-transparent">
                    <TableHead class="sticky top-0 z-10 w-10 bg-card">
                      <Checkbox
                        :model-value="allSelected ? true : selectedCount > 0 ? 'indeterminate' : false"
                        aria-label="全选调查记录"
                        @update:model-value="toggleSelectAll"
                      />
                    </TableHead>
                    <TableHead
                      v-for="column in candidateColumns"
                      :key="column.key"
                      class="sticky top-0 z-10 bg-card"
                    >
                      {{ column.label }}
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow
                    v-for="candidate in candidates"
                    :key="getCandidateKey(candidate)"
                    class="cursor-pointer"
                    :data-state="isCandidateSelected(candidate) ? 'selected' : undefined"
                    @click="updateCandidateSelection(candidate, !isCandidateSelected(candidate))"
                  >
                    <TableCell class="w-10" @click.stop>
                      <Checkbox
                        :model-value="isCandidateSelected(candidate)"
                        :aria-label="`选择 ${candidate.location_id}`"
                        @update:model-value="updateCandidateSelection(candidate, $event)"
                      />
                    </TableCell>
                    <TableCell
                      v-for="column in candidateColumns"
                      :key="column.key"
                      class="max-w-44 truncate"
                    >
                      {{ formatCandidateValue(candidate, column) }}
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>

            <div v-else-if="queried" class="flex flex-1 flex-col items-center justify-center gap-1.5 p-6 text-center">
              <SearchX class="size-4 text-muted-foreground" />
              <p class="text-sm font-medium">未找到记录</p>
              <p class="text-xs text-muted-foreground">请切换日期后重新查询</p>
            </div>

            <div v-else class="flex flex-1 flex-col items-center justify-center gap-1.5 p-6 text-center">
              <CalendarDays class="size-4 text-muted-foreground" />
              <p class="text-sm font-medium">等待查询</p>
              <p class="text-xs text-muted-foreground">{{ idleHint }}</p>
            </div>
          </div>
        </div>
      </section>

      <div class="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
        <p class="text-xs text-muted-foreground">导入后仍可在点位清单中继续编辑</p>
        <Button
          type="button"
          :disabled="!canImport"
          data-testid="survey-import-confirm"
          @click="handleImport"
        >
          导入选中记录
        </Button>
      </div>
    </CardContent>
  </Card>
</template>

<style scoped>
/* 任务配置三个下拉撑满各自网格列，保持等宽对齐（NativeSelect 包装层默认 w-fit） */
.survey-task-grid :deep([data-slot="native-select-wrapper"]) {
  width: 100%;
}

/* 结果区在卡片内独立滚动，粘性表头由此获得真实滚动容器 */
.survey-result-table :deep([data-slot="table-container"]) {
  max-height: 22rem;
}
</style>
