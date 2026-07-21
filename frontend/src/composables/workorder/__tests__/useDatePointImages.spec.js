import { beforeEach, describe, expect, it, vi } from "vitest";

import { useDatePointImages } from "../useDatePointImages.js";
import { fetchSurveyCandidates } from "../../../api/survey.js";
import {
  deletePointDateImage,
  fetchPointDateImages,
  uploadPointDateImages,
} from "../../../api/workorder.js";

vi.mock("../../../api/survey.js", () => ({
  fetchSurveyCandidates: vi.fn(),
}));

vi.mock("../../../api/workorder.js", () => ({
  deletePointDateImage: vi.fn(),
  fetchPointDateImages: vi.fn(),
  uploadPointDateImages: vi.fn(),
}));

function buildToast() {
  return { success: vi.fn(), info: vi.fn(), error: vi.fn() };
}

function buildPoint(code) {
  return { location_id: code, locality: "测试乡镇", location_name: `点位${code}` };
}

describe("useDatePointImages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("queryPoints 查询候选点位并加载当日图片，且不带截图 DataURL", async () => {
    fetchSurveyCandidates.mockResolvedValue([buildPoint("MQ001")]);
    fetchPointDateImages.mockResolvedValue({ images: [{ file_name: "MQ001-1.jpg" }] });

    const toast = buildToast();
    const store = useDatePointImages();
    store.selectedDate.value = "2026-05-26";
    await store.queryPoints({ pestType: "美国白蛾", year: 2026, generation: "第一代" }, toast);

    expect(fetchSurveyCandidates).toHaveBeenCalledWith({
      date: "2026-05-26",
      pestType: "美国白蛾",
      year: 2026,
      generation: "第一代",
      includeImages: false,
    });
    expect(fetchPointDateImages).toHaveBeenCalledWith({ surveyDate: "2026-05-26" });
    expect(store.points.value).toHaveLength(1);
    expect(store.queried.value).toBe(true);
    expect(store.imagesForPoint(store.points.value[0])).toEqual([
      { file_name: "MQ001-1.jpg" },
    ]);
  });

  it("未选择日期时 queryPoints 只提示不发请求", async () => {
    const toast = buildToast();
    const store = useDatePointImages();
    await store.queryPoints({ pestType: "美国白蛾" }, toast);

    expect(fetchSurveyCandidates).not.toHaveBeenCalled();
    expect(toast.info).toHaveBeenCalled();
  });

  it("图片按编号前缀归类，编号重叠时归到最长匹配", async () => {
    fetchSurveyCandidates.mockResolvedValue([buildPoint("MQ1"), buildPoint("MQ10")]);
    fetchPointDateImages.mockResolvedValue({
      images: [
        { file_name: "MQ1-1.jpg" },
        { file_name: "MQ10-1.jpg" },
        { file_name: "MQ10-2.jpg" },
        { file_name: "OTHER-1.jpg" },
      ],
    });

    const store = useDatePointImages();
    store.selectedDate.value = "2026-05-26";
    await store.queryPoints({ pestType: "美国白蛾" }, buildToast());

    const [mq1, mq10] = store.points.value;
    expect(store.imagesForPoint(mq1).map((item) => item.file_name)).toEqual(["MQ1-1.jpg"]);
    expect(store.imagesForPoint(mq10).map((item) => item.file_name)).toEqual([
      "MQ10-1.jpg",
      "MQ10-2.jpg",
    ]);
  });

  it("uploadToPoint 过滤非图片文件，上传成功后刷新图片列表", async () => {
    fetchSurveyCandidates.mockResolvedValue([buildPoint("MQ001")]);
    fetchPointDateImages
      .mockResolvedValueOnce({ images: [] })
      .mockResolvedValueOnce({ images: [{ file_name: "MQ001-1.jpg" }] });
    uploadPointDateImages.mockResolvedValue({ saved_count: 1, rejected: [] });

    const toast = buildToast();
    const store = useDatePointImages();
    store.selectedDate.value = "2026-05-26";
    await store.queryPoints({ pestType: "美国白蛾" }, toast);

    const imageFile = new File(["a"], "现场.jpg", { type: "image/jpeg" });
    const textFile = new File(["t"], "说明.txt", { type: "text/plain" });
    await store.uploadToPoint(store.points.value[0], [imageFile, textFile], toast);

    expect(uploadPointDateImages).toHaveBeenCalledTimes(1);
    const payload = uploadPointDateImages.mock.calls[0][0];
    expect(payload.surveyDate).toBe("2026-05-26");
    expect(payload.pointCode).toBe("MQ001");
    expect(payload.files).toEqual([imageFile]);
    expect(toast.success).toHaveBeenCalled();
    expect(store.imagesForPoint(store.points.value[0])).toEqual([
      { file_name: "MQ001-1.jpg" },
    ]);
  });

  it("uploadToPoint 全部为非图片文件时不发请求", async () => {
    const toast = buildToast();
    const store = useDatePointImages();
    store.selectedDate.value = "2026-05-26";

    await store.uploadToPoint(
      buildPoint("MQ001"),
      [new File(["t"], "说明.txt", { type: "text/plain" })],
      toast,
    );

    expect(uploadPointDateImages).not.toHaveBeenCalled();
    expect(toast.info).toHaveBeenCalled();
  });

  it("uploadToPoint 部分被拒绝时提示失败原因", async () => {
    uploadPointDateImages.mockResolvedValue({
      saved_count: 0,
      rejected: [{ file_name: "坏图.jpg", reason: "上传文件不是有效图片" }],
    });
    fetchPointDateImages.mockResolvedValue({ images: [] });

    const toast = buildToast();
    const store = useDatePointImages();
    store.selectedDate.value = "2026-05-26";

    await store.uploadToPoint(
      buildPoint("MQ001"),
      [new File(["x"], "坏图.jpg", { type: "image/jpeg" })],
      toast,
    );

    expect(toast.error).toHaveBeenCalledWith(
      expect.stringContaining("上传文件不是有效图片"),
      "图片上传失败",
    );
  });

  it("removeImage 调用删除接口并刷新列表", async () => {
    fetchSurveyCandidates.mockResolvedValue([buildPoint("MQ001")]);
    fetchPointDateImages
      .mockResolvedValueOnce({ images: [{ file_name: "MQ001-1.jpg" }] })
      .mockResolvedValueOnce({ images: [] });
    deletePointDateImage.mockResolvedValue({ deleted: "MQ001-1.jpg" });

    const toast = buildToast();
    const store = useDatePointImages();
    store.selectedDate.value = "2026-05-26";
    await store.queryPoints({ pestType: "美国白蛾" }, toast);

    await store.removeImage(store.points.value[0], "MQ001-1.jpg", toast);

    expect(deletePointDateImage).toHaveBeenCalledWith({
      surveyDate: "2026-05-26",
      pointCode: "MQ001",
      fileName: "MQ001-1.jpg",
    });
    expect(toast.success).toHaveBeenCalled();
    expect(store.imagesForPoint(store.points.value[0])).toEqual([]);
  });
});
