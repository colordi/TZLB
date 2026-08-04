/**
 * 寄主分布图表的 ECharts option 纯函数构建器（可单测）。
 * 色值一律来自 chart-palette.js（运行时解析 --chart-* token）。
 */
import { getChartTheme } from "@/config/chart-palette.js";

export const HOST_METRICS = {
  plants: { key: "plants", label: "受害株数", unit: "株" },
  points: { key: "points", label: "受害点位", unit: "个" },
};

export const RANKING_LIMIT = 15;
export const HEATMAP_HOST_LIMIT = 10;
export const HEATMAP_LOCALITY_LIMIT = 16;

/** 「其他」为后端聚合的合并桶（Top N 之外的树种汇合），展示时需与具名寄主区分。 */
export const OTHER_HOST_NAME = "其他";

export function isOtherHost(host) {
  return host?.host === OTHER_HOST_NAME;
}

/** 其他桶的展示名：带合并树种数（后端仅在合并桶上返回 merged_hosts）。 */
export function displayHostName(host) {
  if (isOtherHost(host)) {
    return host.merged_hosts ? `${OTHER_HOST_NAME}（${host.merged_hosts} 种合并）` : OTHER_HOST_NAME;
  }
  return host?.host ?? "";
}

export function formatNumber(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  return Number(value || 0).toLocaleString("zh-CN");
}

