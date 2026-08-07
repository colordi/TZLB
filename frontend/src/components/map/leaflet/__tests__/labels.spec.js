import { describe, expect, it } from "vitest";

import {
  boundsIntersect,
  createLabelCollisionIndex,
  estimateLabelBounds,
  resolveLabelPlacement,
} from "../labels.js";

const PROJECTED = { x: 1000, y: -500 };

describe("map/labels 标签放置", () => {
  it("默认放置在点位右侧", () => {
    const bounds = estimateLabelBounds("A-001", PROJECTED, "right");

    expect(bounds.left).toBeCloseTo(1000 + 9, 5);
    expect(bounds.top).toBeLessThan(PROJECTED.y);
    expect(bounds.bottom).toBeGreaterThan(PROJECTED.y);
  });

  it("各方位标签盒围绕点位分布且不与点位重叠", () => {
    const placements = [
      "right",
      "left",
      "top",
      "bottom",
      "top-right",
      "bottom-right",
      "top-left",
      "bottom-left",
    ];
    const pointBox = { left: 996, top: -504, right: 1004, bottom: -496 };

    for (const placement of placements) {
      const bounds = estimateLabelBounds("A-001", PROJECTED, placement);
      expect(boundsIntersect(bounds, pointBox)).toBe(false);
    }
    // 左方位整体在点左侧，上方位整体在点上方
    expect(estimateLabelBounds("A-001", PROJECTED, "left").right).toBeLessThan(1000);
    expect(estimateLabelBounds("A-001", PROJECTED, "top").bottom).toBeLessThan(-500);
  });

  it("碰撞索引：插入后可检出相交，不相交不检出", () => {
    const index = createLabelCollisionIndex();
    const placed = estimateLabelBounds("A-001", PROJECTED, "right");
    index.insert(placed);

    expect(index.collides(placed)).toBe(true);
    expect(
      index.collides({ left: 2000, top: 2000, right: 2060, bottom: 2020 }),
    ).toBe(false);
  });

  it("右侧被占用时回退到左侧放置", () => {
    const index = createLabelCollisionIndex();
    index.insert(estimateLabelBounds("A-001", PROJECTED, "right"));

    const resolved = resolveLabelPlacement("B-002", PROJECTED, index);

    expect(resolved).not.toBeNull();
    expect(resolved.placement).toBe("left");
  });

  it("全部方位都碰撞时返回 null", () => {
    const index = createLabelCollisionIndex();
    // 用一个覆盖所有候选方位的大盒占满周边
    index.insert({ left: 800, top: -700, right: 1200, bottom: -300 });

    expect(resolveLabelPlacement("A-001", PROJECTED, index)).toBeNull();
  });
});
