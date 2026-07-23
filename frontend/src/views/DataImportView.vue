<script setup>
import { computed, ref } from "vue";
import {
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Inbox,
  Info,
  Upload,
  X,
  XCircle,
} from "@lucide/vue";

import { isUnauthorizedError } from "../api/http.js";
import { downloadImportTemplate, uploadSurveyExcel } from "../api/survey.js";
import { useToast } from "../composables/useToast.js";
import { downloadBlob } from "../utils/download.js";
import PageHeader from "@/components/common/PageHeader.vue";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const { error, info, success } = useToast();

const fileInputRef = ref(null);
const selectedFile = ref(null);
const previewResult = ref(null);
const loading = ref(false);
const committing = ref(false);
const downloadingTemplate = ref(false);

const totals = computed(() => previewResult.value?.totals || {});
const hasErrors = computed(() => Number(totals.value.error_count || 0) > 0);
const importableRows = computed(() => {
  if (totals.value.importable_rows != null) {
    return Number(totals.value.importable_rows || 0);
  }
  return (
    Number(totals.value.valid_rows || 0) -
    Number(totals.value.skipped_duplicate_rows || 0)
  );
});
const canConfirm = computed(
  () =>
    !loading.value &&
    !committing.value &&
    previewResult.value &&
    !hasErrors.value &&
    importableRows.value > 0,
);

function handleFileChange(event) {
  const file = event.target.files?.[0] || null;
  selectedFile.value = file;
  previewResult.value = null;
}

function triggerFileSelect() {
  fileInputRef.value?.click();
}

function clearSelectedFile() {
  if (fileInputRef.value) {
    fileInputRef.value.value = "";
  }
  selectedFile.value = null;
  previewResult.value = null;
}

function sheetHasErrors(sheet) {
  return Boolean(sheet?.errors?.length);
}

function formatSheetTarget(sheet) {
  if (!sheet?.schema_name || !sheet?.table_name) {
    return "未匹配可写表";
  }
  return `${sheet.schema_name}.${sheet.table_name}`;
}

function formatNamedCounts(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return "";
  }
  return items.map((item) => `${item.name} ${item.count}`).join(" · ");
}

function sheetStats(sheet) {
  return sheet?.stats || {};
}

function hasLocalityStats(sheet) {
  return Boolean(sheetStats(sheet).by_locality?.length);
}

function hasDamageStats(sheet) {
  const stats = sheetStats(sheet);
  return stats.damaged_count != null || stats.undamaged_count != null;
}

function hasEventTypeStats(sheet) {
  return Boolean(sheetStats(sheet).by_event_type?.length);
}

function hasBusinessStats(sheet) {
  return (
    hasLocalityStats(sheet) || hasDamageStats(sheet) || hasEventTypeStats(sheet)
  );
}

async function handleDownloadTemplate() {
  if (downloadingTemplate.value) {
    return;
  }

  downloadingTemplate.value = true;
  try {
    const { blob, filename } = await downloadImportTemplate();
    await downloadBlob(blob, filename);
    success("导入模板已下载。", "下载完成");
  } catch (downloadError) {
    if (isUnauthorizedError(downloadError)) {
      return;
    }
    error(`${downloadError.message || downloadError}`, "模板下载失败");
  } finally {
    downloadingTemplate.value = false;
  }
}

async function handlePreview() {
  if (!selectedFile.value) {
    info("请先选择一个 .xlsx 文件。", "缺少文件");
    return;
  }

  loading.value = true;
  try {
    previewResult.value = await uploadSurveyExcel({
      file: selectedFile.value,
      dryRun: true,
    });
    if (hasErrors.value) {
      error("Excel 存在校验错误，暂未入库。", "预览失败");
    } else if (importableRows.value === 0) {
      info("没有可导入的新记录。", "预览完成");
    } else {
      success(`校验通过，可导入 ${importableRows.value} 条记录。`, "预览完成");
    }
  } catch (previewError) {
    if (isUnauthorizedError(previewError)) {
      return;
    }
    error(`${previewError.message || previewError}`, "Excel 预览失败");
  } finally {
    loading.value = false;
  }
}

async function handleConfirm() {
  if (!canConfirm.value || !selectedFile.value) {
    return;
  }

  committing.value = true;
  try {
    const result = await uploadSurveyExcel({
      file: selectedFile.value,
      dryRun: false,
    });
    previewResult.value = result;

    if (Number(result.totals?.error_count || 0) > 0) {
      error("确认导入前数据发生变化，已取消入库。", "导入失败");
      return;
    }

    success(`已导入 ${result.totals?.inserted_rows || 0} 条记录。`, "导入完成");
  } catch (commitError) {
    if (isUnauthorizedError(commitError)) {
      return;
    }
    error(`${commitError.message || commitError}`, "Excel 入库失败");
  } finally {
    committing.value = false;
  }
}
</script>

