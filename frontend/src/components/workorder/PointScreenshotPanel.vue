<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import {
  ChevronLeft,
  ChevronRight,
  Image,
  ImageOff,
  Search,
  SearchX,
  Trash2,
  Upload,
} from "@lucide/vue";

import {
  deletePointScreenshot,
  fetchPointScreenshotBlob,
  listPointScreenshotStatus,
  uploadPointScreenshot,
} from "../../api/pointScreenshot.js";
import { isUnauthorizedError } from "../../api/http.js";
import ConfirmDialog from "@/components/common/ConfirmDialog.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import { useToast } from "../../composables/useToast.js";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

const PEST_TABS = Object.freeze([
  { pestType: "春尺蠖", label: "杨树点位截图" },
  { pestType: "国槐尺蠖", label: "国槐点位截图" },
  { pestType: "美国白蛾", label: "美国白蛾截图" },
]);
const PAGE_SIZE = 48;
const ACCEPTED_IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

const toast = useToast();
const STATUS_FILTERS = Object.freeze([
  { value: "all", label: "总点位", testId: "point-screenshot-total" },
  { value: "existing", label: "已有截图", testId: "point-screenshot-existing" },
  { value: "missing", label: "缺失", testId: "point-screenshot-missing" },
]);

const pestType = ref("美国白蛾");
const points = ref([]);
const searchInput = ref("");
const searchQuery = ref("");
const statusFilter = ref("all");
const loading = ref(false);
const loadFailed = ref(false);
const fileInput = ref(null);
const uploadTarget = ref(null);
const uploadingCode = ref("");
const dragOverCode = ref("");
const pendingDelete = ref(null);
const deletingCode = ref("");
const currentPage = ref(1);
const thumbnailUrls = reactive(new Map());
const thumbnailStates = reactive(new Map());
const lightbox = ref(null);
let loadRequestId = 0;
let thumbnailRequestId = 0;
let lightboxRequestId = 0;
let componentActive = false;

const total = computed(() => points.value.length);
const hasScreenshot = computed(
  () => points.value.filter((point) => point.has_screenshot).length,
);
const missing = computed(() => total.value - hasScreenshot.value);
const operationBusy = computed(() => Boolean(uploadingCode.value || deletingCode.value));

const statusFilterCount = computed(() => ({
  all: total.value,
  existing: hasScreenshot.value,
  missing: missing.value,
}));

const filteredPoints = computed(() => {
  let result = points.value;
  if (statusFilter.value === "existing") {
    result = result.filter((point) => point.has_screenshot);
  } else if (statusFilter.value === "missing") {
    result = result.filter((point) => !point.has_screenshot);
  }

  const query = searchQuery.value.trim().toLocaleLowerCase("zh-CN");
  if (!query) {
    return result;
  }

  return result.filter((point) =>
    [point.code, point.name, point.locality]
      .some((value) => String(value ?? "").toLocaleLowerCase("zh-CN").includes(query)),
  );
});

const emptyFilterMessage = computed(() => {
  if (searchQuery.value.trim() && statusFilter.value !== "all") {
    return "没有同时符合状态筛选与搜索条件的点位。";
  }
  if (searchQuery.value.trim()) {
    return "没有符合搜索条件的点位。";
  }
  if (statusFilter.value === "existing") {
    return "当前没有已有截图的点位。";
  }
  if (statusFilter.value === "missing") {
    return "当前没有缺失截图的点位。";
  }
  return "没有符合条件的点位。";
});
const totalPages = computed(() =>
  Math.max(1, Math.ceil(filteredPoints.value.length / PAGE_SIZE)),
);
const paginatedPoints = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE;
  return filteredPoints.value.slice(start, start + PAGE_SIZE);
});

function pointKey(point) {
  return String(point?.code ?? "");
}

function revokeObjectUrl(url) {
  if (url && typeof URL !== "undefined" && typeof URL.revokeObjectURL === "function") {
    URL.revokeObjectURL(url);
  }
}

function releaseThumbnailUrls() {
  thumbnailRequestId += 1;
  for (const url of thumbnailUrls.values()) {
    revokeObjectUrl(url);
  }
  thumbnailUrls.clear();
  thumbnailStates.clear();
}

