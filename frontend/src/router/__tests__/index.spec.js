import { describe, expect, it } from "vitest";

import router from "../index.js";

describe("router", () => {
  it("默认根路径跳转到调查点位页面", async () => {
    await router.push("/");
    await router.isReady();

    expect(router.currentRoute.value.fullPath).toBe("/map");
  });
});
