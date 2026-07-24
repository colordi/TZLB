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

  it("读取不携带筛选条件的美国白蛾世代汇总", async () => {
    const { getWhiteMothGenerationSummary } = await import("../statistics.js");

    await getWhiteMothGenerationSummary();

    expect(httpMocks.apiFetch).toHaveBeenCalledWith(
      "/api/statistics/white-moth/generation-summary",
    );
  });

  it("读取美国白蛾属地受害汇总", async () => {
    httpMocks.apiFetch.mockResolvedValueOnce({
      json: vi.fn().mockResolvedValue({ localities: [], totals: {} }),
    });
    const { getWhiteMothLocalitySummary } = await import("../statistics.js");

    const result = await getWhiteMothLocalitySummary({
      year: 2026,
      generation: "第一代",
      asOfDate: "2026-06-15",
      severePlantThreshold: 15,
    });

    expect(httpMocks.apiFetch).toHaveBeenCalledWith(
      "/api/statistics/white-moth/locality-summary?year=2026&generation=%E7%AC%AC%E4%B8%80%E4%BB%A3&as_of_date=2026-06-15&severe_plant_threshold=15",
    );
    expect(result).toEqual({ localities: [], totals: {} });
  });
});
