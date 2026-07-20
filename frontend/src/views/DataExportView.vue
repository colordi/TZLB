<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { Download, RefreshCw, Bug, Database, Layers } from "@lucide/vue";

import { listPestExportTypes, getPestExportMeta, downloadPestTypeExport } from "../api/dataExport.js";
import { isUnauthorizedError } from "../api/http.js";
import { useToast } from "../composables/useToast.js";
import { downloadBlob } from "../utils/download.js";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/native-select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

const TABLE_TYPE_LABELS = Object.freeze({
  table: "数据表",
  view: "视图",
});

const { error, success } = useToast();
const pestTypes = ref([]);
const loading = ref(false);
const downloadingPest = ref("");
const selectedPest = ref("");
const pestFilters = reactive({});
const currentPestMeta = ref(null);

const currentPest = computed(() => {
  return pestTypes.value.find((pt) => pt.pest_type === selectedPest.value) || pestTypes.value[0] || null;
});

function formatNumber(value) {
  return Number(value || 0).toLocaleString("zh-CN");
}

function tableLabel(objectType) {
  return TABLE_TYPE_LABELS[objectType] || objectType;
}

function initFilters(pest) {
  if (!pestFilters[pest.pest_type]) {
    pestFilters[pest.pest_type] = { year: "", generation: "" };
  }
}

async function loadCurrentPestMeta() {
  if (!currentPest.value) {
    currentPestMeta.value = null;
    return;
  }
  const pest = currentPest.value;
  const filters = pestFilters[pest.pest_type] || {};
  try {
    currentPestMeta.value = await getPestExportMeta(pest.pest_type, {
      year: filters.year || undefined,
      generation: filters.generation || undefined,
    });
  } catch (metaError) {
    if (isUnauthorizedError(metaError)) {
      return;
    }
    error(`${metaError.message || metaError}`, "读取筛选后记录数失败");
  }
}

function selectPest(pest) {
  selectedPest.value = pest.pest_type;
  initFilters(pest);
  const filters = pestFilters[pest.pest_type];
  if (filters.year && !pest.available_years?.includes(filters.year)) {
    filters.year = "";
  }
  if (filters.generation && !pest.available_generations?.includes(filters.generation)) {
    filters.generation = "";
  }
  loadCurrentPestMeta();
}

function filterLabel(pestType) {
  const f = pestFilters[pestType];
  if (!f || (!f.year && !f.generation)) return "";
  const parts = [];
  if (f.year) parts.push(`${f.year}年`);
  if (f.generation) parts.push(f.generation);
  return parts.join(" ");
}

async function loadPestTypes() {
  loading.value = true;
  try {
    pestTypes.value = await listPestExportTypes();
    for (const pest of pestTypes.value) {
      initFilters(pest);
    }
    if (
      !selectedPest.value ||
      !pestTypes.value.some((pt) => pt.pest_type === selectedPest.value)
    ) {
      selectedPest.value = pestTypes.value[0]?.pest_type || "";
    }
    currentPestMeta.value = currentPest.value;
  } catch (loadError) {
    pestTypes.value = [];
    selectedPest.value = "";
    if (isUnauthorizedError(loadError)) {
      return;
    }
    error(`${loadError.message || loadError}`, "读取虫种信息失败");
  } finally {
    loading.value = false;
  }
}

async function handleDownloadPest(pestType) {
  if (downloadingPest.value) {
    return;
  }

  downloadingPest.value = pestType;
  const filters = pestFilters[pestType] || {};
  try {
    const result = await downloadPestTypeExport(pestType, {
      year: filters.year || undefined,
      generation: filters.generation || undefined,
    });
    await downloadBlob(result.blob, result.filename);
    const label = filterLabel(pestType) || "全部";
    success(`${pestType}（${label}）已开始下载。`, "导出成功");
  } catch (downloadError) {
    if (isUnauthorizedError(downloadError)) {
      return;
    }
    error(`${downloadError.message || downloadError}`, "导出失败");
  } finally {
    downloadingPest.value = "";
  }
}

onMounted(loadPestTypes);
</script>

