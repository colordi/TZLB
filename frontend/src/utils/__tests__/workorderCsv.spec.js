import { describe, expect, it } from "vitest";

import { buildWorkorderCsvRows } from "../workorderCsv.js";

describe("buildWorkorderCsvRows", () => {
  it("按当前害虫字段生成表头和记录行", () => {
    const { headers, rows } = buildWorkorderCsvRows({
      pestType: "春尺蠖",
      taskType: "春尺蠖防治",
      taskName: "2026春尺蠖防治",
      records: [
        {
          survey_date: "2026-03-31",
          town_or_street: "城东镇",
          location_id: "CC-001",
          location_name: "城东林场A区",
          note: "现场北侧",
          description: "现场描述",
          images: ["a", "b"],
        },
      ],
    });

    expect(headers).toEqual([
      "序号",
      "害虫类型",
      "统防统治类型",
      "统防统治任务",
      "调查日期",
      "乡镇｜街道",
      "编号",
      "点位名称",
      "备注",
      "详细情况描述",
      "图片数量",
    ]);
    expect(headers).toContain("图片数量");
    expect(headers).not.toContain("发生位置");
    expect(headers).not.toContain("总虫口数");
    expect(headers).not.toContain("受害程度");
    expect(headers).not.toContain("上报时间");
    expect(rows[0][0]).toBe("01");
    expect(rows[0][1]).toBe("春尺蠖");
    expect(rows[0][8]).toBe("现场北侧");
    expect(rows[0].at(-1)).toBe("2");
  });
});
