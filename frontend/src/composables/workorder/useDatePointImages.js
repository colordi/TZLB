import { computed, ref } from "vue";

import { isUnauthorizedError } from "../../api/http.js";
import { fetchSurveyCandidates } from "../../api/survey.js";
import {
  deletePointDateImage,
  fetchPointDateImages,
  uploadPointDateImages,
} from "../../api/workorder.js";

/**
 * 工单素材-日期现场照片：按日期查询需派单点位，拖拽上传图片到点位，
 * 后端自动按“编号-序号”命名并归档到 images/{日期}/。
 */
export function useDatePointImages() {
  const selectedDate = ref("");
  const points = ref([]);
  const allImages = ref([]);
  const queried = ref(false);
  const loading = ref(false);
  const imagesLoading = ref(false);
  const uploadingCode = ref("");
  const deletingCode = ref("");

  const totalCount = computed(() => points.value.length);

  function normalizeCode(candidate) {
    return `${candidate?.location_id ?? ""}`.trim();
  }

  /** 按“文件名以点位编号开头”把当日图片归到点位，编号重叠时归到最长匹配 */
  const imagesByCode = computed(() => {
    const codes = points.value.map(normalizeCode).filter(Boolean);
    const longestFirst = [...codes].sort((a, b) => b.length - a.length);
    const grouped = new Map(codes.map((code) => [code, []]));

    for (const image of allImages.value) {
      const stem = `${image.file_name || ""}`.replace(/\.[^.]+$/, "");
      const code = longestFirst.find((candidate) => stem.startsWith(candidate));
      if (code) {
        grouped.get(code).push(image);
      }
    }
    return grouped;
  });

  function imagesForPoint(candidate) {
    return imagesByCode.value.get(normalizeCode(candidate)) || [];
  }

  function resetResults() {
    points.value = [];
    allImages.value = [];
    queried.value = false;
  }

  async function loadImages(toast) {
    if (!selectedDate.value) {
      return;
    }
    imagesLoading.value = true;
    try {
      const result = await fetchPointDateImages({ surveyDate: selectedDate.value });
      allImages.value = Array.isArray(result?.images) ? result.images : [];
    } catch (loadError) {
      if (isUnauthorizedError(loadError)) {
        return;
      }
      toast?.error(`${loadError.message || loadError}`, "读取日期图片失败");
    } finally {
      imagesLoading.value = false;
    }
  }

  async function queryPoints({ pestType, year, generation }, toast) {
    if (!selectedDate.value) {
      toast?.info("请先选择调查日期。", "缺少查询条件");
      return;
    }

    loading.value = true;
    try {
      const result = await fetchSurveyCandidates({
        date: selectedDate.value,
        pestType,
        year,
        generation,
        includeImages: false,
      });
      points.value = Array.isArray(result) ? result : [];
      queried.value = true;
      await loadImages(toast);
      if (points.value.length === 0) {
        toast?.info("所选日期没有需派单的点位。", "暂无数据");
      }
    } catch (queryError) {
      if (isUnauthorizedError(queryError)) {
        return;
      }
      toast?.error(`${queryError.message || queryError}`, "查询需派单点位失败");
    } finally {
      loading.value = false;
    }
  }

  function pickImageFiles(files) {
    const incoming = Array.from(files || []);
    const images = incoming.filter((file) => `${file.type || ""}`.startsWith("image/"));
    return { images, skipped: incoming.length - images.length };
  }

  async function uploadToPoint(candidate, files, toast) {
    const code = normalizeCode(candidate);
    if (!code || uploadingCode.value) {
      return;
    }
    if (!selectedDate.value) {
      toast?.info("请先选择调查日期。", "缺少上传条件");
      return;
    }

    const { images, skipped } = pickImageFiles(files);
    if (!images.length) {
      toast?.info("拖入的文件中没有可上传的图片。", "没有图片文件");
      return;
    }

    uploadingCode.value = code;
    try {
      const result = await uploadPointDateImages({
        surveyDate: selectedDate.value,
        pointCode: code,
        files: images,
      });
      const rejectedCount = Array.isArray(result?.rejected) ? result.rejected.length : 0;
      const skippedNote = skipped > 0 ? `，非图片忽略 ${skipped} 个` : "";
      if (Number(result?.saved_count || 0) > 0) {
        const rejectedNote = rejectedCount > 0 ? `，失败 ${rejectedCount} 张` : "";
        toast?.success(
          `已保存 ${result.saved_count} 张到 ${code}${rejectedNote}${skippedNote}。`,
          "图片已上传",
        );
      } else {
        const firstReason = result?.rejected?.[0]?.reason;
        toast?.error(
          firstReason ? `上传被拒绝：${firstReason}` : "没有图片被保存。",
          "图片上传失败",
        );
      }
      await loadImages(toast);
    } catch (uploadError) {
      if (isUnauthorizedError(uploadError)) {
        return;
      }
      toast?.error(`${uploadError.message || uploadError}`, "图片上传失败");
    } finally {
      uploadingCode.value = "";
    }
  }

  async function removePointImages(candidate, toast) {
    const code = normalizeCode(candidate);
    const fileNames = imagesForPoint(candidate).map((image) => image.file_name);
    if (!code || deletingCode.value || fileNames.length === 0) {
      return;
    }

    deletingCode.value = code;
    let deletedCount = 0;
    try {
      for (const fileName of fileNames) {
        await deletePointDateImage({
          surveyDate: selectedDate.value,
          pointCode: code,
          fileName,
        });
        deletedCount += 1;
      }
      toast?.success(`已删除 ${code} 的 ${deletedCount} 张现场照片。`, "现场照片已删除");
    } catch (deleteError) {
      if (isUnauthorizedError(deleteError)) {
        return;
      }
      const progress = deletedCount
        ? `（已删除 ${deletedCount} 张，剩余 ${fileNames.length - deletedCount} 张）`
        : "";
      toast?.error(`${deleteError.message || deleteError}${progress}`, "现场照片删除失败");
    } finally {
      if (deletedCount > 0) {
        await loadImages(toast);
      }
      deletingCode.value = "";
    }
  }

  return {
    selectedDate,
    points,
    allImages,
    queried,
    loading,
    imagesLoading,
    uploadingCode,
    deletingCode,
    totalCount,
    imagesForPoint,
    resetResults,
    queryPoints,
    uploadToPoint,
    removePointImages,
  };
}
