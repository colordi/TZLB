import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import PointScreenshotView from "../PointScreenshotView.vue";

const apiMocks = vi.hoisted(() => ({
  listPointScreenshotStatus: vi.fn(),
  fetchPointScreenshotBlob: vi.fn(),
  uploadPointScreenshot: vi.fn(),
  deletePointScreenshot: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
  revokeObjectURL: vi.fn(),
}));

vi.mock("../../api/pointScreenshot.js", () => ({
  listPointScreenshotStatus: apiMocks.listPointScreenshotStatus,
  fetchPointScreenshotBlob: apiMocks.fetchPointScreenshotBlob,
  uploadPointScreenshot: apiMocks.uploadPointScreenshot,
  deletePointScreenshot: apiMocks.deletePointScreenshot,
}));

vi.mock("../../composables/useToast.js", () => ({
  useToast: () => ({
    success: apiMocks.success,
    error: apiMocks.error,
  }),
}));

const POINTS_BY_PEST = {
  美国白蛾: [
    {
      code: "MQ001",
      name: "玉桥东路",
      locality: "梨园镇",
      has_screenshot: true,
      screenshot_filename: "MQ001.jpg",
    },
    {
      code: "MQ002",
      name: "运河公园",
      locality: "潞城镇",
      has_screenshot: false,
      screenshot_filename: null,
    },
  ],
  春尺蠖: [
    {
      code: "YT001",
      name: "神仙村",
      locality: "于家务乡",
      has_screenshot: true,
      screenshot_filename: "YT001.png",
    },
  ],
  国槐尺蠖: [],
};

function clonePoints(pestType) {
  return POINTS_BY_PEST[pestType].map((point) => ({ ...point }));
}

function createDeferred() {
  let resolve;
  let reject;
  const promise = new Promise((innerResolve, innerReject) => {
    resolve = innerResolve;
    reject = innerReject;
  });
  return { promise, resolve, reject };
}

function mountView() {
  return mount(PointScreenshotView, {
    global: {
      stubs: {
        RouterLink: {
          props: ["to"],
          template: '<a :href="to"><slot /></a>',
        },
        teleport: true,
      },
    },
  });
}

