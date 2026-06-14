import { describe, expect, it } from "vitest";

import {
  PEST_OPTIONS,
  createEmptyRecord,
  getDefaultControlType,
  getDefaultTask,
  getTaskOptions,
  getVisibleFields,
  normalizeRecordForPest,
  toPayloadRecord,
  validateRecords,
} from "../fieldConfig.js";

function buildSpringRecord(overrides = {}) {
  return {
    ...createEmptyRecord("春尺蠖"),
    survey_date: "2026-03-31",
    locality: "城东镇",
    location_id: "CC-001",
    location_name: "城东林场A区",
    description: "现场描述",
    note: "需复查",
    ...overrides,
  };
}

describe("fieldConfig", () => {
  it("春尺蠖只返回模板所需字段", () => {
    const fieldKeys = getVisibleFields("春尺蠖").map((field) => field.key);

    expect(fieldKeys).toEqual([
      "survey_date",
      "locality",
      "location_id",
      "location_name",
      "note",
      "description",
    ]);
  });

  it("国槐尺蠖只返回模板所需字段", () => {
    const fieldKeys = getVisibleFields("国槐尺蠖").map((field) => field.key);

    expect(fieldKeys).toEqual([
      "survey_date",
      "locality",
      "location_id",
      "location_name",
      "note",
      "description",
    ]);
  });

  it("其他害虫只保留模板所需字段", () => {
    const fieldKeys = getVisibleFields("其他害虫").map((field) => field.key);

    expect(fieldKeys).toEqual([
      "survey_date",
      "locality",
      "location_id",
      "location_name",
      "plot_type",
      "pest_name",
      "host_plant",
      "note",
      "description",
    ]);
  });

  it("美国白蛾只保留模板所需字段", () => {
    const fieldKeys = getVisibleFields("美国白蛾").map((field) => field.key);

    expect(fieldKeys).toEqual([
      "survey_date",
      "locality",
      "location_id",
      "location_name",
      "green_space_type",
      "pest_hosts",
      "damaged_plant_count",
      "web_nest_count",
      "note",
      "description",
    ]);
  });

  it("害虫类型选项包含美国白蛾", () => {
    expect(PEST_OPTIONS.map((option) => option.value)).toContain("美国白蛾");
  });

  it("其他害虫默认统防统治类型与任务改为其他害虫防治", () => {
    expect(getDefaultControlType("其他害虫")).toBe("其他害虫防治");
    expect(getDefaultTask("其他害虫")).toBe("2026其他害虫防治");
  });

  it("美国白蛾默认统防统治类型与任务为第一代防治", () => {
    expect(getDefaultControlType("美国白蛾")).toBe("美国白蛾防治");
    expect(getDefaultTask("美国白蛾")).toBe("2026美国白蛾第一代防治");
    expect(getTaskOptions("美国白蛾").map((option) => option.value)).toEqual([
      "2026美国白蛾第一代防治",
    ]);
  });

  it("归一化导入记录时兼容旧属地字段", () => {
    const normalized = normalizeRecordForPest(
      {
        survey_date: "2026-04-01",
        town_or_street: "于家务乡",
        location_id: "YF0069",
        location_name: "神仙村",
        description: "现场描述",
      },
      "春尺蠖",
    );

    expect(normalized.locality).toBe("于家务乡");
  });

  it("国槐尺蠖默认统防统治类型与任务改为国槐尺蠖防治", () => {
    expect(getDefaultControlType("国槐尺蠖")).toBe("国槐尺蠖防治");
    expect(getDefaultTask("国槐尺蠖")).toBe("2026国槐尺蠖第一代防治");
    expect(getTaskOptions("国槐尺蠖").map((option) => option.value)).toEqual([
      "2026国槐尺蠖第一代防治",
      "2026国槐尺蠖第二代防治",
      "2026国槐尺蠖第三代防治",
    ]);
  });

  it("春尺蠖导出载荷只保留模板字段", () => {
    const payload = toPayloadRecord(
      buildSpringRecord({
        region: "乡镇",
        occurrence_position: "林区东侧",
        total_insect_count: "156",
        damage_level: "中",
        plot_type: "平原造林",
        report_time: "2026-03-31",
        images: ["a", "b"],
      }),
      "春尺蠖",
    );

    expect(payload).toEqual({
      survey_date: "2026-03-31",
      locality: "城东镇",
      location_id: "CC-001",
      location_name: "城东林场A区",
      description: "现场描述",
      note: "需复查",
      images: ["a", "b"],
    });
  });

  it("春尺蠖校验不再校验隐藏字段", () => {
    const [errors] = validateRecords(
      [
        buildSpringRecord({
          total_insect_count: "abc",
          damage_level: "重",
          occurrence_position: "林区东侧",
          report_time: "2026-03-31",
        }),
      ],
      "春尺蠖",
    );

    expect(errors).toEqual({});
  });

  it("国槐尺蠖导出载荷只保留模板字段", () => {
    const payload = toPayloadRecord(
      {
        ...createEmptyRecord("国槐尺蠖"),
        survey_date: "2026-05-02",
        locality: "宋庄镇",
        location_id: "1001-1",
        location_name: "管头村",
        description: "现场描述",
        note: "需复查",
        total_insect_count: "45",
        damage_level: "重",
        region: "乡镇",
        occurrence_position: "林区东侧",
        report_time: "2026-05-02",
      },
      "国槐尺蠖",
    );

    expect(payload).toEqual({
      survey_date: "2026-05-02",
      locality: "宋庄镇",
      location_id: "1001-1",
      location_name: "管头村",
      description: "现场描述",
      note: "需复查",
      images: [],
    });
  });

  it("其他害虫导出载荷只保留模板字段", () => {
    const payload = toPayloadRecord(
      {
        ...createEmptyRecord("其他害虫"),
        survey_date: "2026-04-17",
        locality: "潞城镇",
        location_id: "QT0001",
        location_name: "畅和东路北京学校西侧",
        plot_type: "道路绿化",
        pest_name: "蚜虫",
        host_plant: "栾树",
        note: "",
        description: "现场描述",
        region: "城区",
        occurrence_position: "学校西侧",
        report_time: "2026-04-17",
      },
      "其他害虫",
    );

    expect(payload).toEqual({
      survey_date: "2026-04-17",
      locality: "潞城镇",
      location_id: "QT0001",
      location_name: "畅和东路北京学校西侧",
      plot_type: "道路绿化",
      pest_name: "蚜虫",
      host_plant: "栾树",
      note: "",
      description: "现场描述",
      images: [],
    });
  });

  it("美国白蛾导出载荷只保留模板字段", () => {
    const payload = toPayloadRecord(
      {
        ...createEmptyRecord("美国白蛾"),
        survey_date: "2026-05-26",
        region: "城区",
        locality: "梨园镇",
        location_id: "MQ001",
        location_name: "玉桥东路",
        occurrence_position: "道路东侧",
        green_space_type: "道路绿化",
        pest_hosts: "白蜡",
        damaged_plant_count: "3",
        web_nest_count: "5",
        note: "需复查",
        description: "发现美国白蛾网幕，已安排剪网处置。",
        report_time: "2026-05-26",
      },
      "美国白蛾",
    );

    expect(payload).toEqual({
      survey_date: "2026-05-26",
      locality: "梨园镇",
      location_id: "MQ001",
      location_name: "玉桥东路",
      green_space_type: "道路绿化",
      pest_hosts: "白蜡",
      damaged_plant_count: 3,
      web_nest_count: 5,
      description: "发现美国白蛾网幕，已安排剪网处置。",
      note: "需复查",
      images: [],
    });
    expect(payload).not.toHaveProperty("region");
    expect(payload).not.toHaveProperty("occurrence_position");
  });
});
