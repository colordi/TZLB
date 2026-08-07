import { defineComponent, nextTick } from "vue";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MapView from "../MapView.vue";

const apiMocks = vi.hoisted(() => ({
  listMapViews: vi.fn(),
  fetchMapFilterOptions: vi.fn(),
  fetchWhiteMothSiteCodeRules: vi.fn(),
  fetchWhiteMothSiteCodeHint: vi.fn(),
  createWhiteMothSite: vi.fn(),
  fetchOtherPestSiteCodeRules: vi.fn(),
  fetchOtherPestSiteCodeHint: vi.fn(),
  createOtherPestSite: vi.fn(),
  deleteOtherPestSite: vi.fn(),
  deleteOtherPestSiteCheck: vi.fn(),
  deleteWhiteMothSite: vi.fn(),
  deleteWhiteMothSiteCheck: vi.fn(),
  fetchMapView: vi.fn(),
  fetchReferenceLayer: vi.fn(),
  listReferenceLayers: vi.fn(),
}));

vi.mock("../../api/map.js", () => ({
  listMapViews: apiMocks.listMapViews,
  fetchMapFilterOptions: apiMocks.fetchMapFilterOptions,
  fetchWhiteMothSiteCodeRules: apiMocks.fetchWhiteMothSiteCodeRules,
  fetchWhiteMothSiteCodeHint: apiMocks.fetchWhiteMothSiteCodeHint,
  createWhiteMothSite: apiMocks.createWhiteMothSite,
  fetchOtherPestSiteCodeRules: apiMocks.fetchOtherPestSiteCodeRules,
  fetchOtherPestSiteCodeHint: apiMocks.fetchOtherPestSiteCodeHint,
  createOtherPestSite: apiMocks.createOtherPestSite,
  deleteOtherPestSite: apiMocks.deleteOtherPestSite,
  deleteOtherPestSiteCheck: apiMocks.deleteOtherPestSiteCheck,
  deleteWhiteMothSite: apiMocks.deleteWhiteMothSite,
  deleteWhiteMothSiteCheck: apiMocks.deleteWhiteMothSiteCheck,
  fetchMapView: apiMocks.fetchMapView,
  fetchReferenceLayer: apiMocks.fetchReferenceLayer,
  listReferenceLayers: apiMocks.listReferenceLayers,
}));

const LeafletMapStub = defineComponent({
  name: "LeafletMap",
  props: {
    autoFitOnDataChange: {
      type: Boolean,
      default: true,
    },
    basemapMode: {
      type: String,
      default: "satellite",
    },
    geojson: {
      type: Object,
      default: () => ({
        type: "FeatureCollection",
        features: [],
      }),
    },
    popupFields: {
      type: Array,
      default: () => [],
    },
    referenceLayers: {
      type: Array,
      default: () => [],
    },
    showPointLabels: {
      type: Boolean,
      default: false,
    },
    viewName: {
      type: String,
      default: "",
    },
    views: {
      type: Array,
      default: () => [],
    },
    mapFocusRequest: {
      type: Object,
      default: null,
    },
    whiteMothSiteAddMode: {
      type: Boolean,
      default: false,
    },
    siteAddLabel: {
      type: String,
      default: "",
    },
  },
  emits: [
    "update:viewName",
    "update:basemapMode",
    "update:showPointLabels",
    "toggle-white-moth-site-add",
    "toggle-reference-layer",
    "feature-click",
    "map-click",
    "viewport-change",
  ],
  computed: {
    legendLabels() {
      const severityFields = new Set(["危害程度", "严重程度", "等级", "级别", "severity", "level"]);
      const hasSeverityField = this.popupFields.some((field) =>
        severityFields.has(`${field}`.trim().toLowerCase()),
      );
      return hasSeverityField ? ["无", "轻", "中", "重"] : ["危害点位"];
    },
  },
  template: `
    <div>
      <button
        v-if="siteAddLabel"
        type="button"
        data-testid="map-add-site-button"
        @click="$emit('toggle-white-moth-site-add')"
      >
        {{ whiteMothSiteAddMode ? '取消添加' : '添加点位' }}
      </button>
      <button
        type="button"
        data-testid="map-click-target"
        @click="$emit('map-click', { longitude: 116.5, latitude: 39.7 })"
      >
        模拟点选
      </button>
      <div class="map-integrated-panel">
        <div class="panel-header">
          <strong>{{ geojson.features.length }}</strong><span>个调查点位</span>
        </div>
        <div class="map-legend">
          <div v-for="label in legendLabels" :key="label" class="legend-item">
            {{ label }}
          </div>
        </div>
      </div>
    </div>
  `,
});

