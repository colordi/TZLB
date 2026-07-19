<script setup>
import { computed, ref, watch } from "vue";
import { Archive, FileSpreadsheet, FolderUp } from "@lucide/vue";

import { useWorkorderTaskConfig } from "../composables/workorder/useWorkorderTaskConfig.js";
import { useWorkorderRecords } from "../composables/workorder/useWorkorderRecords.js";
import { useRecordSelection } from "../composables/workorder/useRecordSelection.js";
import { useWorkorderExport } from "../composables/workorder/useWorkorderExport.js";
import { useDateFolderUpload } from "../composables/workorder/useDateFolderUpload.js";
import { useRecordDetailModal } from "../composables/workorder/useRecordDetailModal.js";
import { useToast } from "../composables/useToast.js";
import ExcelImportDialog from "../components/workorder/ExcelImportDialog.vue";
import RecordTable from "../components/workorder/RecordTable.vue";
import RecordDetailModal from "../components/workorder/RecordDetailModal.vue";
import SurveyImportDialog from "../components/workorder/SurveyImportDialog.vue";
import ConfirmDialog from "../components/workorder/ConfirmDialog.vue";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";


const toast = useToast();

const taskConfig = useWorkorderTaskConfig();
const {
  PEST_OPTIONS, pestType, year, taskName,
  generation, taskOptions, yearOptions, canImportSurvey,
} = taskConfig;

const recCtrl = useWorkorderRecords(pestType);
const {
  records, validationErrors,
  normalizeAll, handleSurveyImport: importRecords,
  handleUpdateRecord: updateRecord,
  handleBatchDelete: batchDelete,
} = recCtrl;

