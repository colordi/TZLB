<script setup>
import { computed, ref } from "vue";
import { ChevronLeft, ChevronRight, Database } from "@lucide/vue";

import { useWorkorderTaskConfig } from "../composables/workorder/useWorkorderTaskConfig.js";
import { useWorkorderRecords } from "../composables/workorder/useWorkorderRecords.js";
import { useRecordSelection } from "../composables/workorder/useRecordSelection.js";
import { useWorkorderExport } from "../composables/workorder/useWorkorderExport.js";
import { useRecordDetailModal } from "../composables/workorder/useRecordDetailModal.js";
import { useToast } from "../composables/useToast.js";
import RecordTable from "../components/workorder/RecordTable.vue";
import RecordDetailModal from "../components/workorder/RecordDetailModal.vue";
import SurveyImportDialog from "../components/workorder/SurveyImportDialog.vue";
import ConfirmDialog from "@/components/common/ConfirmDialog.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import PageHeader from "@/components/common/PageHeader.vue";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";

const toast = useToast();

const taskConfig = useWorkorderTaskConfig();
const {
  pestType, year, taskName,
  generation, canImportSurvey,
} = taskConfig;

const recCtrl = useWorkorderRecords(pestType);
const {
  records, validationErrors,
  handleSurveyImport: importRecords,
  handleUpdateRecord: updateRecord,
  handleBatchDelete: batchDelete,
} = recCtrl;

const selection = useRecordSelection(records, validationErrors);
const {
  selectedUids, searchQuery, recordFilter,
  currentPage, pageSize, totalPages, serialOffset,
  filteredRecords, pagedRecords, pagedValidationErrors,
  clearSelection,
} = selection;

const exportCtrl = useWorkorderExport(
  taskConfig, records, selectedUids,
);
const {
  generating,
  generateButtonLabel,
  exportProgress,
  exportProgressPercent,
  exportProgressLabel,
} = exportCtrl;

const surveyImportOpen = ref(false);
const pendingDelete = ref(null);
const showConfirmDialog = ref(false);
const sessionLocked = ref(false);

const detailModal = useRecordDetailModal(records, validationErrors, pestType);
const {
  activeRecordUid, showDetailModal, activeRecord, activeRecordError,
  openDetail, closeDetail,
} = detailModal;

const hasRecords = computed(() => records.value.length > 0);
const lockedTask = computed(() => {
  if (!sessionLocked.value) {
    return null;
  }
  return {
    pestType: pestType.value,
    year: year.value,
    taskName: taskName.value,
    generation: generation.value,
  };
});

const confirmDialogTitle = computed(() => {
  if (pendingDelete.value?.scope === "reset") {
    return "清空点位并重新建单";
  }
  if (pendingDelete.value?.scope === "batch") {
    return "删除选中记录";
  }
  return "删除该条记录";
});
const confirmDialogMessage = computed(() => {
  if (pendingDelete.value?.scope === "reset") {
    return "将清空当前点位清单并解锁任务配置，之后可重新从数据库导入。此操作不可撤销。";
  }
  const count = pendingDelete.value?.uids.length || 0;
  if (pendingDelete.value?.scope === "batch") {
    return `确认删除选中的 ${count} 条记录吗？此操作不可撤销。`;
  }
  return "确认删除当前记录吗？此操作不可撤销。";
});

function openSurveyImportDialog() {
  if (generating.value) {
    return;
  }
  if (!sessionLocked.value && !canImportSurvey.value) {
    // still allow open; dialog owns pest selection and canImportSurvey
  }
  surveyImportOpen.value = true;
}

function closeSurveyImportDialog() {
  surveyImportOpen.value = false;
}

function onSurveyImport(payload) {
  const importedRecords = Array.isArray(payload)
    ? payload
    : payload?.records;
  const task = Array.isArray(payload) ? null : payload?.task;

  if (!Array.isArray(importedRecords) || importedRecords.length === 0) {
    toast.info("请至少选择一条调查记录。", "没有可导入项");
    return;
  }

  if (task) {
    pestType.value = task.pestType;
    year.value = task.year;
    taskName.value = task.taskName;
  }

  const count = importRecords(importedRecords).length;
  sessionLocked.value = true;
  surveyImportOpen.value = false;
  toast.success(`已导入 ${count} 条调查记录。`, "导入完成");
}

function requestResetSession() {
  if (!hasRecords.value && !sessionLocked.value) {
    return;
  }
  pendingDelete.value = { scope: "reset", uids: records.value.map((r) => r.__uid) };
  showConfirmDialog.value = true;
}

function resetSession() {
  batchDelete(records.value.map((record) => record.__uid));
  selectedUids.value = [];
  searchQuery.value = "";
  recordFilter.value = "all";
  sessionLocked.value = false;
  taskConfig.resetTaskName();
  closeDetail();
}

