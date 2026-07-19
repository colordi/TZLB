<script setup>
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";
import { FileSpreadsheet } from "@lucide/vue";

import { isUnauthorizedError } from "../api/http.js";
import { downloadImportTemplate, uploadSurveyExcel } from "../api/survey.js";
import { useToast } from "../composables/useToast.js";
import { downloadBlob } from "../utils/download.js";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const { error, info, success } = useToast();

const selectedFile = ref(null);
const previewResult = ref(null);
const loading = ref(false);
const committing = ref(false);
const downloadingTemplate = ref(false);

const totals = computed(() => previewResult.value?.totals || {});
const hasErrors = computed(() => Number(totals.value.error_count || 0) > 0);
const importableRows = computed(
  () =>
    Number(totals.value.valid_rows || 0) -
    Number(totals.value.skipped_duplicate_rows || 0),
);
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

function formatSheetTarget(sheet) {
  if (!sheet?.schema_name || !sheet?.table_name) {
    return "未匹配可写表";
  }
  return `${sheet.schema_name}.${sheet.table_name}`;
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
  <section class="data-import-page mx-auto flex w-full max-w-6xl flex-col gap-4">
    <header class="space-y-1">
      <h1 class="text-2xl font-bold tracking-tight md:text-3xl">调查数据导入</h1>
      <p class="max-w-3xl text-sm text-muted-foreground">
        将 Excel 写入 survey / ledger 表。此处不会进入工单清单；入库后请到
        <RouterLink class="font-medium text-primary underline-offset-4 hover:underline" to="/workorder">
          工单录入
        </RouterLink>
        从数据库选取点位。
      </p>
    </header>

    <Card>
      <CardHeader class="pb-3">
        <CardTitle class="flex items-center gap-2 text-base">
          <FileSpreadsheet class="size-4" />
          Excel 入库
        </CardTitle>
      </CardHeader>
      <CardContent class="space-y-4">
        <div class="rounded-lg border bg-muted/20 p-4 text-sm text-muted-foreground">
          sheet 名必须与 survey 或 ledger 下的可写表名完全一致；先预览校验，确认后才会写入数据库。
        </div>

        <div class="flex flex-wrap items-end gap-3 rounded-lg border p-4">
          <label class="grid min-w-[16rem] flex-1 gap-1.5" for="survey-excel-file">
            <span class="text-xs font-medium text-muted-foreground">本地 Excel 文件</span>
            <input
              id="survey-excel-file"
              type="file"
              class="block w-full text-sm"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              :disabled="loading || committing"
              data-testid="survey-excel-file"
              @change="handleFileChange"
            />
          </label>
          <Button
            type="button"
            :disabled="!selectedFile || loading || committing"
            data-testid="survey-excel-preview"
            @click="handlePreview"
          >
            {{ loading ? "校验中…" : "预览校验" }}
          </Button>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-4">
          <p class="text-sm text-muted-foreground">
            请先下载导入模板，按模板表头填写后再上传。
          </p>
          <Button
            type="button"
            variant="outline"
            :disabled="downloadingTemplate"
            data-testid="survey-excel-download-template"
            @click="handleDownloadTemplate"
          >
            {{ downloadingTemplate ? "正在下载模板…" : "下载导入模板" }}
          </Button>
        </div>

        <div v-if="previewResult" class="space-y-3" data-testid="excel-import-result">
          <div class="flex flex-wrap gap-2 text-xs">
            <span class="rounded-md border px-2 py-1 text-muted-foreground">
              sheet {{ totals.sheet_count || 0 }}
            </span>
            <span class="rounded-md border px-2 py-1 text-muted-foreground">
              总行数 {{ totals.row_count || 0 }}
            </span>
            <span class="rounded-md border px-2 py-1 text-muted-foreground">
              可导入 {{ importableRows }}
            </span>
            <span class="rounded-md border px-2 py-1 text-muted-foreground">
              跳过重复 {{ totals.skipped_duplicate_rows || 0 }}
            </span>
            <span
              class="rounded-md border px-2 py-1"
              :class="hasErrors ? 'border-destructive text-destructive' : 'text-muted-foreground'"
            >
              错误 {{ totals.error_count || 0 }}
            </span>
          </div>

          <div class="grid gap-3">
            <article
              v-for="sheet in previewResult.sheets"
              :key="sheet.sheet_name"
              class="rounded-lg border p-4"
            >
              <div class="flex flex-wrap items-baseline justify-between gap-2">
                <strong class="text-sm">{{ sheet.sheet_name }}</strong>
                <span class="text-xs text-muted-foreground">{{ formatSheetTarget(sheet) }}</span>
              </div>
              <p class="mt-2 text-xs text-muted-foreground">
                总行数 {{ sheet.row_count }} / 有效 {{ sheet.valid_rows }} / 已导入
                {{ sheet.inserted_rows }} / 跳过 {{ sheet.skipped_duplicate_rows }}
              </p>
              <ul v-if="sheet.warnings?.length" class="mt-2 list-disc pl-5 text-xs text-muted-foreground">
                <li v-for="warning in sheet.warnings" :key="warning">{{ warning }}</li>
              </ul>
              <ul v-if="sheet.errors?.length" class="mt-2 list-disc pl-5 text-xs text-destructive">
                <li v-for="sheetError in sheet.errors" :key="sheetError">{{ sheetError }}</li>
              </ul>
            </article>
          </div>
        </div>

        <div
          v-else
          class="grid min-h-40 place-items-center rounded-lg border border-dashed px-6 py-10 text-center text-sm text-muted-foreground"
        >
          选择 .xlsx 文件后先预览，系统会校验 sheet 名、列名、必填项和重复记录。
        </div>

        <div class="flex justify-end border-t pt-4">
          <Button
            type="button"
            :disabled="!canConfirm"
            data-testid="survey-excel-confirm"
            @click="handleConfirm"
          >
            {{ committing ? "正在入库…" : "确认入库" }}
          </Button>
        </div>
      </CardContent>
    </Card>
  </section>
</template>
