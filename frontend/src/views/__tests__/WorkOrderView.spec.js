import { defineComponent } from "vue";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createEmptyRecord } from "../../components/workorder/fieldConfig.js";
import { UnauthorizedError } from "../../api/http.js";
import WorkOrderView from "../WorkOrderView.vue";

const apiMocks = vi.hoisted(() => ({
  generateWorkorder: vi.fn(),
  downloadBlob: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
}));

vi.mock("../../api/workorder.js", () => ({
  generateWorkorder: apiMocks.generateWorkorder,
}));

vi.mock("../../utils/download.js", () => ({
  downloadBlob: apiMocks.downloadBlob,
}));

vi.mock("../../composables/useToast.js", () => ({
  useToast: () => ({
    success: apiMocks.success,
    error: apiMocks.error,
    info: apiMocks.info,
  }),
}));

const RecordTableStub = defineComponent({
  name: "RecordTable",
  props: {
    records: {
      type: Array,
      default: () => [],
    },
  },
  emits: ["update:records"],
  template: '<div data-testid="record-table">记录表格 {{ records.length }}</div>',
});

const SurveyImportDialogStub = defineComponent({
  name: "SurveyImportDialog",
  props: {
    open: {
      type: Boolean,
      default: false,
    },
    pestType: {
      type: String,
      default: "春尺蠖",
    },
  },
  emits: ["close", "import"],
  template: '<div data-testid="survey-import-dialog" :data-open="open ? \'yes\' : \'no\'" />',
});

function mountWorkOrderView() {
  return mount(WorkOrderView, {
    global: {
      stubs: {
        RecordTable: RecordTableStub,
        SurveyImportDialog: SurveyImportDialogStub,
      },
    },
  });
}

function createValidRecord(overrides = {}) {
  return {
    ...createEmptyRecord("春尺蠖"),
    survey_date: "2026-04-01",
    locality: "于家务乡",
    location_id: "YF0069",
    location_name: "神仙村",
    description: "点位描述",
    ...overrides,
  };
}

async function importRecords(wrapper, nextRecords) {
  wrapper.getComponent(SurveyImportDialogStub).vm.$emit("import", nextRecords);
  await wrapper.vm.$nextTick();
}

function findButtonByText(wrapper, keyword) {
  const target = wrapper
    .findAll("button")
    .find((button) => button.text().includes(keyword));

  if (!target) {
    throw new Error(`未找到包含 ${keyword} 的按钮`);
  }

  return target;
}

function createDeferred() {
  let resolve;
  let reject;
  const promise = new Promise((innerResolve, innerReject) => {
    resolve = innerResolve;
    reject = innerReject;
  });

  return { promise, resolve, reject };
}