function handleRowClick(uid) {
  openDetail(uid);
}

function handleCloseDetailModal() {
  closeDetail();
}

function handleUpdateRecord(updatedRecord) {
  if (activeRecordUid.value) {
    updateRecord(activeRecordUid.value, updatedRecord);
    selectedUids.value = [];
    handleCloseDetailModal();
  }
}

function handleDeleteRecord() {
  if (!activeRecordUid.value) {
    return;
  }
  pendingDelete.value = {
    scope: "single",
    uids: [activeRecordUid.value],
  };
  showConfirmDialog.value = true;
}

function onBatchDelete() {
  if (!selectedUids.value.length) {
    return;
  }
  pendingDelete.value = {
    scope: "batch",
    uids: [...selectedUids.value],
  };
  showConfirmDialog.value = true;
}

function closeConfirmDialog() {
  showConfirmDialog.value = false;
  pendingDelete.value = null;
}

function confirmDelete() {
  if (!pendingDelete.value) {
    return;
  }

  if (pendingDelete.value.scope === "reset") {
    resetSession();
    closeConfirmDialog();
    toast.success("已清空点位，可重新导入建单。", "已重置");
    return;
  }

  batchDelete(pendingDelete.value.uids);
  selectedUids.value = selectedUids.value.filter(
    (uid) => !pendingDelete.value.uids.includes(uid),
  );
  const wasSingle = pendingDelete.value.scope === "single";
  closeConfirmDialog();
  if (wasSingle) {
    handleCloseDetailModal();
  }
  if (records.value.length === 0) {
    sessionLocked.value = false;
    taskConfig.resetTaskName();
  }
}

function onGenerate() {
  exportCtrl.handleGenerate(toast);
}
</script>


