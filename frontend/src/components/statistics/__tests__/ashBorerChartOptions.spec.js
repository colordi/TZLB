import { describe, expect, it } from "vitest";

import {
  ASH_BORER_DAMAGE_LEVELS,
  ASH_BORER_RATE_METRICS,
  buildDamageLevelLocalityOption,
  buildDamageLevelOverallOption,
  buildLocalityRateBarOption,
  buildMortalityRankingOption,
  formatRate,
  rankingChartHeight,
} from "../ashBorerChartOptions.js";

const THEME = {
  colors: ["#111", "#222", "#333", "#444", "#555"],
  foreground: "#000",
  mutedForeground: "#888",
  muted: "#f5f5f5",
  border: "#ddd",
  card: "#fff",
  severity: {
    none: "#ffffff",
    light: "#0033ff",
    medium: "#fbff05",
    high: "#ff0000",
  },
};

function buildLocalities() {
  return [
    {
      locality: "宋庄镇",
      surveyed_points: 8,
      excluded_points: 2,
      dead_plants: 4,
      felled_plants: 2,
      agrilus_damaged_plants: 20,
      cossus_damaged_plants: 6,
      mortality_rate: 2.5,
      agrilus_infestation_rate: 8.3,
      cossus_infestation_rate: 2.5,
      agrilus_damage_levels: { none: 4, light: 2, medium: 1, high: 1 },
      cossus_damage_levels: { none: 1, light: 3, medium: 2, high: 2 },
    },
    {
      locality: "潞城镇",
      surveyed_points: 10,
      excluded_points: 0,
      dead_plants: 9,
      felled_plants: 12,
      agrilus_damaged_plants: 5,
      cossus_damaged_plants: 30,
      mortality_rate: 7.0,
      agrilus_infestation_rate: 1.7,
      cossus_infestation_rate: 10.0,
      agrilus_damage_levels: { none: 6, light: 3, medium: 1, high: 0 },
      cossus_damage_levels: { none: 0, light: 2, medium: 3, high: 5 },
    },
    {
      locality: "空属地",
      surveyed_points: 0,
      excluded_points: 3,
      dead_plants: 0,
      felled_plants: 0,
      agrilus_damaged_plants: 0,
      cossus_damaged_plants: 0,
      mortality_rate: null,
      agrilus_infestation_rate: null,
      cossus_infestation_rate: null,
    },
  ];
}

describe("ashBorerChartOptions", () => {
  it("formatRate 对空值显示占位", () => {
    expect(formatRate(2.5)).toBe("2.5%");
    expect(formatRate(null)).toBe("--");
    expect(formatRate(undefined)).toBe("--");
  });

  it("分组柱状图按死亡率降序，并排除无有效点位的属地", () => {
    const option = buildLocalityRateBarOption(buildLocalities(), THEME);

    expect(option.xAxis.data).toEqual(["潞城镇", "宋庄镇"]);
    expect(option.series).toHaveLength(ASH_BORER_RATE_METRICS.length);
    expect(option.series.map((series) => series.name)).toEqual([
      "死亡率",
      "窄吉丁有虫株率",
      "木蠹蛾有虫株率",
    ]);
    expect(option.series[0].data.map((item) => item.value)).toEqual([7, 2.5]);
    expect(option.series[1].data[0]).toMatchObject({
      locality: "潞城镇",
      agrilus_damaged_plants: 5,
      surveyed_points: 10,
    });
    expect(option.series[2].data[1]).toMatchObject({
      locality: "宋庄镇",
      cossus_damaged_plants: 6,
    });
  });

  it("死亡率排行按降序绘制横向柱，标签为百分率", () => {
    const option = buildMortalityRankingOption(buildLocalities(), THEME);

    expect(option.yAxis.data).toEqual(["潞城镇", "宋庄镇"]);
    expect(option.series[0].data.map((item) => item.value)).toEqual([7, 2.5]);
    expect(option.series[0].label.formatter({ value: 7 })).toBe("7.0%");
  });

  it("空数据返回空坐标轴", () => {
    const option = buildLocalityRateBarOption([], THEME);
    expect(option.xAxis.data).toEqual([]);
    expect(option.series[0].data).toEqual([]);
  });

  it("排行图高度随属地数量增加", () => {
    expect(rankingChartHeight(0)).toBe("280px");
    expect(rankingChartHeight(9)).toBe("372px");
  });

  it("全区危害程度堆叠柱按虫种对比无轻中重", () => {
    const option = buildDamageLevelOverallOption(
      {
        agrilus_damage_levels: { none: 10, light: 5, medium: 3, high: 2 },
        cossus_damage_levels: { none: 1, light: 4, medium: 6, high: 9 },
      },
      THEME,
    );

    expect(option.xAxis.data).toEqual(["窄吉丁", "木蠹蛾"]);
    expect(option.series.map((series) => series.name)).toEqual(
      ASH_BORER_DAMAGE_LEVELS.map((level) => level.label),
    );
    expect(option.series[0].data.map((item) => item.value)).toEqual([10, 1]);
    expect(option.series[3].data.map((item) => item.value)).toEqual([2, 9]);
    expect(option.series[0].itemStyle.color).toBe("#ffffff");
    expect(option.series[3].itemStyle.color).toBe("#ff0000");
  });

  it("属地危害程度按重度点位数降序，并排除无有效点位属地", () => {
    const option = buildDamageLevelLocalityOption(
      buildLocalities(),
      "cossus_damage_levels",
      THEME,
    );

    expect(option.xAxis.data).toEqual(["潞城镇", "宋庄镇"]);
    expect(option.series[3].data.map((item) => item.value)).toEqual([5, 2]);
    expect(option.series.map((series) => series.stack)).toEqual([
      "severity",
      "severity",
      "severity",
      "severity",
    ]);
  });
});
