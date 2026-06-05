import { describe, expect, it } from "vitest";
import {
  buildPopupRows,
  buildSurveyStatusSummary,
  hasFeatureSeverityField,
  resolveFeatureHoverLabel,
  resolveFeaturePointLabel,
  resolveFeatureSeverity,
} from "../popupFields.js";

describe("buildPopupRows", () => {
  it("按照当前 view 的 columns 顺序输出字段", () => {
    const columns = ["村", "属地", "编号"];
    const properties = {
      村: "南村",
      属地: "东镇",
      编号: "001",
    };

    expect(buildPopupRows(columns, properties)).toEqual([
      ["村", "南村"],
      ["属地", "东镇"],
      ["编号", "001"],
    ]);
  });

  it("只展示 columns 中存在的字段，不把其他属性混进弹窗", () => {
    const columns = ["编号"];
    const properties = {
      编号: "001",
      extra: "不应显示",
    };

    expect(buildPopupRows(columns, properties)).toEqual([["编号", "001"]]);
  });

  it("空值使用 - 占位", () => {
    const columns = ["调查日期"];

    expect(buildPopupRows(columns, {})).toEqual([["调查日期", "-"]]);
  });

  it("悬停提示优先返回点位名称类字段", () => {
    expect(
      resolveFeatureHoverLabel(["编号", "点位名称"], {
        编号: "CC-001",
        点位名称: "城东林场A区",
      }),
    ).toBe("城东林场A区");
  });

  it("悬停提示可按场景优先返回编号", () => {
    expect(
      resolveFeatureHoverLabel(
        ["id", "编号", "点位名称"],
        {
          id: 12,
          编号: "CC-001",
          点位名称: "城东林场A区",
        },
        { preferIdentifier: true },
      ),
    ).toBe("CC-001");
  });

  it("编号标签优先使用中文编号字段", () => {
    expect(
      resolveFeaturePointLabel({
        编号: " CN-001 ",
        location_id: "LOC-001",
      }),
    ).toBe("CN-001");
  });

  it("编号标签按 location_id、locationId、id 顺序回退", () => {
    expect(
      resolveFeaturePointLabel({
        location_id: "LOC-001",
        locationId: "LOC-002",
        id: "fallback-id",
      }),
    ).toBe("LOC-001");
  });

  it("编号标签在缺少编号或空值时返回空字符串", () => {
    expect(resolveFeaturePointLabel({ 编号: " ", location_id: null })).toBe("");
  });

  it("调查状态统计会按已完成、待调查、调查中归类", () => {
    const summary = buildSurveyStatusSummary([
      { properties: { 调查状态: "调查" } },
      { properties: { 调查状态: "未调查" } },
      { properties: { 调查状态: "调查中" } },
    ]);

    expect(summary).toEqual({
      completed: 1,
      pending: 1,
      in_progress: 1,
    });
  });

  it("支持识别当前 view 是否包含危害程度字段", () => {
    expect(hasFeatureSeverityField(["编号", "危害程度"])).toBe(true);
    expect(hasFeatureSeverityField(["编号", "severity"])).toBe(true);
    expect(hasFeatureSeverityField(["编号", "调查状态"])).toBe(false);
  });

  it("空值和无危害值会归一为无等级", () => {
    expect(resolveFeatureSeverity(0)).toMatchObject({
      key: "level0",
      color: "#E7F3E8",
      label: "无",
    });
    expect(resolveFeatureSeverity("白").label).toBe("无");
    expect(resolveFeatureSeverity("无需防治").label).toBe("无");
    expect(resolveFeatureSeverity("无").label).toBe("无");
  });
});
