import { defineComponent } from "vue";
import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createEmptyRecord } from "../../components/workorder/fieldConfig.js";
import { UnauthorizedError } from "../../api/http.js";
import WorkOrderView from "../WorkOrderView.vue";

const apiMocks = vi.hoisted(() => ({
  generateWorkorder: vi.fn(),
  generateWorkorderBatch: vi.fn(),
  startWorkorderBatchJob: vi.fn(),
  getWorkorderBatchJobStatus: vi.fn(),
  downloadWorkorderBatchJob: vi.fn(),
  uploadDateImageFolder: vi.fn(),
  downloadBlob: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
}));

vi.mock("../../api/workorder.js", () => ({
  generateWorkorder: apiMocks.generateWorkorder,
  generateWorkorderBatch: apiMocks.generateWorkorderBatch,
  startWorkorderBatchJob: apiMocks.startWorkorderBatchJob,
  getWorkorderBatchJobStatus: apiMocks.getWorkorderBatchJobStatus,
  downloadWorkorderBatchJob: apiMocks.downloadWorkorderBatchJob,
  uploadDateImageFolder: apiMocks.uploadDateImageFolder,
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
    selectedUids: {
      type: Array,
      default: () => [],
    },
    errors: {
      type: Array,
      default: () => [],
    },
    serialOffset: {
      type: Number,
      default: 0,
    },
  },
  emits: ["row-click", "update:selectedUids"],
  template: `
    <div data-testid="record-table">
      记录表格 {{ records.length }}
      <button
        v-for="(record, index) in records"
        :key="record.__uid ?? index"
        type="button"
        :data-testid="'record-row-' + (record.__uid ?? index)"
        @click="$emit('row-click', record.__uid ?? index)"
      >
        {{ record.location_name }}
      </button>
    </div>
  `,
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
    year: {
      type: Number,
      default: null,
    },
    generation: {
      type: [String, null],
      default: null,
    },
  },
  emits: ["close", "import"],
  template: '<div data-testid="survey-import-dialog" :data-open="open ? \'yes\' : \'no\'" />',
});

const RecordDetailModalStub = defineComponent({
  name: "RecordDetailModal",
  props: {
    open: {
      type: Boolean,
      default: false,
    },
    record: {
      type: Object,
      default: null,
    },
  },
  emits: ["close", "update", "delete"],
  template: '<div data-testid="record-detail-modal" :data-open="open ? \'yes\' : \'no\'" />',
});

const ExcelImportDialogStub = defineComponent({
  name: "ExcelImportDialog",
  props: {
    open: {
      type: Boolean,
      default: false,
    },
  },
  emits: ["close"],
  template: '<div data-testid="excel-import-dialog" :data-open="open ? \'yes\' : \'no\'" />',
});

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/",
        component: { template: "<div />" },
        meta: {},
      },
      {
        path: "/workorder/point-screenshots",
        component: { template: "<div />" },
      },
    ],
  });
}

