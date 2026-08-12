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
import { useWorkorderTaskConfig } from "../../composables/workorder/useWorkorderTaskConfig.js";
import { getSurveyImportConfig, getTodayDate } from "./fieldConfig.js";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { DatePickerField } from "@/components/ui/date-picker";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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

function handleOpenChange(value) {
  if (!value) {
    emit("close");
  }
}
</script>

<template>
  <Dialog :open="open" @update:open="handleOpenChange">
    <DialogContent class="max-h-[85vh] overflow-y-auto sm:max-w-3xl">
      <DialogHeader>
        <DialogTitle>从数据库导入</DialogTitle>
        <DialogDescription>{{ dialogDescription }}</DialogDescription>
      </DialogHeader>

      <section class="grid gap-3 md:grid-cols-[minmax(0,0.95fr)_minmax(0,0.6fr)_minmax(0,1.45fr)]" data-testid="survey-import-task-panel" aria-label="任务配置">
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

      <DialogFooter class="sm:items-center sm:justify-between">
        <p class="text-xs text-muted-foreground">导入后仍可在点位清单中继续编辑</p>
        <div class="flex justify-end gap-2">
          <Button type="button" variant="outline" @click="emit('close')">取消</Button>
          <Button
            type="button"
            :disabled="!canImport"
            data-testid="survey-import-confirm"
            @click="handleImport"
          >
            导入选中记录
          </Button>
        </div>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<style scoped>
/* 结果区在弹窗内独立滚动，粘性表头由此获得真实滚动容器 */
.survey-result-table :deep([data-slot="table-container"]) {
  max-height: 22rem;
}
</style>
