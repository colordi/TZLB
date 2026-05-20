import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchCurrentUser } from "../auth.js";

describe("api/auth", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("本机 development 模式下 auth/me 返回 401 时使用本机测试用户", async () => {
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

    const user = await fetchCurrentUser({
      locationLike: { hostname: "127.0.0.1" },
      env: { MODE: "development" },
    });

    expect(user).toEqual(
      expect.objectContaining({
        username: "local-dev",
        display_name: "本机测试用户",
        is_active: true,
      }),
    );
  });

  it("本机 development 模式下 auth/me 请求失败时也允许进入前端测试页面", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(
      fetchCurrentUser({
        locationLike: { hostname: "localhost" },
        env: { MODE: "development" },
      }),
    ).resolves.toEqual(
      expect.objectContaining({
        username: "local-dev",
      }),
    );
  });

  it("本机 development 模式下 auth/me 代理异常时也使用本机测试用户", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({
          detail: "后端服务暂不可用",
        }),
      }),
    );

    await expect(
      fetchCurrentUser({
        locationLike: { hostname: "127.0.0.1" },
        env: { MODE: "development" },
      }),
    ).resolves.toEqual(
      expect.objectContaining({
        username: "local-dev",
      }),
    );
  });

  it("非 development 模式下 auth/me 返回 401 时仍视为未登录", async () => {
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

    await expect(
      fetchCurrentUser({
        locationLike: { hostname: "127.0.0.1" },
        env: { MODE: "test" },
      }),
    ).resolves.toBeNull();
  });
});
