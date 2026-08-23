import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { resetAuthSessionState } from "../../composables/useAuthSession.js";
import router from "../index.js";

function mockCurrentUser(user) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        user,
      }),
    }),
  );
}

describe("router", () => {
  beforeEach(() => {
    resetAuthSessionState();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({
          detail: "未登录或登录状态已失效",
        }),
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    resetAuthSessionState();
  });

  it("默认根路径跳转到登录页面", async () => {
    await router.push("/");
    await router.isReady();

    expect(router.currentRoute.value.fullPath).toBe("/login");
  });

  it("未登录访问受保护页面时会跳转到登录页", async () => {
    await router.push("/map");
    await router.isReady();

    expect(router.currentRoute.value.fullPath).toBe("/login?redirect=/map");
  });

  it("调查员访问工单生成时会跳转到地图页", async () => {
    resetAuthSessionState();
    mockCurrentUser({
      id: 2,
      username: "dc01",
      display_name: "调查员 dc01",
      role: "investigator",
      is_active: true,
      last_login_at: null,
    });

    await router.push("/workorder");
    await router.isReady();

    expect(router.currentRoute.value.fullPath).toBe("/map");
  });

  it("管理员可以访问工单素材页面", async () => {
    resetAuthSessionState();
    mockCurrentUser({
      id: 1,
      username: "admin",
      display_name: "管理员",
      role: "admin",
      is_active: true,
      last_login_at: null,
    });

    await router.push("/workorder-assets");
    await router.isReady();

    expect(router.currentRoute.value.fullPath).toBe("/workorder-assets");
    expect(router.currentRoute.value.meta.requiredRoles).toEqual(["admin"]);
  });

  it("调查员访问工单素材页面时会跳转到地图页", async () => {
    resetAuthSessionState();
    mockCurrentUser({
      id: 2,
      username: "dc01",
      display_name: "调查员 dc01",
      role: "investigator",
      is_active: true,
      last_login_at: null,
    });

    await router.push("/map");
    await router.push("/workorder-assets");
    await router.isReady();

    expect(router.currentRoute.value.fullPath).toBe("/map");
  });

  it("已登录调查员从登录页携带工单重定向时仍进入地图页", async () => {
    resetAuthSessionState();
    mockCurrentUser({
      id: 2,
      username: "dc01",
      display_name: "调查员 dc01",
      role: "investigator",
      is_active: true,
      last_login_at: null,
    });

    await router.push("/login?redirect=/workorder");
    await router.isReady();

    expect(router.currentRoute.value.fullPath).toBe("/map");
  });

  it("管理员可以访问数据导出页面", async () => {
    resetAuthSessionState();
    mockCurrentUser({
      id: 1,
      username: "admin",
      display_name: "管理员",
      role: "admin",
      is_active: true,
      last_login_at: null,
    });

    await router.push("/data-export");
    await router.isReady();

    expect(router.currentRoute.value.fullPath).toBe("/data-export");
  });

  it("管理员可以访问数据统计页面", async () => {
    resetAuthSessionState();
    mockCurrentUser({
      id: 1,
      username: "admin",
      display_name: "管理员",
      role: "admin",
      is_active: true,
      last_login_at: null,
    });

    await router.push("/data-statistics");
    await router.isReady();

    expect(router.currentRoute.value.fullPath).toBe("/data-statistics/white-moth");
  });

  it("调查员访问数据导出时会跳转到地图页", async () => {
    await router.push("/map");
    await router.isReady();

    resetAuthSessionState();
    mockCurrentUser({
      id: 2,
      username: "dc01",
      display_name: "调查员 dc01",
      role: "investigator",
      is_active: true,
      last_login_at: null,
    });

    await router.push("/data-export");
    await router.isReady();

    expect(router.currentRoute.value.fullPath).toBe("/map");
  });

  it("调查员访问数据统计时会跳转到地图页", async () => {
    await router.push("/map");
    await router.isReady();

    resetAuthSessionState();
    mockCurrentUser({
      id: 2,
      username: "dc01",
      display_name: "调查员 dc01",
      role: "investigator",
      is_active: true,
      last_login_at: null,
    });

    await router.push("/data-statistics");
    await router.isReady();

    expect(router.currentRoute.value.fullPath).toBe("/map");
  });
});