async function loadThumbnail(point, requestId, previewRequestId, requestedPestType) {
  const code = pointKey(point);
  thumbnailStates.set(code, "loading");
  try {
    const url = await fetchPointScreenshotBlob(requestedPestType, code, { size: "thumb" });
    if (
      !componentActive ||
      requestId !== loadRequestId ||
      previewRequestId !== thumbnailRequestId ||
      requestedPestType !== pestType.value
    ) {
      revokeObjectUrl(url);
      return;
    }
    thumbnailUrls.set(code, url);
    thumbnailStates.set(code, "loaded");
  } catch (error) {
    if (
      componentActive &&
      requestId === loadRequestId &&
      previewRequestId === thumbnailRequestId &&
      requestedPestType === pestType.value
    ) {
      thumbnailStates.set(code, "error");
    }
    if (isUnauthorizedError(error)) {
      return;
    }
  }
}

function closeLightbox() {
  lightboxRequestId += 1;
  const current = lightbox.value;
  if (current?.url) {
    revokeObjectUrl(current.url);
  }
  lightbox.value = null;
}

async function openLightbox(point) {
  if (!point?.has_screenshot || operationBusy.value) {
    return;
  }

  const code = pointKey(point);
  const requestedPestType = pestType.value;
  const requestId = ++lightboxRequestId;

  if (lightbox.value?.url) {
    revokeObjectUrl(lightbox.value.url);
  }

  lightbox.value = {
    code,
    name: point.name || "",
    url: "",
    loading: true,
    error: false,
  };

  try {
    const url = await fetchPointScreenshotBlob(requestedPestType, code, { size: "full" });
    if (
      !componentActive ||
      requestId !== lightboxRequestId ||
      requestedPestType !== pestType.value
    ) {
      revokeObjectUrl(url);
      return;
    }
    lightbox.value = {
      code,
      name: point.name || "",
      url,
      loading: false,
      error: false,
    };
  } catch (error) {
    if (
      componentActive &&
      requestId === lightboxRequestId &&
      requestedPestType === pestType.value
    ) {
      lightbox.value = {
        code,
        name: point.name || "",
        url: "",
        loading: false,
        error: true,
      };
    }
    if (isUnauthorizedError(error)) {
      return;
    }
  }
}

function loadCurrentPageThumbnails(requestId = loadRequestId) {
  if (!componentActive) {
    return;
  }

  const requestedPestType = pestType.value;
  releaseThumbnailUrls();
  const previewRequestId = thumbnailRequestId;
  const visiblePointsWithScreenshot = paginatedPoints.value.filter(
    (point) => point.has_screenshot,
  );
  void Promise.all(
    visiblePointsWithScreenshot.map((point) =>
      loadThumbnail(point, requestId, previewRequestId, requestedPestType),
    ),
  );
}

async function loadPoints() {
  if (!componentActive) {
    return;
  }

  const requestId = ++loadRequestId;
  const requestedPestType = pestType.value;
  loading.value = true;
  loadFailed.value = false;
  points.value = [];
  currentPage.value = 1;
  releaseThumbnailUrls();

  try {
    const payload = await listPointScreenshotStatus(requestedPestType);
    if (
      !componentActive ||
      requestId !== loadRequestId ||
      requestedPestType !== pestType.value
    ) {
      return;
    }

    points.value = Array.isArray(payload?.points) ? payload.points : [];
    loadCurrentPageThumbnails(requestId);
  } catch (error) {
    if (requestId !== loadRequestId) {
      return;
    }
    loadFailed.value = true;
    if (!isUnauthorizedError(error)) {
      toast.error(`${error.message || error}`, "加载点位失败");
    }
  } finally {
    if (requestId === loadRequestId) {
      loading.value = false;
    }
  }
}

function applySearch() {
  const nextQuery = searchInput.value;
  if (nextQuery === searchQuery.value) {
    return;
  }
  searchQuery.value = nextQuery;
  currentPage.value = 1;
  loadCurrentPageThumbnails();
}

function setStatusFilter(nextFilter) {
  if (operationBusy.value) {
    return;
  }
  if (!STATUS_FILTERS.some((item) => item.value === nextFilter)) {
    return;
  }
  if (statusFilter.value === nextFilter) {
    return;
  }
  statusFilter.value = nextFilter;
  currentPage.value = 1;
  loadCurrentPageThumbnails();
}

function goToPage(nextPage) {
  if (operationBusy.value) {
    return;
  }
  const normalizedPage = Math.min(Math.max(1, nextPage), totalPages.value);
  if (normalizedPage === currentPage.value) {
    return;
  }
  currentPage.value = normalizedPage;
  loadCurrentPageThumbnails();
}