function mountWorkOrderView() {
  const router = createTestRouter();
  return mount(WorkOrderView, {
    global: {
      plugins: [router],
      stubs: {
        ExcelImportDialog: ExcelImportDialogStub,
        RecordDetailModal: RecordDetailModalStub,
        RecordTable: RecordTableStub,
        SurveyImportDialog: SurveyImportDialogStub,
        teleport: true,
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
    apiMocks.startWorkorderBatchJob.mockResolvedValue({
      job_id: "job-1",
      total: 3,
      status: "queued",
    });
    apiMocks.getWorkorderBatchJobStatus.mockResolvedValue({
      job_id: "job-1",
      status: "completed",
      current: 3,
      total: 3,
      percent: 100,
      phase: "completed",
      message: "导出完成，可下载",
      ready_for_download: true,
    });
    apiMocks.downloadWorkorderBatchJob.mockResolvedValue({
      blob: new Blob(["zip-content"]),
      filename: "批量导出_2份.zip",
    });
    apiMocks.uploadDateImageFolder.mockResolvedValue({
      folder_name: "2026-05-26",
      saved_count: 1,
      skipped_existing_count: 0,
      skipped_non_image_count: 0,
      skipped_nested_count: 0,
      files: [],
    });
    apiMocks.downloadBlob.mockResolvedValue({ delivery: "download" });
  });

  it("按设计结构渲染页头、任务配置、导入区与点位清单", () => {
    const wrapper = mountWorkOrderView();

    expect(wrapper.find(".page-title-row").exists()).toBe(false);
    expect(wrapper.find(".workspace-intro").exists()).toBe(false);
    expect(wrapper.text()).toContain("调查工单");
    expect(wrapper.text()).toContain("导入调查记录，检查点位信息并批量生成工单。");
    expect(wrapper.text()).toContain("从数据库追加");
    expect(wrapper.text()).toContain("任务配置");
    expect(wrapper.text()).toContain("导入调查数据");
    expect(wrapper.text()).toContain("Excel导入");
    expect(wrapper.text()).toContain("图片文件夹导入");
    expect(wrapper.text()).toContain("截图管理");
    expect(wrapper.text()).not.toContain("拖拽或选择调查 Excel");
    expect(wrapper.text()).toContain("点位清单");
    expect(wrapper.text()).toContain("共 0 个点位");
    expect(wrapper.text()).toContain("导出工作单");
    expect(wrapper.text()).not.toContain("占位功能三");
    expect(wrapper.find(".workorder-controls").exists()).toBe(true);
    expect(wrapper.find(".workorder-action-grid").exists()).toBe(false);
    expect(wrapper.find(".workorder-batch-bar").exists()).toBe(false);
    expect(wrapper.find('[data-testid="workorder-excel-dropzone"]').exists()).toBe(false);
    expect(wrapper.find(".workorder-list-card").exists()).toBe(true);
    expect(wrapper.get('[data-testid="record-table"]').text()).toContain("记录表格");
  });

  it("Excel 导入按钮会打开弹窗，截图管理入口可用", async () => {
    const wrapper = mountWorkOrderView();

    expect(wrapper.getComponent(ExcelImportDialogStub).props("open")).toBe(false);

    await wrapper.get('[data-testid="survey-excel-import-button"]').trigger("click");
    expect(wrapper.getComponent(ExcelImportDialogStub).props("open")).toBe(true);

    expect(wrapper.get('[data-testid="point-screenshot-entry"]').attributes("href"))
      .toBe("/workorder/point-screenshots");
  });

  it("日期图片文件夹按钮会触发文件夹选择", async () => {
    const wrapper = mountWorkOrderView();
    const input = wrapper.get('[data-testid="date-image-folder-input"]');
    const clickSpy = vi.spyOn(input.element, "click").mockImplementation(() => {});

    await wrapper.get('[data-testid="date-image-folder-button"]').trigger("click");

    expect(clickSpy).toHaveBeenCalledTimes(1);
  });

  it("选择有效日期图片文件夹后会上传到后端", async () => {
    const wrapper = mountWorkOrderView();
    const file = new File(["image"], "MQ001.jpg", { type: "image/jpeg" });
    Object.defineProperty(file, "webkitRelativePath", {
      value: "2026-05-26/MQ001.jpg",
      configurable: true,
    });
    const input = wrapper.get('[data-testid="date-image-folder-input"]');
    Object.defineProperty(input.element, "files", {
      value: [file],
      configurable: true,
    });

    await input.trigger("change");
    await flushPromises();

    expect(apiMocks.uploadDateImageFolder).toHaveBeenCalledWith({
      folderName: "2026-05-26",
      files: [file],
    });
    expect(apiMocks.success).toHaveBeenCalledWith(
      "已上传 1 张图片到 2026-05-26。",
      "日期文件夹已上传",
    );
  });

  it("选择非日期文件夹时会拦截并提示错误", async () => {
    const wrapper = mountWorkOrderView();
    const file = new File(["image"], "MQ001.jpg", { type: "image/jpeg" });
    Object.defineProperty(file, "webkitRelativePath", {
      value: "现场图片/MQ001.jpg",
      configurable: true,
    });
    const input = wrapper.get('[data-testid="date-image-folder-input"]');
    Object.defineProperty(input.element, "files", {
      value: [file],
      configurable: true,
    });

    await input.trigger("change");

    expect(apiMocks.uploadDateImageFolder).not.toHaveBeenCalled();
    expect(apiMocks.error).toHaveBeenCalledWith(
      "文件夹名称必须是 YYYY-MM-DD 格式的有效日期。",
      "日期文件夹上传失败",
    );
  });

  it("春尺蠖、国槐尺蠖、美国白蛾和其他害虫都显示调查导入入口", async () => {
    const wrapper = mountWorkOrderView();

    expect(wrapper.find('[data-testid="survey-import-button"]').exists()).toBe(true);
    expect(wrapper.find("#task-type").exists()).toBe(false);

    await wrapper.get("#pest-type").setValue("其他害虫");

    expect(wrapper.find('[data-testid="survey-import-button"]').exists()).toBe(true);
    expect(wrapper.get("#task-name").element.value).toBe("2026其他害虫防治");

    await wrapper.get("#pest-type").setValue("美国白蛾");

    expect(wrapper.find('[data-testid="survey-import-button"]').exists()).toBe(true);
    expect(wrapper.get("#task-name").element.value).toBe("2026美国白蛾第一代防治");

    await wrapper.get("#pest-type").setValue("国槐尺蠖");

    expect(wrapper.find('[data-testid="survey-import-button"]').exists()).toBe(true);
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

  it("追加数据库记录使用旧属地字段时仍显示到工单列表", async () => {
    const wrapper = mountWorkOrderView();

    await importRecords(wrapper, [
      {
        survey_date: "2026-04-01",
        town_or_street: "于家务乡",
        location_id: "YF0069",
        location_name: "神仙村",
        total_insect_count: 50,
        damage_level: "重",
        note: "",
        description: "描述1",
      },
    ]);

    const recordTable = wrapper.getComponent(RecordTableStub);
    expect(recordTable.props("records")).toHaveLength(1);
    expect(recordTable.props("records")[0].locality).toBe("于家务乡");
    expect(recordTable.props("records")[0].location_name).toBe("神仙村");
  });

  it("搜索只过滤当前已导入记录，并保留原始记录用于编辑", async () => {
    const wrapper = mountWorkOrderView();

    await importRecords(wrapper, [
      createValidRecord({ location_id: "YF0069", location_name: "神仙村" }),
      createValidRecord({ location_id: "HX0002", location_name: "林场二区" }),
    ]);
    const secondRecordUid = wrapper
      .getComponent(RecordTableStub)
      .props("records")
      .find((record) => record.location_id === "HX0002").__uid;

    await wrapper.get('[data-testid="workorder-search"]').setValue("林场");

    const recordTable = wrapper.getComponent(RecordTableStub);
    expect(recordTable.props("records")).toHaveLength(1);
    expect(recordTable.props("records")[0].location_id).toBe("HX0002");

    await wrapper.get(`[data-testid="record-row-${secondRecordUid}"]`).trigger("click");
    expect(wrapper.getComponent({ name: "RecordDetailModal" }).props("record").location_id).toBe(
      "HX0002",
    );
  });

  it("分段筛选已选记录时只展示被选中的原始记录", async () => {
    const wrapper = mountWorkOrderView();

    await importRecords(wrapper, [
      createValidRecord({ location_id: "YF0069", location_name: "神仙村" }),
      createValidRecord({ location_id: "HX0002", location_name: "林场二区" }),
    ]);
    const secondRecordUid = wrapper
      .getComponent(RecordTableStub)
      .props("records")
      .find((record) => record.location_id === "HX0002").__uid;

    wrapper.getComponent(RecordTableStub).vm.$emit("update:selectedUids", [secondRecordUid]);
    await wrapper.vm.$nextTick();
    await wrapper.get('[data-testid="workorder-filter-selected"]').trigger("click");

    const recordTable = wrapper.getComponent(RecordTableStub);
    expect(recordTable.props("records")).toHaveLength(1);
    expect(recordTable.props("records")[0].location_id).toBe("HX0002");
  });

  it("点位清单分页每页最多 10 条，可翻页并重置到第一页", async () => {
    const wrapper = mountWorkOrderView();
    const batch = Array.from({ length: 12 }, (_, index) =>
      createValidRecord({
        location_id: `PG${String(index + 1).padStart(4, "0")}`,
        location_name: `分页点位${index + 1}`,
      }),
    );
    await importRecords(wrapper, batch);

    const recordTable = wrapper.getComponent(RecordTableStub);
    expect(recordTable.props("records")).toHaveLength(10);
    expect(recordTable.props("records")[0].location_id).toBe("PG0001");
    expect(recordTable.props("serialOffset")).toBe(0);
    expect(wrapper.get('[data-testid="workorder-page-status"]').text()).toContain("第 1 / 2 页");
    expect(wrapper.get('[data-testid="workorder-page-prev"]').attributes("disabled")).toBeDefined();

    await wrapper.get('[data-testid="workorder-page-next"]').trigger("click");
    await wrapper.vm.$nextTick();

    expect(recordTable.props("records")).toHaveLength(2);
    expect(recordTable.props("records")[0].location_id).toBe("PG0011");
    expect(recordTable.props("serialOffset")).toBe(10);
    expect(wrapper.get('[data-testid="workorder-page-status"]').text()).toContain("第 2 / 2 页");
    expect(wrapper.get('[data-testid="workorder-page-next"]').attributes("disabled")).toBeDefined();

    await wrapper.get('[data-testid="workorder-search"]').setValue("分页点位1");
    await wrapper.vm.$nextTick();

    expect(wrapper.get('[data-testid="workorder-page-status"]').text()).toContain("第 1 /");
    expect(recordTable.props("records").length).toBeLessThanOrEqual(10);
    expect(recordTable.props("serialOffset")).toBe(0);
  });

  it("清单底部支持删除选中记录并清空选择", async () => {
    const wrapper = mountWorkOrderView();

    await importRecords(wrapper, [
      createValidRecord({ location_id: "YF0069", location_name: "神仙村" }),
      createValidRecord({ location_id: "HX0002", location_name: "林场二区" }),
    ]);
    const secondRecordUid = wrapper
      .getComponent(RecordTableStub)
      .props("records")
      .find((record) => record.location_id === "HX0002").__uid;

    wrapper.getComponent(RecordTableStub).vm.$emit("update:selectedUids", [secondRecordUid]);
    await wrapper.vm.$nextTick();

    expect(wrapper.find(".workorder-list-foot").exists()).toBe(true);
    expect(wrapper.text()).toContain("已选择 1 个点位");
    await findButtonByText(wrapper, "删除选中").trigger("click");
    await wrapper.get('[data-testid="confirm-dialog-confirm"]').trigger("click");

    const recordTable = wrapper.getComponent(RecordTableStub);
    expect(recordTable.props("records")).toHaveLength(1);
    expect(recordTable.props("records")[0].location_id).toBe("YF0069");
    expect(recordTable.props("selectedUids")).toEqual([]);
    expect(wrapper.text()).toContain("已选择 0 个点位");
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

    await findButtonByText(wrapper, "导出 1 份工作单").trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.generateWorkorder).toHaveBeenCalledTimes(1);
      expect(apiMocks.success).toHaveBeenCalledWith(
        expect.stringContaining("工作单"),
        "导出成功",
      );
    });

    expect(apiMocks.generateWorkorder).toHaveBeenCalledWith({
      pest_type: "其他害虫",
      task_type: "其他害虫防治",
      task: "2026其他害虫防治",
      year: 2026,
      generation: null,
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

    await findButtonByText(wrapper, "导出 1 份工作单").trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.generateWorkorder).toHaveBeenCalledTimes(1);
      expect(apiMocks.success).toHaveBeenCalledWith(
        expect.stringContaining("工作单"),
        "导出成功",
      );
    });

    expect(apiMocks.generateWorkorder).toHaveBeenCalledWith({
      pest_type: "国槐尺蠖",
      task_type: "国槐尺蠖防治",
      task: "2026国槐尺蠖第三代防治",
      year: 2026,
      generation: "第三代",
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

    await findButtonByText(wrapper, "导出 1 份工作单").trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.generateWorkorder).toHaveBeenCalledTimes(1);
      expect(apiMocks.success).toHaveBeenCalledWith(
        expect.stringContaining("工作单"),
        "导出成功",
      );
    });

    expect(apiMocks.generateWorkorder).toHaveBeenCalledWith({
      pest_type: "美国白蛾",
      task_type: "美国白蛾防治",
      task: "2026美国白蛾第一代防治",
      year: 2026,
      generation: "第一代",
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

    await wrapper.get('[data-testid="workorder-export-button"]').trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.generateWorkorder).toHaveBeenCalledTimes(1);
      expect(apiMocks.success).toHaveBeenCalledWith("工作单已开始下载。", "导出成功");
    });

    expect(apiMocks.generateWorkorder).toHaveBeenCalledWith({
      pest_type: "春尺蠖",
      task_type: "春尺蠖防治",
      task: "2026春尺蠖防治",
      year: 2026,
      generation: null,
      records: [
        expect.objectContaining({
          location_id: "YF0069",
          serial_number: 1,
        }),
      ],
    });
    expect(apiMocks.downloadBlob).toHaveBeenCalledTimes(1);
  });

  it("多条记录会批量导出为一个 zip，并显示批量导出成功提示", async () => {
    const wrapper = mountWorkOrderView();
    await importRecords(wrapper, [
      createValidRecord({ location_id: "YF0069" }),
      createValidRecord({ location_id: "YF0070", location_name: "中心林地" }),
    ]);

    expect(wrapper.get('[data-testid="workorder-export-button"]').text()).toContain(
      "导出 2 份工作单",
    );
    await wrapper.get('[data-testid="workorder-export-button"]').trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.startWorkorderBatchJob).toHaveBeenCalledTimes(1);
      expect(apiMocks.success).toHaveBeenCalledWith(
        "已批量导出 2 条记录的工作单包。",
        "导出成功",
      );
    });

    expect(apiMocks.startWorkorderBatchJob).toHaveBeenCalledWith({
      pest_type: "春尺蠖",
      task_type: "春尺蠖防治",
      task: "2026春尺蠖防治",
      year: 2026,
      generation: null,
      records: [
        expect.objectContaining({
          location_id: "YF0069",
          serial_number: 1,
        }),
        expect.objectContaining({
          location_id: "YF0070",
          serial_number: 2,
        }),
      ],
    });
    expect(apiMocks.getWorkorderBatchJobStatus).toHaveBeenCalledWith("job-1");
    expect(apiMocks.downloadWorkorderBatchJob).toHaveBeenCalledWith("job-1");
    expect(apiMocks.generateWorkorder).not.toHaveBeenCalled();
    expect(apiMocks.downloadBlob).toHaveBeenCalledWith(
      expect.any(Blob),
      "批量导出_2份.zip",
    );
  });

  it("批量导出过程中按后端真实进度更新进度条", async () => {
    apiMocks.getWorkorderBatchJobStatus
      .mockResolvedValueOnce({
        job_id: "job-1",
        status: "running",
        current: 1,
        total: 3,
        percent: 33,
        phase: "generating",
        message: "正在生成 1/2：神仙村",
        ready_for_download: false,
      })
      .mockResolvedValueOnce({
        job_id: "job-1",
        status: "completed",
        current: 3,
        total: 3,
        percent: 100,
        phase: "completed",
        message: "导出完成，可下载",
        ready_for_download: true,
      });

    const wrapper = mountWorkOrderView();
    await importRecords(wrapper, [
      createValidRecord({ location_id: "YF0069" }),
      createValidRecord({ location_id: "YF0070", location_name: "中心林地" }),
    ]);

    await wrapper.get('[data-testid="workorder-export-button"]').trigger("click");

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="workorder-export-progress"]').exists()).toBe(true);
      expect(wrapper.get('[data-testid="workorder-export-progress"]').text()).toContain(
        "正在生成 1/2：神仙村",
      );
      expect(wrapper.get('[data-testid="workorder-export-progress-percent"]').text()).toBe("33%");
    });

    await vi.waitFor(() => {
      expect(apiMocks.downloadWorkorderBatchJob).toHaveBeenCalledWith("job-1");
      expect(apiMocks.success).toHaveBeenCalledWith(
        "已批量导出 2 条记录的工作单包。",
        "导出成功",
      );
      expect(wrapper.find('[data-testid="workorder-export-progress"]').exists()).toBe(false);
    });
  });

  it("有选中时只导出选中记录", async () => {
    const wrapper = mountWorkOrderView();
    await importRecords(wrapper, [
      createValidRecord({ location_id: "YF0069" }),
      createValidRecord({ location_id: "YF0070", location_name: "中心林地" }),
    ]);
    const secondRecordUid = wrapper
      .getComponent(RecordTableStub)
      .props("records")
      .find((record) => record.location_id === "YF0070").__uid;

    wrapper.getComponent(RecordTableStub).vm.$emit("update:selectedUids", [secondRecordUid]);
    await wrapper.vm.$nextTick();

    expect(wrapper.get('[data-testid="workorder-export-button"]').text()).toContain(
      "导出 1 份工作单",
    );
    await wrapper.get('[data-testid="workorder-export-button"]').trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.generateWorkorder).toHaveBeenCalledTimes(1);
      expect(apiMocks.success).toHaveBeenCalledWith(
        expect.stringContaining("工作单"),
        "导出成功",
      );
    });

    expect(apiMocks.generateWorkorder).toHaveBeenCalledWith({
      pest_type: "春尺蠖",
      task_type: "春尺蠖防治",
      task: "2026春尺蠖防治",
      year: 2026,
      generation: null,
      records: [
        expect.objectContaining({
          location_id: "YF0070",
          serial_number: 1,
        }),
      ],
    });
    expect(apiMocks.generateWorkorderBatch).not.toHaveBeenCalled();
  });

  it("多条记录批量导出失败时展示批量导出失败提示", async () => {
    apiMocks.getWorkorderBatchJobStatus.mockResolvedValue({
      job_id: "job-1",
      status: "failed",
      current: 1,
      total: 3,
      percent: 33,
      phase: "failed",
      message: "导出失败",
      error: "网络异常",
      ready_for_download: false,
    });

    const wrapper = mountWorkOrderView();
    await importRecords(wrapper, [
      createValidRecord({ location_id: "YF0069" }),
      createValidRecord({ location_id: "YF0070", location_name: "中心林地" }),
    ]);
    apiMocks.success.mockClear();

    await wrapper.get('[data-testid="workorder-export-button"]').trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.error).toHaveBeenCalledWith(
        "批量导出失败：网络异常。若提示包含失败记录清单，可查看压缩包内“失败记录.json”。",
        "批量导出失败",
      );
    });

    expect(apiMocks.success).not.toHaveBeenCalled();
    expect(apiMocks.downloadWorkorderBatchJob).not.toHaveBeenCalled();
  });

  it("认证失效时批量导出中断", async () => {
    apiMocks.startWorkorderBatchJob.mockRejectedValueOnce(new UnauthorizedError());

    const wrapper = mountWorkOrderView();
    await importRecords(wrapper, [
      createValidRecord({ location_id: "YF0069" }),
      createValidRecord({ location_id: "YF0070", location_name: "中心林地" }),
    ]);
    apiMocks.success.mockClear();
    apiMocks.error.mockClear();
    apiMocks.downloadBlob.mockClear();

    await wrapper.get('[data-testid="workorder-export-button"]').trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.startWorkorderBatchJob).toHaveBeenCalledTimes(1);
      expect(wrapper.find('[data-testid="workorder-export-progress"]').exists()).toBe(false);
    });

    expect(apiMocks.downloadBlob).not.toHaveBeenCalled();
    expect(apiMocks.error).not.toHaveBeenCalled();
    expect(apiMocks.success).not.toHaveBeenCalled();
  });
});
