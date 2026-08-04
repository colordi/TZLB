import { describe, expect, it } from "vitest";

import { getChartColors, getChartTheme, normalizeChartColor } from "../chart-palette.js";

describe("chart-palette", () => {
  it("jsdom 无 canvas 环境时 normalizeChartColor 原样透传", () => {
    expect(normalizeChartColor("oklch(0.52 0.09 155)")).toBe("oklch(0.52 0.09 155)");
    expect(normalizeChartColor("rgb(1, 2, 3)")).toBe("rgb(1, 2, 3)");
  });

  it("空值返回 fallback", () => {
    expect(normalizeChartColor("", "rgb(0, 0, 0)")).toBe("rgb(0, 0, 0)");
    expect(normalizeChartColor(null, "rgb(0, 0, 0)")).toBe("rgb(0, 0, 0)");
    expect(normalizeChartColor("")).toBe("");
  });

  it("主题解析提供 5 个图表基色与语义色", () => {
    expect(getChartColors().length).toBe(5);
    const theme = getChartTheme();
    expect(theme.colors.length).toBe(5);
    for (const key of ["foreground", "mutedForeground", "muted", "border", "card"]) {
      expect(typeof theme[key]).toBe("string");
      expect(theme[key].length).toBeGreaterThan(0);
    }
  });
});
