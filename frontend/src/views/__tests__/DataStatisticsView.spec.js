import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DataStatisticsView from "../DataStatisticsView.vue";

const apiMocks = vi.hoisted(() => ({
  fetchStatisticsYears: vi.fn(),
  getWhiteMothDailyStatistics: vi.fn(),
  getWhiteMothGenerationSummary: vi.fn(),
  getWhiteMothLocalitySummary: vi.fn(),
  getWhiteMothHostSummary: vi.fn(),
  getOtherPestSummary: vi.fn(),
  getYangshuShiyeSummary: vi.fn(),
  getAshBorerSummary: vi.fn(),
  getPoplarInchwormSummary: vi.fn(),
  getSophoraGenerationSummary: vi.fn(),
  getSophoraLocalitySummary: vi.fn(),
  error: vi.fn(),
}));

vi.mock("../../api/statistics.js", () => ({
  fetchStatisticsYears: apiMocks.fetchStatisticsYears,
  getWhiteMothDailyStatistics: apiMocks.getWhiteMothDailyStatistics,
  getWhiteMothGenerationSummary: apiMocks.getWhiteMothGenerationSummary,
  getWhiteMothLocalitySummary: apiMocks.getWhiteMothLocalitySummary,
  getWhiteMothHostSummary: apiMocks.getWhiteMothHostSummary,
  getOtherPestSummary: apiMocks.getOtherPestSummary,
  getYangshuShiyeSummary: apiMocks.getYangshuShiyeSummary,
  getAshBorerSummary: apiMocks.getAshBorerSummary,
  getPoplarInchwormSummary: apiMocks.getPoplarInchwormSummary,
  getSophoraGenerationSummary: apiMocks.getSophoraGenerationSummary,
  getSophoraLocalitySummary: apiMocks.getSophoraLocalitySummary,
}));

vi.mock("@/components/charts/BaseChart.vue", () => ({
  default: {
    name: "BaseChart",
    props: ["option", "height", "loading"],
    template: '<div data-testid="base-chart-stub" />',
  },
}));

vi.mock("../../composables/useToast.js", () => ({
  useToast: () => ({
    error: apiMocks.error,
  }),
}));

function buildPayload(rowCount = 2) {
  const rows = [];
  for (let index = 0; index < rowCount; index += 1) {
    const day = String(rowCount - index).padStart(2, "0");
    rows.push({
      date: `2026-06-${day}`,
      daily_treatment_plants: 100 + index,
      cumulative_completed_points: 50 + index,
      urban_daily_inspected_points: 10 + index,
      town_daily_inspected_points: 20 + index,
      daily_dispatch_points: index,
    });
  }
  return {
    columns: [
      { key: "date", label: "日期", type: "date" },
      { key: "daily_treatment_plants", label: "当日除治量（株）", type: "number" },
      { key: "cumulative_completed_points", label: "累积防治完成点数", type: "number" },
      { key: "urban_daily_inspected_points", label: "城区当日巡查点位数", type: "number" },
      { key: "town_daily_inspected_points", label: "乡镇当日巡查点位数", type: "number" },
      { key: "daily_dispatch_points", label: "当日派单数", type: "number" },
    ],
    rows,
  };
}

function buildGenerationSummary() {
  return {
    as_of_date: "2026-07-11",
    year: 2026,
    generations: [
      {
        generation: "第一代",
        start_date: "2026-05-01",
        end_date: "2026-06-20",
        surveyed_points: 44,
        urban_surveyed_points: 18,
        town_surveyed_points: 26,
        damaged_points: 17,
        urban_damaged_points: 7,
        town_damaged_points: 10,
        dispatch_count: 21,
        dispatch_frequency: [
          { dispatch_times: 1, point_count: 13 },
          { dispatch_times: 2, point_count: 4 },
        ],
      },
      {
        generation: "第二代",
        start_date: null,
        end_date: null,
        surveyed_points: 0,
        urban_surveyed_points: 0,
        town_surveyed_points: 0,
        damaged_points: 0,
        urban_damaged_points: 0,
        town_damaged_points: 0,
        dispatch_count: 0,
        dispatch_frequency: [],
      },
    ],
  };
}

function buildLocalitySummary() {
  return {
    year: 2026,
    generation: null,
    as_of_date: "2026-06-15",
    severe_plant_threshold: 10,
    totals: {
      damaged_points: 15,
      damaged_plants: 120,
      completed_points: 9,
      completion_rate: 60,
      severe_points: 4,
      collab_points: 2,
    },
    localities: [
      {
        locality: "宋庄镇",
        damaged_points: 5,
        damaged_plants: 40,
        completed_points: 3,
        completion_rate: 60,
        severe_points: 1,
        collab_points: 1,
        severe_sites: [{ code: "SZ001", name: "村口绿地", damaged_plants: 15 }],
      },
      {
        locality: "永顺镇",
        damaged_points: 0,
        damaged_plants: 0,
        completed_points: 0,
        completion_rate: 0,
        severe_points: 0,
        collab_points: 0,
        severe_sites: [],
      },
      {
        locality: "张家湾镇",
        damaged_points: 10,
        damaged_plants: 80,
        completed_points: 6,
        completion_rate: 60,
        severe_points: 2,
        collab_points: 1,
        severe_sites: [
          { code: "ZW001", name: "示范点", damaged_plants: 20 },
          { code: "ZW002", name: "公园", damaged_plants: 12 },
        ],
      },
    ],
  };
}

