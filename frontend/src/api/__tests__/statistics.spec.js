import { beforeEach, describe, expect, it, vi } from "vitest";

const httpMocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  ensureApiSuccess: vi.fn(),
}));

vi.mock("../http.js", () => ({
  apiFetch: httpMocks.apiFetch,
  ensureApiSuccess: httpMocks.ensureApiSuccess,
}));

describe("api/statistics", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    httpMocks.apiFetch.mockResolvedValue({
      json: vi.fn().mockResolvedValue({ columns: [], rows: [] }),
    });
    httpMocks.ensureApiSuccess.mockResolvedValue();
  });

  it("读取美国白蛾每日统计", async () => {
    const { getWhiteMothDailyStatistics } = await import("../statistics.js");

    const result = await getWhiteMothDailyStatistics();

    expect(httpMocks.apiFetch).toHaveBeenCalledWith("/api/statistics/white-moth/daily");
    expect(httpMocks.ensureApiSuccess).toHaveBeenCalledTimes(1);
    expect(result).toEqual({ columns: [], rows: [] });
  });

  it("携带年份和代数查询参数", async () => {
    const { getWhiteMothDailyStatistics } = await import("../statistics.js");

    await getWhiteMothDailyStatistics({ year: 2026, generation: "第一代" });

    expect(httpMocks.apiFetch).toHaveBeenCalledWith(
      "/api/statistics/white-moth/daily?year=2026&generation=%E7%AC%AC%E4%B8%80%E4%BB%A3",
    );
  });
});
