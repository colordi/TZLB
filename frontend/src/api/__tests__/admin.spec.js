import { beforeEach, describe, expect, it, vi } from "vitest";

const httpMocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  ensureApiSuccess: vi.fn(),
}));

vi.mock("../http.js", () => ({
  apiFetch: httpMocks.apiFetch,
  ensureApiSuccess: httpMocks.ensureApiSuccess,
}));

describe("api/admin", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    httpMocks.apiFetch.mockResolvedValue({
      json: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    });
    httpMocks.ensureApiSuccess.mockResolvedValue();
  });

  it("读取操作日志时使用默认 limit 与 offset", async () => {
    const { fetchOperationLogs } = await import("../admin.js");

    await fetchOperationLogs();

    const url = httpMocks.apiFetch.mock.calls[0][0];
    const [path, query] = url.split("?");
    const search = new URLSearchParams(query);

    expect(path).toBe("/api/admin/operation-logs");
    expect(search.get("limit")).toBe("100");
    expect(search.get("offset")).toBe("0");
  });

  it("读取操作日志时携带自定义分页参数", async () => {
    const { fetchOperationLogs } = await import("../admin.js");

    await fetchOperationLogs({ limit: 50, offset: 100 });

    const url = httpMocks.apiFetch.mock.calls[0][0];
    const search = new URLSearchParams(url.split("?")[1]);

    expect(search.get("limit")).toBe("50");
    expect(search.get("offset")).toBe("100");
  });
});