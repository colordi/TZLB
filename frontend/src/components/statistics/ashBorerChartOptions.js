/**
 * 白蜡蛀干害虫属地图表的 ECharts option 纯函数构建器（可单测）。
 * 色值一律来自 chart-palette.js（运行时解析 --chart-* token）。
 */
import { getChartTheme } from "@/config/chart-palette.js";

export const ASH_BORER_TREES_PER_POINT = 30;

export const ASH_BORER_RATE_METRICS = [
  {
    key: "mortality_rate",
    label: "死亡率",
    plantsLabel: "死亡+伐除",
  },
  {
    key: "agrilus_infestation_rate",
    label: "窄吉丁有虫株率",
    plantsLabel: "窄吉丁受害",
  },
  {
    key: "cossus_infestation_rate",
    label: "木蠹蛾有虫株率",
    plantsLabel: "木蠹蛾受害",
  },
];

export function formatNumber(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  return Number(value || 0).toLocaleString("zh-CN");
}

export function formatRate(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  return `${Number(value).toFixed(1)}%`;
}

function baseTooltip(theme) {
  return {
    backgroundColor: theme.card,
    borderColor: theme.border,
    textStyle: { color: theme.foreground, fontSize: 12 },
    confine: true,
    transitionDuration: 0,
  };
}

function rateValue(row, key) {
  const value = row?.[key];
  if (value === null || value === undefined || value === "") {
    return 0;
  }
  return Number(value) || 0;
}

function localityTooltipHtml(row) {
  const excluded = Number(row.excluded_points || 0);
  const excludedHint = excluded > 0 ? ` · 已排除换植 ${formatNumber(excluded)} 个` : "";
  return [
    `<b>${row.locality || "未知"}</b>`,
    `有效点位：${formatNumber(row.surveyed_points)} 个${excludedHint}`,
    `死亡率：${formatRate(row.mortality_rate)}（目测死亡 ${formatNumber(row.dead_plants)} + 伐除 ${formatNumber(row.felled_plants)} 株）`,
    `窄吉丁有虫株率：${formatRate(row.agrilus_infestation_rate)}（${formatNumber(row.agrilus_damaged_plants)} 株）`,
    `木蠹蛾有虫株率：${formatRate(row.cossus_infestation_rate)}（${formatNumber(row.cossus_damaged_plants)} 株）`,
  ].join("<br/>");
}

function sortedLocalities(localities) {
  return (Array.isArray(localities) ? localities : [])
    .filter((row) => Number(row?.surveyed_points || 0) > 0)
    .slice()
    .sort((left, right) => {
      const rateDelta = rateValue(right, "mortality_rate") - rateValue(left, "mortality_rate");
      if (rateDelta !== 0) {
        return rateDelta;
      }
      return String(left.locality || "").localeCompare(String(right.locality || ""), "zh-CN");
    });
}

function seriesData(rows, metricKey) {
  return rows.map((row) => ({
    value: rateValue(row, metricKey),
    locality: row.locality,
    surveyed_points: row.surveyed_points,
    excluded_points: row.excluded_points,
    dead_plants: row.dead_plants,
    felled_plants: row.felled_plants,
    agrilus_damaged_plants: row.agrilus_damaged_plants,
    cossus_damaged_plants: row.cossus_damaged_plants,
    mortality_rate: row.mortality_rate,
    agrilus_infestation_rate: row.agrilus_infestation_rate,
    cossus_infestation_rate: row.cossus_infestation_rate,
  }));
}

