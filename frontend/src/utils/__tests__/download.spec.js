import { afterEach, describe, expect, it, vi } from "vitest";

import { downloadBlob } from "../download.js";

const DESKTOP_USER_AGENT =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/135.0.0.0 Safari/537.36";
const IOS_USER_AGENT =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 Version/17.4 Mobile/15E148 Safari/604.1";

function setUserAgent(value) {
  Object.defineProperty(window.navigator, "userAgent", {
    value,
    configurable: true,
  });
}

function ensureBlobUrlApis() {
  if (typeof URL.createObjectURL !== "function") {
    Object.defineProperty(URL, "createObjectURL", {
      value: vi.fn(() => "blob:default"),
      configurable: true,
      writable: true,
    });
  }

  if (typeof URL.revokeObjectURL !== "function") {
    Object.defineProperty(URL, "revokeObjectURL", {
      value: vi.fn(),
      configurable: true,
      writable: true,
    });
  }
}

function captureAnchorClick() {
  const originalCreateElement = document.createElement.bind(document);
  const state = {
    anchor: null,
    click: null,
  };

  const anchor = {
    href: "",
    download: "",
    target: "",
    rel: "",
    click: vi.fn(),
    remove: vi.fn(),
  };
  state.anchor = anchor;
  state.click = anchor.click;

  vi.spyOn(document.body, "appendChild").mockImplementation(() => anchor);
  vi.spyOn(document, "createElement").mockImplementation((tagName, options) => {
    if (`${tagName}`.toLowerCase() === "a") {
      return anchor;
    }
    return originalCreateElement(tagName, options);
  });

  return state;
}

describe("utils/download", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    setUserAgent(DESKTOP_USER_AGENT);
    delete navigator.share;
    delete navigator.canShare;
  });

  it("桌面端优先使用浏览器下载并延迟释放 blob URL", async () => {
    vi.useFakeTimers();
    ensureBlobUrlApis();
    setUserAgent(DESKTOP_USER_AGENT);
    const anchorState = captureAnchorClick();
    const createUrl = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:download");
    const revokeUrl = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});

    const result = await downloadBlob(new Blob(["docx"]), "工作单.docx");

    expect(result).toEqual({ delivery: "download" });
    expect(createUrl).toHaveBeenCalledTimes(1);
    expect(anchorState.anchor?.download).toBe("工作单.docx");
    expect(anchorState.click).toHaveBeenCalledTimes(1);
    expect(revokeUrl).not.toHaveBeenCalled();

    vi.runAllTimers();

    expect(revokeUrl).toHaveBeenCalledWith("blob:download");
  });

  it("移动端无法可靠下载时优先走系统分享", async () => {
    ensureBlobUrlApis();
    setUserAgent(IOS_USER_AGENT);
    const share = vi.fn().mockResolvedValue(undefined);
    const canShare = vi.fn().mockReturnValue(true);
    Object.defineProperty(navigator, "share", {
      value: share,
      configurable: true,
    });
    Object.defineProperty(navigator, "canShare", {
      value: canShare,
      configurable: true,
    });

    const result = await downloadBlob(new Blob(["docx"]), "工作单.docx");

    expect(result).toEqual({ delivery: "share" });
    expect(canShare).toHaveBeenCalledTimes(1);
    expect(share).toHaveBeenCalledTimes(1);
    expect(share.mock.calls[0][0].files).toHaveLength(1);
    expect(share.mock.calls[0][0].files[0].name).toBe("工作单.docx");
  });

  it("移动端无法分享时回退到新页预览", async () => {
    vi.useFakeTimers();
    ensureBlobUrlApis();
    setUserAgent(IOS_USER_AGENT);
    const anchorState = captureAnchorClick();
    const createUrl = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:preview");
    const revokeUrl = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});

    const result = await downloadBlob(new Blob(["docx"]), "工作单.docx");

    expect(result).toEqual({ delivery: "preview" });
    expect(createUrl).toHaveBeenCalledTimes(1);
    expect(anchorState.anchor?.target).toBe("_blank");
    expect(anchorState.anchor?.rel).toContain("noopener");
    expect(anchorState.click).toHaveBeenCalledTimes(1);

    vi.runAllTimers();

    expect(revokeUrl).toHaveBeenCalledWith("blob:preview");
  });

  it("没有可用交付方式时抛出失败错误", async () => {
    ensureBlobUrlApis();
    setUserAgent(IOS_USER_AGENT);
    vi.spyOn(URL, "createObjectURL").mockImplementation(() => {
      throw new Error("blob 不可用");
    });

    await expect(downloadBlob(new Blob(["docx"]), "工作单.docx")).rejects.toThrow(
      "当前浏览器无法交付导出文件",
    );
  });
});