describe("WorkOrderView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.generateWorkorder.mockResolvedValue({
      blob: new Blob(["doc"]),
      filename: "工作单.doc",
    });
    apiMocks.downloadBlob.mockResolvedValue({ delivery: "download" });
  });

  it("移除页面介绍模块后仍保留侧栏和主表格", () => {
    const wrapper = mountWorkOrderView();

    expect(wrapper.find(".page-title-row").exists()).toBe(false);
    expect(wrapper.find(".workspace-intro").exists()).toBe(false);
    expect(wrapper.text()).toContain("当前记录");
    expect(wrapper.text()).toContain("任务配置");
    expect(wrapper.text()).toContain("生成工作单");
    expect(wrapper.text()).toContain("导入调查数据");
    expect(wrapper.get('[data-testid="record-table"]').text()).toContain("记录表格");
  });

  it("春尺蠖、国槐尺蠖、美国白蛾和其他害虫都显示调查导入入口", async () => {
    const wrapper = mountWorkOrderView();

    expect(wrapper.find('[data-testid="survey-import-button"]').exists()).toBe(true);

    await wrapper.get("#pest-type").setValue("其他害虫");

    expect(wrapper.find('[data-testid="survey-import-button"]').exists()).toBe(true);
    expect(wrapper.get("#task-type").element.value).toBe("其他害虫防治");
    expect(wrapper.get("#task-name").element.value).toBe("2026其他害虫防治");

    await wrapper.get("#pest-type").setValue("美国白蛾");

    expect(wrapper.find('[data-testid="survey-import-button"]').exists()).toBe(true);
    expect(wrapper.get("#task-type").element.value).toBe("美国白蛾防治");
    expect(wrapper.get("#task-name").element.value).toBe("2026美国白蛾第一代防治");

    await wrapper.get("#pest-type").setValue("国槐尺蠖");

    expect(wrapper.find('[data-testid="survey-import-button"]').exists()).toBe(true);
    expect(wrapper.get("#task-type").element.value).toBe("国槐尺蠖防治");
    expect(wrapper.get("#task-name").element.value).toBe("2026国槐尺蠖第一代防治");
    expect(
      Array.from(wrapper.get("#task-name").element.options).map((option) => option.value),
    ).toEqual([
      "2026国槐尺蠖第一代防治",
      "2026国槐尺蠖第二代防治",
      "2026国槐尺蠖第三代防治",
    ]);
  });

  it("导入调查记录时会保留自动图片，并在已有记录后继续追加", async () => {
    const wrapper = mountWorkOrderView();
    const recordTable = wrapper.getComponent(RecordTableStub);
    const surveyDialog = wrapper.getComponent(SurveyImportDialogStub);

    await wrapper.get('[data-testid="survey-import-button"]').trigger("click");
    expect(surveyDialog.props("open")).toBe(true);

    await importRecords(wrapper, [
      {
        survey_date: "2026-04-01",
        locality: "于家务乡",
        location_id: "YF0069",
        location_name: "神仙村",
        total_insect_count: 50,
        damage_level: "重",
        note: "",
        description: "描述1",
        images: ["data:image/jpeg;base64,point-screenshot"],
      },
    ]);

    expect(recordTable.props("records")).toHaveLength(1);
    expect(recordTable.props("records")[0].location_id).toBe("YF0069");
    expect(recordTable.props("records")[0].images).toEqual([
      "data:image/jpeg;base64,point-screenshot",
    ]);

    await importRecords(wrapper, [
      {
        survey_date: "2026-04-02",
        locality: "漷县镇",
        location_id: "HX0002",
        location_name: "林场二区",
        total_insect_count: 28,
        damage_level: "中",
        note: "需跟进",
        description: "描述2",
      },
    ]);

    expect(recordTable.props("records")).toHaveLength(2);
    expect(recordTable.props("records")[0].location_id).toBe("YF0069");
    expect(recordTable.props("records")[1].location_id).toBe("HX0002");
  });

  it("其他害虫导入后保留模板字段并支持导出", async () => {
    const wrapper = mountWorkOrderView();

    await wrapper.get("#pest-type").setValue("其他害虫");
    await wrapper.get('[data-testid="survey-import-button"]').trigger("click");

    await importRecords(wrapper, [
      {
        survey_date: "2026-04-17",
        locality: "潞城镇",
        location_id: "QT0001",
        location_name: "畅和东路北京学校西侧",
        pest_name: "蚜虫",
        host_plant: "栾树",
        plot_type: "道路绿化",
        survey_result: "发现问题",
        description: "描述1",
        note: "",
        images: [],
      },
    ]);

    await findButtonByText(wrapper, "生成工作单").trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.generateWorkorder).toHaveBeenCalledTimes(1);
    });

    expect(apiMocks.generateWorkorder).toHaveBeenCalledWith({
      pest_type: "其他害虫",
      task_type: "其他害虫防治",
      task: "2026其他害虫防治",
      records: [
        expect.objectContaining({
          location_id: "QT0001",
          pest_name: "蚜虫",
          host_plant: "栾树",
          plot_type: "道路绿化",
          serial_number: 1,
        }),
      ],
    });
  });

  it("国槐尺蠖导入后保留模板字段并支持导出", async () => {
    const wrapper = mountWorkOrderView();

    await wrapper.get("#pest-type").setValue("国槐尺蠖");
    await wrapper.vm.$nextTick();
    await wrapper.get("#task-name").setValue("2026国槐尺蠖第三代防治");
    await wrapper.get('[data-testid="survey-import-button"]').trigger("click");

    await importRecords(wrapper, [
      {
        survey_date: "2026-05-02",
        locality: "宋庄镇",
        location_id: "1001-1",
        location_name: "管头村",
        total_insect_count: 45,
        damage_level: "重",
        note: "需复查",
        description: "描述1",
        images: [],
      },
    ]);

    await findButtonByText(wrapper, "生成工作单").trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.generateWorkorder).toHaveBeenCalledTimes(1);
    });

    expect(apiMocks.generateWorkorder).toHaveBeenCalledWith({
      pest_type: "国槐尺蠖",
      task_type: "国槐尺蠖防治",
      task: "2026国槐尺蠖第三代防治",
      records: [
        expect.objectContaining({
          location_id: "1001-1",
          note: "需复查",
          serial_number: 1,
        }),
      ],
    });
    expect(apiMocks.generateWorkorder.mock.calls[0][0].records[0]).not.toHaveProperty(
      "total_insect_count",
    );
    expect(apiMocks.generateWorkorder.mock.calls[0][0].records[0]).not.toHaveProperty(
      "damage_level",
    );
  });

  it("美国白蛾导入后保留模板字段并支持导出", async () => {
    const wrapper = mountWorkOrderView();

    await wrapper.get("#pest-type").setValue("美国白蛾");
    await wrapper.get('[data-testid="survey-import-button"]').trigger("click");

    await importRecords(wrapper, [
      {
        survey_date: "2026-05-26",
        region: "城区",
        locality: "梨园镇",
        location_id: "MQ001",
        location_name: "玉桥东路",
        occurrence_position: "道路东侧",
        green_space_type: "道路绿化",
        pest_hosts: "白蜡",
        damaged_plant_count: 3,
        web_nest_count: 5,
        description: "发现美国白蛾网幕，已安排剪网处置。",
        note: "需复查",
        images: [],
      },
    ]);

    await findButtonByText(wrapper, "生成工作单").trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.generateWorkorder).toHaveBeenCalledTimes(1);
    });

    expect(apiMocks.generateWorkorder).toHaveBeenCalledWith({
      pest_type: "美国白蛾",
      task_type: "美国白蛾防治",
      task: "2026美国白蛾第一代防治",
      records: [
        expect.objectContaining({
          location_id: "MQ001",
          green_space_type: "道路绿化",
          pest_hosts: "白蜡",
          damaged_plant_count: 3,
          web_nest_count: 5,
          serial_number: 1,
        }),
      ],
    });
    expect(apiMocks.generateWorkorder.mock.calls[0][0].records[0]).not.toHaveProperty(
      "region",
    );
    expect(apiMocks.generateWorkorder.mock.calls[0][0].records[0]).not.toHaveProperty(
      "occurrence_position",
    );
  });

  it("单条记录导出时只请求一次接口，并按真实下载结果提示成功", async () => {
    const wrapper = mountWorkOrderView();
    await importRecords(wrapper, [createValidRecord()]);

    await findButtonByText(wrapper, "生成工作单").trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.generateWorkorder).toHaveBeenCalledTimes(1);
    });

    expect(apiMocks.generateWorkorder).toHaveBeenCalledWith({
      pest_type: "春尺蠖",
      task_type: "春尺蠖防治",
      task: "2026春尺蠖防治",
      records: [
        expect.objectContaining({
          location_id: "YF0069",
          serial_number: 1,
        }),
      ],
    });
    expect(apiMocks.downloadBlob).toHaveBeenCalledTimes(1);
    expect(apiMocks.success).toHaveBeenCalledWith("工作单已开始下载。", "导出成功");
  });

  it("多条记录会按顺序逐条导出，并显示当前进度与汇总成功提示", async () => {
    const firstRequest = createDeferred();
    const secondRequest = createDeferred();

    apiMocks.generateWorkorder
      .mockImplementationOnce(() => firstRequest.promise)
      .mockImplementationOnce(() => secondRequest.promise);

    const wrapper = mountWorkOrderView();
    await importRecords(wrapper, [
      createValidRecord({ location_id: "YF0069" }),
      createValidRecord({ location_id: "YF0070", location_name: "中心林地" }),
    ]);

    await findButtonByText(wrapper, "生成工作单").trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.generateWorkorder).toHaveBeenCalledTimes(1);
      expect(findButtonByText(wrapper, "正在导出").text()).toContain("1/2");
    });

    firstRequest.resolve({
      blob: new Blob(["doc-1"]),
      filename: "工作单-1.doc",
    });

    await vi.waitFor(() => {
      expect(apiMocks.generateWorkorder).toHaveBeenCalledTimes(2);
      expect(findButtonByText(wrapper, "正在导出").text()).toContain("2/2");
    });

    secondRequest.resolve({
      blob: new Blob(["doc-2"]),
      filename: "工作单-2.doc",
    });

    await vi.waitFor(() => {
      expect(apiMocks.success).toHaveBeenCalledWith("已依次导出 2 份工作单。", "导出成功");
    });

    expect(apiMocks.generateWorkorder.mock.calls[0][0].records).toHaveLength(1);
    expect(apiMocks.generateWorkorder.mock.calls[1][0].records).toHaveLength(1);
    expect(apiMocks.generateWorkorder.mock.calls[0][0].records[0].location_id).toBe("YF0069");
    expect(apiMocks.generateWorkorder.mock.calls[0][0].records[0].serial_number).toBe(1);
    expect(apiMocks.generateWorkorder.mock.calls[1][0].records[0].location_id).toBe("YF0070");
    expect(apiMocks.generateWorkorder.mock.calls[1][0].records[0].serial_number).toBe(2);
  });

  it("多条记录部分失败时展示部分成功提示，不误报全部成功", async () => {
    apiMocks.generateWorkorder
      .mockResolvedValueOnce({
        blob: new Blob(["doc-1"]),
        filename: "工作单-1.doc",
      })
      .mockRejectedValueOnce(new Error("网络异常"));

    const wrapper = mountWorkOrderView();
    await importRecords(wrapper, [
      createValidRecord({ location_id: "YF0069" }),
      createValidRecord({ location_id: "YF0070", location_name: "中心林地" }),
    ]);

    await findButtonByText(wrapper, "生成工作单").trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.error).toHaveBeenCalledWith(
        "已导出 1/2 份工作单，剩余导出失败：网络异常",
        "部分导出失败",
      );
    });

    expect(apiMocks.success).not.toHaveBeenCalledWith("已依次导出 2 份工作单。", "导出成功");
  });

  it("认证失效时中断后续逐条导出", async () => {
    apiMocks.generateWorkorder.mockRejectedValueOnce(new UnauthorizedError());

    const wrapper = mountWorkOrderView();
    await importRecords(wrapper, [
      createValidRecord({ location_id: "YF0069" }),
      createValidRecord({ location_id: "YF0070", location_name: "中心林地" }),
    ]);
    apiMocks.success.mockClear();
    apiMocks.error.mockClear();
    apiMocks.downloadBlob.mockClear();

    await findButtonByText(wrapper, "生成工作单").trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.generateWorkorder).toHaveBeenCalledTimes(1);
    });

    expect(apiMocks.downloadBlob).not.toHaveBeenCalled();
    expect(apiMocks.error).not.toHaveBeenCalled();
    expect(apiMocks.success).not.toHaveBeenCalled();
  });
});