function buildHostSummary() {
  return {
    year: 2026,
    generation: null,
    totals: {
      host_species: 3,
      damaged_plants: 300,
      damaged_points: 12,
      top_host: { host: "法桐", plants: 180, points: 8, share: 0.6 },
    },
    hosts: [
      {
        host: "法桐",
        points: 8,
        plants: 180,
        share: 0.6,
        localities: [
          { locality: "宋庄镇", plants: 100 },
          { locality: "永顺镇", plants: 80 },
        ],
      },
      {
        host: "白蜡",
        points: 3,
        plants: 90,
        share: 0.3,
        localities: [{ locality: "宋庄镇", plants: 90 }],
      },
      {
        host: "桑",
        points: 1,
        plants: 30,
        share: 0.1,
        localities: [{ locality: "张家湾镇", plants: 30 }],
      },
    ],
  };
}

function buildHostCompare() {
  return {
    year: 2026,
    generation: null,
    generations: [
      {
        generation: "第一代",
        totals: {
          host_species: 2,
          damaged_plants: 100,
          damaged_points: 5,
          top_host: { host: "法桐", plants: 80, points: 4, share: 0.8 },
        },
        hosts: [
          { host: "法桐", points: 4, plants: 80, share: 0.8, localities: [] },
          { host: "桑", points: 1, plants: 20, share: 0.2, localities: [] },
        ],
      },
      {
        generation: "第二代",
        totals: {
          host_species: 3,
          damaged_plants: 200,
          damaged_points: 8,
          top_host: { host: "白蜡", plants: 90, points: 3, share: 0.45 },
        },
        hosts: [
          { host: "白蜡", points: 3, plants: 90, share: 0.45, localities: [] },
          { host: "法桐", points: 5, plants: 110, share: 0.55, localities: [] },
        ],
      },
    ],
  };
}

function buildOtherPestSummary() {
  return {
    year: 2026,
    totals: {
      survey_records: 36,
      surveyed_points: 35,
      problem_records: 18,
      no_problem_records: 18,
      problem_points: 17,
      problem_rate: 50.0,
      last_survey_date: "2026-07-27",
      ledger_points: 17,
      status_counts: [
        { status: "待防治", count: 12 },
        { status: "待复查", count: 5 },
      ],
    },
    pest_types: [
      {
        pest_type: "蚜虫",
        survey_records: 30,
        problem_records: 12,
        problem_points: 12,
        last_survey_date: "2026-07-27",
      },
      {
        pest_type: "草履蚧",
        survey_records: 5,
        problem_records: 5,
        problem_points: 4,
        last_survey_date: "2026-04-01",
      },
    ],
  };
}

function buildYangshuShiyeSummary() {
  return {
    year: 2026,
    totals: {
      survey_records: 20,
      surveyed_points: 18,
      problem_records: 6,
      no_problem_records: 14,
      problem_points: 5,
      problem_rate: 30.0,
      last_survey_date: "2026-08-01",
      ledger_points: 4,
      status_counts: [{ status: "待防治", count: 4 }],
    },
    pest_types: [
      {
        pest_type: "杨小舟蛾",
        survey_records: 12,
        problem_records: 5,
        problem_points: 4,
        last_survey_date: "2026-07-30",
      },
    ],
  };
}

function buildAshBorerSummary() {
  return {
    year: 2026,
    trees_per_point: 30,
    totals: {
      survey_records: 15,
      surveyed_points: 12,
      surveyed_trees: 360,
      excluded_points: 3,
      agrilus_damaged_plants: 30,
      agrilus_holes: 120,
      cossus_damaged_plants: 8,
      dead_plants: 5,
      felled_plants: 3,
      mortality_rate: 2.2,
      agrilus_infestation_rate: 8.3,
      cossus_infestation_rate: 2.2,
      agrilus_damage_levels: { none: 6, light: 4, medium: 1, high: 1 },
      cossus_damage_levels: { none: 2, light: 5, medium: 3, high: 2 },
      last_survey_date: "2026-08-05",
    },
    localities: [
      {
        locality: "宋庄镇",
        survey_records: 10,
        surveyed_points: 8,
        surveyed_trees: 240,
        excluded_points: 2,
        agrilus_damaged_plants: 20,
        cossus_damaged_plants: 6,
        dead_plants: 4,
        felled_plants: 2,
        mortality_rate: 2.5,
        agrilus_infestation_rate: 8.3,
        cossus_infestation_rate: 2.5,
        agrilus_damage_levels: { none: 4, light: 2, medium: 1, high: 1 },
        cossus_damage_levels: { none: 1, light: 3, medium: 2, high: 2 },
        last_survey_date: "2026-08-05",
      },
    ],
  };
}

