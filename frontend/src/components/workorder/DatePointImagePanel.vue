<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { CalendarDays, ImagePlus, LoaderCircle, Search, SearchX, Trash2 } from "@lucide/vue";

import { isUnauthorizedError } from "../../api/http.js";
import { fetchPointDateImageBlob } from "../../api/workorder.js";
import { useToast } from "../../composables/useToast.js";
import { useDatePointImages } from "../../composables/workorder/useDatePointImages.js";
import { useWorkorderTaskConfig } from "../../composables/workorder/useWorkorderTaskConfig.js";
import { getPestConfig, getSurveyImportConfig, getTodayDate } from "./fieldConfig.js";
import ConfirmDialog from "@/components/common/ConfirmDialog.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

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
  deletingCode,
  totalCount,
} = dateImages;
selectedDate.value = getTodayDate();

const dragOverCode = ref("");
const fileInput = ref(null);
const uploadTargetCode = ref("");
const pendingDeletePoint = ref(null);
const thumbnailUrls = reactive(new Map());
let thumbnailRequestId = 0;

const candidateColumns = computed(() =>
  getSurveyImportConfig(pestType.value)
    .columns.filter((column) => column.key !== "location_id")
    .slice(0, 3),
);
const autoAssemblyHint = computed(() =>
  getPestConfig(pestType.value).imageStrategy === "auto_disk_images"
    ? `${pestType.value}生成工单时会自动按编号从这些图片中装配现场图（点位截图优先，其次日期现场照）。`
    : "提示：自动装配日期图片的虫种会在生成工单时按编号装配现场图；其余虫种请使用点位截图或清单内图片。",
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

function revokeObjectUrl(url) {
  if (url && typeof URL !== "undefined" && typeof URL.revokeObjectURL === "function") {
    URL.revokeObjectURL(url);
  }
}

function releaseThumbnails() {
  thumbnailRequestId += 1;
  for (const url of thumbnailUrls.values()) {
    revokeObjectUrl(url);
  }
  thumbnailUrls.clear();
}

/** 通过 apiFetch 拉取缩略图 blob（<img> 直接请求无法携带本地免登请求头，会 401） */
async function loadThumbnails(images) {
  const requestId = ++thumbnailRequestId;
  const wanted = new Set(images.map((image) => image.file_name));
  for (const [name, url] of thumbnailUrls) {
    if (!wanted.has(name)) {
      revokeObjectUrl(url);
      thumbnailUrls.delete(name);
    }
  }

  await Promise.all(
    images.map(async (image) => {
      if (thumbnailUrls.has(image.file_name)) {
        return;
      }
      try {
        const url = await fetchPointDateImageBlob({
          surveyDate: selectedDate.value,
          fileName: image.file_name,
        });
        if (requestId !== thumbnailRequestId) {
          revokeObjectUrl(url);
          return;
        }
        thumbnailUrls.set(image.file_name, url);
      } catch (loadError) {
        if (!isUnauthorizedError(loadError)) {
          // 单个缩略图加载失败时保留占位，不阻塞其他图片
        }
      }
    }),
  );
}

function imageUrl(fileName) {
  return thumbnailUrls.get(fileName) || "";
}

function pointImageCount(point) {
  return dateImages.imagesForPoint(point).length;
}

function requestRemoveAll(point) {
  if (uploadingCode.value || deletingCode.value || pointImageCount(point) === 0) {
    return;
  }
  pendingDeletePoint.value = point;
}

function closeRemoveAllDialog() {
  if (!deletingCode.value) {
    pendingDeletePoint.value = null;
  }
}

async function confirmRemoveAll() {
  const point = pendingDeletePoint.value;
  if (!point || deletingCode.value) {
    return;
  }
  await dateImages.removePointImages(point, toast);
  pendingDeletePoint.value = null;
}

watch(
  () => dateImages.allImages.value,
  (images) => {
    void loadThumbnails(Array.isArray(images) ? images : []);
  },
);

onBeforeUnmount(() => {
  releaseThumbnails();
});

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
            查询当日需派单点位后，把图片拖到对应点位所在行即可自动上传到
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
            <span class="text-muted-foreground">事件日期</span>
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

    <EmptyState
      v-if="!queried"
      :icon="CalendarDays"
      title="尚未查询"
      description="选择条件后点击「查询需派单点位」。"
    />
    <EmptyState
      v-else-if="queried && points.length === 0"
      :icon="SearchX"
      title="没有需派单的点位"
      description="所选日期没有下派或复查异常点位，请先在数据导入中导入当日事件流水。"
      data-testid="date-point-empty"
    />

    <template v-else>
      <p class="text-sm text-muted-foreground" aria-live="polite">
        共 {{ totalCount }} 个需派单点位<template v-if="imagesLoading">，正在读取已上传图片…</template>
      </p>

      <div class="overflow-hidden rounded-xl border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow class="hover:bg-transparent">
              <TableHead class="w-28">编号</TableHead>
              <TableHead v-for="column in candidateColumns" :key="column.key">
                {{ column.label }}
              </TableHead>
              <TableHead>现场照片</TableHead>
              <TableHead class="w-36 text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="point in points"
              :key="pointCode(point)"
              :class="{ 'bg-primary/10 hover:bg-primary/10': dragOverCode === pointCode(point) }"
              :data-testid="`date-point-row-${pointCode(point)}`"
              @dragover="onDragOver($event, point)"
              @dragleave="onDragLeave(point)"
              @drop="onDrop($event, point)"
            >
              <TableCell class="font-medium">{{ pointCode(point) || "未填写编号" }}</TableCell>
              <TableCell
                v-for="column in candidateColumns"
                :key="column.key"
                class="max-w-44 truncate"
              >
                {{ formatValue(point, column) }}
              </TableCell>
              <TableCell>
                <div class="flex flex-wrap items-center gap-1.5">
                  <figure
                    v-for="image in dateImages.imagesForPoint(point)"
                    :key="image.file_name"
                    class="size-16 overflow-hidden rounded border bg-muted"
                  >
                    <img
                      v-if="imageUrl(image.file_name)"
                      class="size-full object-cover"
                      :src="imageUrl(image.file_name)"
                      :alt="image.file_name"
                      :title="image.file_name"
                      loading="lazy"
                    />
                  </figure>
                  <span
                    v-if="!dateImages.imagesForPoint(point).length"
                    class="text-xs text-muted-foreground"
                  >
                    暂无
                  </span>
                </div>
              </TableCell>
              <TableCell class="text-right">
                <div class="flex flex-col items-end gap-1.5">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    class="w-28 border-dashed"
                    :disabled="Boolean(uploadingCode) || Boolean(deletingCode) || !pointCode(point)"
                    :title="`${pointCode(point)}：拖拽图片到本行，或点击选择`"
                    :data-testid="`date-point-upload-${pointCode(point)}`"
                    @click="openFilePicker(point)"
                  >
                    <LoaderCircle v-if="uploadingCode === pointCode(point)" class="size-3.5 animate-spin" />
                    <ImagePlus v-else class="size-3.5" />
                    {{ uploadingCode === pointCode(point) ? "上传中…" : "上传图片" }}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    class="w-28 text-destructive hover:bg-destructive/10 hover:text-destructive"
                    :disabled="Boolean(uploadingCode) || Boolean(deletingCode) || pointImageCount(point) === 0"
                    :data-testid="`date-point-delete-all-${pointCode(point)}`"
                    @click="requestRemoveAll(point)"
                  >
                    <LoaderCircle v-if="deletingCode === pointCode(point)" class="size-3.5 animate-spin" />
                    <Trash2 v-else class="size-3.5" />
                    {{ deletingCode === pointCode(point) ? "删除中…" : "删除全部" }}
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
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

    <ConfirmDialog
      :open="Boolean(pendingDeletePoint)"
      title="删除该点位的全部现场照片"
      :message="pendingDeletePoint
        ? `确认删除 ${pointCode(pendingDeletePoint)} 在 ${selectedDate} 下的 ${pointImageCount(pendingDeletePoint)} 张现场照片吗？此操作不可撤销。`
        : ''"
      :busy="Boolean(deletingCode)"
      confirm-text="确认全部删除"
      @close="closeRemoveAllDialog"
      @confirm="confirmRemoveAll"
    />
  </section>
</template>
