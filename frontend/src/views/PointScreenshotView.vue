<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";
import { ArrowLeft, Image, ImageOff, Search, Trash2, Upload } from "@lucide/vue";

import {
  deletePointScreenshot,
  fetchPointScreenshotBlob,
  listPointScreenshotStatus,
  uploadPointScreenshot,
} from "../api/pointScreenshot.js";
import { isUnauthorizedError } from "../api/http.js";
import BaseDialog from "../components/workorder/BaseDialog.vue";
import ConfirmDialog from "../components/workorder/ConfirmDialog.vue";
import { useToast } from "../composables/useToast.js";

const PEST_TABS = Object.freeze([
  { pestType: "春尺蠖", label: "杨树点位截图" },
  { pestType: "国槐尺蠖", label: "国槐点位截图" },
  { pestType: "美国白蛾", label: "美国白蛾截图" },
]);
const PAGE_SIZE = 48;

const toast = useToast();
const pestType = ref("美国白蛾");
const points = ref([]);
const searchQuery = ref("");
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

const filteredPoints = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase("zh-CN");
  if (!query) {
    return points.value;
  }

  return points.value.filter((point) =>
    [point.code, point.name, point.locality]
      .some((value) => String(value ?? "").toLocaleLowerCase("zh-CN").includes(query)),
  );
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
  <section class="page-shell point-screenshot-page">
    <RouterLink class="point-screenshot-back" to="/workorder">
      <ArrowLeft :size="16" :stroke-width="2" />
      返回调查工单
    </RouterLink>

    <header class="point-screenshot-head">
      <div>
        <p class="point-screenshot-eyebrow">POINT SCREENSHOT LIBRARY</p>
        <h1>点位截图管理</h1>
        <p>按害虫类型查看点位截图状态，并上传、替换或删除截图。</p>
      </div>
    </header>

    <section class="point-screenshot-panel" aria-label="点位截图筛选">
      <div class="point-screenshot-tabs" role="group" aria-label="害虫类型">
        <button
          v-for="tab in PEST_TABS"
          :key="tab.pestType"
          type="button"
          :aria-pressed="pestType === tab.pestType"
          :class="{ 'is-active': pestType === tab.pestType }"
          :disabled="operationBusy"
          :data-testid="`point-screenshot-tab-${tab.pestType}`"
          @click="selectPest(tab.pestType)"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="point-screenshot-tools">
        <div class="point-screenshot-stats" aria-label="截图统计" aria-live="polite">
          <span data-testid="point-screenshot-total">总点位 <strong>{{ total }}</strong></span>
          <span data-testid="point-screenshot-existing">
            已有截图 <strong>{{ hasScreenshot }}</strong>
          </span>
          <span data-testid="point-screenshot-missing">缺失 <strong>{{ missing }}</strong></span>
        </div>

        <label class="point-screenshot-search">
          <span class="point-screenshot-sr-only">搜索点位</span>
          <Search :size="16" :stroke-width="2" />
          <input
            :value="searchQuery"
            type="search"
            placeholder="搜索编号、名称、属地…"
            data-testid="point-screenshot-search"
            @input="onSearchInput"
          />
        </label>
      </div>
    </section>

    <div v-if="loading" class="point-screenshot-state" data-testid="point-screenshot-loading">
      正在加载点位…
    </div>
    <div v-else-if="loadFailed" class="point-screenshot-state is-error">
      点位加载失败，请重新选择当前害虫类型后重试。
    </div>
    <div v-else-if="points.length === 0" class="point-screenshot-state">
      当前害虫类型暂无点位。
    </div>
    <div v-else-if="filteredPoints.length === 0" class="point-screenshot-state">
      没有符合搜索条件的点位。
    </div>

    <div v-else class="point-screenshot-grid" aria-live="polite">
      <article
        v-for="point in paginatedPoints"
        :key="point.code"
        class="point-screenshot-card"
        :data-testid="`point-screenshot-card-${point.code}`"
      >
        <div class="point-screenshot-preview">
          <button
            v-if="point.has_screenshot"
            type="button"
            class="point-screenshot-preview-trigger"
            :disabled="operationBusy"
            :data-testid="`point-screenshot-preview-${point.code}`"
            :aria-label="`查看 ${point.code} 大图`"
            @click="openLightbox(point)"
          >
            <img
              v-if="thumbnailUrls.get(pointKey(point))"
              :src="thumbnailUrls.get(pointKey(point))"
              :alt="`${point.code} 点位截图缩略图`"
            />
            <div v-else class="point-screenshot-placeholder has-file">
              <Image :size="26" :stroke-width="1.7" />
              <span v-if="thumbnailStates.get(pointKey(point)) === 'loading'">加载中…</span>
              <span v-else>预览不可用</span>
            </div>
          </button>
          <div v-else class="point-screenshot-placeholder">
            <ImageOff :size="26" :stroke-width="1.7" />
            <span>缺失</span>
          </div>
          <span
            class="point-screenshot-status"
            :class="point.has_screenshot ? 'is-ready' : 'is-missing'"
          >
            {{ point.has_screenshot ? "已有截图" : "缺失" }}
          </span>
        </div>

        <div class="point-screenshot-card-body">
          <div class="point-screenshot-card-copy">
            <strong>{{ point.code }}</strong>
            <span>{{ point.name || "未命名点位" }}</span>
            <small>{{ point.locality || "属地未填写" }}</small>
          </div>

          <div class="point-screenshot-card-actions">
            <button
              type="button"
              class="point-screenshot-action is-upload"
              :disabled="operationBusy"
              :data-testid="point.has_screenshot
                ? `point-screenshot-replace-${point.code}`
                : `point-screenshot-upload-${point.code}`"
              @click="openFilePicker(point)"
            >
              <Upload :size="15" :stroke-width="2" />
              {{ uploadingCode === pointKey(point)
                ? "上传中…"
                : point.has_screenshot ? "替换" : "上传" }}
            </button>
            <button
              v-if="point.has_screenshot"
              type="button"
              class="point-screenshot-action is-delete"
              :disabled="operationBusy"
              :data-testid="`point-screenshot-delete-${point.code}`"
              @click="requestDelete(point)"
            >
              <Trash2 :size="15" :stroke-width="2" />
              {{ deletingCode === pointKey(point) ? "删除中…" : "删除" }}
            </button>
          </div>
        </div>
      </article>
    </div>

    <nav
      v-if="!loading && !loadFailed && filteredPoints.length > 0 && totalPages > 1"
      class="point-screenshot-pagination"
      aria-label="点位分页"
    >
      <button
        type="button"
        class="button-secondary"
        :disabled="currentPage <= 1 || operationBusy"
        data-testid="point-screenshot-prev-page"
        @click="goToPage(currentPage - 1)"
      >
        上一页
      </button>
      <span>第 {{ currentPage }} / {{ totalPages }} 页 · 共 {{ filteredPoints.length }} 条</span>
      <button
        type="button"
        class="button-secondary"
        :disabled="currentPage >= totalPages || operationBusy"
        data-testid="point-screenshot-next-page"
        @click="goToPage(currentPage + 1)"
      >
        下一页
      </button>
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
      dialog-class="point-screenshot-lightbox-dialog"
      @close="closeLightbox"
    >
      <header v-if="lightbox" class="point-screenshot-lightbox-head">
        <div>
          <h3>{{ lightbox.code }}</h3>
          <p>{{ lightbox.name || "未命名点位" }}</p>
        </div>
        <button type="button" class="button-secondary" data-testid="point-screenshot-lightbox-close" @click="closeLightbox">
          关闭
        </button>
      </header>
      <div v-if="lightbox" class="point-screenshot-lightbox-body" data-testid="point-screenshot-lightbox">
        <div v-if="lightbox.loading" class="point-screenshot-lightbox-state">正在加载大图…</div>
        <div v-else-if="lightbox.error" class="point-screenshot-lightbox-state is-error">
          大图加载失败，请稍后重试。
        </div>
        <img
          v-else-if="lightbox.url"
          :src="lightbox.url"
          :alt="`${lightbox.code} 点位截图`"
          data-testid="point-screenshot-lightbox-image"
        />
      </div>
    </BaseDialog>
  </section>
