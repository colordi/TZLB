<script setup>
import { computed, ref, watch } from "vue";
import { ImagePlus, LoaderCircle, Search, Trash2 } from "@lucide/vue";

import { buildPointDateImageUrl } from "../../api/workorder.js";
import { useToast } from "../../composables/useToast.js";
import { useDatePointImages } from "../../composables/workorder/useDatePointImages.js";
import { useWorkorderTaskConfig } from "../../composables/workorder/useWorkorderTaskConfig.js";
import { getSurveyImportConfig, getTodayDate } from "./fieldConfig.js";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";

const toast = useToast();

const taskConfig = useWorkorderTaskConfig();
const { PEST_OPTIONS, pestType, year, taskName, generation, taskOptions, yearOptions } = taskConfig;
pestType.value = "美国白蛾";

const dateImages = useDatePointImages();
const {
  selectedDate,
  points,
  queried,
  loading,
  imagesLoading,
  uploadingCode,
  deletingFile,
  totalCount,
} = dateImages;
selectedDate.value = getTodayDate();

const dragOverCode = ref("");
const fileInput = ref(null);
const uploadTargetCode = ref("");

const candidateColumns = computed(() =>
  getSurveyImportConfig(pestType.value)
    .columns.filter((column) => column.key !== "location_id")
    .slice(0, 3),
);
const autoAssemblyHint = computed(() =>
  pestType.value === "美国白蛾"
    ? "美国白蛾生成工单时会自动按编号从这些图片中装配现场图。"
    : "提示：目前仅美国白蛾生成工单时自动装配日期图片，其他害虫请使用点位截图或清单内图片。",
);

watch([pestType, year, taskName, selectedDate], () => {
  dateImages.resetResults();
});

function pointCode(point) {
  return `${point?.location_id ?? ""}`.trim();
}

function formatValue(point, column) {
  const text = `${point?.[column.key] ?? ""}`.trim();
  return text === "" ? column.fallback : text;
}

function imageUrl(fileName) {
  return buildPointDateImageUrl({ surveyDate: selectedDate.value, fileName });
}

function handleQuery() {
  dateImages.queryPoints(
    { pestType: pestType.value, year: year.value, generation: generation.value },
    toast,
  );
}

function onDragOver(event, point) {
  if (uploadingCode.value) {
    return;
  }
  event.preventDefault();
  dragOverCode.value = pointCode(point);
}

function onDragLeave(point) {
  if (dragOverCode.value === pointCode(point)) {
    dragOverCode.value = "";
  }
}

function onDrop(event, point) {
  event.preventDefault();
  dragOverCode.value = "";
  dateImages.uploadToPoint(point, event.dataTransfer?.files, toast);
}

function openFilePicker(point) {
  if (uploadingCode.value || !fileInput.value) {
    return;
  }
  uploadTargetCode.value = pointCode(point);
  fileInput.value.value = "";
  fileInput.value.click();
}

function onFileChange(event) {
  const input = event.target;
  const point = points.value.find((item) => pointCode(item) === uploadTargetCode.value);
  if (point && input.files?.length) {
    dateImages.uploadToPoint(point, input.files, toast);
  }
  uploadTargetCode.value = "";
  input.value = "";
}
</script>