const selection = useRecordSelection(records, validationErrors);
const {
  selectedUids, searchQuery, recordFilter,
  currentPage, totalPages, serialOffset,
  filteredRecords, pagedRecords, pagedValidationErrors,
  clearSelection, goToPrevPage, goToNextPage,
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

const dateFolder = useDateFolderUpload();
const { dateFolderInput, dateFolderUploading } = dateFolder;

const surveyImportOpen = ref(false);
const excelImportOpen = ref(false);
const pendingDelete = ref(null);
const showConfirmDialog = ref(false);

const detailModal = useRecordDetailModal(records, validationErrors, pestType);
const {
  activeRecordUid, showDetailModal, activeRecord, activeRecordError,
  openDetail, closeDetail,
} = detailModal;

const confirmDialogTitle = computed(() =>
  pendingDelete.value?.scope === "batch"
    ? "删除选中记录"
    : "删除该条记录",
);
const confirmDialogMessage = computed(() => {
  const count = pendingDelete.value?.uids.length || 0;
  if (pendingDelete.value?.scope === "batch") {
    return `确认删除选中的 ${count} 条记录吗？此操作不可撤销。`;
  }
  return "确认删除当前记录吗？此操作不可撤销。";
});

function resetWorkspace() {
  taskConfig.resetTaskName();
  surveyImportOpen.value = false;
  excelImportOpen.value = false;
  selectedUids.value = [];
  normalizeAll();
}

watch(pestType, resetWorkspace);

function openSurveyImportDialog() {
  if (!canImportSurvey.value || generating.value) {
    return;
  }
  surveyImportOpen.value = true;
}

function openExcelImportDialog() {
  if (generating.value) {
    return;
  }
  excelImportOpen.value = true;
}

function closeExcelImportDialog() {
  excelImportOpen.value = false;
}

function closeSurveyImportDialog() {
  surveyImportOpen.value = false;
}

function onDateFolderChange(event) {
  dateFolder.handleDateFolderChange(event, toast);
}

function onOpenDateFolderPicker() {
  dateFolder.openDateFolderPicker(generating.value);
}

function onSurveyImport(importedRecords) {
  if (!Array.isArray(importedRecords) || importedRecords.length === 0) {
    toast.info("请至少选择一条调查记录。", "没有可导入项");
    return;
  }
  const count = importRecords(importedRecords).length;
  surveyImportOpen.value = false;
  toast.success(`已导入 ${count} 条调查记录。`, "导入完成");
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
  batchDelete(pendingDelete.value.uids);
  selectedUids.value = selectedUids.value.filter(
    (uid) => !pendingDelete.value.uids.includes(uid),
  );
  const wasSingle = pendingDelete.value.scope === "single";
  closeConfirmDialog();
  if (wasSingle) {
    handleCloseDetailModal();
  }
}

function onGenerate() {
  exportCtrl.handleGenerate(toast);
}
</script>


<template>
  <section class="workorder-page mx-auto flex w-full max-w-6xl flex-col gap-4">
    <header class="workorder-page-head flex flex-wrap items-start justify-between gap-4">
      <div class="space-y-1">
        <h1 class="text-2xl font-bold tracking-tight md:text-3xl">调查工单</h1>
        <p class="max-w-2xl text-sm text-muted-foreground">
          导入调查记录，检查点位信息并批量生成工单。
        </p>
      </div>
      <div class="workorder-page-actions flex flex-wrap gap-2" aria-label="工单操作">
        <Button
          v-if="canImportSurvey"
          type="button"
          variant="outline"
          :disabled="generating"
          data-testid="survey-import-button"
          @click="openSurveyImportDialog"
        >
          从数据库追加
        </Button>
      </div>
    </header>

    <Card class="workorder-card workorder-card--accent" aria-label="任务配置">
      <CardHeader class="pb-3">
        <CardTitle class="workorder-card-title text-base">任务配置</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="workorder-controls flex flex-wrap gap-3">
          <label class="workorder-field grid min-w-[8rem] gap-1" for="pest-type">
            <span class="workorder-sr-only sr-only">害虫类型</span>
            <select
              id="pest-type"
              v-model="pestType"
              class="h-9 rounded-md border border-input bg-background px-2 text-sm"
              :disabled="generating"
            >
              <option v-for="option in PEST_OPTIONS" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>

          <label class="workorder-field grid min-w-[7rem] gap-1" for="workorder-year">
            <span class="workorder-sr-only sr-only">年份</span>
            <select
              id="workorder-year"
              v-model="year"
              class="h-9 rounded-md border border-input bg-background px-2 text-sm"
              :disabled="generating"
            >
              <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}</option>
            </select>
          </label>

          <label class="workorder-field is-task grid min-w-[12rem] flex-1 gap-1" for="task-name">
            <span class="workorder-sr-only sr-only">统防统治任务</span>
            <select
              id="task-name"
              v-model="taskName"
              class="h-9 rounded-md border border-input bg-background px-2 text-sm"
              :disabled="generating || !taskOptions.length"
            >
              <option v-if="!taskOptions.length" value="">暂无预设任务</option>
              <option v-for="option in taskOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>
        </div>
      </CardContent>
    </Card>

    <Card class="workorder-card workorder-card--accent" aria-label="导入调查数据">
      <CardHeader class="pb-3">
        <CardTitle class="workorder-card-title text-base">导入调查数据</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="workorder-import-actions flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            class="workorder-import-btn"
            :disabled="generating"
            data-testid="survey-excel-import-button"
            @click="openExcelImportDialog"
          >
            <FileSpreadsheet class="size-4" />
            <span>Excel导入</span>
          </Button>
          <Button
            type="button"
            variant="outline"
            class="workorder-import-btn"
            :disabled="generating || dateFolderUploading"
            data-testid="date-image-folder-button"
            @click="onOpenDateFolderPicker"
          >
            <FolderUp class="size-4" />
            <span>{{ dateFolderUploading ? "正在上传…" : "图片文件夹导入" }}</span>
          </Button>
          <input
            ref="dateFolderInput"
            class="workorder-folder-input hidden"
            type="file"
            multiple
            webkitdirectory
            directory
            data-testid="date-image-folder-input"
            @change="onDateFolderChange"
          />
          <Button as-child variant="outline" class="workorder-import-btn">
            <router-link to="/workorder/point-screenshots" data-testid="point-screenshot-entry">
              <Archive class="size-4" />
              <span>截图管理</span>
            </router-link>
          </Button>
        </div>
      </CardContent>
    </Card>

    <Card class="workorder-card workorder-list-card" aria-label="点位清单">
      <CardHeader class="workorder-list-head flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle class="workorder-card-title text-base">点位清单</CardTitle>
        <span class="workorder-list-count text-sm text-muted-foreground">
          共 {{ records.length }} 个点位
        </span>
      </CardHeader>
      <CardContent class="space-y-4">
        <div class="workorder-toolbar flex flex-wrap items-center gap-3">
          <label class="workorder-search relative min-w-[12rem] flex-1">
            <span class="workorder-sr-only sr-only">搜索点位</span>
            <Input
              v-model="searchQuery"
              type="search"
              class="pl-3"
              placeholder="搜索点位……"
              data-testid="workorder-search"
            />
          </label>

          <div
            class="workorder-segmented inline-flex rounded-md border p-0.5"
            aria-label="记录筛选"
          >
            <Button
              type="button"
              size="sm"
              :variant="recordFilter === 'all' ? 'default' : 'ghost'"
              :class="{ 'is-active': recordFilter === 'all' }"
              data-testid="workorder-filter-all"
              @click="recordFilter = 'all'"
            >
              全部
            </Button>
            <Button
              type="button"
              size="sm"
              :variant="recordFilter === 'errors' ? 'default' : 'ghost'"
              :class="{ 'is-active': recordFilter === 'errors' }"
              data-testid="workorder-filter-errors"
              @click="recordFilter = 'errors'"
            >
              错误
            </Button>
            <Button
              type="button"
              size="sm"
              :variant="recordFilter === 'selected' ? 'default' : 'ghost'"
              :class="{ 'is-active': recordFilter === 'selected' }"
              data-testid="workorder-filter-selected"
              @click="recordFilter = 'selected'"
            >
              已选
            </Button>
          </div>
        </div>

        <RecordTable
          class="workorder-record-table"
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
          v-if="records.length > 0 && filteredRecords.length === 0"
          class="workorder-empty py-6 text-center text-sm text-muted-foreground"
        >
          当前筛选条件下没有工单记录。
        </div>

        <div
          v-if="generating"
          class="workorder-export-progress space-y-2 rounded-md border bg-muted/30 p-3"
          data-testid="workorder-export-progress"
          aria-live="polite"
        >
          <div class="workorder-export-progress-head flex items-center justify-between text-sm">
            <strong>{{ exportProgressLabel }}</strong>
            <span data-testid="workorder-export-progress-percent">{{ exportProgressPercent }}%</span>
          </div>
          <div
            class="workorder-export-progress-track h-2 overflow-hidden rounded-full bg-muted"
            role="progressbar"
            :aria-valuenow="exportProgressPercent"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-label="exportProgressLabel"
          >
            <div
              class="workorder-export-progress-fill h-full bg-primary transition-[width]"
              :style="{ width: `${exportProgressPercent}%` }"
            />
          </div>
          <p v-if="exportProgress.total > 0" class="workorder-export-progress-meta text-xs text-muted-foreground">
            进度 {{ Math.min(exportProgress.current, exportProgress.total) }} / {{ exportProgress.total }}
          </p>
        </div>

        <div
          v-if="filteredRecords.length > 0"
          class="workorder-pagination flex items-center justify-center gap-3"
          data-testid="workorder-pagination"
        >
          <Button
            type="button"
            variant="outline"
            size="sm"
            class="workorder-page-btn"
            :disabled="currentPage <= 1 || generating"
            data-testid="workorder-page-prev"
            @click="goToPrevPage"
          >
            上一页
          </Button>
          <span class="workorder-page-status text-sm text-muted-foreground" data-testid="workorder-page-status">
            第 {{ currentPage }} / {{ totalPages }} 页
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            class="workorder-page-btn"
            :disabled="currentPage >= totalPages || generating"
            data-testid="workorder-page-next"
            @click="goToNextPage"
          >
            下一页
          </Button>
        </div>

        <footer class="workorder-list-foot flex flex-wrap items-center justify-between gap-3 border-t pt-4">
          <div class="workorder-list-foot-meta flex flex-wrap items-center gap-3 text-sm">
            <span>
              已选择 <strong>{{ selectedUids.length }}</strong> 个点位
            </span>
            <template v-if="selectedUids.length">
              <Button
                type="button"
                variant="link"
                class="workorder-text-btn h-auto px-0"
                :disabled="generating"
                @click="clearSelection"
              >
                取消选择
              </Button>
              <Button
                type="button"
                variant="link"
                class="workorder-text-btn is-danger h-auto px-0 text-destructive"
                :disabled="generating"
                @click="onBatchDelete"
              >
                删除选中
              </Button>
            </template>
          </div>
          <Button
            type="button"
            class="workorder-export-btn"
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
      :pest-type="pestType"
      :year="year"
      :generation="generation"
      @close="closeSurveyImportDialog"
      @import="onSurveyImport"
    />

    <ExcelImportDialog
      :busy="generating"
      :open="excelImportOpen"
      @close="closeExcelImportDialog"
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