function createFeatureCollection(features) {
  return {
    type: "FeatureCollection",
    features,
  };
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

function mountMapView() {
  return mount(MapView, {
    global: {
      // reka-ui 弹窗经 Teleport 渲染，需让 teleport 桩内联渲染默认插槽内容
      renderStubDefaultSlot: true,
      stubs: {
        LeafletMap: LeafletMapStub,
        teleport: true,
      },
    },
  });
}

function getLeafletMapStub(wrapper) {
  return wrapper.getComponent(LeafletMapStub);
}

const DEFAULT_MAP_OPTIONS = {};

describe("MapView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "虫情总览",
        columns: ["属地", "村", "调查日期"],
      },
      {
        name: "高风险点位",
        columns: ["编号", "总虫口数"],
      },
    ]);
    apiMocks.fetchMapFilterOptions.mockImplementation(async (viewName) => {
      if (viewName === "高风险点位") {
        return {
          localities: [],
          supports_locality_filter: false,
          supports_survey_status_filter: false,
          filter_fields: [],
        };
      }

      return {
        localities: [],
        supports_locality_filter: false,
        supports_survey_status_filter: true,
        filter_fields: [
          {
            key: "调查状态",
            label: "调查状态",
            type: "select",
            options: [
              { value: "调查", label: "调查" },
              { value: "未调查", label: "未调查" },
            ],
            default_value: "",
          },
        ],
        survey_status_counts: {
          all: 327,
          completed: 256,
          pending: 71,
        },
      };
    });
    apiMocks.fetchMapView.mockResolvedValue({
      type: "FeatureCollection",
      features: [],
    });
    apiMocks.listReferenceLayers.mockResolvedValue([
      {
        name: "通州区行政区边界",
        label: "通州区行政区边界",
        columns: ["区域"],
        default_visible: true,
      },
      {
        name: "通州区小区边界",
        label: "通州区小区边界",
        columns: ["名称"],
        default_visible: false,
      },
    ]);
    apiMocks.fetchReferenceLayer.mockResolvedValue({
      type: "FeatureCollection",
      features: [],
    });
    apiMocks.fetchWhiteMothSiteCodeRules.mockResolvedValue({
      code_pattern: "^[A-Z]{2,3}\\d{3}$",
      code_example: "MQ001",
      prefix_localities: {
        MQ: "马驹桥镇",
        TH: "台湖镇",
        LY: "梨园镇",
        LYI: "潞邑街道",
        LYU: "潞源街道",
        JK: "九棵树街道",
      },
    });
    apiMocks.fetchWhiteMothSiteCodeHint.mockImplementation(async (prefix) => ({
      prefix: `${prefix}`.toUpperCase(),
      locality:
        {
          MQ: "马驹桥镇",
          TH: "台湖镇",
          LY: "梨园镇",
          LYI: "潞邑街道",
          LYU: "潞源街道",
          JK: "九棵树街道",
        }[`${prefix}`.toUpperCase()] || "",
      latest_code: `${`${prefix}`.toUpperCase()}042`,
      latest_serial: 42,
      suggested_next_code: `${`${prefix}`.toUpperCase()}043`,
    }));
    apiMocks.createWhiteMothSite.mockResolvedValue({
      gid: 14,
      code: "MQ001",
      locality: "马驹桥镇",
      site_name: "示范点",
      longitude: 116.5,
      latitude: 39.7,
    });
    apiMocks.fetchOtherPestSiteCodeRules.mockResolvedValue({
      code_pattern: "^QT\\d{4}$",
      code_example: "QT0001",
      code_prefix: "QT",
      localities: ["马驹桥镇", "台湖镇", "梨园镇", "潞邑街道", "潞源街道", "九棵树街道"],
    });
    apiMocks.fetchOtherPestSiteCodeHint.mockResolvedValue({
      prefix: "QT",
      latest_code: "QT0006",
      latest_serial: 6,
      suggested_next_code: "QT0007",
    });
    apiMocks.createOtherPestSite.mockResolvedValue({
      gid: 8,
      code: "QT0007",
      locality: "梨园镇",
      site_name: "",
      longitude: 116.5,
      latitude: 39.7,
    });
    apiMocks.deleteWhiteMothSiteCheck.mockResolvedValue({
      code: "MQ001",
      exists: true,
      site_name: "示范点",
      locality: "马驹桥镇",
      longitude: 116.5,
      latitude: 39.7,
      survey_record_count: 0,
    });
    apiMocks.deleteWhiteMothSite.mockResolvedValue({
      code: "MQ001",
      site_name: "示范点",
      locality: "马驹桥镇",
      longitude: 116.5,
      latitude: 39.7,
      survey_record_count: 0,
    });
    apiMocks.deleteOtherPestSiteCheck.mockResolvedValue({
      code: "QT0007",
      exists: true,
      site_name: "示范点",
      locality: "梨园镇",
      longitude: 116.5,
      latitude: 39.7,
      survey_record_count: 0,
    });
    apiMocks.deleteOtherPestSite.mockResolvedValue({
      code: "QT0007",
      site_name: "示范点",
      locality: "梨园镇",
      longitude: 116.5,
      latitude: 39.7,
      survey_record_count: 0,
    });
  });

  it("初始加载后把默认选中 view 的 columns 传给 LeafletMap", async () => {
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      const mapStub = getLeafletMapStub(wrapper);

      expect(mapStub.props("viewName")).toBe("虫情总览");
      expect(mapStub.props("popupFields")).toEqual(["属地", "村", "调查日期"]);
      expect(mapStub.props("basemapMode")).toBe("satellite");
      expect(mapStub.props("showPointLabels")).toBe(true);
    });
  });

  it("支持调查日期字段的 view 默认只展示筛选图标，展开后显示状态全量数量", async () => {
    apiMocks.fetchMapView.mockResolvedValue(
      createFeatureCollection([
        {
          type: "Feature",
          properties: { 编号: "MQ001", 调查日期: "2026-06-01" },
          geometry: { type: "Point", coordinates: [116.5, 39.7] },
        },
        {
          type: "Feature",
          properties: { 编号: "MQ002" },
          geometry: { type: "Point", coordinates: [116.6, 39.8] },
        },
      ]),
    );
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(wrapper.get('[data-testid="map-search-toggle"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="map-search-popover"]').exists()).toBe(false);
      expect(wrapper.find('[data-testid="map-search-input"]').exists()).toBe(false);
      expect(wrapper.get('[data-testid="map-survey-status-toggle"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="map-survey-status-filter"]').exists()).toBe(false);
      expect(wrapper.find('[data-testid="map-survey-status-count"]').exists()).toBe(false);
      expect(wrapper.text()).not.toContain("当前显示");
    });

    await wrapper.get('[data-testid="map-survey-status-toggle"]').trigger("click");

    await vi.waitFor(() => {
      const filterText = wrapper.get('[data-testid="map-survey-status-filter"]').text();

      expect(filterText).toContain("全部");
      expect(filterText).toContain("327");
      expect(filterText).toContain("已调查");
      expect(filterText).toContain("256");
      expect(filterText).toContain("未调查");
      expect(filterText).toContain("71");
      expect(wrapper.find('[data-testid="map-survey-status-count"]').exists()).toBe(false);
      expect(wrapper.find('[data-testid="map-search-popover"]').exists()).toBe(false);
      expect(wrapper.text()).not.toContain("当前显示");
    });
  });

  it("点击未调查后按调查状态筛选当前 view 且不自动缩放", async () => {
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(
        wrapper.get('[data-testid="map-survey-status-toggle"]').attributes("disabled"),
      ).toBeUndefined();
    });

    await wrapper.get('[data-testid="map-survey-status-toggle"]').trigger("click");
    await vi.waitFor(() => {
      expect(
        wrapper.get('[data-testid="map-survey-status-pending"]').attributes("disabled"),
      ).toBeUndefined();
    });

    apiMocks.fetchMapView.mockClear();
    apiMocks.fetchMapView.mockResolvedValueOnce(
      createFeatureCollection([
        {
          type: "Feature",
          properties: { 编号: "MQ002" },
          geometry: { type: "Point", coordinates: [116.6, 39.8] },
        },
      ]),
    );

    await wrapper.get('[data-testid="map-survey-status-pending"]').trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.fetchMapView).toHaveBeenCalledWith(
        "虫情总览",
        {
          调查状态: ["未调查"],
        },
        DEFAULT_MAP_OPTIONS,
      );
      expect(getLeafletMapStub(wrapper).props("autoFitOnDataChange")).toBe(false);
      expect(wrapper.find('[data-testid="map-survey-status-filter"]').exists()).toBe(false);
      expect(wrapper.get('[data-testid="map-survey-status-toggle"]').classes()).toContain(
        "is-active",
      );
    });

    await wrapper.get('[data-testid="map-survey-status-toggle"]').trigger("click");
    await vi.waitFor(() => {
      expect(wrapper.get('[data-testid="map-survey-status-pending"]').classes()).toContain(
        "is-active",
      );
    });
  });

  it("搜索面板展开后地图刷新不会禁用输入框", async () => {
    apiMocks.fetchMapView.mockResolvedValue(
      createFeatureCollection([
        {
          type: "Feature",
          properties: { 编号: "MQ001", 点位名称: "马驹桥点位" },
          geometry: { type: "Point", coordinates: [116.5, 39.7] },
        },
      ]),
    );
    const nextRequest = createDeferred();
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("geojson").features.length).toBeGreaterThan(0);
    });

    await wrapper.get('[data-testid="map-search-toggle"]').trigger("click");
    await vi.waitFor(() => {
      expect(
        wrapper.get('[data-testid="map-search-input"]').attributes("disabled"),
      ).toBeUndefined();
    });

    apiMocks.fetchMapView.mockImplementationOnce(() => nextRequest.promise);
    getLeafletMapStub(wrapper).vm.$emit("viewport-change", {
      bbox: [116.1, 39.5, 116.9, 40.1],
      zoom: 13,
    });
    await nextTick();

    expect(wrapper.get('[data-testid="map-search-input"]').attributes("disabled")).toBeUndefined();

    nextRequest.resolve(createFeatureCollection([]));
  });

  it("点击已调查后按调查状态筛选当前 view", async () => {
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(
        wrapper.get('[data-testid="map-survey-status-toggle"]').attributes("disabled"),
      ).toBeUndefined();
    });

    await wrapper.get('[data-testid="map-survey-status-toggle"]').trigger("click");
    await vi.waitFor(() => {
      expect(
        wrapper.get('[data-testid="map-survey-status-completed"]').attributes("disabled"),
      ).toBeUndefined();
    });

    apiMocks.fetchMapView.mockClear();
    apiMocks.fetchMapView.mockResolvedValueOnce(createFeatureCollection([]));

    await wrapper.get('[data-testid="map-survey-status-completed"]').trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.fetchMapView).toHaveBeenCalledWith(
        "虫情总览",
        {
          调查状态: ["调查"],
        },
        DEFAULT_MAP_OPTIONS,
      );
      expect(wrapper.find('[data-testid="map-survey-status-filter"]').exists()).toBe(false);
      expect(wrapper.get('[data-testid="map-survey-status-toggle"]').classes()).toContain(
        "is-active",
      );
    });
  });

  it("点击地图空白处会关闭搜索和调查状态筛选面板", async () => {
    apiMocks.fetchMapView.mockResolvedValue(
      createFeatureCollection([
        {
          type: "Feature",
          properties: { 编号: "TY001", 属地: "通运街道" },
          geometry: { type: "Point", coordinates: [116.6, 39.8] },
        },
      ]),
    );
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("geojson").features.length).toBeGreaterThan(0);
    });

    await wrapper.get('[data-testid="map-search-toggle"]').trigger("click");
    expect(wrapper.find('[data-testid="map-search-popover"]').exists()).toBe(true);

    getLeafletMapStub(wrapper).vm.$emit("map-click", {
      latitude: 39.8,
      longitude: 116.6,
    });
    await wrapper.vm.$nextTick();

    expect(wrapper.find('[data-testid="map-search-popover"]').exists()).toBe(false);

    await wrapper.get('[data-testid="map-survey-status-toggle"]').trigger("click");
    expect(wrapper.find('[data-testid="map-survey-status-filter"]').exists()).toBe(true);

    getLeafletMapStub(wrapper).vm.$emit("map-click", {
      latitude: 39.8,
      longitude: 116.6,
    });
    await wrapper.vm.$nextTick();

    expect(wrapper.find('[data-testid="map-survey-status-filter"]').exists()).toBe(false);
  });

  it("切换到不支持调查状态的 view 后隐藏筛选并重置为空筛选", async () => {
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="map-survey-status-toggle"]').exists()).toBe(true);
    });

    await wrapper.get('[data-testid="map-survey-status-toggle"]').trigger("click");
    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="map-survey-status-filter"]').exists()).toBe(true);
    });
    await wrapper.get('[data-testid="map-survey-status-pending"]').trigger("click");
    await vi.waitFor(() => {
      expect(apiMocks.fetchMapView).toHaveBeenCalledWith(
        "虫情总览",
        {
          调查状态: ["未调查"],
        },
        DEFAULT_MAP_OPTIONS,
      );
    });

    apiMocks.fetchMapView.mockClear();
    getLeafletMapStub(wrapper).vm.$emit("update:viewName", "高风险点位");
    await nextTick();

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="map-survey-status-filter"]').exists()).toBe(false);
      expect(wrapper.find('[data-testid="map-survey-status-toggle"]').exists()).toBe(false);
      expect(apiMocks.fetchMapView).toHaveBeenCalledWith(
        "高风险点位",
        {},
        DEFAULT_MAP_OPTIONS,
      );
    });
  });

  it("初始加载 reference 图层并响应图层开关", async () => {
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      const referenceLayers = getLeafletMapStub(wrapper).props("referenceLayers");

      expect(apiMocks.fetchReferenceLayer).toHaveBeenCalledWith(
        "通州区行政区边界",
        DEFAULT_MAP_OPTIONS,
      );
      expect(referenceLayers).toEqual(
        expect.arrayContaining([
          expect.objectContaining({
            name: "通州区行政区边界",
            active: true,
          }),
          expect.objectContaining({
            name: "通州区小区边界",
            active: false,
          }),
        ]),
      );
    });

    getLeafletMapStub(wrapper).vm.$emit("toggle-reference-layer", "通州区小区边界");

    await vi.waitFor(() => {
      expect(apiMocks.fetchReferenceLayer).toHaveBeenCalledWith(
        "通州区小区边界",
        DEFAULT_MAP_OPTIONS,
      );
      expect(
        getLeafletMapStub(wrapper)
          .props("referenceLayers")
          .find((layer) => layer.name === "通州区小区边界").active,
      ).toBe(true);
    });
  });

  it("地图视窗变化后不再重新请求数据", async () => {
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(apiMocks.fetchMapView).toHaveBeenCalled();
      expect(apiMocks.fetchReferenceLayer).toHaveBeenCalledWith(
        "通州区行政区边界",
        DEFAULT_MAP_OPTIONS,
      );
    });

    apiMocks.fetchMapView.mockClear();
    apiMocks.fetchReferenceLayer.mockClear();

    getLeafletMapStub(wrapper).vm.$emit("viewport-change", {
      bbox: [116.1, 39.5, 116.9, 40.1],
      zoom: 13,
    });
    await nextTick();

    expect(apiMocks.fetchMapView).not.toHaveBeenCalled();
    expect(apiMocks.fetchReferenceLayer).not.toHaveBeenCalled();
  });

  it("刷新页面后优先恢复浏览器记住的上次视图", async () => {
    window.localStorage.setItem("tzlb.map.selectedView", "高风险点位");

    const wrapper = mountMapView();

    await vi.waitFor(() => {
      const mapStub = getLeafletMapStub(wrapper);

      expect(mapStub.props("viewName")).toBe("高风险点位");
      expect(mapStub.props("popupFields")).toEqual(["编号", "总虫口数"]);
    });

    expect(apiMocks.fetchMapView).toHaveBeenCalledWith(
      "高风险点位",
      {},
      DEFAULT_MAP_OPTIONS,
    );
  });

  it("地图图层面板切换编号后更新传给 LeafletMap 的 showPointLabels", async () => {
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("showPointLabels")).toBe(true);
      expect(apiMocks.fetchMapView).toHaveBeenCalled();
    });

    getLeafletMapStub(wrapper).vm.$emit("update:showPointLabels", false);
    await nextTick();
    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("showPointLabels")).toBe(false);
    });

    getLeafletMapStub(wrapper).vm.$emit("update:showPointLabels", true);
    await nextTick();
    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("showPointLabels")).toBe(true);
    });
  });

  it("搜索当前视图点位后打开详情并通知地图聚焦", async () => {
    const targetFeature = {
      type: "Feature",
      properties: {
        编号: "MQ001",
        点位名称: "马大路与230国道交叉口",
        属地: "马驹桥镇",
      },
      geometry: { type: "Point", coordinates: [116.5, 39.7] },
    };
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "美国白蛾点位",
        columns: ["编号", "点位名称", "属地"],
      },
    ]);
    apiMocks.fetchMapView.mockResolvedValue(
      createFeatureCollection([
        targetFeature,
        {
          type: "Feature",
          properties: {
            编号: "TY002",
            点位名称: "京贸家园",
            属地: "通运街道",
          },
          geometry: { type: "Point", coordinates: [116.6, 39.8] },
        },
      ]),
    );

    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("geojson").features).toHaveLength(2);
    });

    await wrapper.get('[data-testid="map-search-toggle"]').trigger("click");
    await wrapper.get('[data-testid="map-search-input"]').setValue("马驹桥");

    await vi.waitFor(() => {
      const results = wrapper.get('[data-testid="map-search-results"]');
      expect(results.text()).toContain("马大路与230国道交叉口");
      expect(results.text()).toContain("MQ001 · 马驹桥镇");
    });

    await wrapper.get(".map-search-result").trigger("mousedown");

    expect(wrapper.get(".detail-drawer").text()).toContain("马大路与230国道交叉口");
    expect(getLeafletMapStub(wrapper).props("mapFocusRequest").feature).toStrictEqual(targetFeature);
  });

  it("搜索覆盖当前视图全部点位（含未加载到地图上的点位）", async () => {
    const offscreenFeature = {
      type: "Feature",
      properties: {
        编号: "TY002",
        总虫口数: 12,
      },
      geometry: { type: "Point", coordinates: [116.7, 39.9] },
    };
    // 地图加载带筛选参数（返回空）；搜索索引不带任何参数拉取全量点位
    apiMocks.fetchMapView.mockImplementation(async (viewName, filters, options) =>
      options === undefined
        ? createFeatureCollection([offscreenFeature])
        : createFeatureCollection([]),
    );

    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("viewName")).toBe("虫情总览");
    });
    expect(getLeafletMapStub(wrapper).props("geojson").features).toHaveLength(0);

    await wrapper.get('[data-testid="map-search-toggle"]').trigger("click");
    await wrapper.get('[data-testid="map-search-input"]').setValue("TY002");

    await vi.waitFor(() => {
      expect(wrapper.get('[data-testid="map-search-results"]').text()).toContain("TY002");
    });

    await wrapper.get(".map-search-result").trigger("mousedown");

    expect(getLeafletMapStub(wrapper).props("viewName")).toBe("虫情总览");
    expect(wrapper.get(".detail-drawer").text()).toContain("TY002");
    expect(getLeafletMapStub(wrapper).props("mapFocusRequest").feature).toStrictEqual(offscreenFeature);
  });

  it("点位详情打开后点击地图空白处会关闭详情", async () => {
    const targetFeature = {
      type: "Feature",
      properties: {
        编号: "TY001",
        点位名称: "通运家园",
        属地: "通运街道",
      },
      geometry: { type: "Point", coordinates: [116.6, 39.8] },
    };
    apiMocks.fetchMapView.mockResolvedValue(createFeatureCollection([targetFeature]));
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("geojson").features).toHaveLength(1);
    });

    getLeafletMapStub(wrapper).vm.$emit("feature-click", targetFeature);
    await wrapper.vm.$nextTick();

    expect(wrapper.get(".detail-drawer").text()).toContain("通运家园");

    getLeafletMapStub(wrapper).vm.$emit("map-click", {
      latitude: 39.8,
      longitude: 116.6,
    });
    await wrapper.vm.$nextTick();

    expect(wrapper.find(".detail-drawer").exists()).toBe(false);
  });

  it("切换 view 后更新传给 LeafletMap 的 popupFields", async () => {
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      const mapStub = getLeafletMapStub(wrapper);

      expect(mapStub.props("viewName")).toBe("虫情总览");
    });

    getLeafletMapStub(wrapper).vm.$emit("update:viewName", "高风险点位");
    await nextTick();

    await vi.waitFor(() => {
      const mapStub = getLeafletMapStub(wrapper);

      expect(mapStub.props("viewName")).toBe("高风险点位");
      expect(mapStub.props("popupFields")).toEqual(["编号", "总虫口数"]);
      expect(window.localStorage.getItem("tzlb.map.selectedView")).toBe("高风险点位");
    });
  });

  it("切换到新 view 后在新请求返回前立即清空传给 LeafletMap 的点位", async () => {
    const initialData = createFeatureCollection([
      {
        type: "Feature",
        properties: { 名称: "旧点位" },
        geometry: { type: "Point", coordinates: [108, 34] },
      },
    ]);
    const nextRequest = createDeferred();

    apiMocks.fetchMapView
      .mockResolvedValueOnce(initialData)
      .mockImplementationOnce(() => nextRequest.promise);

    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("geojson").features).toHaveLength(1);
    });

    getLeafletMapStub(wrapper).vm.$emit("update:viewName", "高风险点位");
    await nextTick();

    await vi.waitFor(() => {
      const mapStub = getLeafletMapStub(wrapper);

      expect(mapStub.props("viewName")).toBe("高风险点位");
      expect(mapStub.props("geojson").features).toEqual([]);
    });

    nextRequest.resolve(createFeatureCollection([]));
    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("geojson").features).toEqual([]);
    });
  });

  it("旧请求晚返回时不会覆盖当前 view 的结果", async () => {
    const firstRequest = createDeferred();
    const secondRequest = createDeferred();

    apiMocks.fetchMapView
      .mockImplementationOnce(() => firstRequest.promise)
      .mockImplementationOnce(() => secondRequest.promise);

    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(apiMocks.fetchMapView).toHaveBeenCalledTimes(1);
    });

    getLeafletMapStub(wrapper).vm.$emit("update:viewName", "高风险点位");
    await nextTick();

    secondRequest.resolve(
      createFeatureCollection([
        {
          type: "Feature",
          properties: { 名称: "新点位" },
          geometry: { type: "Point", coordinates: [109, 35] },
        },
      ]),
    );
    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("geojson").features).toHaveLength(1);
      expect(getLeafletMapStub(wrapper).props("geojson").features[0].properties.名称).toBe(
        "新点位",
      );
    });

    firstRequest.resolve(
      createFeatureCollection([
        {
          type: "Feature",
          properties: { 名称: "旧点位" },
          geometry: { type: "Point", coordinates: [108, 34] },
        },
      ]),
    );

    await vi.waitFor(() => {
      const mapStub = getLeafletMapStub(wrapper);

      expect(mapStub.props("viewName")).toBe("高风险点位");
      expect(mapStub.props("geojson").features).toHaveLength(1);
      expect(mapStub.props("geojson").features[0].properties.名称).toBe("新点位");
    });
  });

  it("不展示热力或聚合模式入口", async () => {
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(apiMocks.fetchMapView).toHaveBeenCalled();
    });

    expect(wrapper.find(".page-title-row").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("热力");
    expect(wrapper.text()).not.toContain("聚合");
  });

  it("不再渲染移动端底部操作栏", async () => {
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(apiMocks.fetchMapView).toHaveBeenCalled();
    });

    expect(wrapper.find(".map-mobile-bar").exists()).toBe(false);
  });

  it("不再渲染右下角当前视图提示框", async () => {
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(apiMocks.fetchMapView).toHaveBeenCalled();
    });

    expect(wrapper.find(".map-stage-note").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("当前视图：");
  });

  it("地图页移除标题栏，并且仅保留图例配置", async () => {
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "国槐尺蠖幼虫历年发生情况",
        columns: ["编号", "属地", "危害程度"],
      },
    ]);
    apiMocks.fetchMapView.mockResolvedValue(
      createFeatureCollection([
        {
          type: "Feature",
          properties: { 总虫口数: 0 },
          geometry: { type: "Point", coordinates: [108, 34] },
        },
        {
          type: "Feature",
          properties: { 总虫口数: 50 },
          geometry: { type: "Point", coordinates: [109, 34] },
        },
        {
          type: "Feature",
          properties: { 总虫口数: 120 },
          geometry: { type: "Point", coordinates: [110, 34] },
        },
        {
          type: "Feature",
          properties: { 总虫口数: 800 },
          geometry: { type: "Point", coordinates: [111, 34] },
        },
      ]),
    );
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(apiMocks.fetchMapView).toHaveBeenCalled();
    });

    const legendText = wrapper.get(".map-legend").text();

    expect(wrapper.text()).not.toContain("调查点位分布");
    expect(wrapper.text()).not.toContain("可用视图");
    expect(wrapper.text()).not.toContain("点位总数");
    expect(wrapper.text()).not.toContain("已完成调查");
    expect(wrapper.text()).not.toContain("待调查");
    expect(wrapper.findAll(".legend-item")).toHaveLength(4);
    expect(legendText).toContain("无");
    expect(legendText).toContain("轻");
    expect(legendText).toContain("中");
    expect(legendText).toContain("重");
    expect(legendText).not.toContain("白");
    expect(legendText).not.toContain("危害程度");
    expect(legendText).not.toContain("<100");
    expect(legendText).not.toContain("100-500");
    expect(legendText).not.toContain(">500");
    expect(legendText).not.toContain("个点位");
  });

  it("无危害程度字段的 view 仅显示危害点位图例", async () => {
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(apiMocks.fetchMapView).toHaveBeenCalled();
    });

    const legendText = wrapper.get(".map-legend").text();

    expect(wrapper.findAll(".legend-item")).toHaveLength(1);
    expect(legendText).toContain("危害点位");
    expect(legendText).not.toContain("无");
    expect(legendText).not.toContain("轻");
    expect(legendText).not.toContain("中");
    expect(legendText).not.toContain("重");
  });

  it("新增美国白蛾点位时格式化编号并显示自动识别属地", async () => {
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "美国白蛾点位",
        columns: ["gid", "编号", "属地", "点位名称"],
      },
    ]);
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("viewName")).toBe("美国白蛾点位");
      expect(apiMocks.fetchWhiteMothSiteCodeRules).toHaveBeenCalled();
    });

    await wrapper.get('[data-testid="map-add-site-button"]').trigger("click");
    await wrapper.get('[data-testid="map-click-target"]').trigger("click");
    await wrapper.get('[data-testid="white-moth-site-code"]').setValue("mq001");

    expect(wrapper.get('[data-testid="white-moth-site-code"]').element.value).toBe("MQ001");
    expect(wrapper.get('[data-testid="white-moth-site-locality"]').text()).toBe("马驹桥镇");

    await wrapper.get('[data-testid="site-add-name"]').setValue("示范点");
    await wrapper.get(".site-add-form").trigger("submit");

    await vi.waitFor(() => {
      expect(apiMocks.createWhiteMothSite).toHaveBeenCalledWith({
        code: "MQ001",
        site_name: "示范点",
        longitude: 116.5,
        latitude: 39.7,
      });
    });
  });

  it("进入新增点位模式后先保留地图可选点，点选后再显示录入表单", async () => {
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "美国白蛾点位",
        columns: ["gid", "编号", "属地", "点位名称"],
      },
    ]);
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("viewName")).toBe("美国白蛾点位");
      expect(apiMocks.fetchWhiteMothSiteCodeRules).toHaveBeenCalled();
    });

    await wrapper.get('[data-testid="map-add-site-button"]').trigger("click");

    expect(getLeafletMapStub(wrapper).props("whiteMothSiteAddMode")).toBe(true);
    expect(wrapper.find('[data-testid="white-moth-site-code"]').exists()).toBe(false);

    await wrapper.get('[data-testid="map-click-target"]').trigger("click");

    expect(wrapper.get('[data-testid="white-moth-site-code"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="site-add-location-text"]').text()).toContain(
      "116.500000",
    );
  });

  it("编号前缀不支持时阻止新增美国白蛾点位", async () => {
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "美国白蛾点位",
        columns: ["gid", "编号", "属地", "点位名称"],
      },
    ]);
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("viewName")).toBe("美国白蛾点位");
      expect(apiMocks.fetchWhiteMothSiteCodeRules).toHaveBeenCalled();
    });

    await wrapper.get('[data-testid="map-add-site-button"]').trigger("click");
    await wrapper.get('[data-testid="map-click-target"]').trigger("click");
    await wrapper.get('[data-testid="white-moth-site-code"]').setValue("ab001");

    expect(wrapper.get('[data-testid="white-moth-site-code-error"]').text()).toContain(
      "编号格式不正确",
    );
    expect(wrapper.get('[data-testid="site-add-submit"]').attributes("disabled")).toBe(
      "",
    );
    await wrapper.get(".site-add-form").trigger("submit");
    expect(apiMocks.createWhiteMothSite).not.toHaveBeenCalled();
  });

  it("三位编号前缀能正确识别属地且不与两位前缀混淆", async () => {
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "美国白蛾点位",
        columns: ["gid", "编号", "属地", "点位名称"],
      },
    ]);
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("viewName")).toBe("美国白蛾点位");
      expect(apiMocks.fetchWhiteMothSiteCodeRules).toHaveBeenCalled();
    });

    await wrapper.get('[data-testid="map-add-site-button"]').trigger("click");
    await wrapper.get('[data-testid="map-click-target"]').trigger("click");

    await wrapper.get('[data-testid="white-moth-site-code"]').setValue("lyi001");
    expect(wrapper.get('[data-testid="white-moth-site-code"]').element.value).toBe("LYI001");
    expect(wrapper.get('[data-testid="white-moth-site-locality"]').text()).toBe("潞邑街道");

    await wrapper.get('[data-testid="white-moth-site-code"]').setValue("ly001");
    expect(wrapper.get('[data-testid="white-moth-site-locality"]').text()).toBe("梨园镇");

    await wrapper.get('[data-testid="white-moth-site-code"]').setValue("jk001");
    expect(wrapper.get('[data-testid="white-moth-site-locality"]').text()).toBe("九棵树街道");
  });

  it("仅输入前缀即可识别属地并展示最新编号提示", async () => {
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "美国白蛾点位",
        columns: ["gid", "编号", "属地", "点位名称"],
      },
    ]);
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("viewName")).toBe("美国白蛾点位");
      expect(apiMocks.fetchWhiteMothSiteCodeRules).toHaveBeenCalled();
    });

    await wrapper.get('[data-testid="map-add-site-button"]').trigger("click");
    await wrapper.get('[data-testid="map-click-target"]').trigger("click");
    await wrapper.get('[data-testid="white-moth-site-code"]').setValue("mq");

    expect(wrapper.get('[data-testid="white-moth-site-locality"]').text()).toBe("马驹桥镇");
    await vi.waitFor(() => {
      expect(apiMocks.fetchWhiteMothSiteCodeHint).toHaveBeenCalledWith("MQ");
    });
    await vi.waitFor(() => {
      expect(wrapper.get('[data-testid="white-moth-site-code-hint-text"]').text()).toContain(
        "MQ042",
      );
      expect(wrapper.get('[data-testid="white-moth-site-code-hint-text"]').text()).toContain(
        "MQ043",
      );
    });
    expect(wrapper.get('[data-testid="site-add-submit"]').attributes("disabled")).toBe(
      "",
    );

    await wrapper.get('[data-testid="white-moth-site-fill-suggested-code"]').trigger("click");
    expect(wrapper.get('[data-testid="white-moth-site-code"]').element.value).toBe("MQ043");
    expect(wrapper.get('[data-testid="site-add-submit"]').attributes("disabled")).toBeUndefined();
  });

  it("非目标图层下不开放添加点位", async () => {
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("viewName")).toBe("虫情总览");
    });

    // 按钮不渲染；即使触发切换事件也不会进入添加模式
    expect(getLeafletMapStub(wrapper).props("siteAddLabel")).toBe("");
    expect(wrapper.find('[data-testid="map-add-site-button"]').exists()).toBe(false);

    getLeafletMapStub(wrapper).vm.$emit("toggle-white-moth-site-add");
    await wrapper.vm.$nextTick();

    expect(getLeafletMapStub(wrapper).props("whiteMothSiteAddMode")).toBe(false);
    expect(wrapper.find(".site-add-drawer").exists()).toBe(false);
    expect(apiMocks.createWhiteMothSite).not.toHaveBeenCalled();
    expect(apiMocks.createOtherPestSite).not.toHaveBeenCalled();
  });

  it("其他害虫点位图层下新增其他害虫点位", async () => {
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "其他害虫点位",
        columns: ["编号", "属地", "点位名称", "害虫类型", "调查日期", "年份"],
      },
    ]);
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("viewName")).toBe("其他害虫点位");
      expect(apiMocks.fetchOtherPestSiteCodeRules).toHaveBeenCalled();
    });
    expect(getLeafletMapStub(wrapper).props("siteAddLabel")).toBe("添加其他害虫点位");

    await wrapper.get('[data-testid="map-add-site-button"]').trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.fetchOtherPestSiteCodeHint).toHaveBeenCalled();
    });

    await wrapper.get('[data-testid="map-click-target"]').trigger("click");

    // 其他害虫分支渲染：QT 编号 + 属地下拉，不渲染美国白蛾的自动识别属地
    expect(wrapper.find('[data-testid="other-pest-site-code"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="white-moth-site-code"]').exists()).toBe(false);

    await wrapper.get('[data-testid="other-pest-site-code"]').setValue("qt0007");
    expect(wrapper.get('[data-testid="other-pest-site-code"]').element.value).toBe("QT0007");

    await vi.waitFor(() => {
      expect(
        wrapper.get('[data-testid="other-pest-site-code-hint-text"]').text(),
      ).toContain("QT0007");
    });

    // 未选属地时禁止提交
    expect(wrapper.get('[data-testid="site-add-submit"]').attributes("disabled")).toBe(
      "",
    );

    await wrapper
      .get('[data-testid="other-pest-site-locality-select"]')
      .setValue("梨园镇");
    expect(
      wrapper.get('[data-testid="site-add-submit"]').attributes("disabled"),
    ).toBeUndefined();

    await wrapper.get(".site-add-form").trigger("submit");

    await vi.waitFor(() => {
      expect(apiMocks.createOtherPestSite).toHaveBeenCalledWith({
        code: "QT0007",
        site_name: "",
        locality: "梨园镇",
        longitude: 116.5,
        latitude: 39.7,
      });
    });
    expect(apiMocks.createWhiteMothSite).not.toHaveBeenCalled();
    // 保存后停留在当前视图并重载数据
    expect(getLeafletMapStub(wrapper).props("viewName")).toBe("其他害虫点位");
  });

  it("其他害虫编号格式不正确时阻止提交", async () => {
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "其他害虫点位",
        columns: ["编号", "属地", "点位名称", "害虫类型", "调查日期", "年份"],
      },
    ]);
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("viewName")).toBe("其他害虫点位");
    });

    await wrapper.get('[data-testid="map-add-site-button"]').trigger("click");
    await wrapper.get('[data-testid="map-click-target"]').trigger("click");
    await wrapper.get('[data-testid="other-pest-site-code"]').setValue("mq001");
    await wrapper
      .get('[data-testid="other-pest-site-locality-select"]')
      .setValue("梨园镇");

    expect(wrapper.get('[data-testid="other-pest-site-code-error"]').text()).toContain(
      "编号格式不正确",
    );
    expect(wrapper.get('[data-testid="site-add-submit"]').attributes("disabled")).toBe(
      "",
    );
    await wrapper.get(".site-add-form").trigger("submit");
    expect(apiMocks.createOtherPestSite).not.toHaveBeenCalled();
  });

  it("已经在美国白蛾点位视图时保存点位不会触发自动缩放", async () => {
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "美国白蛾点位",
        columns: ["gid", "编号", "属地", "点位名称"],
      },
    ]);

    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("viewName")).toBe("美国白蛾点位");
    });

    await wrapper.get('[data-testid="map-add-site-button"]').trigger("click");
    await wrapper.get('[data-testid="map-click-target"]').trigger("click");
    await wrapper.get('[data-testid="white-moth-site-code"]').setValue("MQ001");
    await wrapper.get(".site-add-form").trigger("submit");

    await vi.waitFor(() => {
      expect(apiMocks.createWhiteMothSite).toHaveBeenCalled();
      expect(getLeafletMapStub(wrapper).props("autoFitOnDataChange")).toBe(false);
    });
  });

  it("切换到配了默认筛选的 view 后按默认筛选请求初始数据", async () => {
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "美国白蛾调查",
        columns: ["编号", "属地", "调查日期", "年份", "世代"],
        default_filters: { 世代: "第二代" },
      },
    ]);
    apiMocks.fetchMapFilterOptions.mockResolvedValue({
      localities: [],
      supports_locality_filter: true,
      supports_survey_status_filter: true,
      filter_fields: [
        {
          key: "调查状态",
          label: "调查状态",
          type: "select",
          options: [
            { value: "调查", label: "调查" },
            { value: "未调查", label: "未调查" },
          ],
          default_value: "",
        },
        {
          key: "世代",
          label: "世代",
          type: "select",
          options: [
            { value: "第一代", label: "第一代" },
            { value: "第二代", label: "第二代" },
            { value: "第三代", label: "第三代" },
          ],
          default_value: "",
        },
      ],
      survey_status_counts: { all: 100, completed: 50, pending: 50 },
    });
    apiMocks.fetchMapView.mockResolvedValue(createFeatureCollection([]));

    mountMapView();

    await vi.waitFor(() => {
      expect(apiMocks.fetchMapView).toHaveBeenCalledWith(
        "美国白蛾调查",
        { 世代: ["第二代"] },
        DEFAULT_MAP_OPTIONS,
      );
    });
  });

  it("默认筛选值不在当前选项中时忽略该项", async () => {
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "美国白蛾调查",
        columns: ["编号", "属地", "调查日期", "年份", "世代"],
        default_filters: { 世代: "第四代" },
      },
    ]);
    apiMocks.fetchMapFilterOptions.mockResolvedValue({
      localities: [],
      supports_locality_filter: true,
      supports_survey_status_filter: true,
      filter_fields: [
        {
          key: "调查状态",
          label: "调查状态",
          type: "select",
          options: [
            { value: "调查", label: "调查" },
            { value: "未调查", label: "未调查" },
          ],
          default_value: "",
        },
        {
          key: "世代",
          label: "世代",
          type: "select",
          options: [
            { value: "第一代", label: "第一代" },
            { value: "第二代", label: "第二代" },
          ],
          default_value: "",
        },
      ],
      survey_status_counts: { all: 100, completed: 50, pending: 50 },
    });
    apiMocks.fetchMapView.mockResolvedValue(createFeatureCollection([]));

    mountMapView();

    await vi.waitFor(() => {
      expect(apiMocks.fetchMapView).toHaveBeenCalledWith(
        "美国白蛾调查",
        {},
        DEFAULT_MAP_OPTIONS,
      );
    });
  });

  it("未配默认筛选时年份字段回退到后端 default_value", async () => {
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "美国白蛾调查",
        columns: ["编号", "属地", "调查日期", "年份", "世代"],
        default_filters: {},
      },
    ]);
    apiMocks.fetchMapFilterOptions.mockResolvedValue({
      localities: [],
      supports_locality_filter: true,
      supports_survey_status_filter: true,
      filter_fields: [
        {
          key: "调查状态",
          label: "调查状态",
          type: "select",
          options: [
            { value: "调查", label: "调查" },
            { value: "未调查", label: "未调查" },
          ],
          default_value: "",
        },
        {
          key: "年份",
          label: "年份",
          type: "select",
          options: [
            { value: "2025", label: "2025" },
            { value: "2026", label: "2026" },
          ],
          default_value: "2026",
        },
      ],
      survey_status_counts: { all: 100, completed: 50, pending: 50 },
    });
    apiMocks.fetchMapView.mockResolvedValue(createFeatureCollection([]));

    mountMapView();

    await vi.waitFor(() => {
      expect(apiMocks.fetchMapView).toHaveBeenCalledWith(
        "美国白蛾调查",
        { 年份: ["2026"] },
        DEFAULT_MAP_OPTIONS,
      );
    });
  });

  it("切换世代筛选后调查状态计数按筛选条件刷新", async () => {
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "美国白蛾调查",
        columns: ["编号", "属地", "调查日期", "年份", "世代"],
      },
    ]);
    apiMocks.fetchMapFilterOptions.mockImplementation(async (viewName, filters = {}) => ({
      localities: [],
      supports_locality_filter: true,
      supports_survey_status_filter: true,
      filter_fields: [
        {
          key: "调查状态",
          label: "调查状态",
          type: "select",
          options: [
            { value: "调查", label: "调查" },
            { value: "未调查", label: "未调查" },
          ],
          default_value: "",
        },
        {
          key: "世代",
          label: "世代",
          type: "select",
          options: [
            { value: "第一代", label: "第一代" },
            { value: "第二代", label: "第二代" },
            { value: "第三代", label: "第三代" },
          ],
          default_value: "",
        },
      ],
      survey_status_counts: (filters["世代"] || []).includes("第二代")
        ? { all: 471, completed: 388, pending: 83 }
        : { all: 1413, completed: 859, pending: 554 },
    }));
    apiMocks.fetchMapView.mockResolvedValue(createFeatureCollection([]));

    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="map-survey-status-toggle"]').exists()).toBe(true);
    });

    await wrapper.get('[data-testid="map-survey-status-toggle"]').trigger("click");

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="map-filter-世代"]').exists()).toBe(true);
    });
    expect(wrapper.get('[data-testid="map-survey-status-completed"]').text()).toContain("859");

    await wrapper.get('[data-testid="map-filter-世代"]').setValue("第二代");

    await vi.waitFor(() => {
      expect(apiMocks.fetchMapFilterOptions).toHaveBeenCalledWith(
        "美国白蛾调查",
        { 世代: "第二代" },
      );
    });
    await vi.waitFor(() => {
      expect(wrapper.get('[data-testid="map-survey-status-completed"]').text()).toContain("388");
      expect(wrapper.get('[data-testid="map-survey-status-pending"]').text()).toContain("83");
    });
  });

  it("在美国白蛾点位视图选中点位后显示删除按钮", async () => {
    const targetFeature = {
      type: "Feature",
      properties: {
        编号: "MQ001",
        点位名称: "马驹桥示范点",
        属地: "马驹桥镇",
      },
      geometry: { type: "Point", coordinates: [116.5, 39.7] },
    };
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "美国白蛾点位",
        columns: ["编号", "点位名称", "属地"],
      },
    ]);
    apiMocks.fetchMapView.mockResolvedValue(createFeatureCollection([targetFeature]));

    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("viewName")).toBe("美国白蛾点位");
    });

    getLeafletMapStub(wrapper).vm.$emit("feature-click", targetFeature);
    await wrapper.vm.$nextTick();

    expect(
      wrapper.find('[data-testid="site-delete-btn"]').exists(),
    ).toBe(true);
  });

  it("不支持点位管理的视图选中点位后不显示删除按钮", async () => {
    const targetFeature = {
      type: "Feature",
      properties: {
        编号: "TY001",
        点位名称: "高风险点位",
      },
      geometry: { type: "Point", coordinates: [116.6, 39.8] },
    };
    apiMocks.listMapViews.mockResolvedValue([
      { name: "高风险点位", columns: ["编号", "总虫口数"] },
    ]);
    apiMocks.fetchMapView.mockResolvedValue(createFeatureCollection([targetFeature]));

    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("viewName")).toBe("高风险点位");
    });

    getLeafletMapStub(wrapper).vm.$emit("feature-click", targetFeature);
    await wrapper.vm.$nextTick();

    expect(
      wrapper.find('[data-testid="site-delete-btn"]').exists(),
    ).toBe(false);
  });

  it("删除点位触发预检查与二次确认，确认后调用删除并关闭详情", async () => {
    const targetFeature = {
      type: "Feature",
      properties: {
        编号: "MQ001",
        点位名称: "马驹桥示范点",
        属地: "马驹桥镇",
      },
      geometry: { type: "Point", coordinates: [116.5, 39.7] },
    };
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "美国白蛾点位",
        columns: ["编号", "点位名称", "属地"],
      },
    ]);
    apiMocks.fetchMapView.mockResolvedValue(createFeatureCollection([targetFeature]));
    apiMocks.deleteWhiteMothSiteCheck.mockResolvedValue({
      code: "MQ001",
      exists: true,
      site_name: "马驹桥示范点",
      locality: "马驹桥镇",
      longitude: 116.5,
      latitude: 39.7,
      survey_record_count: 2,
    });
    apiMocks.deleteWhiteMothSite.mockResolvedValue({
      code: "MQ001",
      site_name: "马驹桥示范点",
      locality: "马驹桥镇",
      longitude: 116.5,
      latitude: 39.7,
      survey_record_count: 2,
    });

    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("viewName")).toBe("美国白蛾点位");
    });

    getLeafletMapStub(wrapper).vm.$emit("feature-click", targetFeature);
    await wrapper.vm.$nextTick();

    await wrapper.get('[data-testid="site-delete-btn"]').trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.deleteWhiteMothSiteCheck).toHaveBeenCalledWith("MQ001");
    });

    await vi.waitFor(() => {
      const message = wrapper.get('[data-slot="alert-dialog-description"]').text();
      expect(message).toContain("MQ001");
      expect(message).toContain("2 条调查记录");
    });

    await wrapper.get('[data-testid="confirm-dialog-confirm"]').trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.deleteWhiteMothSite).toHaveBeenCalledWith("MQ001");
    });

    expect(wrapper.find(".detail-drawer").exists()).toBe(false);
  });

  it("预检查返回点位不存在时提示并刷新，不弹确认窗", async () => {
    const targetFeature = {
      type: "Feature",
      properties: {
        编号: "MQ001",
        点位名称: "马驹桥示范点",
        属地: "马驹桥镇",
      },
      geometry: { type: "Point", coordinates: [116.5, 39.7] },
    };
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "美国白蛾点位",
        columns: ["编号", "点位名称", "属地"],
      },
    ]);
    apiMocks.fetchMapView.mockResolvedValue(createFeatureCollection([targetFeature]));
    apiMocks.deleteWhiteMothSiteCheck.mockResolvedValue({
      code: "MQ001",
      exists: false,
      survey_record_count: 0,
    });

    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("viewName")).toBe("美国白蛾点位");
    });

    getLeafletMapStub(wrapper).vm.$emit("feature-click", targetFeature);
    await wrapper.vm.$nextTick();

    await wrapper.get('[data-testid="site-delete-btn"]').trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.deleteWhiteMothSiteCheck).toHaveBeenCalledWith("MQ001");
    });

    expect(apiMocks.deleteWhiteMothSite).not.toHaveBeenCalled();
    expect(wrapper.find('[data-slot="alert-dialog-description"]').exists()).toBe(false);
  });

  it("其他害虫点位视图删除点位走其他害虫删除链路", async () => {
    const targetFeature = {
      type: "Feature",
      properties: {
        编号: "QT0007",
        点位名称: "梨园示范点",
        属地: "梨园镇",
      },
      geometry: { type: "Point", coordinates: [116.5, 39.7] },
    };
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "其他害虫点位",
        columns: ["编号", "点位名称", "属地"],
      },
    ]);
    apiMocks.fetchMapView.mockResolvedValue(createFeatureCollection([targetFeature]));
    apiMocks.deleteOtherPestSiteCheck.mockResolvedValue({
      code: "QT0007",
      exists: true,
      site_name: "梨园示范点",
      locality: "梨园镇",
      longitude: 116.5,
      latitude: 39.7,
      survey_record_count: 1,
    });
    apiMocks.deleteOtherPestSite.mockResolvedValue({
      code: "QT0007",
      site_name: "梨园示范点",
      locality: "梨园镇",
      longitude: 116.5,
      latitude: 39.7,
      survey_record_count: 1,
    });

    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("viewName")).toBe("其他害虫点位");
    });

    getLeafletMapStub(wrapper).vm.$emit("feature-click", targetFeature);
    await wrapper.vm.$nextTick();

    await wrapper.get('[data-testid="site-delete-btn"]').trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.deleteOtherPestSiteCheck).toHaveBeenCalledWith("QT0007");
    });
    expect(apiMocks.deleteWhiteMothSiteCheck).not.toHaveBeenCalled();

    await vi.waitFor(() => {
      const message = wrapper.get('[data-slot="alert-dialog-description"]').text();
      expect(message).toContain("其他害虫点位");
      expect(message).toContain("QT0007");
      expect(message).toContain("1 条调查记录");
    });

    await wrapper.get('[data-testid="confirm-dialog-confirm"]').trigger("click");

    await vi.waitFor(() => {
      expect(apiMocks.deleteOtherPestSite).toHaveBeenCalledWith("QT0007");
    });
    expect(apiMocks.deleteWhiteMothSite).not.toHaveBeenCalled();
    expect(wrapper.find(".detail-drawer").exists()).toBe(false);
  });
});
