import { ref } from "vue";

import { isUnauthorizedError } from "../../api/http.js";
import { uploadDateImageFolder } from "../../api/workorder.js";

const DATE_FOLDER_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

export function useDateFolderUpload() {
  const dateFolderInput = ref(null);
  const dateFolderUploading = ref(false);

  function isValidDateFolderName(folderName) {
    if (!DATE_FOLDER_PATTERN.test(folderName)) {
      return false;
    }
    const [year, month, day] = folderName.split("-").map(Number);
    const parsedDate = new Date(Date.UTC(year, month - 1, day));
    return (
      parsedDate.getUTCFullYear() === year &&
      parsedDate.getUTCMonth() === month - 1 &&
      parsedDate.getUTCDate() === day
    );
  }

  function resolveSelectedFolderName(files) {
    const folderNames = new Set();
    for (const file of files) {
      const relativePath = file.webkitRelativePath || "";
      const [folderName] = relativePath.split("/");
      if (folderName) {
        folderNames.add(folderName);
      }
    }

    if (folderNames.size !== 1) {
      throw new Error("请选择一个日期文件夹。");
    }

    const [folderName] = Array.from(folderNames);
    if (!isValidDateFolderName(folderName)) {
      throw new Error("文件夹名称必须是 YYYY-MM-DD 格式的有效日期。");
    }
    return folderName;
  }

  function summarizeDateFolderUpload(result) {
    const skippedParts = [];
    if (result.skipped_existing_count) {
      skippedParts.push(`同名跳过 ${result.skipped_existing_count}`);
    }
    if (result.skipped_non_image_count) {
      skippedParts.push(`非图片跳过 ${result.skipped_non_image_count}`);
    }
    if (result.skipped_nested_count) {
      skippedParts.push(`子目录跳过 ${result.skipped_nested_count}`);
    }
    return skippedParts.length ? `，${skippedParts.join("，")}` : "";
  }

  function openDateFolderPicker(generating) {
    if (generating || dateFolderUploading.value) {
      return;
    }
    dateFolderInput.value?.click();
  }

  async function handleDateFolderChange(event, toast) {
    const { success, info, error } = toast;
    const input = event.target;
    const files = Array.from(input.files || []);

    try {
      if (!files.length) {
        return;
      }

      const folderName = resolveSelectedFolderName(files);
      dateFolderUploading.value = true;
      const result = await uploadDateImageFolder({
        folderName,
        files,
      });
      const skippedSummary = summarizeDateFolderUpload(result);
      if (Number(result.saved_count || 0) > 0) {
        success(
          `已上传 ${result.saved_count} 张图片到 ${result.folder_name}${skippedSummary}。`,
          "日期文件夹已上传",
        );
      } else {
        info(`没有新增图片${skippedSummary}。`, "日期文件夹已处理");
      }
    } catch (uploadError) {
      if (isUnauthorizedError(uploadError)) {
        return;
      }
      error(`${uploadError.message || uploadError}`, "日期文件夹上传失败");
    } finally {
      dateFolderUploading.value = false;
      input.value = "";
    }
  }

  return {
    dateFolderInput,
    dateFolderUploading,
    openDateFolderPicker,
    handleDateFolderChange,
  };
}
