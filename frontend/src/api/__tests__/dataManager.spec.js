import { beforeEach, describe, expect, it, vi } from "vitest";

const httpMocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  ensureApiSuccess: vi.fn(),
}));

vi.mock("../http.js", () => ({
  apiFetch: httpMocks.apiFetch,
  ensureApiSuccess: httpMocks.ensureApiSuccess,
}));

describe("api/dataManager", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    httpMocks.apiFetch.mockResolvedValue({
      json: vi.fn().mockResolvedValue({ ok: true }),
    });
    httpMocks.ensureApiSuccess.mockResolvedValue();
  });

  it("读取可管理的表清单", async () => {
    const { fetchManageableTables } = await import("../dataManager.js");

    await fetchManageableTables();

    expect(httpMocks.apiFetch).toHaveBeenCalledWith("/api/data-manager/tables");
  });

  it("读取表字段时对 schema 和表名做 URL 编码", async () => {
    const { fetchTableColumns } = await import("../dataManager.js");

    await fetchTableColumns("survey", "美国白蛾调查表");

    expect(httpMocks.apiFetch).toHaveBeenCalledWith(
      "/api/data-manager/tables/survey/%E7%BE%8E%E5%9B%BD%E7%99%BD%E8%9B%BE%E8%B0%83%E6%9F%A5%E8%A1%A8/columns",
    );
  });

  it("读取行数据时使用默认分页参数", async () => {
    const { fetchTableRows } = await import("../dataManager.js");

    await fetchTableRows("survey", "春尺蠖调查表");

    expect(httpMocks.apiFetch).toHaveBeenCalledWith(
      `/api/data-manager/tables/survey/${encodeURIComponent("春尺蠖调查表")}/rows?page=1&page_size=20`,
    );
  });

  it("读取行数据时拼接分页、排序和 JSON 编码的过滤条件", async () => {
    const { fetchTableRows } = await import("../dataManager.js");

    await fetchTableRows("ledger", "美国白蛾台账", {
      page: 2,
      pageSize: 20,
      sort: "-调查日期",
      filters: { 属地: "宋庄", 年份: "2026" },
    });

    const [url] = httpMocks.apiFetch.mock.calls[0];
    const [path, query] = url.split("?");
    expect(path).toBe(
      `/api/data-manager/tables/ledger/${encodeURIComponent("美国白蛾台账")}/rows`,
    );
    const params = new URLSearchParams(query);
    expect(params.get("page")).toBe("2");
    expect(params.get("page_size")).toBe("20");
    expect(params.get("sort")).toBe("-调查日期");
    expect(JSON.parse(params.get("filters"))).toEqual({ 属地: "宋庄", 年份: "2026" });
  });

  it("空过滤条件时不携带 filters 参数", async () => {
    const { fetchTableRows } = await import("../dataManager.js");

    await fetchTableRows("sites", "杨树点位基础表", { filters: {} });

    const [url] = httpMocks.apiFetch.mock.calls[0];
    expect(url).not.toContain("filters=");
  });

  it("新增记录时以 POST 提交 values", async () => {
    const { createTableRow } = await import("../dataManager.js");

    await createTableRow("survey", "其他害虫调查表", { 编号: "QT-01", 年份: 2026 });

    expect(httpMocks.apiFetch).toHaveBeenCalledWith(
      `/api/data-manager/tables/survey/${encodeURIComponent("其他害虫调查表")}/rows`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ values: { 编号: "QT-01", 年份: 2026 } }),
      },
    );
  });

  it("更新记录时以 PUT 提交 pk 和 values", async () => {
    const { updateTableRow } = await import("../dataManager.js");

    await updateTableRow("ledger", "春尺蠖台账", { id: 7 }, { 属地: "梨园" });

    expect(httpMocks.apiFetch).toHaveBeenCalledWith(
      `/api/data-manager/tables/ledger/${encodeURIComponent("春尺蠖台账")}/rows`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pk: { id: 7 }, values: { 属地: "梨园" } }),
      },
    );
  });

  it("删除记录时以 DELETE 提交 pk", async () => {
    const { deleteTableRow } = await import("../dataManager.js");

    await deleteTableRow("sites", "杨树点位基础表", { 编号: "YS-100" });

    expect(httpMocks.apiFetch).toHaveBeenCalledWith(
      `/api/data-manager/tables/sites/${encodeURIComponent("杨树点位基础表")}/rows`,
      {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pk: { 编号: "YS-100" } }),
      },
    );
  });

  it("读取变更记录时使用默认分页", async () => {
    const { fetchChangeLogs } = await import("../dataManager.js");

    await fetchChangeLogs();

    expect(httpMocks.apiFetch).toHaveBeenCalledWith(
      "/api/data-manager/change-logs?limit=50&offset=0",
    );
  });

  it("读取变更记录时拼接 schema、表名与分页参数", async () => {
    const { fetchChangeLogs } = await import("../dataManager.js");

    await fetchChangeLogs({
      schemaName: "survey",
      tableName: "美国白蛾调查表",
      limit: 20,
      offset: 40,
    });

    const [url] = httpMocks.apiFetch.mock.calls[0];
    const [path, query] = url.split("?");
    expect(path).toBe("/api/data-manager/change-logs");
    const params = new URLSearchParams(query);
    expect(params.get("schema_name")).toBe("survey");
    expect(params.get("table_name")).toBe("美国白蛾调查表");
    expect(params.get("limit")).toBe("20");
    expect(params.get("offset")).toBe("40");
  });
});