<template>
  <div class="mx-auto w-full max-w-6xl space-y-6">
    <PageHeader
      title="数据导入"
      description="将 Excel 写入数据库；入库后请到「工单录入」中生成工单。"
    />

    <Card>
      <CardContent class="space-y-4">
        <div class="flex items-center gap-2 rounded-lg bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
          <Info class="size-3.5 shrink-0" />
          <p>导入的 sheet 需和模板字段完全一致；先预览校验，确认后才会写入数据库。</p>
        </div>

        <!-- 操作行：选择文件 → 预览校验 → 下载模板 -->
        <div class="flex flex-wrap items-center gap-2">
          <input
            id="survey-excel-file"
            ref="fileInputRef"
            type="file"
            class="sr-only"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            :disabled="loading || committing"
            data-testid="survey-excel-file"
            @change="handleFileChange"
          />
          <template v-if="selectedFile">
            <span class="flex h-8 min-w-0 max-w-72 items-center gap-2 rounded-md border bg-muted/30 px-2.5 text-sm">
              <FileSpreadsheet class="size-4 shrink-0 text-muted-foreground" />
              <span class="truncate">{{ selectedFile.name }}</span>
            </span>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              class="shrink-0"
              :disabled="loading || committing"
              aria-label="清除已选文件"
              @click="clearSelectedFile"
            >
              <X class="size-4" />
            </Button>
          </template>
          <Button
            v-else
            type="button"
            variant="outline"
            size="sm"
            :disabled="loading || committing"
            @click="triggerFileSelect"
          >
            <Upload class="size-4" />
            选择 Excel 文件
          </Button>
          <Button
            type="button"
            size="sm"
            :disabled="!selectedFile || loading || committing"
            data-testid="survey-excel-preview"
            @click="handlePreview"
          >
            {{ loading ? "校验中…" : "预览校验" }}
          </Button>
          <span class="text-xs text-muted-foreground">仅支持 .xlsx</span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            class="ml-auto"
            :disabled="downloadingTemplate"
            data-testid="survey-excel-download-template"
            @click="handleDownloadTemplate"
          >
            <Download class="size-4" />
            {{ downloadingTemplate ? "正在下载模板…" : "下载模板" }}
          </Button>
        </div>

        <!-- 校验结果 -->
        <div v-if="previewResult" class="space-y-2" data-testid="excel-import-result">
          <p class="text-sm font-medium">校验结果</p>

          <div class="divide-y rounded-lg border">
            <div
              v-for="sheet in previewResult.sheets"
              :key="sheet.sheet_name"
              class="px-3 py-2.5"
              :class="{ 'bg-destructive/5': sheetHasErrors(sheet) }"
            >
              <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
                <span class="flex items-center gap-1.5">
                  <XCircle
                    v-if="sheetHasErrors(sheet)"
                    class="size-4 text-destructive"
                  />
                  <CheckCircle2 v-else class="size-4 text-success" />
                  <strong class="text-sm font-medium">{{ sheet.sheet_name }}</strong>
                </span>
                <Badge variant="outline" class="ml-auto font-mono font-normal">
                  {{ formatSheetTarget(sheet) }}
                </Badge>
              </div>

              <div
                v-if="hasBusinessStats(sheet)"
                class="mt-1.5 space-y-0.5 text-xs text-muted-foreground"
              >
                <p v-if="hasLocalityStats(sheet)">
                  属地：{{ formatNamedCounts(sheetStats(sheet).by_locality) }}
                </p>
                <p v-if="hasDamageStats(sheet)">
                  受害点位 {{ sheetStats(sheet).damaged_count ?? 0 }} · 无受害点位
                  {{ sheetStats(sheet).undamaged_count ?? 0 }}
                </p>
                <p v-if="hasEventTypeStats(sheet)">
                  事件类型：{{ formatNamedCounts(sheetStats(sheet).by_event_type) }}
                </p>
              </div>

              <ul v-if="sheet.warnings?.length" class="mt-1 list-disc pl-5 text-xs text-muted-foreground">
                <li v-for="warning in sheet.warnings" :key="warning">{{ warning }}</li>
              </ul>
              <ul v-if="sheet.errors?.length" class="mt-1 list-disc pl-5 text-xs text-destructive">
                <li v-for="sheetError in sheet.errors" :key="sheetError">{{ sheetError }}</li>
              </ul>
            </div>
          </div>
        </div>

        <div
          v-else
          class="flex items-center justify-center gap-2 rounded-lg border border-dashed px-4 py-4 text-xs text-muted-foreground"
        >
          <Inbox class="size-4 text-muted-foreground/50" />
          <p>选择 .xlsx 文件后先预览，系统会校验 sheet 名、列名、必填项和重复记录。</p>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-3 border-t pt-3">
          <p class="text-xs text-muted-foreground">
            <template v-if="canConfirm">共 {{ importableRows }} 条记录待入库</template>
            <template v-else>请先通过预览校验后再入库</template>
          </p>
          <Button
            type="button"
            size="sm"
            :disabled="!canConfirm"
            data-testid="survey-excel-confirm"
            @click="handleConfirm"
          >
            {{ committing ? "正在入库…" : "确认入库" }}
          </Button>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
