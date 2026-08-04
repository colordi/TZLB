/**
 * 图表（ECharts）运行时色值唯一来源，与 map-palette.js 同模式：
 * 色值定义在 themes/forestry-light.css 的 --chart-* 等 token，
 * 此处负责在运行时从 CSS 变量解析（含 fallback），业务代码禁止裸 hex。
 *
 * 注意：主题 token 使用 oklch()，canvas 直接填充没问题，但 ECharts 底层
 * zrender 做高亮提亮、visualMap 插值时无法解析 oklch（悬停矩形变白/闪烁），
 * 因此输出前统一经 normalizeChartColor 转成 rgb()/rgba()。
 */

const CHART_FALLBACKS = [
  "oklch(0.52 0.09 155)",
  "oklch(0.65 0.12 130)",
  "oklch(0.72 0.13 90)",
  "oklch(0.55 0.11 250)",
  "oklch(0.6 0.13 30)",
];

const TOKEN_FALLBACKS = {
  foreground: "oklch(0.35 0.03 150)",
  "muted-foreground": "oklch(0.5 0.02 150)",
  muted: "oklch(0.96 0.01 150)",
  border: "oklch(0.9 0.01 150)",
  card: "oklch(1 0 0)",
};

let probeContext;
const normalizedColorCache = new Map();

function getProbeContext() {
  if (probeContext !== undefined) {
    return probeContext;
  }
  probeContext = null;
  if (typeof document !== "undefined") {
    const canvas = document.createElement("canvas");
    canvas.width = 1;
    canvas.height = 1;
    // jsdom 等无 canvas 环境返回 null，走原样透传
    probeContext = canvas.getContext("2d");
  }
  return probeContext;
}

/**
 * 将任意 CSS 颜色（含 oklch 等 CSS Color 4 写法）转换为 zrender 可解析的
 * rgb()/rgba() 字符串。原理：用 1px canvas 探针让浏览器实际渲染该颜色并
 * 读回像素值。环境不支持 canvas 或颜色非法时原样返回。
 */
export function normalizeChartColor(color, fallback = "") {
  if (!color) {
    return fallback;
  }
  if (normalizedColorCache.has(color)) {
    return normalizedColorCache.get(color);
  }
  let normalized = color;
  const ctx = getProbeContext();
  if (ctx) {
    ctx.clearRect(0, 0, 1, 1);
    ctx.fillStyle = "#000001";
    ctx.fillStyle = color;
    // 非法颜色赋值会被忽略（fillStyle 保持原值），此时透传原字符串
    if (ctx.fillStyle !== "#000001") {
      ctx.fillRect(0, 0, 1, 1);
      const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data;
      normalized =
        a >= 255
          ? `rgb(${r}, ${g}, ${b})`
          : `rgba(${r}, ${g}, ${b}, ${Number((a / 255).toFixed(3))})`;
    }
  }
  normalizedColorCache.set(color, normalized);
  return normalized;
}

export function resolveCssToken(name, fallback = "") {
  if (typeof window === "undefined" || typeof getComputedStyle !== "function") {
    return fallback;
  }
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function resolveChartToken(name, fallback) {
  return normalizeChartColor(resolveCssToken(name, fallback), fallback);
}

/** 5 个图表基色（--chart-1..5），类别多于 5 时循环使用。 */
export function getChartColors() {
  return CHART_FALLBACKS.map((fallback, index) =>
    resolveChartToken(`--chart-${index + 1}`, fallback),
  );
}

/** ECharts option 常用文本/边框色，全部来自语义 token。 */
export function getChartTheme() {
  return {
    colors: getChartColors(),
    foreground: resolveChartToken("--foreground", TOKEN_FALLBACKS.foreground),
    mutedForeground: resolveChartToken("--muted-foreground", TOKEN_FALLBACKS["muted-foreground"]),
    muted: resolveChartToken("--muted", TOKEN_FALLBACKS.muted),
    border: resolveChartToken("--border", TOKEN_FALLBACKS.border),
    card: resolveChartToken("--card", TOKEN_FALLBACKS.card),
  };
}