function buildPoplarInchwormSummary() {
  return {
    year: 2026,
    adult: {
      survey_records: 40,
      surveyed_points: 36,
      avg_insect_count: 12.5,
      total_insect_count: 500,
      last_survey_date: "2026-04-10",
      damage_levels: [{ damage_level: "中度", count: 9 }],
    },
    larva: {
      survey_records: 25,
      surveyed_points: 24,
      avg_insect_count: 3.2,
      total_insect_count: 80,
      last_survey_date: "2026-05-15",
      damage_levels: [{ damage_level: "轻", count: 7 }],
    },
    ring_wrap: {
      survey_records: 30,
      surveyed_points: 30,
      repair_count: 6,
      adult_count: 88,
      last_survey_date: "2026-03-01",
    },
    ledger: {
      ledger_points: 5,
      status_counts: [
        { status: "已闭环", count: 3 },
        { status: "待防治", count: 2 },
      ],
    },
  };
}

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/data-statistics", redirect: "/data-statistics/white-moth" },
      {
        path: "/data-statistics/:pest",
        name: "data-statistics",
        component: DataStatisticsView,
      },
    ],
  });
}

async function mountView(path = "/data-statistics/white-moth") {
  const router = createTestRouter();
  router.push(path);
  await router.isReady();
  const wrapper = mount(DataStatisticsView, {
    global: { plugins: [router] },
  });
  return { wrapper, router };
}

