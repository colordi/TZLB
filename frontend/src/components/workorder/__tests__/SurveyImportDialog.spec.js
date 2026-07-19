import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import SurveyImportDialog from "../SurveyImportDialog.vue";

function buildResponse(payload, ok = true) {
  return {
    ok,
    async json() {
      return payload;
    },
  };
}

describe("SurveyImportDialog", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("查询后默认全选并导入全部结果", async () => {
    global.fetch.mockResolvedValue(
      buildResponse([
        {
          survey_date: "2026-04-01",
          locality: "于家务乡",
          location_id: "YF0069",
          location_name: "神仙村",
          total_insect_count: 50,
          damage_level: "重",
          note: "",
          description: "描述1",
        },
        {
          survey_date: "2026-04-01",
          locality: "于家务乡",
          location_id: "YF0070",
          location_name: "前南定村",
          total_insect_count: 18,
          damage_level: "中",
          note: "需复查",
          description: "描述2",
        },
      ]),
    );

    const wrapper = mount(SurveyImportDialog, {
      props: {
        open: true,
      },
      global: {
        stubs: {
          teleport: true,
        },
      },
    });

    wrapper.vm.selectedDate = "2026-04-01";
    await wrapper.vm.$nextTick();
    await wrapper.get('[data-testid="survey-query-button"]').trigger("click");
    await flushPromises();

    expect(global.fetch).toHaveBeenCalledWith(
      "/api/survey/candidates?date=2026-04-01&pest_type=%E6%98%A5%E5%B0%BA%E8%A0%96&year=2026",
      expect.objectContaining({
        credentials: "same-origin",
      }),
    );
    expect(wrapper.text()).toContain("共 2 条，已选 2 条");

    await wrapper.get('[data-testid="survey-import-confirm"]').trigger("click");

    const events = wrapper.emitted("import");
    expect(events).toBeTruthy();
    expect(events[0][0].records).toHaveLength(2);
    expect(events[0][0].records[1].location_id).toBe("YF0070");
    expect(events[0][0].task).toMatchObject({
      pestType: "春尺蠖",
    });
  });

  it("查询无结果时显示空状态并禁用导入", async () => {
    global.fetch.mockResolvedValue(buildResponse([]));

    const wrapper = mount(SurveyImportDialog, {
      props: {
        open: true,
      },
      global: {
        stubs: {
          teleport: true,
        },
      },
    });

    wrapper.vm.selectedDate = "2026-04-02";
    await wrapper.vm.$nextTick();
    await wrapper.get('[data-testid="survey-query-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("未找到记录");
    expect(wrapper.get('[data-testid="survey-import-confirm"]').attributes("disabled")).toBeDefined();
  });

  it("其他害虫查询时带上 pest_type 并展示其他害虫列头", async () => {
    global.fetch.mockResolvedValue(
      buildResponse([
        {
          survey_date: "2026-04-17",
          locality: "潞城镇",
          location_id: "QT0001",
          location_name: "畅和东路北京学校西侧",
          pest_name: "蚜虫",
          host_plant: "栾树",
          survey_result: "发现问题",
          plot_type: "道路绿化",
          description: "描述1",
          note: "",
          images: [],
        },
      ]),
    );

    const wrapper = mount(SurveyImportDialog, {
      props: {
        open: true,
      },
      global: {
        stubs: {
          teleport: true,
        },
      },
    });

    await wrapper.get('[data-testid="survey-import-pest-type"]').setValue("其他害虫");
    wrapper.vm.selectedDate = "2026-04-17";
    await wrapper.vm.$nextTick();
    await wrapper.get('[data-testid="survey-query-button"]').trigger("click");
    await flushPromises();

    expect(global.fetch).toHaveBeenCalledWith(
      "/api/survey/candidates?date=2026-04-17&pest_type=%E5%85%B6%E4%BB%96%E5%AE%B3%E8%99%AB&year=2026",
      expect.objectContaining({
        credentials: "same-origin",
      }),
    );
    expect(wrapper.text()).toContain("虫害类型");
    expect(wrapper.text()).toContain("寄主树种");
    expect(wrapper.text()).toContain("调查结论");
    expect(wrapper.text()).toContain("蚜虫");
    expect(wrapper.text()).toContain("栾树");
  });

  it("国槐尺蠖查询时带上 pest_type 并展示尺蠖幼虫列头", async () => {
    global.fetch.mockResolvedValue(
      buildResponse([
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
      ]),
    );

    const wrapper = mount(SurveyImportDialog, {
      props: {
        open: true,
      },
      global: {
        stubs: {
          teleport: true,
        },
      },
    });

    await wrapper.get('[data-testid="survey-import-pest-type"]').setValue("国槐尺蠖");
    wrapper.vm.selectedDate = "2026-05-02";
    await wrapper.vm.$nextTick();
    await wrapper.get('[data-testid="survey-query-button"]').trigger("click");
    await flushPromises();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/survey/candidates?date=2026-05-02&pest_type=%E5%9B%BD%E6%A7%90%E5%B0%BA%E8%A0%96&year=2026"),
      expect.objectContaining({
        credentials: "same-origin",
      }),
    );
    expect(wrapper.text()).toContain("国槐尺蠖受害点位");
    expect(wrapper.text()).toContain("总虫口数");
    expect(wrapper.text()).toContain("受害程度");
    expect(wrapper.text()).toContain("1001-1");
    expect(wrapper.text()).toContain("重");
  });

  it("美国白蛾查询时带上 pest_type 并展示美国白蛾列头", async () => {
    global.fetch.mockResolvedValue(
      buildResponse([
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
      ]),
    );

    const wrapper = mount(SurveyImportDialog, {
      props: {
        open: true,
      },
      global: {
        stubs: {
          teleport: true,
        },
      },
    });

    await wrapper.get('[data-testid="survey-import-pest-type"]').setValue("美国白蛾");
    wrapper.vm.selectedDate = "2026-05-26";
    await wrapper.vm.$nextTick();
    await wrapper.get('[data-testid="survey-query-button"]').trigger("click");
    await flushPromises();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/survey/candidates?date=2026-05-26&pest_type=%E7%BE%8E%E5%9B%BD%E7%99%BD%E8%9B%BE&year=2026"),
      expect.objectContaining({
        credentials: "same-origin",
      }),
    );
    expect(wrapper.text()).toContain("美国白蛾第一代问题点位");
    expect(wrapper.text()).toContain("绿地性质");
    expect(wrapper.text()).toContain("危害寄主");
    expect(wrapper.text()).toContain("受害株数");
    expect(wrapper.text()).toContain("网幕数量");
    expect(wrapper.text()).toContain("白蜡");
  });
});