</template>

<style scoped>
.point-screenshot-page {
  gap: var(--space-7);
  padding-bottom: var(--space-8);
}

.point-screenshot-back {
  width: fit-content;
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  font-weight: 650;
  text-decoration: none;
}

.point-screenshot-back:hover {
  color: var(--color-primary);
}

.point-screenshot-back:focus-visible {
  border-radius: var(--radius-xs);
  outline: none;
  box-shadow: var(--focus-ring);
}

.point-screenshot-head h1 {
  color: var(--color-text);
  font-size: var(--text-title);
}

.point-screenshot-head p:last-child {
  margin-top: var(--space-2);
  color: var(--color-text-muted);
  font-size: var(--text-md);
}

.point-screenshot-eyebrow {
  margin-bottom: var(--space-2);
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: var(--text-2xs);
  font-weight: 700;
  letter-spacing: 0.12em;
}

.point-screenshot-panel {
  flex: 0 0 auto;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.point-screenshot-tabs {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-4) var(--space-5) 0;
  border-bottom: 1px solid var(--color-border);
}

.point-screenshot-tabs button {
  min-height: 42px;
  padding: 0 var(--space-5);
  border: 0;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  background: transparent;
  color: var(--color-text-muted);
  box-shadow: none;
  font-size: var(--text-sm);
  font-weight: 700;
  transform: none;
}

