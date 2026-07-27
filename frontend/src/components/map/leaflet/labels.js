export const POINT_LABEL_FONT_SIZE = 12;
export const POINT_LABEL_OFFSET_X = 8;
export const POINT_LABEL_OFFSET_Y = -7;
export const POINT_LABEL_PADDING_X = 2;
export const POINT_LABEL_PADDING_Y = 2;

export function estimateLabelTextWidth(label) {
  return Array.from(`${label}`).reduce((width, char) => {
    const isWideChar = /[^\x00-\xff]/.test(char);
    return width + (isWideChar ? POINT_LABEL_FONT_SIZE : POINT_LABEL_FONT_SIZE * 0.68);
  }, POINT_LABEL_FONT_SIZE * 0.2);
}

export function estimateLabelBounds(label, projected) {
  const textWidth = estimateLabelTextWidth(label);
  const textHeight = POINT_LABEL_FONT_SIZE * 1.25;
  const left = projected.x + POINT_LABEL_OFFSET_X - POINT_LABEL_PADDING_X;
  const top = projected.y + POINT_LABEL_OFFSET_Y - POINT_LABEL_PADDING_Y;

  return {
    left,
    top,
    right: left + textWidth + POINT_LABEL_PADDING_X * 2,
    bottom: top + textHeight + POINT_LABEL_PADDING_Y * 2,
  };
}

export function boundsIntersect(left, right) {
  return !(
    left.right <= right.left ||
    left.left >= right.right ||
    left.bottom <= right.top ||
    left.top >= right.bottom
  );
}
