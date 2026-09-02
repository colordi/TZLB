/**
 * 数据管理页数据表格的列排序与冻结列规则（纯逻辑，便于单测）。
 *
 * 事件流水表（ledger.*问题点位事件流水表）把 编号/点位名称/事件时间/事件类型
 * 提到最前展示，其余列保持数据库原始顺序；其中 编号/点位名称/事件时间
 * 三列在横向滚动时冻结在左侧。冻结列使用固定宽度，左侧偏移才能静态计算，
 * 无需运行时测量单元格宽度。
 */

/** 事件流水表前置展示的列，数组顺序即展示顺序 */
export const LEDGER_FLOW_PRIORITY_COLUMNS = ["编号", "点位名称", "事件时间", "事件类型"];

/** 事件流水表冻结列的固定宽度（rem），顺序必须是前置列的前缀 */
const LEDGER_FLOW_STICKY_SPECS = [
  { name: "编号", widthRem: 6 },
  { name: "点位名称", widthRem: 10 },
  { name: "事件时间", widthRem: 11 },
];

export function isLedgerFlowTable(table) {
  return (
    table?.schema_name === "ledger" &&
    typeof table?.table_name === "string" &&
    table.table_name.endsWith("问题点位事件流水表")
  );
}

/**
 * 数据表格列排序：事件流水表把优先列提到最前，其余列保持原相对顺序；
 * 优先列在表中不存在时跳过；其他表原样返回。
 */
export function orderGridColumns(table, columns) {
  const list = columns || [];
  if (!isLedgerFlowTable(table)) {
    return list;
  }
  const byName = new Map(list.map((col) => [col.name, col]));
  const head = LEDGER_FLOW_PRIORITY_COLUMNS.map((name) => byName.get(name)).filter(Boolean);
  const headNames = new Set(head.map((col) => col.name));
  const rest = list.filter((col) => !headNames.has(col.name));
  return [...head, ...rest];
}

/**
 * 冻结列布局，返回 [{ name, widthRem, leftRem }]，leftRem 为前序冻结列宽度之和。
 * 仅事件流水表返回非空；某冻结列不存在时跳过，后续列偏移相应前移。
 */
export function stickyColumnLayout(table, orderedColumns) {
  if (!isLedgerFlowTable(table)) {
    return [];
  }
  const present = new Set((orderedColumns || []).map((col) => col.name));
  const layout = [];
  let leftRem = 0;
  for (const spec of LEDGER_FLOW_STICKY_SPECS) {
    if (!present.has(spec.name)) {
      continue;
    }
    layout.push({ name: spec.name, widthRem: spec.widthRem, leftRem });
    leftRem += spec.widthRem;
  }
  return layout;
}
