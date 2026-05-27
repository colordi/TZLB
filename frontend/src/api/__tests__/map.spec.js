import { beforeEach, describe, expect, it, vi } from "vitest";

const httpMocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  ensureApiSuccess: vi.fn(),
}));

vi.mock("../http.js", () => ({
  apiFetch: httpMocks.apiFetch,
  ensureApiSuccess: httpMocks.ensureApiSuccess,
}));

describe("api/map", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    httpMocks.apiFetch.mockResolvedValue({
      json: vi.fn().mockResolvedValue({ type: "FeatureCollection", features: [] }),
    });
    httpMocks.ensureApiSuccess.mockResolvedValue();
  });

  it("读取地图视图时把数组筛选序列化为重复查询参数", async () => {
    const { fetchMapView } = await import("../map.js");

    await fetchMapView("虫情 总览", {
      年份: ["2024", "2025"],
      危害程度: "重",
      空值: [],
    });

    const url = httpMocks.apiFetch.mock.calls[0][0];
    const [path, query] = url.split("?");
    const search = new URLSearchParams(query);

    expect(decodeURIComponent(path)).toBe("/api/map/views/虫情 总览");
    expect(search.getAll("年份")).toEqual(["2024", "2025"]);
    expect(search.getAll("危害程度")).toEqual(["重"]);
    expect(search.has("空值")).toBe(false);
  });

  it("新增美国白蛾点位时提交 JSON 载荷", async () => {
    const { createWhiteMothSite } = await import("../map.js");

    await createWhiteMothSite({
      code: "MQ001",
      site_name: "示范点",
      longitude: 116.5,
      latitude: 39.7,
    });

    expect(httpMocks.apiFetch).toHaveBeenCalledWith("/api/map/white-moth-sites", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        code: "MQ001",
        site_name: "示范点",
        longitude: 116.5,
        latitude: 39.7,
      }),
    });
  });

  it("读取美国白蛾编号规则", async () => {
    const { fetchWhiteMothSiteCodeRules } = await import("../map.js");

    await fetchWhiteMothSiteCodeRules();

    expect(httpMocks.apiFetch).toHaveBeenCalledWith(
      "/api/map/white-moth-sites/code-rules",
    );
  });
});
