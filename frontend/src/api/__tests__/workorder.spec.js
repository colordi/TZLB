import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { uploadDateImageFolder } from "../workorder.js";

function buildResponse(payload, ok = true) {
  return {
    ok,
    async json() {
      return payload;
    },
  };
}

describe("workorder api", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("uploadDateImageFolder 使用 multipart 表单上传日期文件夹", async () => {
    global.fetch.mockResolvedValue(buildResponse({ saved_count: 1 }));
    const file = new File(["image"], "MQ001.jpg", { type: "image/jpeg" });
    Object.defineProperty(file, "webkitRelativePath", {
      value: "2026-05-26/MQ001.jpg",
      configurable: true,
    });

    await uploadDateImageFolder({
      folderName: "2026-05-26",
      files: [file],
    });

    const [, init] = global.fetch.mock.calls[0];
    expect(global.fetch.mock.calls[0][0]).toBe("/api/workorder/date-image-folder");
    expect(init).toEqual(
      expect.objectContaining({
        method: "POST",
        credentials: "same-origin",
      }),
    );
    expect(init.body).toBeInstanceOf(FormData);
    expect(init.body.get("folder_name")).toBe("2026-05-26");
    expect(init.body.get("files")).toBe(file);
    expect(init.body.get("relative_paths")).toBe("2026-05-26/MQ001.jpg");
  });
});