/** 各属地死亡率 / 窄吉丁有虫株率 / 木蠹蛾有虫株率分组柱状图。 */
export function buildLocalityRateBarOption(localities, theme = getChartTheme()) {
  const rows = sortedLocalities(localities);
  const names = rows.map((row) => row.locality || "未知");
  return {
    color: theme.colors,
    tooltip: {
      ...baseTooltip(theme),
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (items) => {
        const first = Array.isArray(items) ? items[0] : items;
        return localityTooltipHtml(first?.data || {});
      },
    },
    legend: {
      bottom: 0,
      textStyle: { color: theme.mutedForeground, fontSize: 11 },
    },
    grid: { left: 8, right: 16, top: 24, bottom: 48, containLabel: true },
    xAxis: {
      type: "category",
      data: names,
      axisLabel: {
        color: theme.foreground,
        fontSize: 12,
        interval: 0,
        rotate: names.length > 6 ? 30 : 0,
      },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      name: "%",
      nameTextStyle: { color: theme.mutedForeground, fontSize: 11 },
      axisLabel: {
        color: theme.mutedForeground,
        fontSize: 11,
        formatter: (value) => `${value}%`,
      },
      splitLine: { lineStyle: { color: theme.border } },
    },
    series: ASH_BORER_RATE_METRICS.map((metric, index) => ({
      name: metric.label,
      type: "bar",
      barMaxWidth: 22,
      itemStyle: {
        color: theme.colors[index % theme.colors.length],
        borderRadius: [3, 3, 0, 0],
      },
      data: seriesData(rows, metric.key),
    })),
  };
}

/** 属地死亡率横向排行（同时在 tooltip 中给出两种有虫株率）。 */
export function buildMortalityRankingOption(localities, theme = getChartTheme()) {
  const rows = sortedLocalities(localities);
  return {
    grid: { left: 8, right: 56, top: 8, bottom: 8, containLabel: true },
    tooltip: {
      ...baseTooltip(theme),
      formatter: (info) => localityTooltipHtml(info.data || {}),
    },
    xAxis: {
      type: "value",
      axisLabel: {
        color: theme.mutedForeground,
        fontSize: 11,
        formatter: (value) => `${value}%`,
      },
      splitLine: { lineStyle: { color: theme.border } },
    },
    yAxis: {
      type: "category",
      inverse: true,
      data: rows.map((row) => row.locality || "未知"),
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
          formatter: (info) => formatRate(info.value),
        },
        data: seriesData(rows, "mortality_rate"),
      },
    ],
  };
}

export function rankingChartHeight(localityCount) {
  const count = Number(localityCount) || 0;
  return `${Math.max(280, 48 + count * 36)}px`;
}

export const ASH_BORER_DAMAGE_LEVELS = [
  { key: "none", label: "无" },
  { key: "light", label: "轻" },
  { key: "medium", label: "中" },
  { key: "high", label: "重" },
];

export const ASH_BORER_DAMAGE_PESTS = [
  { key: "agrilus_damage_levels", label: "窄吉丁" },
  { key: "cossus_damage_levels", label: "木蠹蛾" },
];

function emptyDamageLevels() {
  return { none: 0, light: 0, medium: 0, high: 0 };
}

function damageLevelsOf(source, pestKey) {
  return { ...emptyDamageLevels(), ...(source?.[pestKey] || {}) };
}

function levelCount(levels, key) {
  return Number(levels?.[key] || 0);
}

function levelsTotal(levels) {
  return ASH_BORER_DAMAGE_LEVELS.reduce((sum, level) => sum + levelCount(levels, level.key), 0);
}

function severityColors(theme) {
  return theme?.severity || {};
}

function severityItemStyle(levelKey, theme) {
  const color = severityColors(theme)[levelKey] || theme.colors[0];
  const style = { color };
  if (levelKey === "none") {
    style.borderColor = theme.border;
    style.borderWidth = 1;
  }
  return style;
}

function damageLevelTooltipHtml(title, levels) {
  const total = levelsTotal(levels);
  const lines = ASH_BORER_DAMAGE_LEVELS.map((level) => {
    const count = levelCount(levels, level.key);
    const share = total > 0 ? `（${((count / total) * 100).toFixed(1)}%）` : "";
    return `${level.label}：${formatNumber(count)} 个${share}`;
  });
  return [`<b>${title}</b>`, ...lines, `合计：${formatNumber(total)} 个点位`].join("<br/>");
}