describe("PointScreenshotView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("URL", {
      revokeObjectURL: apiMocks.revokeObjectURL,
    });
    apiMocks.listPointScreenshotStatus.mockImplementation((pestType) =>
      Promise.resolve({
        pest_type: pestType,
        points: clonePoints(pestType),
      }),
    );
    apiMocks.fetchPointScreenshotBlob.mockImplementation((pestType, code) =>
      Promise.resolve(`blob:${pestType}:${code}`),
    );
    apiMocks.uploadPointScreenshot.mockResolvedValue({
      code: "MQ002",
      filename: "MQ002.png",
      size: 1024,
    });
    apiMocks.deletePointScreenshot.mockResolvedValue({
      code: "MQ001",
      deleted: true,
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("默认展示美国白蛾统计，并可切换害虫类型", async () => {
    const wrapper = mountView();
    await flushPromises();

    expect(apiMocks.listPointScreenshotStatus).toHaveBeenCalledWith("美国白蛾");
    expect(wrapper.findAll(".point-screenshot-tabs button")).toHaveLength(3);
    expect(wrapper.get('[data-testid="point-screenshot-total"]').text()).toContain("2");
    expect(wrapper.get('[data-testid="point-screenshot-existing"]').text()).toContain("1");
    expect(wrapper.get('[data-testid="point-screenshot-missing"]').text()).toContain("1");
    expect(wrapper.findAll(".point-screenshot-card")).toHaveLength(2);
    expect(apiMocks.fetchPointScreenshotBlob).toHaveBeenCalledWith("美国白蛾", "MQ001");

    await wrapper.get('[data-testid="point-screenshot-tab-春尺蠖"]').trigger("click");
    await flushPromises();

    expect(apiMocks.listPointScreenshotStatus).toHaveBeenLastCalledWith("春尺蠖");
    expect(wrapper.get('[data-testid="point-screenshot-total"]').text()).toContain("1");
    expect(wrapper.text()).toContain("神仙村");
    expect(wrapper.text()).not.toContain("运河公园");
    expect(apiMocks.revokeObjectURL).toHaveBeenCalledWith("blob:美国白蛾:MQ001");
  });

  it("每页最多加载 48 个缩略图，翻页时回收上一页 objectURL", async () => {
    const points = Array.from({ length: 100 }, (_, index) => ({
      code: `MQ${String(index + 1).padStart(4, "0")}`,
      name: `点位 ${index + 1}`,
      locality: "梨园镇",
      has_screenshot: true,
      screenshot_filename: `MQ${String(index + 1).padStart(4, "0")}.jpg`,
    }));
    apiMocks.listPointScreenshotStatus.mockResolvedValue({
      pest_type: "美国白蛾",
      points,
    });

    const wrapper = mountView();
    await flushPromises();

    expect(wrapper.findAll(".point-screenshot-card")).toHaveLength(48);
    expect(apiMocks.fetchPointScreenshotBlob).toHaveBeenCalledTimes(48);
    expect(wrapper.text()).toContain("第 1 / 3 页");

    await wrapper.get('[data-testid="point-screenshot-next-page"]').trigger("click");
    await flushPromises();

    expect(wrapper.findAll(".point-screenshot-card")).toHaveLength(48);
    expect(wrapper.text()).toContain("MQ0049");
    expect(apiMocks.fetchPointScreenshotBlob).toHaveBeenCalledTimes(96);
    expect(apiMocks.revokeObjectURL).toHaveBeenCalledTimes(48);
  });

  it("缺失点位选择图片后上传并刷新状态", async () => {
    apiMocks.listPointScreenshotStatus
      .mockResolvedValueOnce({
        pest_type: "美国白蛾",
        points: [clonePoints("美国白蛾")[1]],
      })
      .mockResolvedValueOnce({
        pest_type: "美国白蛾",
        points: [{ ...clonePoints("美国白蛾")[1], has_screenshot: true }],
      });
    const wrapper = mountView();
    await flushPromises();
    const input = wrapper.get('[data-testid="point-screenshot-file-input"]');
    const inputClick = vi.spyOn(input.element, "click").mockImplementation(() => {});

    await wrapper.get('[data-testid="point-screenshot-upload-MQ002"]').trigger("click");
    expect(inputClick).toHaveBeenCalledTimes(1);

    const file = new File(["image"], "new-point.png", { type: "image/png" });
    Object.defineProperty(input.element, "files", {
      value: [file],
      configurable: true,
    });
    await input.trigger("change");
    await flushPromises();

    expect(apiMocks.uploadPointScreenshot).toHaveBeenCalledWith({
      pestType: "美国白蛾",
      code: "MQ002",
      file,
    });
    expect(apiMocks.listPointScreenshotStatus).toHaveBeenCalledTimes(2);
    expect(wrapper.get('[data-testid="point-screenshot-existing"]').text()).toContain("1");
    expect(apiMocks.success).toHaveBeenCalledWith(
      "已上传 MQ002 的点位截图。",
      "截图已上传",
    );
  });

  it("已有点位可替换截图并回收旧 objectURL", async () => {
    const wrapper = mountView();
    await flushPromises();
    const input = wrapper.get('[data-testid="point-screenshot-file-input"]');
    vi.spyOn(input.element, "click").mockImplementation(() => {});

    await wrapper.get('[data-testid="point-screenshot-replace-MQ001"]').trigger("click");
    const file = new File(["image"], "replacement.webp", { type: "image/webp" });
    Object.defineProperty(input.element, "files", {
      value: [file],
      configurable: true,
    });
    await input.trigger("change");
    await flushPromises();

    expect(apiMocks.uploadPointScreenshot).toHaveBeenCalledWith({
      pestType: "美国白蛾",
      code: "MQ001",
      file,
    });
    expect(apiMocks.revokeObjectURL).toHaveBeenCalledWith("blob:美国白蛾:MQ001");
    expect(apiMocks.success).toHaveBeenCalledWith(
      "已替换 MQ001 的点位截图。",
      "截图已替换",
    );
  });

  it("删除已有截图前二次确认，成功后刷新状态并回收 objectURL", async () => {
    apiMocks.listPointScreenshotStatus
      .mockResolvedValueOnce({
        pest_type: "美国白蛾",
        points: [clonePoints("美国白蛾")[0]],
      })
      .mockResolvedValueOnce({
        pest_type: "美国白蛾",
        points: [{ ...clonePoints("美国白蛾")[0], has_screenshot: false }],
      });
    const wrapper = mountView();
    await flushPromises();

    await wrapper.get('[data-testid="point-screenshot-delete-MQ001"]').trigger("click");
    expect(wrapper.text()).toContain("确认删除 MQ001");

    await wrapper.get('[data-testid="confirm-dialog-confirm"]').trigger("click");
    await flushPromises();

    expect(apiMocks.deletePointScreenshot).toHaveBeenCalledWith("美国白蛾", "MQ001");
    expect(wrapper.get('[data-testid="point-screenshot-missing"]').text()).toContain("1");
    expect(apiMocks.revokeObjectURL).toHaveBeenCalledWith("blob:美国白蛾:MQ001");
    expect(apiMocks.success).toHaveBeenCalledWith(
      "已删除 MQ001 的点位截图。",
      "截图已删除",
    );
  });

  it("页面卸载时回收当前页缩略图 objectURL", async () => {
    const wrapper = mountView();
    await flushPromises();

    wrapper.unmount();

    expect(apiMocks.revokeObjectURL).toHaveBeenCalledWith("blob:美国白蛾:MQ001");
  });

  it("上传期间卸载页面后不再提示或刷新，并隐藏文件输入焦点", async () => {
    const deferred = createDeferred();
    apiMocks.uploadPointScreenshot.mockReturnValue(deferred.promise);
    const wrapper = mountView();
    await flushPromises();
    const input = wrapper.get('[data-testid="point-screenshot-file-input"]');
    vi.spyOn(input.element, "click").mockImplementation(() => {});

    expect(input.attributes("hidden")).toBeDefined();
    await wrapper.get('[data-testid="point-screenshot-upload-MQ002"]').trigger("click");
    const file = new File(["image"], "new-point.png", { type: "image/png" });
    Object.defineProperty(input.element, "files", {
      value: [file],
      configurable: true,
    });
    await input.trigger("change");
    expect(apiMocks.uploadPointScreenshot).toHaveBeenCalledTimes(1);

    const listCallCount = apiMocks.listPointScreenshotStatus.mock.calls.length;
    wrapper.unmount();
    deferred.resolve({ code: "MQ002", filename: "MQ002.png", size: 1024 });
    await flushPromises();

    expect(apiMocks.success).not.toHaveBeenCalled();
    expect(apiMocks.listPointScreenshotStatus).toHaveBeenCalledTimes(listCallCount);
  });
});
