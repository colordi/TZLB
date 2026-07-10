import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  deletePointScreenshot,
  fetchPointScreenshotBlob,
  listPointScreenshotStatus,
  uploadPointScreenshot,
} from "../pointScreenshot.js";

function buildJsonResponse(payload) {
  return {
    ok: true,
    async json() {
      return payload;
    },
  };
}

describe("pointScreenshot api", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("按害虫类型查询点位截图状态", async () => {
    global.fetch.mockResolvedValue(buildJsonResponse({
      pest_type: "美国白蛾",
      points: [],
    }));

    await listPointScreenshotStatus("美国白蛾");

    expect(global.fetch.mock.calls[0][0]).toBe(
      `/api/point-screenshots/status?pest_type=${encodeURIComponent("美国白蛾")}`,
    );
  });

  it("使用 multipart 表单上传点位截图", async () => {
    global.fetch.mockResolvedValue(buildJsonResponse({ filename: "MQ001.png" }));
    const file = new File(["image"], "point.png", { type: "image/png" });

    await uploadPointScreenshot({
      pestType: "美国白蛾",
      code: "MQ001",
      file,
    });

    const [, init] = global.fetch.mock.calls[0];
    expect(init).toEqual(expect.objectContaining({ method: "POST" }));
    expect(init.body).toBeInstanceOf(FormData);
    expect(init.body.get("pest_type")).toBe("美国白蛾");
    expect(init.body.get("code")).toBe("MQ001");
    expect(init.body.get("file")).toBe(file);
  });

  it("按害虫类型和编号删除点位截图", async () => {
    global.fetch.mockResolvedValue(buildJsonResponse({ code: "MQ 001", deleted: true }));

    await deletePointScreenshot("美国白蛾", "MQ 001");

    const [url, init] = global.fetch.mock.calls[0];
    expect(url).toBe(
      `/api/point-screenshots/?pest_type=${encodeURIComponent("美国白蛾")}&code=MQ%20001`,
    );
    expect(init).toEqual(expect.objectContaining({ method: "DELETE" }));
  });

  it("读取预览图片并返回 objectURL", async () => {
    const blob = new Blob(["image"], { type: "image/jpeg" });
    const createObjectURL = vi.fn().mockReturnValue("blob:point-preview");
    vi.stubGlobal("URL", { createObjectURL });
    global.fetch.mockResolvedValue({
      ok: true,
      async blob() {
        return blob;
      },
    });

    const result = await fetchPointScreenshotBlob("春尺蠖", "YT001");

    expect(result).toBe("blob:point-preview");
    expect(createObjectURL).toHaveBeenCalledWith(blob);
  });
});
