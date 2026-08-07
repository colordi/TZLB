export const POINT_LABEL_FONT_SIZE = 12;
export const POINT_LABEL_GAP = 9;
export const POINT_LABEL_DIAGONAL_GAP = 7;
export const POINT_LABEL_PADDING = 2;

/**
 * 标签候选方位（按优先级）：类似 GIS 软件的自动标注放置，
 * 依次尝试直至找到无碰撞的位置，全部碰撞则不渲染该标签。
 * 与 leaflet-map.css 中 .map-point-label-text--* 的 transform 一一对应。
 */
export const POINT_LABEL_PLACEMENTS = [
  "right",
  "left",
  "top",
  "bottom",
  "top-right",
  "bottom-right",
  "top-left",
  "bottom-left",
];

export function estimateLabelTextWidth(label) {
  return Array.from(`${label}`).reduce((width, char) => {
    const isWideChar = /[^\x00-\xff]/.test(char);
    return width + (isWideChar ? POINT_LABEL_FONT_SIZE : POINT_LABEL_FONT_SIZE * 0.68);
  }, POINT_LABEL_FONT_SIZE * 0.2);
}

function makeBounds(left, top, width, height) {
  return { left, top, right: left + width, bottom: top + height };
}

export function estimateLabelBounds(label, projected, placement = "right") {
  const width = estimateLabelTextWidth(label) + POINT_LABEL_PADDING * 2;
  const height = POINT_LABEL_FONT_SIZE * 1.25 + POINT_LABEL_PADDING * 2;
  const { x, y } = projected;

  switch (placement) {
    case "left":
      return makeBounds(x - POINT_LABEL_GAP - width, y - height / 2, width, height);
    case "top":
      return makeBounds(x - width / 2, y - POINT_LABEL_GAP - height, width, height);
    case "bottom":
      return makeBounds(x - width / 2, y + POINT_LABEL_GAP, width, height);
    case "top-right":
      return makeBounds(
        x + POINT_LABEL_DIAGONAL_GAP,
        y - POINT_LABEL_DIAGONAL_GAP - height,
        width,
        height,
      );
    case "bottom-right":
      return makeBounds(
        x + POINT_LABEL_DIAGONAL_GAP,
        y + POINT_LABEL_DIAGONAL_GAP,
        width,
        height,
      );
    case "top-left":
      return makeBounds(
        x - POINT_LABEL_DIAGONAL_GAP - width,
        y - POINT_LABEL_DIAGONAL_GAP - height,
        width,
        height,
      );
    case "bottom-left":
      return makeBounds(
        x - POINT_LABEL_DIAGONAL_GAP - width,
        y + POINT_LABEL_DIAGONAL_GAP,
        width,
        height,
      );
    case "right":
    default:
      return makeBounds(x + POINT_LABEL_GAP, y - height / 2, width, height);
  }
}

export function boundsIntersect(left, right) {
  return !(
    left.right <= right.left ||
    left.left >= right.right ||
    left.bottom <= right.top ||
    left.top >= right.bottom
  );
}

/**
 * 网格哈希碰撞索引：把已渲染标签盒按网格桶存储，
 * 候选盒只需与同桶及相邻桶内的盒比较，避免 O(n²) 全量扫描。
 */
export function createLabelCollisionIndex(cellSize = 48) {
  const cells = new Map();

  function cellKeys(bounds) {
    const keys = [];
    const minX = Math.floor(bounds.left / cellSize);
    const maxX = Math.floor((bounds.right - 0.01) / cellSize);
    const minY = Math.floor(bounds.top / cellSize);
    const maxY = Math.floor((bounds.bottom - 0.01) / cellSize);
    for (let cx = minX; cx <= maxX; cx += 1) {
      for (let cy = minY; cy <= maxY; cy += 1) {
        keys.push(`${cx},${cy}`);
      }
    }
    return keys;
  }

  return {
    collides(bounds) {
      for (const key of cellKeys(bounds)) {
        const bucket = cells.get(key);
        if (!bucket) {
          continue;
        }
        for (const placed of bucket) {
          if (boundsIntersect(placed, bounds)) {
            return true;
          }
        }
      }
      return false;
    },
    insert(bounds) {
      for (const key of cellKeys(bounds)) {
        const bucket = cells.get(key) || [];
        bucket.push(bounds);
        cells.set(key, bucket);
      }
    },
  };
}

/** 按候选方位顺序找到第一个无碰撞的放置，全部碰撞返回 null。 */
export function resolveLabelPlacement(label, projected, collisionIndex) {
  for (const placement of POINT_LABEL_PLACEMENTS) {
    const bounds = estimateLabelBounds(label, projected, placement);
    if (!collisionIndex.collides(bounds)) {
      return { placement, bounds };
    }
  }
  return null;
}
