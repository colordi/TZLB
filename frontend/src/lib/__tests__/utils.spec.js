import { describe, expect, it } from "vitest";

import { cn } from "../utils.js";

describe("cn", () => {
  it("合并 class 并处理 Tailwind 冲突", () => {
    expect(cn("px-2 py-1", "px-4")).toBe("py-1 px-4");
    expect(cn("bg-background", false && "hidden", "text-foreground")).toBe(
      "bg-background text-foreground",
    );
  });
});
