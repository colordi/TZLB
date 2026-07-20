<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { Image, ImageOff, Search, Trash2, Upload } from "@lucide/vue";

import {
  deletePointScreenshot,
  fetchPointScreenshotBlob,
  listPointScreenshotStatus,
  uploadPointScreenshot,
} from "../../api/pointScreenshot.js";
import { isUnauthorizedError } from "../../api/http.js";
import BaseDialog from "./BaseDialog.vue";
import ConfirmDialog from "./ConfirmDialog.vue";
import { useToast } from "../../composables/useToast.js";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const PEST_TABS = Object.freeze([
  { pestType: "春尺蠖", label: "杨树点位截图" },
  { pestType: "国槐尺蠖", label: "国槐点位截图" },
  { pestType: "美国白蛾", label: "美国白蛾截图" },
]);
const PAGE_SIZE = 48;

const toast = useToast();
const STATUS_FILTERS = Object.freeze([
  { value: "all", label: "总点位", testId: "point-screenshot-total" },
  { value: "existing", label: "已有截图", testId: "point-screenshot-existing" },
  { value: "missing", label: "缺失", testId: "point-screenshot-missing" },
]);

const pestType = ref("美国白蛾");
const points = ref([]);
const searchQuery = ref("");
const statusFilter = ref("all");
const loading = ref(false);
const loadFailed = ref(false);
const fileInput = ref(null);
const uploadTarget = ref(null);
const uploadingCode = ref("");
const pendingDelete = ref(null);
const deletingCode = ref("");
const currentPage = ref(1);
const thumbnailUrls = reactive(new Map());
const thumbnailStates = reactive(new Map());
const lightbox = ref(null);
let loadRequestId = 0;
let thumbnailRequestId = 0;
let lightboxRequestId = 0;
let searchTimer = null;
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