export function formatShare(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

function metricValue(host, metric) {
  return Number(metric === "points" ? host.points : host.plants) || 0;
}

function baseTooltip(theme) {
  return {
    backgroundColor: theme.card,
    borderColor: theme.border,
    textStyle: { color: theme.foreground, fontSize: 12 },
    // 防 hover 闪烁：tooltip 限制在图表内且不做过渡动画
    // （默认配置下 tooltip 追逐光标 + 溢出容器会引发抖动/闪烁）
    confine: true,
    transitionDuration: 0,
  };
}

function hostTooltipLines(data) {
  const lines = [
    `<b>${data.displayName || data.name}</b>`,
    `受害株数：${formatNumber(data.plants)} 株`,
    `受害点位：${formatNumber(data.points)} 个`,
    `株数占比：${formatShare(data.share)}`,
  ];
  if (data.mergedHosts) {
    lines.push(`（${data.mergedHosts} 个树种合并，不参与排名）`);
  }
  return lines.join("<br/>");
}

/** 寄主构成矩形树图：面积 = 当前指标（受害株数/受害点位）。 */
export function buildTreemapOption(hosts, metric, theme = getChartTheme()) {
  const data = (Array.isArray(hosts) ? hosts : []).map((host, index) => ({
    name: host.host,
    displayName: displayHostName(host),
    value: metricValue(host, metric),
    plants: host.plants,
    points: host.points,
    share: host.share,
    mergedHosts: host.merged_hosts || 0,
    // 具名寄主用图表基色循环，「其他」合并桶用中性灰区分
    itemStyle: {
      color: isOtherHost(host)
        ? theme.mutedForeground
        : theme.colors[index % theme.colors.length],
    },
  }));
  return {
    color: theme.colors,
    tooltip: {
      ...baseTooltip(theme),
      formatter: (info) => hostTooltipLines(info.data || {}),
    },
    series: [
      {
        type: "treemap",
        roam: false,
        nodeClick: false,
        breadcrumb: { show: false },
        width: "100%",
        height: "100%",
        label: {
          show: true,
          color: theme.card,
          formatter: (info) =>
            `${info.name}\n${formatNumber(info.value)} ${HOST_METRICS[metric]?.unit || ""}`,
        },
        itemStyle: { borderColor: theme.card, borderWidth: 2, gapWidth: 2 },
        data,
      },
    ],
  };
}

/**
 * 寄主受害横向排行榜（Top N）。
 * 「其他」是多树种合并桶：不参与名次，固定置于榜尾并以灰色作参照。
 */
export function buildRankingOption(hosts, metric, theme = getChartTheme()) {
  const metricInfo = HOST_METRICS[metric] || HOST_METRICS.plants;
  const source = Array.isArray(hosts) ? hosts : [];
  const otherHost = source.find(isOtherHost);
  const ranked = source
    .filter((host) => !isOtherHost(host))
    .sort((a, b) => metricValue(b, metric) - metricValue(a, metric))
    .slice(0, RANKING_LIMIT);
  const rows = otherHost ? [...ranked, otherHost] : ranked;
  return {
    grid: { left: 8, right: 48, top: 8, bottom: 8, containLabel: true },
    tooltip: {
      ...baseTooltip(theme),
      formatter: (info) => hostTooltipLines(info.data || {}),
    },
    xAxis: {
      type: "value",
      axisLabel: { color: theme.mutedForeground, fontSize: 11 },
      splitLine: { lineStyle: { color: theme.border } },
    },
    yAxis: {
      type: "category",
      inverse: true,
      data: rows.map((host) => displayHostName(host)),
      axisLabel: { color: theme.foreground, fontSize: 12 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        type: "bar",
        barMaxWidth: 18,
        itemStyle: { color: theme.colors[0], borderRadius: [0, 4, 4, 0] },
        label: {
          show: true,
          position: "right",
          color: theme.mutedForeground,
          fontSize: 11,
          formatter: (info) => `${formatNumber(info.value)} ${metricInfo.unit}`,
        },
        data: rows.map((host) => ({
          name: host.host,
          displayName: displayHostName(host),
          value: metricValue(host, metric),
          plants: host.plants,
          points: host.points,
          share: host.share,
          mergedHosts: host.merged_hosts || 0,
          itemStyle: {
            color: isOtherHost(host) ? theme.mutedForeground : theme.colors[0],
            borderRadius: [0, 4, 4, 0],
          },
        })),
      },
    ],
  };
}

/** 寄主 × 属地受害株数热力矩阵（按株数，Top 寄主 × Top 属地）。 */
export function buildHeatmapOption(hosts, theme = getChartTheme()) {
  const topHosts = (Array.isArray(hosts) ? hosts : [])
    .filter((host) => !isOtherHost(host))
    .slice(0, HEATMAP_HOST_LIMIT);

  const localityTotals = new Map();
  topHosts.forEach((host) => {
    (host.localities || []).forEach(({ locality, plants }) => {
      localityTotals.set(locality, (localityTotals.get(locality) || 0) + Number(plants || 0));
    });
  });
  const localities = [...localityTotals.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, HEATMAP_LOCALITY_LIMIT)
    .map(([locality]) => locality);

  const hostNames = topHosts.map((host) => host.host);
  const data = [];
  let max = 0;
  topHosts.forEach((host, hostIndex) => {
    const plantsByLocality = new Map(
      (host.localities || []).map(({ locality, plants }) => [locality, Number(plants || 0)]),
    );
    localities.forEach((locality, localityIndex) => {
      const value = plantsByLocality.get(locality) || 0;
      if (value > max) {
        max = value;
      }
      data.push([localityIndex, hostIndex, value]);
    });
  });

  return {
    grid: { left: 8, right: 16, top: 8, bottom: 64, containLabel: true },
    tooltip: {
      ...baseTooltip(theme),
      formatter: (info) =>
        `<b>${hostNames[info.value[1]]} · ${localities[info.value[0]]}</b><br/>受害株数：${formatNumber(info.value[2])} 株`,
    },
    xAxis: {
      type: "category",
      data: localities,
      axisLabel: { color: theme.mutedForeground, fontSize: 11, rotate: 45 },
      axisLine: { show: false },
      axisTick: { show: false },
      splitArea: { show: true },
    },
    yAxis: {
      type: "category",
      inverse: true,
      data: hostNames,
      axisLabel: { color: theme.foreground, fontSize: 12 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    visualMap: {
      min: 0,
      max: max || 1,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      calculable: false,
      textStyle: { color: theme.mutedForeground, fontSize: 11 },
      inRange: { color: [theme.muted, theme.colors[0]] },
    },
    series: [
      {
        type: "heatmap",
        data,
        itemStyle: { borderColor: theme.card, borderWidth: 1 },
        emphasis: { itemStyle: { shadowBlur: 6, shadowColor: theme.mutedForeground } },
      },
    ],
  };
}
