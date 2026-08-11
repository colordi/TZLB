import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";

import {
  deletePointScreenshot,
  fetchPointScreenshotBlob,
  listPointScreenshotStatus,
  uploadPointScreenshot,
} from "../../api/pointScreenshot.js";
import { isUnauthorizedError } from "../../api/http.js";
import { useToast } from "../useToast.js";

/**
 * Point screenshot management: list, filter, upload, lightbox, delete.
 */
export function usePointScreenshots() {
  const toast = useToast();

  const PEST_TABS = Object.freeze([
    { pestType: "春尺蠖", label: "杨树点位截图" },
    { pestType: "国槐尺蠖", label: "国槐点位截图" },
    { pestType: "美国白蛾", label: "美国白蛾截图" },
    { pestType: "其他害虫", label: "其他害虫截图" },
    { pestType: "杨树食叶害虫", label: "杨树食叶害虫截图" },
  ]);
  const PAGE_SIZE = 48;
  const ACCEPTED_IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

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

  return {
    PEST_TABS,
    PAGE_SIZE,
    ACCEPTED_IMAGE_TYPES,
    STATUS_FILTERS,
    pestType,
    points,
    searchInput,
    searchQuery,
    statusFilter,
    loading,
    loadFailed,
    fileInput,
    uploadTarget,
    uploadingCode,
    dragOverCode,
    pendingDelete,
    deletingCode,
    currentPage,
    thumbnailUrls,
    thumbnailStates,
    lightbox,
    total,
    hasScreenshot,
    missing,
    operationBusy,
    statusFilterCount,
    filteredPoints,
    emptyFilterMessage,
    totalPages,
    paginatedPoints,
    pointKey,
    loadThumbnail,
    closeLightbox,
    openLightbox,
    loadPoints,
    applySearch,
    setStatusFilter,
    goToPage,
    selectPest,
    openFilePicker,
    performUpload,
    onFileChange,
    onDragOver,
    onDragLeave,
    onDrop,
    requestDelete,
    closeDeleteDialog,
    confirmDelete,
    handleLightboxOpenChange,
  };
}