describe("DataStatisticsView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // 年份选项来自实际数据年份接口：默认提供当前年与上一年，覆盖筛选交互
    const currentYear = new Date().getFullYear();
    apiMocks.fetchStatisticsYears.mockResolvedValue({
      "white-moth": [currentYear - 1, currentYear],
      "poplar-inchworm": [currentYear - 1, currentYear],
      "sophora-inchworm": [currentYear - 1, currentYear],
      "other-pests": [currentYear - 1, currentYear],
      "yangshu-shiye": [currentYear - 1, currentYear],
      "ash-borer": [currentYear - 1, currentYear],
    });
    apiMocks.getWhiteMothDailyStatistics.mockResolvedValue(buildPayload());
    apiMocks.getWhiteMothGenerationSummary.mockResolvedValue(buildGenerationSummary());
    apiMocks.getWhiteMothLocalitySummary.mockResolvedValue(buildLocalitySummary());
    apiMocks.getWhiteMothHostSummary.mockImplementation(({ byGeneration } = {}) =>
      Promise.resolve(byGeneration ? buildHostCompare() : buildHostSummary()),
    );
    apiMocks.getOtherPestSummary.mockResolvedValue(buildOtherPestSummary());
    apiMocks.getYangshuShiyeSummary.mockResolvedValue(buildYangshuShiyeSummary());
    apiMocks.getAshBorerSummary.mockResolvedValue(buildAshBorerSummary());
    apiMocks.getPoplarInchwormSummary.mockResolvedValue(buildPoplarInchwormSummary());
    apiMocks.getSophoraGenerationSummary.mockResolvedValue({
      as_of_date: "2026-08-12",
      year: 2026,
      generations: [
        {
          generation: "第一代",
          start_date: "2026-05-09",
          end_date: "2026-05-24",
          surveyed_points: 535,
          damaged_points: 70,
          damage_rate: 13.1,
          light_points: 26,
          medium_points: 16,
          severe_points: 28,
          avg_insect_count: 8.5,
          ledger_points: 60,
          pending_treatment: 4,
          pending_recheck: 45,
          recheck_abnormal: 10,
          closed_points: 1,
          closure_rate: 1.7,
        },
        {
          generation: "第二代",
          start_date: null,
          end_date: null,
          surveyed_points: 0,
          damaged_points: 0,
          damage_rate: null,
          light_points: 0,
          medium_points: 0,
          severe_points: 0,
          avg_insect_count: null,
          ledger_points: 0,
          pending_treatment: 0,
          pending_recheck: 0,
          recheck_abnormal: 0,
          closed_points: 0,
          closure_rate: null,
        },
        {
          generation: "第三代",
          start_date: "2026-08-10",
          end_date: "2026-08-11",
          surveyed_points: 107,
          damaged_points: 0,
          damage_rate: 0,
          light_points: 0,
          medium_points: 0,
          severe_points: 0,
          avg_insect_count: null,
          ledger_points: 0,
          pending_treatment: 0,
          pending_recheck: 0,
          recheck_abnormal: 0,
          closed_points: 0,
          closure_rate: null,
        },
      ],
    });
    apiMocks.getSophoraLocalitySummary.mockResolvedValue({
      year: 2026,
      generation: null,
      totals: {
        surveyed_points: 600,
        damaged_points: 70,
        damage_rate: 11.7,
        severe_points: 2,
        ledger_points: 60,
        closed_points: 1,
        closure_rate: 1.7,
      },
      localities: [
        {
          locality: "永乐店镇",
          monitor_points: 239,
          surveyed_points: 57,
          coverage_rate: 23.8,
          damaged_points: 30,
          light_points: 10,
          medium_points: 12,
          severe_points: 1,
          avg_insect_count: 9.5,
          ledger_points: 30,
          pending_treatment: 2,
          pending_recheck: 20,
          recheck_abnormal: 7,
          closed_points: 1,
          closure_rate: 3.3,
          severe_sites: [
            {
              code: "YL001",
              name: "示范村",
              avg_insect_count: 15,
              survey_date: "2026-05-12",
              ledger_status: "待复查",
            },
          ],
        },
      ],
    });
  });

  it("加载美国白蛾每日统计并展示表格", async () => {
    const { wrapper } = await mountView();
    await flushPromises();

    expect(apiMocks.getWhiteMothDailyStatistics).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain("美国白蛾每日信息统计");
    expect(wrapper.text()).toContain("2026-06-02");
    expect(wrapper.text()).toContain("2026-06-01");
    expect(wrapper.text()).toContain("当日除治量（株）");
    expect(wrapper.get('[data-testid="data-statistics-row-2026-06-01"]').text()).toContain(
      "101",
    );
  });

  it("展示各属地受害情况 KPI 与榜单", async () => {
    const { wrapper } = await mountView();
    await flushPromises();

    const today = new Date();
    const todayIso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
    expect(apiMocks.getWhiteMothLocalitySummary).toHaveBeenCalledWith({
      year: new Date().getFullYear(),
      generation: undefined,
      asOfDate: todayIso,
      severePlantThreshold: 10,
    });
    expect(wrapper.text()).toContain("各属地受害情况");
    expect(wrapper.get('[data-testid="data-statistics-locality-as-of-date"]').element.value).toBe(
      todayIso,
    );
    expect(
      wrapper.get('[data-testid="data-statistics-locality-severe-threshold"]').element.value,
    ).toBe("10");
    expect(wrapper.get('[data-testid="data-statistics-locality-kpi-damaged_points"]').text()).toContain(
      "15",
    );
    expect(wrapper.get('[data-testid="data-statistics-locality-kpi-completion_rate"]').text()).toContain(
      "60",
    );
    expect(wrapper.get('[data-testid="data-statistics-locality-row-张家湾镇"]').text()).toContain(
      "张家湾镇",
    );
    const severeText = wrapper.get('[data-testid="data-statistics-locality-severe-张家湾镇"]').text();
    expect(severeText).toContain("ZW001");
    expect(severeText).toContain("示范点");
    expect(severeText).toContain("ZW002");
    expect(wrapper.get('[data-testid="data-statistics-locality-rate-宋庄镇"]').text()).toContain(
      "60%",
    );
    // 固定 Excel 顺序：宋庄镇在张家湾镇之前
    const listText = wrapper.get('[data-testid="data-statistics-locality-list"]').text();
    expect(listText.indexOf("宋庄镇")).toBeLessThan(listText.indexOf("张家湾镇"));
  });

  it("按世代展示独立的调查、受害和派单汇总", async () => {
    const { wrapper } = await mountView();
    await flushPromises();

    expect(apiMocks.getWhiteMothGenerationSummary).toHaveBeenCalledWith({
      year: new Date().getFullYear(),
    });
    const summary = wrapper.get('[data-testid="data-statistics-summary-第一代"]').text();
    expect(summary).toContain("05-01 ~ 06-20");
    expect(summary).toContain("44");
    expect(summary).toContain("个点位完成调查");
    expect(summary).toContain("城区 18 · 乡镇 26");
    expect(summary).toContain("发现受害点位");
    expect(summary).toContain("17 个");
    expect(summary).toContain("城区 7 · 乡镇 10");
    expect(summary).toContain("共下发派单");
    expect(summary).toContain("21 次");
    expect(summary).toContain("1 次派单 13 个");
    expect(summary).toContain("2 次派单 4 个");
    expect(wrapper.get('[data-testid="data-statistics-summary-第二代"]').text()).toContain("暂无派单");
    expect(wrapper.get('[data-testid="data-statistics-summary-第二代"]').text()).toContain("暂无调查日期");
    expect(wrapper.get('[data-testid="data-statistics-summary-panel"]').text()).toContain(
      "各世代累计情况",
    );
    expect(wrapper.get('[data-testid="data-statistics-summary-panel"]').text()).not.toContain(
      "美国白蛾每日信息统计",
    );
    expect(wrapper.get('[data-testid="data-statistics-daily-panel"]').text()).not.toContain(
      "各世代累计情况",
    );
  });

  it("六个虫种统计入口均已启用", async () => {
    const { wrapper } = await mountView();
    await flushPromises();

    const pests = [
      "white-moth",
      "poplar-inchworm",
      "sophora-inchworm",
      "other-pests",
      "yangshu-shiye",
      "ash-borer",
    ];
    for (const pest of pests) {
      expect(
        wrapper.get(`[data-testid="data-statistics-pest-${pest}"]`).attributes("disabled"),
      ).toBeUndefined();
    }
  });

  it("春尺蠖统计展示成虫、幼虫、围环与台账汇总", async () => {
    const { wrapper } = await mountView("/data-statistics/poplar-inchworm");
    await flushPromises();

    expect(apiMocks.getPoplarInchwormSummary).toHaveBeenCalledWith({
      year: new Date().getFullYear(),
    });
    const adult = wrapper.get('[data-testid="data-statistics-poplar-inchworm-adult"]').text();
    expect(adult).toContain("40");
    expect(adult).toContain("12.5");
    expect(
      wrapper.get('[data-testid="data-statistics-poplar-inchworm-adult-levels"]').text(),
    ).toContain("中度 9");
    expect(
      wrapper.get('[data-testid="data-statistics-poplar-inchworm-larva"]').text(),
    ).toContain("25");
    const ring = wrapper.get('[data-testid="data-statistics-poplar-inchworm-ring"]').text();
    expect(ring).toContain("30");
    expect(ring).toContain("88");
    const ledger = wrapper.get('[data-testid="data-statistics-poplar-inchworm-ledger"]').text();
    expect(ledger).toContain("已闭环 3");
    expect(ledger).toContain("待防治 2");
  });

  it("杨树食叶害虫统计展示整体汇总与虫害类型计数", async () => {
    const { wrapper } = await mountView("/data-statistics/yangshu-shiye");
    await flushPromises();

    expect(apiMocks.getYangshuShiyeSummary).toHaveBeenCalledWith({
      year: new Date().getFullYear(),
    });
    expect(wrapper.get('[data-testid="data-statistics-yangshu-shiye-kpi-survey"]').text()).toContain(
      "20",
    );
    expect(wrapper.get('[data-testid="data-statistics-yangshu-shiye-kpi-rate"]').text()).toContain(
      "30.0%",
    );
    expect(
      wrapper.get('[data-testid="data-statistics-yangshu-shiye-kpi-ledger"]').text(),
    ).toContain("待防治 4");
    const row = wrapper.get('[data-testid="data-statistics-yangshu-shiye-row-杨小舟蛾"]').text();
    expect(row).toContain("杨小舟蛾");
    expect(row).toContain("12");
    expect(row).toContain("2026-07-30");
  });

  it("白蜡蛀干害虫统计展示率值合计与属地图表", async () => {
    const { wrapper } = await mountView("/data-statistics/ash-borer");
    await flushPromises();

    expect(apiMocks.getAshBorerSummary).toHaveBeenCalledWith({
      year: new Date().getFullYear(),
    });
    const survey = wrapper.get('[data-testid="data-statistics-ash-borer-kpi-survey"]').text();
    expect(survey).toContain("12");
    expect(survey).toContain("3");
    expect(wrapper.get('[data-testid="data-statistics-ash-borer-kpi-mortality"]').text()).toContain(
      "2.2%",
    );
    const agrilus = wrapper.get('[data-testid="data-statistics-ash-borer-kpi-agrilus"]').text();
    expect(agrilus).toContain("8.3%");
    expect(agrilus).toContain("120");
    expect(wrapper.get('[data-testid="data-statistics-ash-borer-kpi-cossus"]').text()).toContain(
      "2.2%",
    );
    expect(wrapper.get('[data-testid="data-statistics-ash-borer-locality-chart"]').text()).toContain(
      "各属地危害率对比",
    );
    expect(wrapper.get('[data-testid="data-statistics-ash-borer-mortality-ranking"]').exists()).toBe(
      true,
    );
    expect(wrapper.get('[data-testid="data-statistics-ash-borer-damage-overall"]').text()).toContain(
      "各虫种危害程度构成",
    );
    expect(wrapper.get('[data-testid="data-statistics-ash-borer-damage-agrilus"]').exists()).toBe(
      true,
    );
    expect(wrapper.get('[data-testid="data-statistics-ash-borer-damage-cossus"]').exists()).toBe(
      true,
    );
    expect(wrapper.find('[data-testid="data-statistics-ash-borer-row-宋庄镇"]').exists()).toBe(false);
  });

  it("国槐尺蠖统计展示世代汇总", async () => {
    const { wrapper } = await mountView("/data-statistics/sophora-inchworm");
    await flushPromises();

    expect(apiMocks.getSophoraGenerationSummary).toHaveBeenCalledWith({
      year: new Date().getFullYear(),
    });
    expect(wrapper.get('[data-testid="data-statistics-sophora-summary-panel"]').text()).toContain(
      "国槐尺蠖各世代累计情况",
    );
    const first = wrapper.get('[data-testid="data-statistics-sophora-summary-第一代"]').text();
    expect(first).toContain("535");
    expect(first).toContain("轻 / 中 / 重");
    expect(first).toContain("待防治");
    expect(wrapper.get('[data-testid="data-statistics-sophora-summary-第二代"]').text()).toContain(
      "暂无调查日期",
    );
  });

  it("其他害虫统计展示整体汇总与虫害类型计数", async () => {
    const { wrapper } = await mountView("/data-statistics/other-pests");
    await flushPromises();

    expect(apiMocks.getOtherPestSummary).toHaveBeenCalledWith({
      year: new Date().getFullYear(),
    });
    expect(wrapper.get('[data-testid="data-statistics-other-pest-totals"]').text()).toContain(
      "年整体情况",
    );
    expect(wrapper.get('[data-testid="data-statistics-other-pest-kpi-survey"]').text()).toContain(
      "36",
    );
    expect(wrapper.get('[data-testid="data-statistics-other-pest-kpi-rate"]').text()).toContain(
      "50.0%",
    );
    expect(wrapper.get('[data-testid="data-statistics-other-pest-kpi-ledger"]').text()).toContain(
      "待防治 12",
    );
    const aphidRow = wrapper.get('[data-testid="data-statistics-other-pest-row-蚜虫"]').text();
    expect(aphidRow).toContain("蚜虫");
    expect(aphidRow).toContain("30");
    expect(aphidRow).toContain("2026-07-27");
    expect(wrapper.get('[data-testid="data-statistics-other-pest-row-草履蚧"]').exists()).toBe(true);

    await wrapper
      .get('[data-testid="data-statistics-other-pest-year-filter"]')
      .setValue(String(new Date().getFullYear() - 1));
    await flushPromises();

    expect(apiMocks.getOtherPestSummary).toHaveBeenCalledTimes(2);
    expect(apiMocks.getOtherPestSummary).toHaveBeenLastCalledWith({
      year: new Date().getFullYear() - 1,
    });
  });

  it("非法虫种路径重定向到美国白蛾", async () => {
    const { wrapper, router } = await mountView("/data-statistics/not-a-pest");
    await flushPromises();

    expect(router.currentRoute.value.path).toBe("/data-statistics/white-moth");
    expect(wrapper.text()).toContain("美国白蛾每日信息统计");
  });

  it("没有统计数据时展示空状态", async () => {
    apiMocks.getWhiteMothDailyStatistics.mockResolvedValueOnce({
      columns: [{ key: "date", label: "日期", type: "date" }],
      rows: [],
    });

    const { wrapper } = await mountView();
    await flushPromises();

    expect(wrapper.text()).toContain("暂无美国白蛾每日统计数据。");
    expect(wrapper.findAll('[data-testid^="data-statistics-row-"]').length).toBe(0);
    expect(wrapper.find('[data-testid="data-statistics-next-page"]').exists()).toBe(false);
  });

  it("读取失败时展示错误提示", async () => {
    apiMocks.getWhiteMothDailyStatistics.mockRejectedValueOnce(new Error("连接失败"));

    await mountView();
    await flushPromises();

    expect(apiMocks.error).toHaveBeenCalledWith("连接失败", "读取数据统计失败");
  });

  it("美国白蛾统计页拆分为独立子 tab", async () => {
    const { wrapper } = await mountView();
    await flushPromises();

    expect(wrapper.get('[data-testid="data-statistics-white-moth-tab-generation"]').text()).toContain(
      "世代汇总",
    );
    expect(wrapper.get('[data-testid="data-statistics-white-moth-tab-locality"]').text()).toContain(
      "属地受害",
    );
    expect(wrapper.get('[data-testid="data-statistics-white-moth-tab-host"]').text()).toContain(
      "寄主分布",
    );
    expect(wrapper.get('[data-testid="data-statistics-white-moth-tab-daily"]').text()).toContain(
      "每日统计",
    );

    // 默认激活世代汇总 tab，点击后切换到每日统计
    expect(
      wrapper.get('[data-testid="data-statistics-white-moth-tab-generation"]').attributes(
        "data-state",
      ),
    ).toBe("active");
    await wrapper
      .get('[data-testid="data-statistics-white-moth-tab-daily"]')
      .trigger("mousedown", { button: 0 });
    await flushPromises();
    expect(
      wrapper.get('[data-testid="data-statistics-white-moth-tab-daily"]').attributes("data-state"),
    ).toBe("active");
  });

  it("每日统计 tab 的年份与世代筛选独立生效", async () => {
    const { wrapper } = await mountView();
    await flushPromises();

    expect(apiMocks.getWhiteMothDailyStatistics).toHaveBeenCalledTimes(1);
    expect(apiMocks.getWhiteMothDailyStatistics).toHaveBeenLastCalledWith({
      year: new Date().getFullYear(),
      generation: undefined,
    });

    await wrapper.get('[data-testid="data-statistics-daily-year-filter"]').setValue(
      String(new Date().getFullYear() - 1),
    );
    await flushPromises();

    expect(apiMocks.getWhiteMothDailyStatistics).toHaveBeenCalledTimes(2);
    expect(apiMocks.getWhiteMothDailyStatistics).toHaveBeenLastCalledWith({
      year: new Date().getFullYear() - 1,
      generation: undefined,
    });
    // 每日统计的筛选不影响其它板块
    expect(apiMocks.getWhiteMothGenerationSummary).toHaveBeenCalledTimes(1);
    expect(apiMocks.getWhiteMothLocalitySummary).toHaveBeenCalledTimes(1);

    await wrapper.get('[data-testid="data-statistics-generation-filter"]').setValue("第一代");
    await flushPromises();

    expect(apiMocks.getWhiteMothDailyStatistics).toHaveBeenCalledTimes(3);
    expect(apiMocks.getWhiteMothDailyStatistics).toHaveBeenLastCalledWith({
      year: new Date().getFullYear() - 1,
      generation: "第一代",
    });
    expect(apiMocks.getWhiteMothGenerationSummary).toHaveBeenCalledTimes(1);
    expect(apiMocks.getWhiteMothLocalitySummary).toHaveBeenCalledTimes(1);
  });

  it("属地受害 tab 的筛选器独立生效", async () => {
    const { wrapper } = await mountView();
    await flushPromises();

    const today = new Date();
    const todayIso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
    expect(apiMocks.getWhiteMothLocalitySummary).toHaveBeenCalledTimes(1);

    await wrapper.get('[data-testid="data-statistics-locality-year-filter"]').setValue(
      String(new Date().getFullYear() - 1),
    );
    await flushPromises();

    expect(apiMocks.getWhiteMothLocalitySummary).toHaveBeenCalledTimes(2);
    expect(apiMocks.getWhiteMothLocalitySummary).toHaveBeenLastCalledWith({
      year: new Date().getFullYear() - 1,
      generation: undefined,
      asOfDate: todayIso,
      severePlantThreshold: 10,
    });
    // 属地筛选不影响其它板块
    expect(apiMocks.getWhiteMothDailyStatistics).toHaveBeenCalledTimes(1);
    expect(apiMocks.getWhiteMothGenerationSummary).toHaveBeenCalledTimes(1);

    await wrapper.get('[data-testid="data-statistics-locality-generation-filter"]').setValue("第一代");
    await flushPromises();

    expect(apiMocks.getWhiteMothLocalitySummary).toHaveBeenCalledTimes(3);
    expect(apiMocks.getWhiteMothLocalitySummary).toHaveBeenLastCalledWith({
      year: new Date().getFullYear() - 1,
      generation: "第一代",
      asOfDate: todayIso,
      severePlantThreshold: 10,
    });

    await wrapper.get('[data-testid="data-statistics-locality-as-of-date"]').setValue("2026-06-01");
    await flushPromises();

    expect(apiMocks.getWhiteMothLocalitySummary).toHaveBeenCalledTimes(4);
    expect(apiMocks.getWhiteMothLocalitySummary).toHaveBeenLastCalledWith({
      year: new Date().getFullYear() - 1,
      generation: "第一代",
      asOfDate: "2026-06-01",
      severePlantThreshold: 10,
    });

    await wrapper.get('[data-testid="data-statistics-locality-severe-threshold"]').setValue("20");
    await wrapper.get('[data-testid="data-statistics-locality-severe-threshold"]').trigger("change");
    await flushPromises();

    expect(apiMocks.getWhiteMothLocalitySummary).toHaveBeenCalledTimes(5);
    expect(apiMocks.getWhiteMothLocalitySummary).toHaveBeenLastCalledWith({
      year: new Date().getFullYear() - 1,
      generation: "第一代",
      asOfDate: "2026-06-01",
      severePlantThreshold: 20,
    });
    // 调查截止日/阈值只影响属地汇总
    expect(apiMocks.getWhiteMothDailyStatistics).toHaveBeenCalledTimes(1);
    expect(apiMocks.getWhiteMothGenerationSummary).toHaveBeenCalledTimes(1);
  });

  it("世代汇总 tab 的年份筛选独立生效", async () => {
    const { wrapper } = await mountView();
    await flushPromises();

    expect(apiMocks.getWhiteMothGenerationSummary).toHaveBeenCalledTimes(1);
    expect(apiMocks.getWhiteMothGenerationSummary).toHaveBeenLastCalledWith({
      year: new Date().getFullYear(),
    });

    await wrapper.get('[data-testid="data-statistics-generation-year-filter"]').setValue(
      String(new Date().getFullYear() - 1),
    );
    await flushPromises();

    expect(apiMocks.getWhiteMothGenerationSummary).toHaveBeenCalledTimes(2);
    expect(apiMocks.getWhiteMothGenerationSummary).toHaveBeenLastCalledWith({
      year: new Date().getFullYear() - 1,
    });
    // 世代汇总的筛选不影响其它板块
    expect(apiMocks.getWhiteMothDailyStatistics).toHaveBeenCalledTimes(1);
    expect(apiMocks.getWhiteMothLocalitySummary).toHaveBeenCalledTimes(1);
  });

  it("寄主分布 tab 展示 KPI 与图表，筛选器独立生效", async () => {
    const { wrapper } = await mountView();
    await flushPromises();

    expect(apiMocks.getWhiteMothHostSummary).toHaveBeenCalledTimes(1);
    expect(apiMocks.getWhiteMothHostSummary).toHaveBeenLastCalledWith({
      year: new Date().getFullYear(),
      generation: undefined,
    });

    // KPI 卡片
    expect(wrapper.get('[data-testid="data-statistics-host-kpi-host_species"]').text()).toContain("3");
    expect(wrapper.get('[data-testid="data-statistics-host-kpi-damaged_plants"]').text()).toContain(
      "300",
    );
    expect(wrapper.get('[data-testid="data-statistics-host-kpi-damaged_points"]').text()).toContain(
      "12",
    );
    const topHostKpi = wrapper.get('[data-testid="data-statistics-host-kpi-top_host"]').text();
    expect(topHostKpi).toContain("法桐");
    expect(topHostKpi).toContain("60.0%");

    // 三张图表（BaseChart 已 stub）
    expect(wrapper.get('[data-testid="data-statistics-host-treemap-panel"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="data-statistics-host-ranking-panel"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="data-statistics-host-heatmap-panel"]').exists()).toBe(true);
    expect(wrapper.findAll('[data-testid="base-chart-stub"]').length).toBe(3);

    await wrapper.get('[data-testid="data-statistics-host-year-filter"]').setValue(
      String(new Date().getFullYear() - 1),
    );
    await flushPromises();

    expect(apiMocks.getWhiteMothHostSummary).toHaveBeenCalledTimes(2);
    expect(apiMocks.getWhiteMothHostSummary).toHaveBeenLastCalledWith({
      year: new Date().getFullYear() - 1,
      generation: undefined,
    });
    // 寄主分布的筛选不影响其它板块
    expect(apiMocks.getWhiteMothDailyStatistics).toHaveBeenCalledTimes(1);
    expect(apiMocks.getWhiteMothGenerationSummary).toHaveBeenCalledTimes(1);
    expect(apiMocks.getWhiteMothLocalitySummary).toHaveBeenCalledTimes(1);

    await wrapper.get('[data-testid="data-statistics-host-generation-filter"]').setValue("第二代");
    await flushPromises();

    expect(apiMocks.getWhiteMothHostSummary).toHaveBeenCalledTimes(3);
    expect(apiMocks.getWhiteMothHostSummary).toHaveBeenLastCalledWith({
      year: new Date().getFullYear() - 1,
      generation: "第二代",
    });
    expect(apiMocks.getWhiteMothDailyStatistics).toHaveBeenCalledTimes(1);
  });

  it("寄主分布分代对比视图：一次请求返回各世代并渲染对比内容", async () => {
    const { wrapper } = await mountView();
    await flushPromises();

    expect(apiMocks.getWhiteMothHostSummary).toHaveBeenCalledTimes(1);

    await wrapper
      .get('[data-testid="data-statistics-host-view-compare"]')
      .trigger("mousedown", { button: 0 });
    await flushPromises();

    // 切到对比模式后按 byGeneration 重新请求
    expect(apiMocks.getWhiteMothHostSummary).toHaveBeenCalledTimes(2);
    expect(apiMocks.getWhiteMothHostSummary).toHaveBeenLastCalledWith({
      year: new Date().getFullYear(),
      byGeneration: true,
    });

    // 世代下拉隐藏，对比内容渲染
    expect(wrapper.find('[data-testid="data-statistics-host-generation-filter"]').exists()).toBe(
      false,
    );
    const kpiTable = wrapper.get('[data-testid="data-statistics-host-compare-kpi"]').text();
    expect(kpiTable).toContain("第一代");
    expect(kpiTable).toContain("第二代");
    expect(kpiTable).toContain("100 株");
    expect(kpiTable).toContain("200 株");
    expect(
      wrapper.get('[data-testid="data-statistics-host-compare-top-第一代"]').text(),
    ).toContain("法桐（80.0%）");
    expect(
      wrapper.get('[data-testid="data-statistics-host-compare-top-第二代"]').text(),
    ).toContain("白蜡（45.0%）");
    expect(wrapper.findAll('[data-testid="base-chart-stub"]').length).toBe(2);

    // 年份筛选在对比模式下仍然生效
    await wrapper.get('[data-testid="data-statistics-host-year-filter"]').setValue(
      String(new Date().getFullYear() - 1),
    );
    await flushPromises();
    expect(apiMocks.getWhiteMothHostSummary).toHaveBeenLastCalledWith({
      year: new Date().getFullYear() - 1,
      byGeneration: true,
    });

    // 切回单代恢复原有请求与界面
    await wrapper
      .get('[data-testid="data-statistics-host-view-single"]')
      .trigger("mousedown", { button: 0 });
    await flushPromises();
    expect(apiMocks.getWhiteMothHostSummary).toHaveBeenLastCalledWith({
      year: new Date().getFullYear() - 1,
      generation: undefined,
    });
    expect(wrapper.find('[data-testid="data-statistics-host-generation-filter"]').exists()).toBe(
      true,
    );
    expect(wrapper.find('[data-testid="data-statistics-host-kpi"]').exists()).toBe(true);
  });

  it("超过 7 行时只显示第一页，并可通过翻页查看后续行", async () => {
    apiMocks.getWhiteMothDailyStatistics.mockResolvedValueOnce(buildPayload(9));

    const { wrapper } = await mountView();
    await flushPromises();

    expect(wrapper.findAll('[data-testid^="data-statistics-row-"]').length).toBe(7);
    expect(wrapper.text()).toContain("第 1–7 条，共 9 条");
    expect(wrapper.find('[data-testid="data-statistics-prev-page"]').attributes("disabled")).toBeDefined();

    await wrapper.get('[data-testid="data-statistics-next-page"]').trigger("click");
    await flushPromises();

    expect(wrapper.findAll('[data-testid^="data-statistics-row-"]').length).toBe(2);
    expect(wrapper.text()).toContain("第 8–9 条，共 9 条");
    expect(wrapper.find('[data-testid="data-statistics-next-page"]').attributes("disabled")).toBeDefined();

    await wrapper.get('[data-testid="data-statistics-prev-page"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("第 1–7 条，共 9 条");
  });
});
