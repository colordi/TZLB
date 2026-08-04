import { describe, expect, it } from "vitest";

import {
  buildGenerationCompareBarOption,
  buildGenerationHeatmapOption,
  buildHeatmapOption,
  buildRankingOption,
  buildTreemapOption,
  formatShare,
  HEATMAP_HOST_LIMIT,
  RANKING_LIMIT,
} from "../hostChartOptions.js";

const THEME = {
  colors: ["#111", "#222", "#333", "#444", "#555"],
  foreground: "#000",
  mutedForeground: "#888",
  muted: "#f5f5f5",
  border: "#ddd",
  card: "#fff",
};

function buildHosts(count) {
  const hosts = [];
  for (let index = 0; index < count; index += 1) {
    hosts.push({
      host: `树种${index + 1}`,
      points: count - index,
      plants: (count - index) * 10,
      share: 0.1,
      localities: [
        { locality: `属地${(index % 3) + 1}`, plants: (count - index) * 6 },
        { locality: "宋庄镇", plants: index + 1 },
      ],
    });
  }
  return hosts;
}

describe("hostChartOptions", () => {
  it("树图按指标取值并附带 tooltip 数据", () => {
    const hosts = buildHosts(3);
    const plantsOption = buildTreemapOption(hosts, "plants", THEME);
    const pointsOption = buildTreemapOption(hosts, "points", THEME);

    expect(plantsOption.series[0].data.map((item) => item.value)).toEqual([30, 20, 10]);
    expect(pointsOption.series[0].data.map((item) => item.value)).toEqual([3, 2, 1]);
    expect(plantsOption.series[0].data[0]).toMatchObject({
      name: "树种1",
      plants: 30,
      points: 3,
    });
  });

  it("排行榜按指标降序并截取 Top N", () => {
    const hosts = buildHosts(20);
    const option = buildRankingOption(hosts, "plants", THEME);

    expect(option.yAxis.data.length).toBe(RANKING_LIMIT);
    expect(option.series[0].data[0]).toMatchObject({ name: "树种1", value: 200 });
    expect(option.series[0].data.at(-1)).toMatchObject({ name: "树种15", value: 60 });
  });

  it("排行榜支持按点位数排序", () => {
    const hosts = [
      { host: "甲", points: 1, plants: 100, share: 0.5, localities: [] },
      { host: "乙", points: 9, plants: 5, share: 0.5, localities: [] },
    ];
    const option = buildRankingOption(hosts, "points", THEME);
    expect(option.series[0].data.map((item) => item.name)).toEqual(["乙", "甲"]);
  });

  it("排行榜中「其他」合并桶不参与名次，固定置于榜尾且颜色区分", () => {
    const hosts = [
      { host: "甲", points: 1, plants: 50, share: 0.1, localities: [] },
      { host: "乙", points: 2, plants: 40, share: 0.1, localities: [] },
      // 合并值最大，但不应占据榜首
      { host: "其他", points: 99, plants: 999, share: 0.8, localities: [], merged_hosts: 45 },
    ];
    const option = buildRankingOption(hosts, "plants", THEME);

    expect(option.yAxis.data).toEqual(["甲", "乙", "其他（45 种合并）"]);
    const otherBar = option.series[0].data.at(-1);
    expect(otherBar.mergedHosts).toBe(45);
    expect(otherBar.itemStyle.color).toBe(THEME.mutedForeground);
    expect(option.series[0].data[0].itemStyle.color).toBe(THEME.colors[0]);
  });

  it("树图中「其他」合并桶使用中性灰，具名寄主使用图表基色", () => {
    const hosts = [
      { host: "甲", points: 1, plants: 50, share: 0.5, localities: [] },
      { host: "其他", points: 2, plants: 40, share: 0.5, localities: [], merged_hosts: 3 },
    ];
    const option = buildTreemapOption(hosts, "plants", THEME);

    expect(option.series[0].data[0].itemStyle.color).toBe(THEME.colors[0]);
    expect(option.series[0].data[1].itemStyle.color).toBe(THEME.mutedForeground);
    expect(option.series[0].data[1].displayName).toBe("其他（3 种合并）");
  });

  it("热力矩阵构建寄主×属地网格并跳过「其他」", () => {
    const hosts = buildHosts(3);
    hosts.push({ host: "其他", points: 1, plants: 999, share: 0.1, localities: [] });
    const option = buildHeatmapOption(hosts, THEME);

    expect(option.yAxis.data.length).toBe(3);
    expect(option.xAxis.data).toContain("宋庄镇");
    // 3 寄主 × N 属地 = 全网格数据点
    expect(option.series[0].data.length).toBe(3 * option.xAxis.data.length);
    const values = option.series[0].data.map((item) => item[2]);
    expect(option.visualMap.max).toBe(Math.max(...values));
  });

  it("热力矩阵寄主数受 HEATMAP_HOST_LIMIT 限制", () => {
    const hosts = buildHosts(15);
    const option = buildHeatmapOption(hosts, THEME);
    expect(option.yAxis.data.length).toBe(HEATMAP_HOST_LIMIT);
  });

  it("空数据时返回安全默认值", () => {
    expect(buildTreemapOption([], "plants", THEME).series[0].data).toEqual([]);
    expect(buildRankingOption([], "plants", THEME).series[0].data).toEqual([]);
    const heatmap = buildHeatmapOption([], THEME);
    expect(heatmap.series[0].data).toEqual([]);
    expect(heatmap.visualMap.max).toBe(1);
  });

  it("formatShare 输出百分比", () => {
    expect(formatShare(0.6)).toBe("60.0%");
    expect(formatShare(0)).toBe("0.0%");
  });
});

