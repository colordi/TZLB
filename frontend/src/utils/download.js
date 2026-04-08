const OBJECT_URL_RELEASE_DELAY = 60_000;
const MOBILE_BROWSER_PATTERN = /Android|iPhone|iPad|iPod/i;

function isLikelyMobileBrowser() {
  return MOBILE_BROWSER_PATTERN.test(globalThis.navigator?.userAgent || "");
}

function createObjectUrl(blob) {
  if (typeof URL?.createObjectURL !== "function") {
    throw new Error("当前浏览器无法交付导出文件");
  }
  return URL.createObjectURL(blob);
}

function releaseObjectUrlLater(url) {
  if (typeof URL?.revokeObjectURL !== "function") {
    return;
  }

  window.setTimeout(() => {
    URL.revokeObjectURL(url);
  }, OBJECT_URL_RELEASE_DELAY);
}

function triggerTemporaryLink(configureLink) {
  if (typeof document?.createElement !== "function") {
    return false;
  }

  const link = document.createElement("a");
  if (!link || typeof link.click !== "function") {
    return false;
  }

  configureLink(link);
  document.body?.appendChild?.(link);
  link.click();
  link.remove?.();
  return true;
}

function canUseNativeDownload() {
  if (isLikelyMobileBrowser()) {
    return false;
  }

  if (typeof document?.createElement !== "function") {
    return false;
  }

  const link = document.createElement("a");
  return Boolean(link && "download" in link);
}

async function shareBlob(blob, filename) {
  if (typeof File !== "function" || typeof navigator?.share !== "function") {
    return null;
  }

  const file = new File([blob], filename, {
    type: blob.type || "application/octet-stream",
  });
  const sharePayload = {
    title: filename,
    files: [file],
  };

  if (typeof navigator.canShare === "function" && !navigator.canShare(sharePayload)) {
    return null;
  }

  await navigator.share(sharePayload);
  return { delivery: "share" };
}

function previewBlob(blob) {
  const url = createObjectUrl(blob);
  releaseObjectUrlLater(url);

  const opened = triggerTemporaryLink((link) => {
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
  });

  if (!opened) {
    URL.revokeObjectURL?.(url);
    return null;
  }

  return { delivery: "preview" };
}

export async function downloadBlob(blob, filename) {
  try {
    if (canUseNativeDownload()) {
      const url = createObjectUrl(blob);
      releaseObjectUrlLater(url);

      const started = triggerTemporaryLink((link) => {
        link.href = url;
        link.download = filename;
      });

      if (started) {
        return { delivery: "download" };
      }

      URL.revokeObjectURL?.(url);
    }

    const shared = await shareBlob(blob, filename);
    if (shared) {
      return shared;
    }

    const previewed = previewBlob(blob);
    if (previewed) {
      return previewed;
    }
  } catch (downloadError) {
    if (downloadError?.name === "AbortError") {
      throw new Error("已取消系统分享。");
    }
    if (downloadError instanceof Error && downloadError.message === "当前浏览器无法交付导出文件") {
      throw downloadError;
    }
  }

  throw new Error("当前浏览器无法交付导出文件");
}