.point-screenshot-tabs button:hover,
.point-screenshot-tabs button.is-active {
  border-bottom-color: var(--color-primary);
  background: transparent;
  color: var(--color-primary);
  box-shadow: none;
  transform: none;
}

.point-screenshot-tools {
  display: flex;
  align-items: center;
  gap: var(--space-6);
  padding: var(--space-5);
}

.point-screenshot-stats {
  display: flex;
  align-items: center;
  gap: var(--space-5);
  flex-wrap: wrap;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.point-screenshot-stats span + span {
  padding-left: var(--space-5);
  border-left: 1px solid var(--color-border);
}

.point-screenshot-stats strong {
  margin-left: var(--space-1);
  color: var(--color-text);
  font-family: var(--font-mono);
  font-size: var(--text-md);
}

.point-screenshot-search {
  position: relative;
  width: min(360px, 100%);
  margin-left: auto;
}

.point-screenshot-search > svg {
  position: absolute;
  top: 50%;
  left: var(--space-4);
  z-index: 1;
  color: var(--color-text-muted);
  transform: translateY(-50%);
}

.point-screenshot-search input {
  min-height: 38px;
  padding: 0 var(--space-4) 0 38px;
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
}

.point-screenshot-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: var(--space-5);
}

.point-screenshot-card {
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.point-screenshot-preview {
  position: relative;
  aspect-ratio: 16 / 10;
  overflow: hidden;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg);
}

.point-screenshot-preview-trigger {
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: zoom-in;
  color: inherit;
  text-align: inherit;
}

.point-screenshot-preview-trigger:disabled {
  cursor: not-allowed;
  opacity: 0.72;
}

.point-screenshot-preview-trigger:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: -2px;
}

.point-screenshot-preview img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
  background: var(--color-surface-container-low);
}

.point-screenshot-placeholder {
  width: 100%;
  height: 100%;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: var(--space-2);
  color: var(--color-text-muted);
  font-size: var(--text-xs);
}

.point-screenshot-placeholder.has-file {
  color: var(--color-primary);
}

.point-screenshot-status {
  position: absolute;
  top: var(--space-3);
  right: var(--space-3);
  padding: 4px 8px;
  border-radius: var(--radius-full);
  font-size: var(--text-2xs);
  font-weight: 750;
  box-shadow: var(--shadow-soft);
}

