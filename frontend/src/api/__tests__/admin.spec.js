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

  it("读取任务视图构建器候选源表", async () => {
    const { fetchViewBuilderSources } = await import("../admin.js");

    await fetchViewBuilderSources();

    expect(httpMocks.apiFetch).toHaveBeenCalledWith(
      "/api/admin/view-builder/sources",
    );
  });

  it("预览任务视图时提交定义", async () => {
    const { previewTaskView } = await import("../admin.js");
    const payload = {
      name: "task_baie_2026",
      display_name: "美国白蛾2026",
      base_table: "美国白蛾点位基础表",
      related_table: "survey.美国白蛾调查表",
      site_name_column: "点位名称",
      filters: { year: "2026", generation: null },
    };

    await previewTaskView(payload);

    const [url, options] = httpMocks.apiFetch.mock.calls[0];
    expect(url).toBe("/api/admin/view-builder/preview");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual(payload);
  });

  it("发布任务视图时提交定义", async () => {
    const { createTaskView } = await import("../admin.js");
    const payload = {
      name: "task_sites_only",
      display_name: "其他害虫点位",
      base_table: "其他害虫点位基础表",
      related_table: null,
      site_name_column: null,
      filters: { year: null, generation: null },
    };

    await createTaskView(payload);

    const [url, options] = httpMocks.apiFetch.mock.calls[0];
    expect(url).toBe("/api/admin/view-builder/views");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual(payload);
  });

  it("删除任务视图时对视图名做 URL 编码", async () => {
    const { deleteTaskView } = await import("../admin.js");

    await deleteTaskView("task_baie_2026");

    const [url, options] = httpMocks.apiFetch.mock.calls[0];
    expect(url).toBe("/api/admin/view-builder/views/task_baie_2026");
    expect(options.method).toBe("DELETE");
  });
});