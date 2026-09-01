import { beforeEach, describe, expect, it, vi } from "vitest";

import { usePointCompleteMarks } from "../usePointCompleteMarks.js";

const STORAGE_KEY = "tzlb:date-point-complete-marks";
const SCOPE_A = "美国白蛾|2026|第一代|2026-05-26";
const SCOPE_B = "春尺蠖|2026||2026-04-01";

describe("usePointCompleteMarks", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("toggle 标记与取消，并持久化到 localStorage", () => {
    const marks = usePointCompleteMarks();

    expect(marks.isComplete(SCOPE_A, "MQ001")).toBe(false);

    marks.toggleComplete(SCOPE_A, "MQ001");
    expect(marks.isComplete(SCOPE_A, "MQ001")).toBe(true);
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY))).toEqual({
      [SCOPE_A]: { MQ001: expect.any(Number) },
    });

    marks.toggleComplete(SCOPE_A, "MQ001");
    expect(marks.isComplete(SCOPE_A, "MQ001")).toBe(false);
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY))).toEqual({});
  });

  it("不同查询范围的标记互不影响", () => {
    const marks = usePointCompleteMarks();

    marks.toggleComplete(SCOPE_A, "MQ001");
    marks.toggleComplete(SCOPE_B, "MQ001");

    expect(marks.isComplete(SCOPE_A, "MQ001")).toBe(true);
    expect(marks.isComplete(SCOPE_B, "MQ001")).toBe(true);

    marks.toggleComplete(SCOPE_A, "MQ001");
    expect(marks.isComplete(SCOPE_A, "MQ001")).toBe(false);
    expect(marks.isComplete(SCOPE_B, "MQ001")).toBe(true);
  });

  it("resetScope 只清除当前范围并返回清除数量", () => {
    const marks = usePointCompleteMarks();

    marks.toggleComplete(SCOPE_A, "MQ001");
    marks.toggleComplete(SCOPE_A, "MQ002");
    marks.toggleComplete(SCOPE_B, "YL001");

    expect(marks.resetScope(SCOPE_A)).toBe(2);
    expect(marks.isComplete(SCOPE_A, "MQ001")).toBe(false);
    expect(marks.isComplete(SCOPE_A, "MQ002")).toBe(false);
    expect(marks.isComplete(SCOPE_B, "YL001")).toBe(true);

    expect(marks.resetScope(SCOPE_A)).toBe(0);
  });

  it("读取时清理 60 天前的过期标记", () => {
    const now = Date.now();
    vi.spyOn(Date, "now").mockReturnValue(now);
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        [SCOPE_A]: {
          MQ001: now - 61 * 24 * 60 * 60 * 1000,
          MQ002: now - 1000,
        },
      }),
    );

    const marks = usePointCompleteMarks();
    expect(marks.isComplete(SCOPE_A, "MQ001")).toBe(false);
    expect(marks.isComplete(SCOPE_A, "MQ002")).toBe(true);
  });

  it("localStorage 内容损坏时按无标记处理", () => {
    localStorage.setItem(STORAGE_KEY, "{not-json");

    const marks = usePointCompleteMarks();
    expect(marks.isComplete(SCOPE_A, "MQ001")).toBe(false);

    marks.toggleComplete(SCOPE_A, "MQ001");
    expect(marks.isComplete(SCOPE_A, "MQ001")).toBe(true);
  });
});