<template>
  <section class="mx-auto w-full max-w-6xl space-y-6">
    <PageHeader
      title="工单录入"
      description="从数据库选取调查记录，校对点位后批量生成工单。"
    />

    <Card
      v-if="sessionLocked"
      aria-label="本单任务"
      data-testid="workorder-session-task"
    >
      <CardContent class="flex flex-wrap items-center justify-between gap-3 py-4">
        <div class="space-y-1">
          <p class="text-xs font-medium text-muted-foreground">本单任务（已锁定）</p>
          <p class="text-sm font-semibold">
            {{ pestType }} · {{ year }} · {{ taskName }}
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          :disabled="generating"
          data-testid="workorder-reset-session"
          @click="requestResetSession"
        >
          清空点位并重新建单
        </Button>
      </CardContent>
    </Card>

    <Card class="workorder-list-card flex-1" aria-label="点位清单">
      <CardHeader class="flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle class="text-base">点位清单</CardTitle>
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-sm text-muted-foreground">
            共 {{ records.length }} 个点位
          </span>
          <Button
            v-if="hasRecords"
            type="button"
            size="sm"
            variant="outline"
            :disabled="generating"
            data-testid="survey-import-button"
            @click="openSurveyImportDialog"
          >
            <Database class="size-4" />
            <span>继续导入</span>
          </Button>
        </div>
      </CardHeader>
      <CardContent class="space-y-4">
        <div
          v-if="hasRecords"
          class="flex flex-wrap items-center gap-3"
        >
          <label class="relative min-w-[12rem] flex-1">
            <span class="sr-only">搜索点位</span>
            <Input
              v-model="searchQuery"
              type="search"
              class="pl-3"
              placeholder="搜索点位……"
              data-testid="workorder-search"
            />
          </label>

          <div class="flex flex-wrap gap-2" aria-label="记录筛选">
            <Button
              type="button"
              size="sm"
              :variant="recordFilter === 'all' ? 'default' : 'outline'"
              data-testid="workorder-filter-all"
              @click="recordFilter = 'all'"
            >
              全部
            </Button>
            <Button
              type="button"
              size="sm"
              :variant="recordFilter === 'errors' ? 'default' : 'outline'"
              data-testid="workorder-filter-errors"
              @click="recordFilter = 'errors'"
            >
              错误
            </Button>
            <Button
              type="button"
              size="sm"
              :variant="recordFilter === 'selected' ? 'default' : 'outline'"
              data-testid="workorder-filter-selected"
              @click="recordFilter = 'selected'"
            >
              已选
            </Button>
          </div>
        </div>

        <EmptyState
          v-if="!hasRecords"
          :icon="Database"
          title="暂无点位"
          description="请从数据库导入调查记录以建立本单。"
          data-testid="workorder-empty-state"
        >
          <Button
            type="button"
            :disabled="generating"
            data-testid="survey-import-button"
            @click="openSurveyImportDialog"
          >
            <Database class="size-4" />
            <span>从数据库导入</span>
          </Button>
        </EmptyState>

        <RecordTable
          v-else
          v-model:selectedUids="selectedUids"
          :records="pagedRecords"
          :pest-type="pestType"
          :busy="generating"
          :busy-label="exportProgressLabel"
          :busy-percent="exportProgressPercent"
          :errors="pagedValidationErrors"
          :serial-offset="serialOffset"
          @row-click="handleRowClick"
        />

        <div
          v-if="hasRecords && filteredRecords.length === 0"
          class="py-6 text-center text-sm text-muted-foreground"
        >
          当前筛选条件下没有匹配的点位。
        </div>

        <div
          v-if="generating"
          class="space-y-2 rounded-md border bg-muted/30 p-3"
          data-testid="workorder-export-progress"
          aria-live="polite"
        >
          <div class="flex items-center justify-between text-sm">
            <strong>{{ exportProgressLabel }}</strong>
            <span data-testid="workorder-export-progress-percent">{{ exportProgressPercent }}%</span>
          </div>
          <div
            class="h-2 overflow-hidden rounded-full bg-muted"
            role="progressbar"
            :aria-valuenow="exportProgressPercent"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-label="exportProgressLabel"
          >
            <div
              class="h-full bg-primary transition-[width]"
              :style="{ width: `${exportProgressPercent}%` }"
            />
          </div>
          <p v-if="exportProgress.total > 0" class="text-xs text-muted-foreground">
            进度 {{ Math.min(exportProgress.current, exportProgress.total) }} / {{ exportProgress.total }}
          </p>
        </div>

        <div
          v-if="filteredRecords.length > 0"
          class="flex flex-wrap items-center justify-center gap-3"
          data-testid="workorder-pagination"
        >
          <span class="text-sm text-muted-foreground" data-testid="workorder-page-status">
            第 {{ currentPage }} / {{ totalPages }} 页
          </span>
          <Pagination
            v-model:page="currentPage"
            :items-per-page="pageSize"
            :total="filteredRecords.length"
            :sibling-count="1"
            :disabled="generating"
            show-edges
            class="mx-0 w-auto"
          >
            <PaginationContent v-slot="{ items }">
              <PaginationPrevious data-testid="workorder-page-prev">
                <ChevronLeft class="size-4" />
                <span class="hidden sm:block">上一页</span>
              </PaginationPrevious>
              <template v-for="(item, index) in items" :key="index">
                <PaginationItem
                  v-if="item.type === 'page'"
                  :value="item.value"
                  :is-active="item.value === currentPage"
                >
                  {{ item.value }}
                </PaginationItem>
                <PaginationEllipsis v-else />
              </template>
              <PaginationNext data-testid="workorder-page-next">
                <span class="hidden sm:block">下一页</span>
                <ChevronRight class="size-4" />
              </PaginationNext>
            </PaginationContent>
          </Pagination>
        </div>

        <footer
          v-if="hasRecords"
          class="workorder-list-foot flex flex-wrap items-center justify-between gap-3 border-t pt-4"
        >
          <div class="flex flex-wrap items-center gap-3 text-sm">
            <span>
              已选择 <strong>{{ selectedUids.length }}</strong> 个点位
            </span>
            <template v-if="selectedUids.length">
              <Button
                type="button"
                variant="link"
                class="h-auto px-0"
                :disabled="generating"
                @click="clearSelection"
              >
                取消选择
              </Button>
              <Button
                type="button"
                variant="link"
                class="h-auto px-0 text-destructive"
                :disabled="generating"
                @click="onBatchDelete"
              >
                删除选中
              </Button>
            </template>
          </div>
          <Button
            type="button"
            :disabled="generating || records.length === 0"
            data-testid="workorder-export-button"
            @click="onGenerate"
          >
            {{ generateButtonLabel }}
          </Button>
        </footer>
      </CardContent>
    </Card>

    <RecordDetailModal
      :open="showDetailModal"
      :record="activeRecord"
      :pest-type="pestType"
      :busy="generating"
      :error="activeRecordError"
      @close="handleCloseDetailModal"
      @update="handleUpdateRecord"
      @delete="handleDeleteRecord"
    />

    <SurveyImportDialog
      :busy="generating"
      :open="surveyImportOpen"
      :locked-task="lockedTask"
      @close="closeSurveyImportDialog"
      @import="onSurveyImport"
    />

    <ConfirmDialog
      :open="showConfirmDialog"
      :title="confirmDialogTitle"
      :message="confirmDialogMessage"
      :busy="generating"
      @close="closeConfirmDialog"
      @confirm="confirmDelete"
    />
  </section>
</template>
