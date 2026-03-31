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
          region: "乡镇",
          town_or_street: "城东镇",
          location_id: "CC-001",
          location_name: "城东林场A区",
          occurrence_position: "林区东侧",
          total_insect_count: "156",
          damage_level: "中",
          plot_type: "平原造林",
          report_time: "2026-03-31",
          description: "现场描述",
          images: ["a", "b"],
        },
      ],
    });

    expect(headers).toContain("调查日期");
    expect(headers).toContain("图片数量");
    expect(rows[0][0]).toBe("01");
    expect(rows[0][1]).toBe("春尺蠖");
    expect(rows[0].at(-1)).toBe("2");
  });
});
