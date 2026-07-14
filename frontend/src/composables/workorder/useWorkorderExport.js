import { computed, ref, unref } from "vue";

import { isUnauthorizedError } from "../../api/http.js";
import {
  downloadWorkorderBatchJob,
  generateWorkorder,
  getWorkorderBatchJobStatus,
  startWorkorderBatchJob,
} from "../../api/workorder.js";
import { MOCK_PREVIEW_DELAY_MS } from "../../fixtures/design/workorderMock.js";
import { hasValidationErrors, toPayloadRecord, validateRecords } from "../../components/workorder/fieldConfig.js";
import { downloadBlob } from "../../utils/download.js";

const BATCH_POLL_INTERVAL_MS = 400;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * @param {object} taskConfig
 * @param {import('vue').Ref|import('vue').ComputedRef} records
 * @param {import('vue').Ref|import('vue').ComputedRef|boolean} isPreview
 * @param {import('vue').Ref|import('vue').ComputedRef} [selectedUids] 有选中时优先导出选中记录
 */
export function useWorkorderExport(
  taskConfig,
  records,
  isPreview,
  selectedUids,
) {
  const generating = ref(false);
  const exportProgress = ref({ current: 0, total: 0, percent: 0, message: "" });

  const exportRecords = computed(() => {
    const all = unref(records) || [];
    const uids = selectedUids ? unref(selectedUids) : [];
    if (Array.isArray(uids) && uids.length > 0) {
      const selected = new Set(uids);
      return all.filter((record) => selected.has(record.__uid));
    }
    return all;
  });

  const exportCount = computed(() => exportRecords.value.length);

  const exportProgressPercent = computed(() => {
    if (!generating.value) {
      return 0;
    }
    const percent = Number(exportProgress.value.percent);
    if (Number.isFinite(percent)) {
      return Math.max(0, Math.min(100, Math.round(percent)));
    }
    const total = exportProgress.value.total || 0;
    if (!total) {
      return 0;
    }
    return Math.round(((exportProgress.value.current || 0) / total) * 100);
  });

  const generateButtonLabel = computed(() => {
    const total = exportCount.value;

    if (!generating.value) {
      if (total <= 0) {
        return "导出工作单";
      }
      return `导出 ${total} 份工作单`;
    }

    if (total > 1) {
      return "正在批量导出…";
    }

    return "正在导出工作单…";
  });

  const exportProgressLabel = computed(() => {
    if (!generating.value) {
      return "";
    }
    if (exportProgress.value.message) {
      return exportProgress.value.message;
    }
    const total = exportProgress.value.total || exportCount.value || 0;
    if (total > 1) {
      return `正在批量导出工作单（${exportProgress.value.current || 0}/${total}）`;
    }
    return "正在导出工作单";
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
    exportProgress.value = { current: 0, total: 0, percent: 0, message: "" };
  }

  function setProgress({ current = 0, total = 0, percent = 0, message = "" } = {}) {
    exportProgress.value = {
      current,
      total,
      percent,
      message,
    };
  }

  async function runBatchExportWithJob(payload, recordCount) {
    const created = await startWorkorderBatchJob(payload);
    const jobId = created.job_id;
    setProgress({
      current: 0,
      total: created.total || recordCount + 1,
      percent: 0,
      message: `开始批量导出 ${recordCount} 份工作单…`,
    });

    while (true) {
      const status = await getWorkorderBatchJobStatus(jobId);
      setProgress({
        current: Number(status.current) || 0,
        total: Number(status.total) || recordCount + 1,
        percent: Number(status.percent) || 0,
        message: status.message || "",
      });

      if (status.status === "completed" || status.ready_for_download) {
        const file = await downloadWorkorderBatchJob(jobId);
        setProgress({
          current: Number(status.total) || recordCount + 1,
          total: Number(status.total) || recordCount + 1,
          percent: 100,
          message: "导出完成，正在下载…",
        });
        return file;
      }

      if (status.status === "failed") {
        throw new Error(status.error || "批量导出失败");
      }

      await sleep(BATCH_POLL_INTERVAL_MS);
    }
  }

  async function handleGenerate(toast) {
    const { error, success } = toast;
    const targetRecords = exportRecords.value;

    if (!targetRecords.length) {
      error("请先导入或选择要导出的点位。", "没有可导出记录");
      return;
    }

    const errors = validateRecords(targetRecords, taskConfig.pestType.value);
    if (hasValidationErrors(errors)) {
      error("请先补全所有必填项并修正错误字段。", "还有未完成的记录");
      return;
    }

    const total = targetRecords.length;
    generating.value = true;
    setProgress({
      current: 0,
      total,
      percent: 0,
      message: total > 1 ? `准备导出 ${total} 份工作单…` : "正在导出工作单…",
    });

    try {
      if (unref(isPreview)) {
        setProgress({
          current: 0,
          total: total + 1,
          percent: 10,
          message: `预览模式：模拟生成 0/${total}`,
        });
        const steps = total + 1;
        for (let step = 1; step <= steps; step += 1) {
          await sleep(Math.max(80, Math.floor(MOCK_PREVIEW_DELAY_MS / steps)));
          setProgress({
            current: step,
            total: steps,
            percent: Math.round((step / steps) * 100),
            message: step <= total
              ? `预览模式：模拟生成 ${step}/${total}`
              : "预览模式：模拟打包…",
          });
        }
        success(
          `预览模式已模拟导出 ${total} 条记录的工作单。`,
          "预览导出完成",
        );
        return;
      }

      const payload = {
        pest_type: taskConfig.pestType.value,
        task_type: taskConfig.taskType.value,
        task: taskConfig.taskName.value,
        year: taskConfig.year.value,
        generation: taskConfig.generation.value,
      };
      const payloadRecords = targetRecords.map((record, index) => ({
        ...toPayloadRecord(record, taskConfig.pestType.value),
        serial_number: index + 1,
      }));

      if (payloadRecords.length === 1) {
        setProgress({
          current: 0,
          total: 1,
          percent: 20,
          message: "正在生成工作单…",
        });
        const { blob, filename } = await generateWorkorder({
          ...payload,
          records: payloadRecords,
        });
        setProgress({
          current: 1,
          total: 1,
          percent: 100,
          message: "导出完成，正在下载…",
        });
        const delivery = await downloadBlob(blob, filename);
        success(buildDeliveryMessage(delivery, "工作单"), "导出成功");
        return;
      }

      const { blob, filename } = await runBatchExportWithJob(
        {
          ...payload,
          records: payloadRecords,
        },
        payloadRecords.length,
      );
      await downloadBlob(blob, filename);
      success(`已批量导出 ${payloadRecords.length} 条记录的工作单包。`, "导出成功");
    } catch (generateError) {
      if (isUnauthorizedError(generateError)) {
        return;
      }

      const message = generateError.message || generateError;
      if (targetRecords.length > 1) {
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
    exportProgressPercent,
    exportProgressLabel,
    exportCount,
    generateButtonLabel,
    handleGenerate,
  };
}
