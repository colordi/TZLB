import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildLoginRedirectPath,
  ensureApiSuccess,
  isUnauthorizedError,
  resetUnauthorizedRedirectState,
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
});