.point-screenshot-status.is-ready {
  background: var(--color-primary-container);
  color: var(--color-primary);
}

.point-screenshot-status.is-missing {
  background: var(--color-surface);
  color: var(--color-warning);
}

.point-screenshot-card-body {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-4);
}

.point-screenshot-card-copy {
  min-width: 0;
  display: grid;
  gap: var(--space-1);
}

.point-screenshot-card-copy strong,
.point-screenshot-card-copy span,
.point-screenshot-card-copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.point-screenshot-card-copy strong {
  color: var(--color-text);
  font-family: var(--font-mono);
  font-size: var(--text-md);
}

.point-screenshot-card-copy span {
  color: var(--color-text);
  font-size: var(--text-sm);
}

.point-screenshot-card-copy small {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
}

.point-screenshot-card-actions {
  display: flex;
  gap: var(--space-2);
}

.point-screenshot-action {
  min-height: 34px;
  flex: 1;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  box-shadow: none;
  color: var(--color-primary);
  font-size: var(--text-xs);
  font-weight: 700;
}

.point-screenshot-action:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  box-shadow: none;
  transform: none;
}

.point-screenshot-action.is-delete {
  color: var(--color-danger);
}

.point-screenshot-action.is-delete:hover {
  border-color: var(--color-danger);
  background: color-mix(in oklch, var(--color-danger) 7%, var(--color-surface));
}

.point-screenshot-state {
  min-height: 220px;
  display: grid;
  place-items: center;
  padding: var(--space-8);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-lg);
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  text-align: center;
}

.point-screenshot-state.is-error {
  color: var(--color-danger);
}

.point-screenshot-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.point-screenshot-pagination button {
  min-height: 36px;
  padding: 0 var(--space-4);
  font-size: var(--text-xs);
}

.point-screenshot-file-input,
.point-screenshot-sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 760px) {
  .point-screenshot-tools {
    align-items: stretch;
    flex-direction: column;
  }

  .point-screenshot-search {
    width: 100%;
    margin-left: 0;
  }

  .point-screenshot-tabs {
    overflow-x: auto;
  }

  .point-screenshot-tabs button {
    flex: 0 0 auto;
  }

  .point-screenshot-pagination {
    justify-content: space-between;
  }
}

@media (max-width: 480px) {
  .point-screenshot-grid {
    grid-template-columns: 1fr;
  }

  .point-screenshot-stats {
    gap: var(--space-3);
  }

  .point-screenshot-stats span + span {
    padding-left: var(--space-3);
  }
}

.point-screenshot-lightbox-head {
  display: flex;
  flex-shrink: 0;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.point-screenshot-lightbox-head h3 {
  margin: 0;
  color: var(--color-text);
  font-family: var(--font-mono);
  font-size: var(--text-lg);
  font-weight: 700;
}

.point-screenshot-lightbox-head p {
  margin: var(--space-1) 0 0;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.point-screenshot-lightbox-body {
  display: grid;
  flex: 1 1 auto;
  place-items: center;
  min-height: 0;
  overflow: auto;
  padding: var(--space-5);
  background: var(--color-bg);
}

.point-screenshot-lightbox-body img {
  max-width: min(100%, 92vw);
  max-height: min(72vh, 48rem);
  width: auto;
  height: auto;
  display: block;
  object-fit: contain;
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-soft);
}

.point-screenshot-lightbox-state {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  text-align: center;
}

.point-screenshot-lightbox-state.is-error {
  color: var(--color-danger);
}
</style>

<style>
.base-dialog-mask.point-screenshot-lightbox-mask {
  z-index: 1600;
  backdrop-filter: blur(8px);
}

.base-dialog-content.point-screenshot-lightbox-dialog {
  width: min(56rem, calc(100vw - 2rem));
  max-height: min(90vh, 54rem);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
