import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { resetAuthSessionState } from "../../composables/useAuthSession.js";
import router from "../index.js";

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
});
