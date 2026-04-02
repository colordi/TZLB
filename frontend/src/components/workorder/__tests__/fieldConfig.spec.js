import { describe, expect, it } from "vitest";

import {
  createEmptyRecord,
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

  it("国槐尺蠖继续保留原有字段集合", () => {
    const fieldKeys = getVisibleFields("国槐尺蠖").map((field) => field.key);

    expect(fieldKeys).toContain("region");
    expect(fieldKeys).toContain("occurrence_position");
    expect(fieldKeys).toContain("total_insect_count");
    expect(fieldKeys).toContain("damage_level");
    expect(fieldKeys).toContain("report_time");
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
});
