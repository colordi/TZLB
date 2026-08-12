import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AdminStorageView from "../AdminStorageView.vue";

const apiMocks = vi.hoisted(() => ({
  fetchStorageConfig: vi.fn(),
  updateStorageConfig: vi.fn(),
  testStorageConnection: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
  isUnauthorizedError: vi.fn(() => false),
}));

vi.mock("../../api/admin.js", () => ({
  fetchStorageConfig: apiMocks.fetchStorageConfig,
  updateStorageConfig: apiMocks.updateStorageConfig,
  testStorageConnection: apiMocks.testStorageConnection,
}));

vi.mock("../../api/http.js", () => ({
  isUnauthorizedError: apiMocks.isUnauthorizedError,
}));

vi.mock("../../composables/useToast.js", () => ({
  useToast: () => ({ error: apiMocks.error, info: apiMocks.info }),
}));

function buildConfig(overrides = {}) {
  return {
    backend: "r2",
    r2_endpoint_url: "https://example.r2.cloudflarestorage.com",
    r2_access_key_id: "key-id",
    r2_secret_configured: true,
    r2_bucket: "tzlb-assets",
    r2_prefix: "assets/",
    source: "database",
    updated_by: "admin",
    updated_at: "2026-08-12T10:00:00+00:00",
    ...overrides,
  };
}

async function mountView(config = buildConfig()) {
  apiMocks.fetchStorageConfig.mockResolvedValue(config);
  const wrapper = mount(AdminStorageView);
  await flushPromises();
  return wrapper;
}

describe("AdminStorageView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("加载配置并回填表单（密钥脱敏不回显）", async () => {
    const wrapper = await mountView();

    expect(wrapper.find('[data-testid="storage-backend"]').element.value).toBe("r2");
    expect(wrapper.find('[data-testid="r2-endpoint"]').element.value).toBe(
      "https://example.r2.cloudflarestorage.com",
    );
    expect(wrapper.find('[data-testid="r2-bucket"]').element.value).toBe("tzlb-assets");
    const secretInput = wrapper.find('[data-testid="r2-secret-access-key"]');
    expect(secretInput.element.value).toBe("");
    expect(secretInput.attributes("placeholder")).toContain("已配置");
    expect(wrapper.find('[data-testid="storage-status"]').text()).toContain(
      "Cloudflare R2",
    );
    expect(wrapper.find('[data-testid="storage-status"]').text()).toContain(
      "管理后台配置",
    );
    expect(wrapper.find('[data-testid="storage-status"]').text()).toContain("admin");
  });

  it("本地磁盘模式隐藏 R2 字段组", async () => {
    const wrapper = await mountView(buildConfig({ backend: "local", source: "env" }));

    expect(wrapper.find('[data-testid="r2-endpoint"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="storage-test"]').exists()).toBe(false);
  });

  it("保存时提交表单内容并提示成功", async () => {
    const wrapper = await mountView();
    apiMocks.updateStorageConfig.mockResolvedValue(buildConfig());

    await wrapper.find('[data-testid="r2-bucket"]').setValue("new-bucket");
    await wrapper.find("form").trigger("submit.prevent");
    await flushPromises();

    expect(apiMocks.updateStorageConfig).toHaveBeenCalledWith({
      backend: "r2",
      r2_endpoint_url: "https://example.r2.cloudflarestorage.com",
      r2_access_key_id: "key-id",
      r2_secret_access_key: "",
      r2_bucket: "new-bucket",
      r2_prefix: "assets/",
    });
    expect(apiMocks.info).toHaveBeenCalled();
  });

  it("保存失败时提示错误", async () => {
    const wrapper = await mountView();
    apiMocks.updateStorageConfig.mockRejectedValue(new Error("使用 R2 存储需要填写 Bucket 名称"));

    await wrapper.find("form").trigger("submit.prevent");
    await flushPromises();

    expect(apiMocks.error).toHaveBeenCalled();
    expect(apiMocks.error.mock.calls[0][0]).toContain("Bucket");
  });

  it("点击测试连接调用测试接口", async () => {
    const wrapper = await mountView();
    apiMocks.testStorageConnection.mockResolvedValue({ ok: true, message: "连接成功" });

    await wrapper.find('[data-testid="storage-test"]').trigger("click");
    await flushPromises();

    expect(apiMocks.testStorageConnection).toHaveBeenCalledWith(
      expect.objectContaining({ backend: "r2", r2_bucket: "tzlb-assets" }),
    );
    expect(apiMocks.info).toHaveBeenCalled();
  });
});
