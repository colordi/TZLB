/**
 * 数据管理页筛选栏：由列元数据推导筛选控件（纯逻辑，便于单测）。
 *
 * - 文本筛选：PREFERRED_FILTER_COLUMNS 中存在的列，后端按文本模糊匹配；
 * - 日期区间：input_kind 为 date/datetime 的列（date/timestamp 类型），
 *   渲染起止两个日期输入框。事件流水表的"事件时间"不在偏好清单里，
 *   由类型识别自动补上日期筛选，新表同理无需改配置。
 */

/** 工具栏优先展示的过滤列，按顺序取表中存在的列 */
export const PREFERRED_FILTER_COLUMNS = [
  "编号",
  "属地",
  "点位名称",
  "调查日期",
  "年份",
  "世代",
  "危害程度",
  "害虫类型",
];

export const MAX_FILTER_INPUTS = 5;

const DATE_INPUT_KINDS = new Set(["date", "datetime"]);

export function isDateFilterColumn(column) {
  return DATE_INPUT_KINDS.has(column?.input_kind);
}

/**
 * 生成筛选控件清单 [{ name, kind: "text" | "date" }]。
 * 偏好列保持声明顺序；偏好清单之外的日期/时间列按表内列序追加。
 * 日期区间筛选始终保留，max 只约束文本输入个数（否则偏好列凑满上限时，
 * 事件流水表的"事件时间"会被截掉）。
 */
export function buildFilterSpecs(columns, max = MAX_FILTER_INPUTS) {
  const byName = new Map((columns || []).map((c) => [c.name, c]));
  const specs = [];
  for (const name of PREFERRED_FILTER_COLUMNS) {
    const column = byName.get(name);
    if (!column) continue;
    specs.push({ name, kind: isDateFilterColumn(column) ? "date" : "text" });
  }
  const picked = new Set(specs.map((s) => s.name));
  for (const column of columns || []) {
    if (picked.has(column.name) || !isDateFilterColumn(column)) continue;
    specs.push({ name: column.name, kind: "date" });
  }
  let textCount = 0;
  return specs.filter((spec) => {
    if (spec.kind === "date") return true;
    textCount += 1;
    return textCount <= max;
  });
}
