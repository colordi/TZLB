/**
 * 地图域运行时色值唯一来源（规范 §2.5 / §7）。
 *
 * Leaflet API（circleMarker、divIcon、图例、图层色板等）只能接收 JS 色值，
 * 全部集中在本文件维护；CSS 侧对应 token 见
 * frontend/src/styles/themes/forestry-light.css（--severity-*、--map-boundary），
 * 两侧注释互相指向，修改时必须同步核对。
 *
 * 危害程度四色为调查行业既定判读约定，值锁定，不可调整。
 */

/** 危害程度四色：行业判读约定，值锁定（对应 CSS --severity-none/light/medium/high） */
export const SEVERITY_COLORS = {
  none: "#ffffff",
  light: "#0033ff",
  medium: "#fbff05",
  high: "#ff0000",
};

/** 地块状态三色：调查红 / 伐除黑 / 其他白（沿用 popupFields.js 既有取值） */
export const PARCEL_STATUS_COLORS = {
  surveyed: "#ff0000",
  removed: "#000000",
  other: "#ffffff",
};

/** 危害点位固定渲染色（当前视图无危害程度/地块状态字段时使用） */
export const HAZARD_POINT_COLOR = "#ff0000";

/** 点位描边色（circleMarker color） */
export const POINT_OUTLINE_COLOR = "#1F2933";

/**
 * 点位图层色板（6 色）：仅用于图层面板区分图层，
 * 与危害程度色职责分离（规范 §7），不参与点位渲染。
 */
export const POINT_LAYER_COLORS = [
  "#16A34A",
  "#2563EB",
  "#9333EA",
  "#0891B2",
  "#DC2626",
  "#D97706",
];

/** 参考图层色板：按图层顺序取色渲染参考边界/参考点 */
export const REFERENCE_LAYER_COLORS = [
  "#D97706",
  "#2563EB",
  "#16A34A",
  "#9333EA",
  "#0891B2",
  "#64748B",
];

/** 行政区边界色（对应 CSS --map-boundary，值锁定） */
export const ADMIN_BOUNDARY_COLOR = "#D97706";

/** 实时定位标记蓝：divIcon 内联 SVG 填充色，无对应 CSS token，仅此一处维护 */
export const LOCATE_MARKER_COLOR = "#2f80ed";

/** 定位标记蓝派生透明色：辉光投影 / 脉冲圈 / 外圈阴影 */
export const LOCATE_MARKER_GLOW = "rgba(47, 128, 237, 0.3)";
export const LOCATE_MARKER_PULSE = "rgba(47, 128, 237, 0.18)";
export const LOCATE_MARKER_RING = "rgba(47, 128, 237, 0.34)";

/** 定位标记白色晕圈（深色底图上保证可读性） */
export const LOCATE_MARKER_HALO = "rgba(255, 255, 255, 0.9)";

/** 调查完成小勾底色（divIcon 内联样式） */
export const SURVEY_COMPLETION_COLOR = "#16a34a";
