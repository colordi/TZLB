import { describe, expect, it } from "vitest";

import {
  isLedgerFlowTable,
  orderGridColumns,
  stickyColumnLayout,
} from "../columnLayout.js";

function col(name) {
  return { name };
}

function makeTable(schemaName, tableName) {
  return { schema_name: schemaName, table_name: tableName };
}

const ledgerTable = makeTable("ledger", "美国白蛾问题点位事件流水表");

/** 美国白蛾事件流水表在数据库中的真实列顺序 */
function ledgerColumns() {
  return [
    "id",
    "事件时间",
    "事件类型",
    "属地",
    "编号",
    "点位名称",
    "发生位置",
    "本次详细情况",
    "备注",
    "年份",
    "世代",
  ].map(col);
}

describe("datamanager/columnLayout isLedgerFlowTable", () => {
  it("匹配 ledger 下全部事件流水表", () => {
    for (const name of [
      "美国白蛾问题点位事件流水表",
      "国槐尺蠖问题点位事件流水表",
      "春尺蠖问题点位事件流水表",
      "其他害虫问题点位事件流水表",
      "杨树食叶害虫问题点位事件流水表",
    ]) {
      expect(isLedgerFlowTable(makeTable("ledger", name))).toBe(true);
    }
  });

  it("调查表、台账、点位基础表不匹配", () => {
    expect(isLedgerFlowTable(makeTable("survey", "美国白蛾调查表"))).toBe(false);
    expect(isLedgerFlowTable(makeTable("ledger", "美国白蛾问题点位台账"))).toBe(false);
    expect(isLedgerFlowTable(makeTable("sites", "美国白蛾点位基础表"))).toBe(false);
  });

  it("空表返回 false", () => {
    expect(isLedgerFlowTable(null)).toBe(false);
    expect(isLedgerFlowTable(undefined)).toBe(false);
    expect(isLedgerFlowTable({})).toBe(false);
  });
});

describe("datamanager/columnLayout orderGridColumns", () => {
  it("事件流水表：编号/点位名称/事件时间/事件类型提到最前，其余保持原顺序", () => {
    const ordered = orderGridColumns(ledgerTable, ledgerColumns());

    expect(ordered.map((c) => c.name)).toEqual([
      "编号",
      "点位名称",
      "事件时间",
      "事件类型",
      "id",
      "属地",
      "发生位置",
      "本次详细情况",
      "备注",
      "年份",
      "世代",
    ]);
  });

  it("缺少优先列时跳过，不打乱其余列", () => {
    const ordered = orderGridColumns(
      ledgerTable,
      ["id", "事件时间", "事件类型", "编号", "备注"].map(col),
    );

    expect(ordered.map((c) => c.name)).toEqual([
      "编号",
      "事件时间",
      "事件类型",
      "id",
      "备注",
    ]);
  });

  it("非事件流水表原样返回（同一引用）", () => {
    const columns = ["id", "编号", "调查日期"].map(col);
    expect(orderGridColumns(makeTable("survey", "美国白蛾调查表"), columns)).toBe(
      columns,
    );
  });

  it("空列清单返回空数组", () => {
    expect(orderGridColumns(ledgerTable, [])).toEqual([]);
    expect(orderGridColumns(ledgerTable, undefined)).toEqual([]);
  });
});

describe("datamanager/columnLayout stickyColumnLayout", () => {
  it("事件流水表：冻结 编号/点位名称/事件时间，偏移为前序宽度之和", () => {
    const ordered = orderGridColumns(ledgerTable, ledgerColumns());
    const layout = stickyColumnLayout(ledgerTable, ordered);

    expect(layout).toEqual([
      { name: "编号", widthRem: 6, leftRem: 0 },
      { name: "点位名称", widthRem: 10, leftRem: 6 },
      { name: "事件时间", widthRem: 11, leftRem: 16 },
    ]);
  });

  it("缺少冻结列时跳过，后续偏移前移", () => {
    const ordered = orderGridColumns(
      ledgerTable,
      ["id", "事件时间", "事件类型", "编号"].map(col),
    );
    const layout = stickyColumnLayout(ledgerTable, ordered);

    expect(layout).toEqual([
      { name: "编号", widthRem: 6, leftRem: 0 },
      { name: "事件时间", widthRem: 11, leftRem: 6 },
    ]);
  });

  it("非事件流水表不冻结任何列", () => {
    const layout = stickyColumnLayout(
      makeTable("survey", "美国白蛾调查表"),
      ["编号", "点位名称", "事件时间"].map(col),
    );

    expect(layout).toEqual([]);
  });
});