function clearSearchTimer() {
  if (searchTimer !== null) {
    window.clearTimeout(searchTimer);
    searchTimer = null;
  }
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
  clearSearchTimer();
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

function onSearchInput(event) {
  searchQuery.value = event.target.value;
  currentPage.value = 1;
  clearSearchTimer();
  searchTimer = window.setTimeout(() => {
    searchTimer = null;
    loadCurrentPageThumbnails();
  }, 180);
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
  closeLightbox();
  statusFilter.value = "all";
  searchQuery.value = "";
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

async function onFileChange(event) {
  const file = event.target.files?.[0];
  const target = uploadTarget.value;
  if (!file || !target) {
    uploadTarget.value = null;
    event.target.value = "";
    return;
  }

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
    uploadTarget.value = null;
    event.target.value = "";
  }
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

onMounted(() => {
  componentActive = true;
  void loadPoints();
});

onBeforeUnmount(() => {
  componentActive = false;
  loadRequestId += 1;
  clearSearchTimer();
  closeLightbox();
  releaseThumbnailUrls();
});
</script>


<template>
  <section class="point-screenshot-panel-root flex w-full flex-col gap-4">
    <Card class="point-screenshot-panel" aria-label="点位截图筛选">
      <CardContent class="space-y-4 p-4">
        <div class="point-screenshot-tabs flex flex-wrap gap-2" role="group" aria-label="害虫类型">
          <Button
            v-for="tab in PEST_TABS"
            :key="tab.pestType"
            type="button"
            size="sm"
            :variant="pestType === tab.pestType ? 'default' : 'outline'"
            :aria-pressed="pestType === tab.pestType"
            :class="{ 'is-active': pestType === tab.pestType }"
            :disabled="operationBusy"
            :data-testid="`point-screenshot-tab-${tab.pestType}`"
            @click="selectPest(tab.pestType)"
          >
            {{ tab.label }}
          </Button>
        </div>

        <div class="point-screenshot-tools flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div
            class="point-screenshot-stats flex flex-wrap gap-2"
            role="group"
            aria-label="按截图状态筛选"
            aria-live="polite"
          >
            <Button
              v-for="item in STATUS_FILTERS"
              :key="item.value"
              type="button"
              size="sm"
              variant="outline"
              class="point-screenshot-stat gap-2"
              :class="{ 'is-active border-primary bg-primary/10': statusFilter === item.value }"
              :aria-pressed="statusFilter === item.value"
              :disabled="operationBusy"
              :data-testid="item.testId"
              @click="setStatusFilter(item.value)"
            >
              {{ item.label }}
              <strong class="tabular-nums">{{ statusFilterCount[item.value] }}</strong>
            </Button>
          </div>

          <label class="point-screenshot-search relative min-w-[14rem] max-w-sm flex-1">
            <span class="point-screenshot-sr-only sr-only">搜索点位</span>
            <Search class="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              :value="searchQuery"
              type="search"
              class="h-8 pl-8"
              placeholder="搜索编号、名称、属地…"
              data-testid="point-screenshot-search"
              @input="onSearchInput"
            />
          </label>
        </div>
      </CardContent>
    </Card>

    <div v-if="loading" class="point-screenshot-state py-12 text-center text-muted-foreground" data-testid="point-screenshot-loading">
      正在加载点位…
    </div>
    <div v-else-if="loadFailed" class="point-screenshot-state is-error py-12 text-center text-destructive">
      点位加载失败，请重新选择当前害虫类型后重试。
    </div>
    <div v-else-if="points.length === 0" class="point-screenshot-state py-12 text-center text-muted-foreground">
      当前害虫类型暂无点位。
    </div>
    <div v-else-if="filteredPoints.length === 0" class="point-screenshot-state py-12 text-center text-muted-foreground">
      {{ emptyFilterMessage }}
    </div>

    <div v-else class="point-screenshot-grid grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" aria-live="polite">
      <article
        v-for="point in paginatedPoints"
        :key="point.code"
        class="point-screenshot-card overflow-hidden rounded-lg border bg-card"
        :data-testid="`point-screenshot-card-${point.code}`"
      >
        <div class="point-screenshot-preview relative aspect-[4/3] bg-muted">
          <button
            v-if="point.has_screenshot"
            type="button"
            class="point-screenshot-preview-trigger absolute inset-0"
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
              class="point-screenshot-placeholder has-file flex size-full flex-col items-center justify-center gap-1 text-muted-foreground"
            >
              <Image class="size-6" />
              <span v-if="thumbnailStates.get(pointKey(point)) === 'loading'" class="text-xs">加载中…</span>
              <span v-else class="text-xs">预览不可用</span>
            </div>
          </button>
          <div
            v-else
            class="point-screenshot-placeholder flex size-full flex-col items-center justify-center gap-1 text-muted-foreground"
          >
            <ImageOff class="size-6" />
            <span class="text-xs">缺失</span>
          </div>
          <Badge
            class="point-screenshot-status absolute top-2 right-2"
            :class="point.has_screenshot ? 'is-ready' : 'is-missing'"
            :variant="point.has_screenshot ? 'default' : 'secondary'"
          >
            {{ point.has_screenshot ? "已有截图" : "缺失" }}
          </Badge>
        </div>

        <div class="point-screenshot-card-body space-y-3 p-3">
          <div class="point-screenshot-card-copy space-y-0.5">
            <strong class="block text-sm">{{ point.code }}</strong>
            <span class="block text-sm text-muted-foreground">{{ point.name || "未命名点位" }}</span>
            <small class="block text-xs text-muted-foreground">{{ point.locality || "属地未填写" }}</small>
          </div>

          <div class="point-screenshot-card-actions flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              class="point-screenshot-action is-upload"
              :disabled="operationBusy"
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
              variant="destructive"
              class="point-screenshot-action is-delete"
              :disabled="operationBusy"
              :data-testid="`point-screenshot-delete-${point.code}`"
              @click="requestDelete(point)"
            >
              <Trash2 class="size-3.5" />
              {{ deletingCode === pointKey(point) ? "删除中…" : "删除" }}
            </Button>
          </div>
        </div>
      </article>
    </div>

    <nav
      v-if="!loading && !loadFailed && filteredPoints.length > 0 && totalPages > 1"
      class="point-screenshot-pagination flex items-center justify-center gap-3"
      aria-label="点位分页"
    >
      <Button
        type="button"
        variant="outline"
        size="sm"
        :disabled="currentPage <= 1 || operationBusy"
        data-testid="point-screenshot-prev-page"
        @click="goToPage(currentPage - 1)"
      >
        上一页
      </Button>
      <span class="text-sm text-muted-foreground">
        第 {{ currentPage }} / {{ totalPages }} 页 · 共 {{ filteredPoints.length }} 条
      </span>
      <Button
        type="button"
        variant="outline"
        size="sm"
        :disabled="currentPage >= totalPages || operationBusy"
        data-testid="point-screenshot-next-page"
        @click="goToPage(currentPage + 1)"
      >
        下一页
      </Button>
    </nav>

    <input
      ref="fileInput"
      hidden
      class="point-screenshot-file-input"
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

    <BaseDialog
      :open="Boolean(lightbox)"
      :aria-label="lightbox ? `${lightbox.code} 点位截图大图` : '点位截图大图'"
      mask-class="point-screenshot-lightbox-mask"
      dialog-class="point-screenshot-lightbox-dialog max-w-4xl"
      @close="closeLightbox"
    >
      <header
        v-if="lightbox"
        class="point-screenshot-lightbox-head flex items-start justify-between gap-3 border-b px-4 py-3"
      >
        <div>
          <h3 class="font-semibold">{{ lightbox.code }}</h3>
          <p class="text-sm text-muted-foreground">{{ lightbox.name || "未命名点位" }}</p>
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
      </header>
      <div
        v-if="lightbox"
        class="point-screenshot-lightbox-body min-h-[16rem] p-4"
        data-testid="point-screenshot-lightbox"
      >
        <div v-if="lightbox.loading" class="point-screenshot-lightbox-state py-16 text-center text-muted-foreground">
          正在加载大图…
        </div>
        <div
          v-else-if="lightbox.error"
          class="point-screenshot-lightbox-state is-error py-16 text-center text-destructive"
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
    </BaseDialog>
  </section>
</template>