/** 全区：窄吉丁 / 木蠹蛾 两根堆叠柱，堆叠无/轻/中/重。 */
export function buildDamageLevelOverallOption(totals, theme = getChartTheme()) {
  const source = totals || {};
  return {
    tooltip: {
      ...baseTooltip(theme),
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (items) => {
        const first = Array.isArray(items) ? items[0] : items;
        const pestLabel = first?.axisValue || first?.data?.pest || "";
        const pest = ASH_BORER_DAMAGE_PESTS.find((item) => item.label === pestLabel);
        return damageLevelTooltipHtml(pestLabel, damageLevelsOf(source, pest?.key));
      },
    },
    legend: {
      bottom: 0,
      data: ASH_BORER_DAMAGE_LEVELS.map((level) => level.label),
      textStyle: { color: theme.mutedForeground, fontSize: 11 },
    },
    grid: { left: 8, right: 16, top: 24, bottom: 48, containLabel: true },
    xAxis: {
      type: "category",
      data: ASH_BORER_DAMAGE_PESTS.map((pest) => pest.label),
      axisLabel: { color: theme.foreground, fontSize: 12 },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      name: "点位",
      minInterval: 1,
      nameTextStyle: { color: theme.mutedForeground, fontSize: 11 },
      axisLabel: { color: theme.mutedForeground, fontSize: 11 },
      splitLine: { lineStyle: { color: theme.border } },
    },
    series: ASH_BORER_DAMAGE_LEVELS.map((level) => ({
      name: level.label,
      type: "bar",
      stack: "severity",
      barMaxWidth: 72,
      itemStyle: severityItemStyle(level.key, theme),
      data: ASH_BORER_DAMAGE_PESTS.map((pest) => ({
        value: levelCount(damageLevelsOf(source, pest.key), level.key),
        pest: pest.label,
        level: level.label,
      })),
    })),
  };
}

function sortedLocalitiesBySeverity(localities, pestKey) {
  return (Array.isArray(localities) ? localities : [])
    .filter((row) => Number(row?.surveyed_points || 0) > 0)
    .slice()
    .sort((left, right) => {
      const leftLevels = damageLevelsOf(left, pestKey);
      const rightLevels = damageLevelsOf(right, pestKey);
      const highDelta = levelCount(rightLevels, "high") - levelCount(leftLevels, "high");
      if (highDelta !== 0) {
        return highDelta;
      }
      const mediumDelta = levelCount(rightLevels, "medium") - levelCount(leftLevels, "medium");
      if (mediumDelta !== 0) {
        return mediumDelta;
      }
      return String(left.locality || "").localeCompare(String(right.locality || ""), "zh-CN");
    });
}

/** 各属地危害程度堆叠柱（单个虫种）。 */
export function buildDamageLevelLocalityOption(localities, pestKey, theme = getChartTheme()) {
  const pest = ASH_BORER_DAMAGE_PESTS.find((item) => item.key === pestKey) || ASH_BORER_DAMAGE_PESTS[0];
  const rows = sortedLocalitiesBySeverity(localities, pest.key);
  const names = rows.map((row) => row.locality || "未知");
  return {
    tooltip: {
      ...baseTooltip(theme),
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (items) => {
        const first = Array.isArray(items) ? items[0] : items;
        const name = first?.axisValue || first?.data?.locality || "";
        const row = rows.find((item) => (item.locality || "未知") === name) || {};
        return damageLevelTooltipHtml(`${name} · ${pest.label}`, damageLevelsOf(row, pest.key));
      },
    },
    legend: {
      bottom: 0,
      data: ASH_BORER_DAMAGE_LEVELS.map((level) => level.label),
      textStyle: { color: theme.mutedForeground, fontSize: 11 },
    },
    grid: { left: 8, right: 16, top: 16, bottom: 48, containLabel: true },
    xAxis: {
      type: "category",
      data: names,
      axisLabel: {
        color: theme.foreground,
        fontSize: 12,
        interval: 0,
        rotate: names.length > 6 ? 30 : 0,
      },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      name: "点位",
      minInterval: 1,
      nameTextStyle: { color: theme.mutedForeground, fontSize: 11 },
      axisLabel: { color: theme.mutedForeground, fontSize: 11 },
      splitLine: { lineStyle: { color: theme.border } },
    },
    series: ASH_BORER_DAMAGE_LEVELS.map((level) => ({
      name: level.label,
      type: "bar",
      stack: "severity",
      barMaxWidth: 28,
      itemStyle: severityItemStyle(level.key, theme),
      data: rows.map((row) => ({
        value: levelCount(damageLevelsOf(row, pest.key), level.key),
        locality: row.locality,
        level: level.label,
      })),
    })),
  };
}
