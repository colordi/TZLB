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

  it("读取美国白蛾寄主分布汇总", async () => {
    httpMocks.apiFetch.mockResolvedValueOnce({
      json: vi.fn().mockResolvedValue({ hosts: [], totals: {} }),
    });
    const { getWhiteMothHostSummary } = await import("../statistics.js");

    const result = await getWhiteMothHostSummary({ year: 2026, generation: "第二代" });

    expect(httpMocks.apiFetch).toHaveBeenCalledWith(
      "/api/statistics/white-moth/host-summary?year=2026&generation=%E7%AC%AC%E4%BA%8C%E4%BB%A3",
    );
    expect(result).toEqual({ hosts: [], totals: {} });
  });

  it("读取不携带筛选条件的美国白蛾寄主分布汇总", async () => {
    const { getWhiteMothHostSummary } = await import("../statistics.js");

    await getWhiteMothHostSummary();

    expect(httpMocks.apiFetch).toHaveBeenCalledWith("/api/statistics/white-moth/host-summary");
  });

  it("读取其他害虫整体汇总", async () => {
    httpMocks.apiFetch.mockResolvedValueOnce({
      json: vi.fn().mockResolvedValue({ totals: {}, pest_types: [] }),
    });
    const { getOtherPestSummary } = await import("../statistics.js");

    const result = await getOtherPestSummary({ year: 2026 });

    expect(httpMocks.apiFetch).toHaveBeenCalledWith("/api/statistics/other-pest/summary?year=2026");
    expect(httpMocks.ensureApiSuccess).toHaveBeenCalledTimes(1);
    expect(result).toEqual({ totals: {}, pest_types: [] });
  });

  it("读取不携带筛选条件的其他害虫整体汇总", async () => {
    const { getOtherPestSummary } = await import("../statistics.js");

    await getOtherPestSummary();

    expect(httpMocks.apiFetch).toHaveBeenCalledWith("/api/statistics/other-pest/summary");
  });

  it("读取杨树食叶害虫整体汇总", async () => {
    httpMocks.apiFetch.mockResolvedValueOnce({
      json: vi.fn().mockResolvedValue({ totals: {}, pest_types: [] }),
    });
    const { getYangshuShiyeSummary } = await import("../statistics.js");

    const result = await getYangshuShiyeSummary({ year: 2026 });

    expect(httpMocks.apiFetch).toHaveBeenCalledWith(
      "/api/statistics/yangshu-shiye/summary?year=2026",
    );
    expect(httpMocks.ensureApiSuccess).toHaveBeenCalledTimes(1);
    expect(result).toEqual({ totals: {}, pest_types: [] });
  });

  it("读取不携带筛选条件的杨树食叶害虫整体汇总", async () => {
    const { getYangshuShiyeSummary } = await import("../statistics.js");

    await getYangshuShiyeSummary();

    expect(httpMocks.apiFetch).toHaveBeenCalledWith("/api/statistics/yangshu-shiye/summary");
  });

  it("读取白蜡蛀干害虫整体汇总", async () => {
    httpMocks.apiFetch.mockResolvedValueOnce({
      json: vi.fn().mockResolvedValue({ totals: {}, localities: [] }),
    });
    const { getAshBorerSummary } = await import("../statistics.js");

    const result = await getAshBorerSummary({ year: 2026 });

    expect(httpMocks.apiFetch).toHaveBeenCalledWith(
      "/api/statistics/ash-borer/summary?year=2026",
    );
    expect(httpMocks.ensureApiSuccess).toHaveBeenCalledTimes(1);
    expect(result).toEqual({ totals: {}, localities: [] });
  });

  it("读取不携带筛选条件的白蜡蛀干害虫整体汇总", async () => {
    const { getAshBorerSummary } = await import("../statistics.js");

    await getAshBorerSummary();

    expect(httpMocks.apiFetch).toHaveBeenCalledWith("/api/statistics/ash-borer/summary");
  });

  it("读取春尺蠖整体汇总", async () => {
    httpMocks.apiFetch.mockResolvedValueOnce({
      json: vi.fn().mockResolvedValue({ adult: {}, larva: {}, ring_wrap: {}, ledger: {} }),
    });
    const { getPoplarInchwormSummary } = await import("../statistics.js");

    const result = await getPoplarInchwormSummary({ year: 2026 });

    expect(httpMocks.apiFetch).toHaveBeenCalledWith(
      "/api/statistics/poplar-inchworm/summary?year=2026",
    );
    expect(httpMocks.ensureApiSuccess).toHaveBeenCalledTimes(1);
    expect(result).toEqual({ adult: {}, larva: {}, ring_wrap: {}, ledger: {} });
  });

  it("读取不携带筛选条件的春尺蠖整体汇总", async () => {
    const { getPoplarInchwormSummary } = await import("../statistics.js");

    await getPoplarInchwormSummary();

    expect(httpMocks.apiFetch).toHaveBeenCalledWith("/api/statistics/poplar-inchworm/summary");
  });

  it("读取国槐尺蠖世代汇总", async () => {
    httpMocks.apiFetch.mockResolvedValueOnce({
      json: vi.fn().mockResolvedValue({ generations: [] }),
    });
    const { getSophoraGenerationSummary } = await import("../statistics.js");

    const result = await getSophoraGenerationSummary({ year: 2026 });

    expect(httpMocks.apiFetch).toHaveBeenCalledWith(
      "/api/statistics/sophora-inchworm/generation-summary?year=2026",
    );
    expect(result).toEqual({ generations: [] });
  });

  it("读取国槐尺蠖属地受害汇总", async () => {
    httpMocks.apiFetch.mockResolvedValueOnce({
      json: vi.fn().mockResolvedValue({ localities: [], totals: {} }),
    });
    const { getSophoraLocalitySummary } = await import("../statistics.js");

    const result = await getSophoraLocalitySummary({
      year: 2026,
      generation: "第一代",
    });

    expect(httpMocks.apiFetch).toHaveBeenCalledWith(
      "/api/statistics/sophora-inchworm/locality-summary?year=2026&generation=%E7%AC%AC%E4%B8%80%E4%BB%A3",
    );
    expect(result).toEqual({ localities: [], totals: {} });
  });
});
