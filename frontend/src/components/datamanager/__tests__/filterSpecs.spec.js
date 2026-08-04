import { describe, expect, it } from "vitest";

import {
  MAX_FILTER_INPUTS,
  buildFilterSpecs,
  isDateFilterColumn,
} from "../filterSpecs.js";

function col(name, input_kind = "text") {
  return { name, input_kind };
}

describe("datamanager/filterSpecs", () => {
  it("识别日期与时间列", () => {
    expect(isDateFilterColumn(col("调查日期", "date"))).toBe(true);
    expect(isDateFilterColumn(col("事件时间", "datetime"))).toBe(true);
    expect(isDateFilterColumn(col("属地", "text"))).toBe(false);
    expect(isDateFilterColumn(undefined)).toBe(false);
  });

  it("偏好列按声明顺序返回，date 类型列标记为 date 控件", () => {
    const specs = buildFilterSpecs([
      col("年份", "number"),
      col("属地"),
      col("编号"),
      col("调查日期", "date"),
    ]);

    expect(specs).toEqual([
      { name: "编号", kind: "text" },
      { name: "属地", kind: "text" },
      { name: "调查日期", kind: "date" },
      { name: "年份", kind: "text" },
    ]);
  });

  it("偏好清单之外的日期/时间列自动追加（事件流水表的事件时间）", () => {
    const specs = buildFilterSpecs([
      col("编号"),
      col("属地"),
      col("事件类型"),
      col("事件时间", "datetime"),
      col("年份", "number"),
    ]);

    expect(specs).toContainEqual({ name: "事件时间", kind: "date" });
    expect(specs.map((s) => s.name)).toEqual([
      "编号",
      "属地",
      "年份",
      "事件时间",
    ]);
  });

  it("非偏好且非日期的列不进入筛选栏", () => {
    const specs = buildFilterSpecs([col("备注"), col("成虫数量", "number")]);
    expect(specs).toEqual([]);
  });

  it("文本筛选不超过上限，日期区间始终保留", () => {
    const specs = buildFilterSpecs([
      col("编号"),
      col("属地"),
      col("点位名称"),
      col("调查日期", "date"),
      col("年份", "number"),
      col("世代"),
      col("危害程度"),
      col("害虫类型"),
      col("事件时间", "datetime"),
    ]);
    const texts = specs.filter((s) => s.kind === "text");
    const dates = specs.filter((s) => s.kind === "date");
    expect(texts).toHaveLength(MAX_FILTER_INPUTS);
    expect(dates.map((s) => s.name)).toEqual(["调查日期", "事件时间"]);
  });

  it("偏好文本列凑满上限时日期列不被截掉（美国白蛾事件流水表场景）", () => {
    const specs = buildFilterSpecs([
      col("编号"),
      col("属地"),
      col("点位名称"),
      col("年份", "number"),
      col("世代"),
      col("事件时间", "datetime"),
    ]);
    expect(specs.map((s) => s.name)).toEqual([
      "编号",
      "属地",
      "点位名称",
      "年份",
      "世代",
      "事件时间",
    ]);
  });

  it("空列清单返回空数组", () => {
    expect(buildFilterSpecs([])).toEqual([]);
    expect(buildFilterSpecs(null)).toEqual([]);
  });
});