function selectPest(nextPestType) {
  if (operationBusy.value) {
    return;
  }
  // ui/tabs 在 mousedown 时已切换；点击已激活 tab（或同一次点击的 click 阶段）不重复加载
  if (nextPestType === pestType.value) {
    return;
  }
  closeLightbox();
  statusFilter.value = "all";
  searchInput.value = "";
  searchQuery.value = "";
  dragOverCode.value = "";
  pestType.value = nextPestType;
  loadPoints();
}

function openFilePicker(point) {
  if (operationBusy.value) {
    return;
  }
  uploadTarget.value = {
    pestType: pestType.value,
    code: pointKey(point),
    replacing: Boolean(point.has_screenshot),
  };
  if (fileInput.value) {
    fileInput.value.value = "";
    fileInput.value.click();
  }
}

async function performUpload(target, file) {
  const action = target.replacing ? "替换" : "上传";
  uploadingCode.value = target.code;
  try {
    await uploadPointScreenshot({
      pestType: target.pestType,
      code: target.code,
      file,
    });
    if (!componentActive) {
      return;
    }
    toast.success(
      `已${action} ${target.code} 的点位截图。`,
      target.replacing ? "截图已替换" : "截图已上传",
    );
    if (target.pestType === pestType.value) {
      await loadPoints();
    }
  } catch (error) {
    if (componentActive && !isUnauthorizedError(error)) {
      toast.error(`${error.message || error}`, `截图${action}失败`);
    }
  } finally {
    uploadingCode.value = "";
  }
}

async function onFileChange(event) {
  const file = event.target.files?.[0];
  const target = uploadTarget.value;
  uploadTarget.value = null;
  event.target.value = "";
  if (!file || !target) {
    return;
  }
  await performUpload(target, file);
}

function onDragOver(event, point) {
  if (operationBusy.value) {
    return;
  }
  event.preventDefault();
  dragOverCode.value = pointKey(point);
}

function onDragLeave(point) {
  if (dragOverCode.value === pointKey(point)) {
    dragOverCode.value = "";
  }
}

function onDrop(event, point) {
  event.preventDefault();
  dragOverCode.value = "";
  if (operationBusy.value) {
    return;
  }
  const file = event.dataTransfer?.files?.[0];
  if (!file) {
    return;
  }
  if (!ACCEPTED_IMAGE_TYPES.has(file.type)) {
    toast.error("仅支持 JPG、PNG、WebP 格式的图片。", "截图上传失败");
    return;
  }
  void performUpload(
    {
      pestType: pestType.value,
      code: pointKey(point),
      replacing: Boolean(point.has_screenshot),
    },
    file,
  );
}

function requestDelete(point) {
  if (operationBusy.value) {
    return;
  }
  pendingDelete.value = {
    pestType: pestType.value,
    code: pointKey(point),
    name: point.name || "",
  };
}

function closeDeleteDialog() {
  if (!deletingCode.value) {
    pendingDelete.value = null;
  }
}

async function confirmDelete() {
  const target = pendingDelete.value;
  if (!target || deletingCode.value) {
    return;
  }

  deletingCode.value = target.code;
  try {
    await deletePointScreenshot(target.pestType, target.code);
    if (!componentActive) {
      return;
    }
    toast.success(`已删除 ${target.code} 的点位截图。`, "截图已删除");
    pendingDelete.value = null;
    if (target.pestType === pestType.value) {
      await loadPoints();
    }
  } catch (error) {
    if (componentActive && !isUnauthorizedError(error)) {
      toast.error(`${error.message || error}`, "截图删除失败");
    }
  } finally {
    deletingCode.value = "";
  }
}

function handleLightboxOpenChange(value) {
  if (!value) {
    closeLightbox();
  }
}

onMounted(() => {
  componentActive = true;
  void loadPoints();
});

onBeforeUnmount(() => {
  componentActive = false;
  loadRequestId += 1;
  closeLightbox();
  releaseThumbnailUrls();
});
</script>


