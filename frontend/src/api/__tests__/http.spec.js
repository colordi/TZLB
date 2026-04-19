import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildLoginRedirectPath,
  ensureApiSuccess,
  isUnauthorizedError,
  isLocalhostHostname,
  resetUnauthorizedRedirectState,
  shouldAttachLocalAuthBypass,
} from "../http.js";

describe("api/http", () => {
  afterEach(() => {
    resetUnauthorizedRedirectState();
  });

  it("401 时会跳转到带 redirect 参数的登录页", async () => {
    const locationLike = {
      pathname: "/map",
      search: "?view=latest",
      hash: "#panel",
      replace: vi.fn(),
    };
    let capturedError = null;

    try {
      await ensureApiSuccess(
        {
          ok: false,
          status: 401,
          json: async () => ({
            detail: "未登录或登录状态已失效",
          }),
        },
        { locationLike },
      );
    } catch (error) {
      capturedError = error;
    }

    expect(isUnauthorizedError(capturedError)).toBe(true);
    expect(locationLike.replace).toHaveBeenCalledWith(
      "/login?redirect=%2Fmap%3Fview%3Dlatest%23panel",
    );
  });

  it("登录页不重复追加 redirect 参数", () => {
    expect(
      buildLoginRedirectPath({
        pathname: "/login",
        search: "?redirect=%2Fmap",
        hash: "",
      }),
    ).toBe("/login");
  });

  it("仅本机地址会附加本机免登标记", () => {
    expect(isLocalhostHostname("127.0.0.1")).toBe(true);
    expect(isLocalhostHostname("localhost")).toBe(true);
    expect(isLocalhostHostname("[::1]")).toBe(true);
    expect(isLocalhostHostname("192.168.1.20")).toBe(false);

    expect(shouldAttachLocalAuthBypass({ hostname: "127.0.0.1" })).toBe(true);
    expect(shouldAttachLocalAuthBypass({ hostname: "localhost" })).toBe(true);
    expect(shouldAttachLocalAuthBypass({ hostname: "192.168.1.20" })).toBe(false);
  });
});