describe("分代对比 option 构建器", () => {
  const GENERATIONS = [
    {
      generation: "第一代",
      totals: {},
      hosts: [
        { host: "法桐", points: 10, plants: 100, share: 0.5, localities: [] },
        { host: "白蜡", points: 5, plants: 50, share: 0.25, localities: [] },
        { host: "其他", points: 99, plants: 999, share: 0.25, localities: [], merged_hosts: 3 },
      ],
    },
    {
      generation: "第二代",
      totals: {},
      hosts: [
        { host: "法桐", points: 20, plants: 200, share: 0.5, localities: [] },
        { host: "桑", points: 8, plants: 80, share: 0.2, localities: [] },
      ],
    },
  ];

  it("分组柱状图取寄主并集、缺代补 0、排除「其他」", () => {
    const option = buildGenerationCompareBarOption(GENERATIONS, "plants", THEME);

    // 并集按株数合计排序：法桐 300、桑 80、白蜡 50
    expect(option.xAxis.data).toEqual(["法桐", "桑", "白蜡"]);
    expect(option.series.length).toBe(2);
    expect(option.series[0].name).toBe("第一代");
    expect(option.series[0].data).toEqual([100, 0, 50]);
    expect(option.series[1].name).toBe("第二代");
    expect(option.series[1].data).toEqual([200, 80, 0]);
    expect(option.series[0].itemStyle.color).toBe(THEME.colors[0]);
    expect(option.series[1].itemStyle.color).toBe(THEME.colors[1]);
  });

  it("分组柱状图支持按点位数取值", () => {
    const option = buildGenerationCompareBarOption(GENERATIONS, "points", THEME);
    expect(option.series[0].data).toEqual([10, 0, 5]);
    expect(option.series[1].data).toEqual([20, 8, 0]);
  });

  it("世代热力图行列与最大值正确", () => {
    const option = buildGenerationHeatmapOption(GENERATIONS, THEME);

    expect(option.xAxis.data).toEqual(["第一代", "第二代"]);
    expect(option.yAxis.data).toEqual(["法桐", "桑", "白蜡"]);
    expect(option.series[0].data.length).toBe(6);
    expect(option.visualMap.max).toBe(200);
  });

  it("空数据时返回安全默认值", () => {
    const bar = buildGenerationCompareBarOption([], "plants", THEME);
    expect(bar.series).toEqual([]);
    expect(bar.xAxis.data).toEqual([]);
    const heatmap = buildGenerationHeatmapOption([], THEME);
    expect(heatmap.series[0].data).toEqual([]);
    expect(heatmap.visualMap.max).toBe(1);
  });
});
