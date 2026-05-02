import { describe, expect, it } from "vitest";

import {
  createEmptyRecord,
  getDefaultControlType,
  getDefaultTask,
  getVisibleFields,
  toPayloadRecord,
  validateRecords,
} from "../fieldConfig.js";

function buildSpringRecord(overrides = {}) {
  return {
    ...createEmptyRecord("春尺蠖"),
    survey_date: "2026-03-31",
    town_or_street: "城东镇",
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
      "town_or_street",
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
      "town_or_street",
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
      "town_or_street",
      "location_id",
      "location_name",
      "plot_type",
      "pest_name",
      "host_plant",
      "note",
      "description",
    ]);
  });

  it("其他害虫默认统防统治类型与任务改为其他害虫防治", () => {
    expect(getDefaultControlType("其他害虫")).toBe("其他害虫防治");
    expect(getDefaultTask("其他害虫")).toBe("2026其他害虫防治");
  });

  it("国槐尺蠖默认统防统治类型与任务改为国槐尺蠖防治", () => {
    expect(getDefaultControlType("国槐尺蠖")).toBe("国槐尺蠖防治");
    expect(getDefaultTask("国槐尺蠖")).toBe("2026国槐尺蠖防治");
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
      town_or_street: "城东镇",
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
        town_or_street: "宋庄镇",
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
      town_or_street: "宋庄镇",
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
        town_or_street: "潞城镇",
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
      town_or_street: "潞城镇",
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
});
