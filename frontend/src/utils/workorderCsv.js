import {
  getVisibleFields,
  normalizeRecordForPest,
} from "../components/workorder/fieldConfig.js";

function pad(value) {
  return `${value}`.padStart(2, "0");
}

function getTimestamp() {
  const now = new Date();
  return [
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate()),
  ].join("") + `_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
}

function escapeCsvCell(value) {
  const normalized = value === undefined || value === null ? "" : `${value}`;
  if (/[",\n]/.test(normalized)) {
    return `"${normalized.replace(/"/g, "\"\"")}"`;
  }
  return normalized;
}

export function buildWorkorderCsvRows({ pestType, taskName, taskType, records }) {
  const visibleFields = getVisibleFields(pestType);
  const headers = [
    "序号",
    "害虫类型",
    "统防统治类型",
    "统防统治任务",
    ...visibleFields.map((field) => field.label),
    "图片数量",
  ];

  const rows = records.map((record, index) => {
    const normalized = normalizeRecordForPest(record, pestType);
    return [
      String(index + 1).padStart(2, "0"),
      pestType,
      taskType,
      taskName || taskType,
      ...visibleFields.map((field) => normalized[field.key] || ""),
      `${normalized.images?.length || 0}`,
    ];
  });

  return { headers, rows };
}

export function createWorkorderCsvFile(options) {
  const { headers, rows } = buildWorkorderCsvRows(options);
  const lines = [headers, ...rows].map((row) => row.map(escapeCsvCell).join(","));
  const content = `\uFEFF${lines.join("\r\n")}`;

  return {
    blob: new Blob([content], { type: "text/csv;charset=utf-8;" }),
    filename: `林业调查数据_${getTimestamp()}.csv`,
  };
}