<template>
  <section class="flex w-full flex-col gap-4">
    <Card aria-label="点位截图筛选">
      <CardContent class="space-y-4 p-4">
        <Tabs
          :model-value="pestType"
          class="point-screenshot-tabs w-fit"
          aria-label="害虫类型"
          @update:model-value="selectPest"
        >
          <TabsList>
            <TabsTrigger
              v-for="tab in PEST_TABS"
              :key="tab.pestType"
              :value="tab.pestType"
              :disabled="operationBusy"
              :data-testid="`point-screenshot-tab-${tab.pestType}`"
              @click="selectPest(tab.pestType)"
            >
              {{ tab.label }}
            </TabsTrigger>
          </TabsList>
        </Tabs>

        <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div
            class="flex flex-wrap gap-2"
            role="group"
            aria-label="按截图状态筛选"
            aria-live="polite"
          >
            <Button
              v-for="item in STATUS_FILTERS"
              :key="item.value"
              type="button"
              size="sm"
              :variant="statusFilter === item.value ? 'default' : 'outline'"
              class="gap-2"
              :class="{ 'is-active': statusFilter === item.value }"
              :aria-pressed="statusFilter === item.value"
              :disabled="operationBusy"
              :data-testid="item.testId"
              @click="setStatusFilter(item.value)"
            >
              {{ item.label }}
              <strong class="tabular-nums">{{ statusFilterCount[item.value] }}</strong>
            </Button>
          </div>

          <div class="flex min-w-[14rem] max-w-sm flex-1 items-center gap-2">
            <label class="relative flex-1">
              <span class="sr-only">搜索点位</span>
              <Search class="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                v-model="searchInput"
                type="search"
                class="h-8 pl-8"
                placeholder="搜索编号、名称、属地…"
                data-testid="point-screenshot-search"
                @keydown.enter="applySearch"
              />
            </label>
            <Button
              type="button"
              size="sm"
              class="h-8"
              :disabled="operationBusy"
              data-testid="point-screenshot-search-submit"
              @click="applySearch"
            >
              <Search class="size-3.5" />
              查询
            </Button>
          </div>
        </div>

        <p class="text-sm text-muted-foreground">
          输入条件后点击「查询」或按回车执行筛选；拖拽图片到对应点位所在行即可上传或替换截图。
        </p>
      </CardContent>
    </Card>

    <div v-if="loading" class="py-12 text-center text-sm text-muted-foreground" data-testid="point-screenshot-loading">
      正在加载点位…
    </div>
    <div v-else-if="loadFailed" class="py-12 text-center text-sm text-destructive">
      点位加载失败，请重新选择当前害虫类型后重试。
    </div>
    <EmptyState
      v-else-if="points.length === 0"
      :icon="ImageOff"
      title="当前害虫类型暂无点位。"
    />
    <EmptyState
      v-else-if="filteredPoints.length === 0"
      :icon="SearchX"
      :title="emptyFilterMessage"
    />

    <div v-else class="overflow-hidden rounded-xl border bg-card shadow-sm" aria-live="polite">
      <Table>
        <TableHeader>
          <TableRow class="hover:bg-transparent">
            <TableHead class="w-28">编号</TableHead>
            <TableHead>名称</TableHead>
            <TableHead>属地</TableHead>
            <TableHead>点位截图</TableHead>
            <TableHead class="w-24">状态</TableHead>
            <TableHead class="w-36 text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow
            v-for="point in paginatedPoints"
            :key="point.code"
            class="point-screenshot-row"
            :class="{ 'bg-primary/10 hover:bg-primary/10': dragOverCode === pointKey(point) }"
            :data-testid="`point-screenshot-row-${point.code}`"
            @dragover="onDragOver($event, point)"
            @dragleave="onDragLeave(point)"
            @drop="onDrop($event, point)"
          >
            <TableCell class="font-medium">{{ point.code }}</TableCell>
            <TableCell class="max-w-44 truncate">{{ point.name || "未命名点位" }}</TableCell>
            <TableCell class="max-w-44 truncate">{{ point.locality || "属地未填写" }}</TableCell>
            <TableCell>
              <button
                v-if="point.has_screenshot"
                type="button"
                class="block size-16 cursor-pointer overflow-hidden rounded border bg-muted focus-visible:ring-3 focus-visible:ring-ring/50"
                :disabled="operationBusy"
                :data-testid="`point-screenshot-preview-${point.code}`"
                :aria-label="`查看 ${point.code} 大图`"
                @click="openLightbox(point)"
              >
                <img
                  v-if="thumbnailUrls.get(pointKey(point))"
                  class="size-full object-cover"
                  :src="thumbnailUrls.get(pointKey(point))"
                  :alt="`${point.code} 点位截图缩略图`"
                />
                <div
                  v-else
                  class="flex size-full flex-col items-center justify-center gap-1 text-muted-foreground"
                >
                  <Image class="size-4" />
                  <span v-if="thumbnailStates.get(pointKey(point)) === 'loading'" class="text-xs">加载中…</span>
                  <span v-else class="text-xs">预览不可用</span>
                </div>
              </button>
              <div
                v-else
                class="flex size-16 flex-col items-center justify-center gap-1 rounded border border-dashed text-muted-foreground"
              >
                <ImageOff class="size-4" />
                <span class="text-xs">缺失</span>
              </div>
            </TableCell>
            <TableCell>
              <Badge :variant="point.has_screenshot ? 'default' : 'secondary'">
                {{ point.has_screenshot ? "已有截图" : "缺失" }}
              </Badge>
            </TableCell>
            <TableCell class="text-right">
              <div class="flex flex-col items-end gap-1.5">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  class="w-28 border-dashed"
                  :disabled="operationBusy"
                  :title="`${point.code}：拖拽图片到本行，或点击选择`"
                  :data-testid="point.has_screenshot
                    ? `point-screenshot-replace-${point.code}`
                    : `point-screenshot-upload-${point.code}`"
                  @click="openFilePicker(point)"
                >
                  <Upload class="size-3.5" />
                  {{ uploadingCode === pointKey(point)
                    ? "上传中…"
                    : point.has_screenshot ? "替换" : "上传" }}
                </Button>
                <Button
                  v-if="point.has_screenshot"
                  type="button"
                  size="sm"
                  variant="ghost"
                  class="w-28 text-destructive hover:bg-destructive/10 hover:text-destructive"
                  :disabled="operationBusy"
                  :data-testid="`point-screenshot-delete-${point.code}`"
                  @click="requestDelete(point)"
                >
                  <Trash2 class="size-3.5" />
                  {{ deletingCode === pointKey(point) ? "删除中…" : "删除" }}
                </Button>
              </div>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>

    <div
      v-if="!loading && !loadFailed && filteredPoints.length > 0 && totalPages > 1"
      class="flex flex-wrap items-center justify-center gap-3"
      aria-label="点位分页"
    >
      <span class="text-sm text-muted-foreground">
        第 {{ currentPage }} / {{ totalPages }} 页 · 共 {{ filteredPoints.length }} 条
      </span>
      <Pagination
        :page="currentPage"
        :items-per-page="PAGE_SIZE"
        :total="filteredPoints.length"
        :sibling-count="1"
        :disabled="operationBusy"
        show-edges
        class="mx-0 w-auto"
        @update:page="goToPage"
      >
        <PaginationContent v-slot="{ items }">
          <PaginationPrevious data-testid="point-screenshot-prev-page">
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
          <PaginationNext data-testid="point-screenshot-next-page">
            <span class="hidden sm:block">下一页</span>
            <ChevronRight class="size-4" />
          </PaginationNext>
        </PaginationContent>
      </Pagination>
    </div>

    <input
      ref="fileInput"
      hidden
      type="file"
      accept="image/jpeg,image/png,image/webp"
      data-testid="point-screenshot-file-input"
      @change="onFileChange"
    />

    <ConfirmDialog
      :open="Boolean(pendingDelete)"
      title="删除点位截图"
      :message="pendingDelete
        ? `确认删除 ${pendingDelete.code}${pendingDelete.name ? `（${pendingDelete.name}）` : ''} 的点位截图吗？此操作不可撤销。`
        : ''"
      :busy="Boolean(deletingCode)"
      confirm-text="确认删除"
      @close="closeDeleteDialog"
      @confirm="confirmDelete"
    />

    <Dialog :open="Boolean(lightbox)" @update:open="handleLightboxOpenChange">
      <DialogContent class="sm:max-w-4xl" :show-close-button="false">
        <div v-if="lightbox" class="flex items-start justify-between gap-3">
          <div class="space-y-1">
            <DialogTitle class="text-base">{{ lightbox.code }}</DialogTitle>
            <DialogDescription>{{ lightbox.name || "未命名点位" }}</DialogDescription>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            data-testid="point-screenshot-lightbox-close"
            @click="closeLightbox"
          >
            关闭
          </Button>
        </div>
        <div
          v-if="lightbox"
          class="min-h-64"
          data-testid="point-screenshot-lightbox"
        >
          <div v-if="lightbox.loading" class="py-16 text-center text-sm text-muted-foreground">
            正在加载大图…
          </div>
          <div
            v-else-if="lightbox.error"
            class="py-16 text-center text-sm text-destructive"
          >
            大图加载失败，请稍后重试。
          </div>
          <img
            v-else-if="lightbox.url"
            class="mx-auto max-h-[70vh] w-auto max-w-full rounded-md"
            :src="lightbox.url"
            :alt="`${lightbox.code} 点位截图`"
            data-testid="point-screenshot-lightbox-image"
          />
        </div>
      </DialogContent>
    </Dialog>
  </section>
</template>
