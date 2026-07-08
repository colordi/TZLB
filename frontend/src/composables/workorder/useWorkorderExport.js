import { computed, ref } from "vue";

import { isUnauthorizedError } from "../../api/http.js";
import {
  generateWorkorder,
  generateWorkorderBatch,
} from "../../api/workorder.js";
import { MOCK_PREVIEW_DELAY_MS } from "../../fixtures/design/workorderMock.js";
import { hasValidationErrors, toPayloadRecord, validateRecords } from "../../components/workorder/fieldConfig.js";
import { downloadBlob } from "../../utils/download.js";

export function useWorkorderExport(
  taskConfig,
  records,
  isPreview,
) {
  const generating = ref(false);
  const exportProgress = ref({ current: 0, total: 0 });

  const generateButtonLabel = computed(() => {
    const total = records.value.length;

    if (!generating.value) {
      return total > 1 ? `批量导出工作单（${total} 条）` : "导出工作单";
    }

    if (total > 1) {
      return "正在生成批量导出包…";
    }

    const current = exportProgress.value.current || 1;
    const progressTotal = exportProgress.value.total || total || 1;
    return `正在导出 ${current}/${progressTotal}…`;
  });

  function joinDeliveryLabel(label, message) {
    return /^[A-Za-z0-9_.-]+$/.test(label) ? `${label} ${message}` : `${label}${message}`;
  }

  function buildDeliveryMessage(result, label) {
    if (result?.delivery === "share") {
      return joinDeliveryLabel(label, "已打开系统分享。");
    }
    if (result?.delivery === "preview") {
      return joinDeliveryLabel(label, "已打开预览，请在新页面中保存文件。");
    }
    return joinDeliveryLabel(label, "已开始下载。");
  }

  function resetExportProgress() {
    exportProgress.value = { current: 0, total: 0 };
  }

  async function handleGenerate(toast) {
    const { error, success } = toast;
    const errors = validateRecords(records.value, taskConfig.pestType.value);
    if (hasValidationErrors(errors)) {
      error("请先补全所有必填项并修正错误字段。", "还有未完成的记录");
      return;
    }

    if (isPreview.value) {
      generating.value = true;
      exportProgress.value = { current: 0, total: records.value.length };
      try {
        await new Promise((resolve) => setTimeout(resolve, MOCK_PREVIEW_DELAY_MS));
        success(
          `预览模式已模拟导出 ${records.value.length} 条记录的工作单。`,
          "预览导出完成",
        );
      } finally {
        generating.value = false;
        resetExportProgress();
      }
      return;
    }

    generating.value = true;
    exportProgress.value = { current: 0, total: records.value.length };

    try {
      const payload = {
        pest_type: taskConfig.pestType.value,
        task_type: taskConfig.taskType.value,
        task: taskConfig.taskName.value,
        year: taskConfig.year.value,
        generation: taskConfig.generation.value,
      };
      const payloadRecords = records.value.map((record, index) => ({
        ...toPayloadRecord(record, taskConfig.pestType.value),
        serial_number: index + 1,
      }));

      if (payloadRecords.length === 1) {
        const { blob, filename } = await generateWorkorder({
          ...payload,
          records: payloadRecords,
        });
        const delivery = await downloadBlob(blob, filename);
        success(buildDeliveryMessage(delivery, "工作单"), "导出成功");
        return;
      }

      const { blob, filename } = await generateWorkorderBatch({
        ...payload,
        records: payloadRecords,
      });
      await downloadBlob(blob, filename);
      success(`已批量导出 ${payloadRecords.length} 条记录的工作单包。`, "导出成功");
    } catch (generateError) {
      if (isUnauthorizedError(generateError)) {
        return;
      }

      const message = generateError.message || generateError;
      if (records.value.length > 1) {
        error(
          `批量导出失败：${message}。若提示包含失败记录清单，可查看压缩包内\u201c失败记录.json\u201d。`,
          "批量导出失败",
        );
        return;
      }

      error(`${message}`, "工作单生成失败");
    } finally {
      generating.value = false;
      resetExportProgress();
    }
  }

  return {
    generating,
    exportProgress,
    generateButtonLabel,
    handleGenerate,
  };
}