<template>
  <section class="date-point-image-panel flex w-full flex-col gap-4" aria-label="日期现场照片">
    <Card>
      <CardHeader class="pb-3">
        <CardTitle class="text-base">按点位上传当日现场照片</CardTitle>
      </CardHeader>
      <CardContent class="space-y-4">
        <div class="space-y-1 text-sm text-muted-foreground">
          <p>
            查询当日需派单点位后，把图片拖到对应点位卡片上即可自动上传到
            <code class="rounded bg-muted px-1 py-0.5 text-xs">images/日期/</code>
            并按
            <code class="rounded bg-muted px-1 py-0.5 text-xs">点位编号-序号</code>
            自动重命名，无需在本地预先改名。
          </p>
          <p>{{ autoAssemblyHint }}</p>
        </div>

        <div class="flex flex-wrap items-end gap-3">
          <label class="flex flex-col gap-1.5 text-sm">
            <span class="text-muted-foreground">害虫类型</span>
            <NativeSelect
              v-model="pestType"
              class="h-9 py-1"
              :disabled="loading"
              data-testid="date-point-pest-type"
            >
              <option v-for="option in PEST_OPTIONS" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </NativeSelect>
          </label>
          <label class="flex flex-col gap-1.5 text-sm">
            <span class="text-muted-foreground">年份</span>
            <NativeSelect
              v-model="year"
              class="h-9 py-1"
              :disabled="loading"
              data-testid="date-point-year"
            >
              <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}</option>
            </NativeSelect>
          </label>
          <label class="flex flex-col gap-1.5 text-sm">
            <span class="text-muted-foreground">统防统治任务</span>
            <NativeSelect
              v-model="taskName"
              class="h-9 py-1"
              :disabled="loading || !taskOptions.length"
              data-testid="date-point-task"
            >
              <option v-if="!taskOptions.length" value="">暂无预设任务</option>
              <option v-for="option in taskOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </NativeSelect>
          </label>
          <label class="flex flex-col gap-1.5 text-sm">
            <span class="text-muted-foreground">调查日期</span>
            <Input
              v-model="selectedDate"
              type="date"
              class="h-9 w-40"
              :disabled="loading"
              data-testid="date-point-survey-date"
            />
          </label>
          <Button
            type="button"
            class="h-9"
            :disabled="loading || !taskName || !selectedDate"
            data-testid="date-point-query-button"
            @click="handleQuery"
          >
            <LoaderCircle v-if="loading" class="size-4 animate-spin" />
            <Search v-else class="size-4" />
            {{ loading ? "查询中…" : "查询需派单点位" }}
          </Button>
        </div>
      </CardContent>
    </Card>

    <div v-if="!queried" class="py-8 text-center text-sm text-muted-foreground">
      选择条件后点击「查询需派单点位」。
    </div>
    <div
      v-else-if="queried && points.length === 0"
      class="py-8 text-center text-sm text-muted-foreground"
      data-testid="date-point-empty"
    >
      所选日期没有需派单的点位，请先在数据导入中导入当日调查数据。
    </div>

    <template v-else>
      <p class="text-sm text-muted-foreground" aria-live="polite">
        共 {{ totalCount }} 个需派单点位<template v-if="imagesLoading">，正在读取已上传图片…</template>
      </p>

      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-live="polite">
        <article
          v-for="point in points"
          :key="pointCode(point)"
          class="rounded-lg border bg-card p-3 transition-colors"
          :class="dragOverCode === pointCode(point) ? 'border-primary bg-primary/5 ring-2 ring-primary/30' : ''"
          :data-testid="`date-point-card-${pointCode(point)}`"
          @dragover="onDragOver($event, point)"
          @dragleave="onDragLeave(point)"
          @drop="onDrop($event, point)"
        >
          <header class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <strong class="block truncate text-sm">{{ pointCode(point) || "未填写编号" }}</strong>
              <span
                v-for="column in candidateColumns"
                :key="column.key"
                class="block truncate text-xs text-muted-foreground"
              >
                {{ column.label }}：{{ formatValue(point, column) }}
              </span>
            </div>
            <Badge :variant="dateImages.imagesForPoint(point).length ? 'default' : 'secondary'">
              {{ dateImages.imagesForPoint(point).length }} 张
            </Badge>
          </header>

          <div
            v-if="dateImages.imagesForPoint(point).length"
            class="mt-2 flex flex-wrap gap-2"
          >
            <figure
              v-for="image in dateImages.imagesForPoint(point)"
              :key="image.file_name"
              class="group relative size-16 overflow-hidden rounded-md border"
            >
              <img
                class="size-full object-cover"
                :src="imageUrl(image.file_name)"
                :alt="image.file_name"
                :title="image.file_name"
                loading="lazy"
              />
              <button
                type="button"
                class="absolute inset-0 hidden items-center justify-center bg-black/50 text-white group-hover:flex"
                :disabled="deletingFile === image.file_name"
                :aria-label="`删除 ${image.file_name}`"
                :data-testid="`date-point-delete-${image.file_name}`"
                @click.stop="dateImages.removeImage(point, image.file_name, toast)"
              >
                <Trash2 class="size-4" />
              </button>
            </figure>
          </div>

          <Button
            type="button"
            variant="outline"
            size="sm"
            class="mt-2 w-full border-dashed"
            :disabled="Boolean(uploadingCode) || !pointCode(point)"
            :data-testid="`date-point-upload-${pointCode(point)}`"
            @click="openFilePicker(point)"
          >
            <LoaderCircle v-if="uploadingCode === pointCode(point)" class="size-3.5 animate-spin" />
            <ImagePlus v-else class="size-3.5" />
            {{ uploadingCode === pointCode(point) ? "上传中…" : "拖拽图片到此卡片，或点击选择" }}
          </Button>
        </article>
      </div>
    </template>

    <input
      ref="fileInput"
      hidden
      type="file"
      multiple
      accept="image/jpeg,image/png,image/webp"
      data-testid="date-point-file-input"
      @change="onFileChange"
    />
  </section>
</template>
