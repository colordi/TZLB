import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AdminOperationLogsView from "../AdminOperationLogsView.vue";

const apiMocks = vi.hoisted(() => ({
  fetchOperationLogs: vi.fn(),
  error: vi.fn(),
  isUnauthorizedError: vi.fn(() => false),
}));

vi.mock("../../api/admin.js", () => ({
  fetchOperationLogs: apiMocks.fetchOperationLogs,
}));

vi.mock("../../api/http.js", () => ({
  isUnauthorizedError: apiMocks.isUnauthorizedError,
}));

vi.mock("../../composables/useToast.js", () => ({
  useToast: () => ({ error: apiMocks.error }),
}));

function buildItem(overrides = {}) {
  return {
    id: 1,
    occurred_at: "2026-07-09T10:30:00+00:00",
    action: "删除美国白蛾点位",
    operator_id: 7,
    operator_username: "investigator1",
    operator_display_name: "张调查",
    operator_role: "investigator",
    site_code: "MQ001",
    site_name: "示范点",
    locality: "马驹桥镇",
    longitude: 116.5,
    latitude: 39.7,
    survey_record_count: 2,
    ...overrides,
  };
}

describe("AdminOperationLogsView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.fetchOperationLogs.mockResolvedValue({
      items: [buildItem()],
      total: 1,
    });
  });

  it("加载操作日志并渲染表格行", async () => {
    const wrapper = mount(AdminOperationLogsView);
    await flushPromises();

    expect(apiMocks.fetchOperationLogs).toHaveBeenCalledWith({ limit: 50, offset: 0 });
    expect(wrapper.text()).toContain("张调查");
    expect(wrapper.text()).toContain("MQ001");
    expect(wrapper.text()).toContain("马驹桥镇");
    expect(wrapper.text()).toContain("2");
  });

  it("空数据显示空态", async () => {
    apiMocks.fetchOperationLogs.mockResolvedValue({ items: [], total: 0 });
    const wrapper = mount(AdminOperationLogsView);
    await flushPromises();

    expect(wrapper.text()).toContain("暂无操作日志");
  });

  it("下一页用对应 offset 请求", async () => {
    apiMocks.fetchOperationLogs.mockResolvedValue({
      items: [buildItem()],
      total: 120,
    });
    const wrapper = mount(AdminOperationLogsView);
    await flushPromises();

    apiMocks.fetchOperationLogs.mockClear();
    await wrapper.get(".pager-btn:last-child").trigger("click");
    await flushPromises();

    expect(apiMocks.fetchOperationLogs).toHaveBeenCalledWith({ limit: 50, offset: 50 });
  });

  it("无下一页时禁用下一页按钮", async () => {
    apiMocks.fetchOperationLogs.mockResolvedValue({
      items: [buildItem()],
      total: 1,
    });
    const wrapper = mount(AdminOperationLogsView);
    await flushPromises();

    const nextBtn = wrapper.get(".pager-btn:last-child");
    expect(nextBtn.attributes("disabled")).toBe("");
  });
});