<template>
  <section class="mx-auto flex w-full max-w-6xl flex-col gap-4">
    <header class="space-y-1">
      <p class="text-[10px] font-bold tracking-[0.12em] text-primary">DATA EXPORT</p>
      <h1 class="text-2xl font-bold tracking-tight md:text-3xl">数据导出</h1>
      <p class="text-sm text-muted-foreground">
        按虫种导出调查数据和台账数据，选择虫种后可按年份/世代筛选并下载。
      </p>
    </header>

    <section
      v-if="!loading && pestTypes.length > 0"
      class="flex flex-wrap gap-2"
      aria-label="虫种选择"
    >
      <Button
        v-for="pest in pestTypes"
        :key="pest.pest_type"
        type="button"
        size="sm"
        :variant="selectedPest === pest.pest_type ? 'default' : 'outline'"
        :data-testid="`data-export-pest-${pest.pest_type}`"
        @click="selectPest(pest)"
      >
        <Bug class="size-4" />
        <span>{{ pest.pest_type }}</span>
      </Button>
    </section>

    <div
      v-if="loading"
      class="flex flex-col items-center gap-2 py-12 text-muted-foreground"
    >
      <RefreshCw class="size-7 animate-spin" />
      <p>正在读取虫种信息…</p>
    </div>
    <div
      v-else-if="pestTypes.length === 0"
      class="flex flex-col items-center gap-2 py-12 text-muted-foreground"
    >
      <Database class="size-7" />
      <p>暂无可导出的虫种数据。</p>
    </div>

    <Card
      v-else-if="currentPestMeta"
      :data-testid="`pest-panel-${currentPestMeta.pest_type}`"
    >
      <CardHeader class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div class="space-y-1">
          <CardTitle>{{ currentPestMeta.pest_type }}</CardTitle>
          <CardDescription>
            <strong class="text-foreground">{{ formatNumber(currentPestMeta.total_row_count) }}</strong>
            条记录，
            <strong class="text-foreground">{{ currentPestMeta.tables.length }}</strong>
            张表 / 视图
          </CardDescription>
        </div>

        <div class="flex flex-wrap items-center gap-2" aria-label="导出筛选条件">
          <label
            v-if="currentPestMeta.available_years?.length"
            class="flex items-center gap-2 text-sm text-muted-foreground"
          >
            <span>年份</span>
            <NativeSelect
              v-model="pestFilters[currentPestMeta.pest_type].year"
              @focus="initFilters(currentPestMeta)"
              @update:model-value="loadCurrentPestMeta"
            >
              <option value="">全部年份</option>
              <option
                v-for="y in currentPestMeta.available_years"
                :key="y"
                :value="y"
              >{{ y }}</option>
            </NativeSelect>
          </label>
          <label
            v-if="currentPestMeta.available_generations?.length"
            class="flex items-center gap-2 text-sm text-muted-foreground"
          >
            <span>世代</span>
            <NativeSelect
              v-model="pestFilters[currentPestMeta.pest_type].generation"
              @focus="initFilters(currentPestMeta)"
              @update:model-value="loadCurrentPestMeta"
            >
              <option value="">全部世代</option>
              <option
                v-for="g in currentPestMeta.available_generations"
                :key="g"
                :value="g"
              >{{ g }}</option>
            </NativeSelect>
          </label>

          <Button
            type="button"
            :disabled="Boolean(downloadingPest)"
            :data-testid="`pest-download-${currentPestMeta.pest_type}`"
            @click="handleDownloadPest(currentPestMeta.pest_type)"
          >
            <Download class="size-4" />
            <span>
              {{
                downloadingPest === currentPestMeta.pest_type
                  ? "导出中"
                  : filterLabel(currentPestMeta.pest_type) || "导出全部数据"
              }}
            </span>
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        <div class="overflow-hidden rounded-xl border shadow-sm">
          <div class="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>对象名称</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead class="text-right">记录数</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow
                  v-for="table in currentPestMeta.tables"
                  :key="`${table.schema_name}.${table.table_name}`"
                >
                  <TableCell>
                    <span class="inline-flex items-center gap-2 font-medium">
                      <Layers class="size-4 text-muted-foreground" />
                      {{ table.table_name }}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge
                      :variant="table.object_type === 'view' ? 'secondary' : 'outline'"
                      :class="cn(table.object_type === 'view' && 'text-primary')"
                    >
                      {{ tableLabel(table.object_type) }}
                    </Badge>
                  </TableCell>
                  <TableCell class="text-right font-medium text-muted-foreground">
                    {{ formatNumber(table.row_count) }}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        </div>
      </CardContent>
    </Card>
  </section>
</template>
