import { defineComponent, nextTick } from "vue";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MapView from "../MapView.vue";
import { mapActions, mapStore } from "../../stores/mapStore.js";

const apiMocks = vi.hoisted(() => ({
  listMapViews: vi.fn(),
  fetchWhiteMothSiteCodeRules: vi.fn(),
  createWhiteMothSite: vi.fn(),
  fetchMapView: vi.fn(),
  fetchReferenceLayer: vi.fn(),
  listReferenceLayers: vi.fn(),
}));

vi.mock("../../api/map.js", () => ({
  listMapViews: apiMocks.listMapViews,
  fetchWhiteMothSiteCodeRules: apiMocks.fetchWhiteMothSiteCodeRules,
  createWhiteMothSite: apiMocks.createWhiteMothSite,
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
  },
  emits: [
    "update:viewName",
    "update:basemapMode",
    "update:showPointLabels",
    "toggle-white-moth-site-add",
    "toggle-reference-layer",
    "map-click",
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
        type="button"
        data-testid="map-add-white-moth-site-button"
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
      stubs: {
        LeafletMap: LeafletMapStub,
      },
    },
  });
}

function getLeafletMapStub(wrapper) {
  return wrapper.getComponent(LeafletMapStub);
}

function resetMapContext() {
  mapActions.setReady(false);
  mapActions.setViews([]);
  mapActions.setSelectedView("");
  mapActions.setLoadingViews(false);
  mapActions.setFilterFields([]);
  mapActions.setActiveFilters({});
  mapActions.setOpenFilterMenus({});
  mapActions.setBasemapMode("standard");
  mapActions.setShowPointLabels(true);
  mapActions.setLoading(false);
  mapActions.setFilterPanelOpen(false);
  mapActions.setActiveFilterCount(0);
}

describe("MapView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetMapContext();
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
      code_pattern: "^[A-Z]{2}\\d{3}$",
      code_example: "MQ001",
      prefix_localities: {
        MQ: "马驹桥镇",
        TH: "台湖镇",
      },
    });
    apiMocks.createWhiteMothSite.mockResolvedValue({
      gid: 14,
      code: "MQ001",
      locality: "马驹桥镇",
      site_name: "示范点",
      longitude: 116.5,
      latitude: 39.7,
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

  it("初始加载 reference 图层并响应图层开关", async () => {
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      const referenceLayers = getLeafletMapStub(wrapper).props("referenceLayers");

      expect(apiMocks.fetchReferenceLayer).toHaveBeenCalledWith("通州区行政区边界");
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
      expect(apiMocks.fetchReferenceLayer).toHaveBeenCalledWith("通州区小区边界");
      expect(
        getLeafletMapStub(wrapper)
          .props("referenceLayers")
          .find((layer) => layer.name === "通州区小区边界").active,
      ).toBe(true);
    });
  });

  it("刷新页面后优先恢复浏览器记住的上次视图", async () => {
    window.localStorage.setItem("tzlb.map.selectedView", "高风险点位");

    const wrapper = mountMapView();

    await vi.waitFor(() => {
      const mapStub = getLeafletMapStub(wrapper);

      expect(mapStub.props("viewName")).toBe("高风险点位");
      expect(mapStub.props("popupFields")).toEqual(["编号", "总虫口数"]);
    });

    expect(apiMocks.fetchMapView).toHaveBeenCalledWith("高风险点位", {});
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

    await wrapper.get('[data-testid="map-search-input"]').setValue("马驹桥");

    const results = wrapper.get('[data-testid="map-search-results"]');
    expect(results.text()).toContain("马大路与230国道交叉口");
    expect(results.text()).toContain("MQ001 · 马驹桥镇");

    await wrapper.get(".map-search-result").trigger("mousedown");

    expect(wrapper.get(".detail-drawer").text()).toContain("马大路与230国道交叉口");
    expect(getLeafletMapStub(wrapper).props("mapFocusRequest").feature).toStrictEqual(targetFeature);
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
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(apiMocks.fetchWhiteMothSiteCodeRules).toHaveBeenCalled();
    });

    await wrapper.get('[data-testid="map-add-white-moth-site-button"]').trigger("click");
    await wrapper.get('[data-testid="map-click-target"]').trigger("click");
    await wrapper.get('[data-testid="white-moth-site-code"]').setValue("mq001");

    expect(wrapper.get('[data-testid="white-moth-site-code"]').element.value).toBe("MQ001");
    expect(wrapper.get('[data-testid="white-moth-site-locality"]').text()).toBe("马驹桥镇");

    await wrapper.get('[data-testid="white-moth-site-name"]').setValue("示范点");
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
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(apiMocks.fetchWhiteMothSiteCodeRules).toHaveBeenCalled();
    });

    await wrapper.get('[data-testid="map-add-white-moth-site-button"]').trigger("click");

    expect(getLeafletMapStub(wrapper).props("whiteMothSiteAddMode")).toBe(true);
    expect(wrapper.find('[data-testid="white-moth-site-code"]').exists()).toBe(false);

    await wrapper.get('[data-testid="map-click-target"]').trigger("click");

    expect(wrapper.get('[data-testid="white-moth-site-code"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="white-moth-site-location"]').text()).toContain(
      "116.500000",
    );
  });

  it("编号前缀不支持时阻止新增美国白蛾点位", async () => {
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(apiMocks.fetchWhiteMothSiteCodeRules).toHaveBeenCalled();
    });

    await wrapper.get('[data-testid="map-add-white-moth-site-button"]').trigger("click");
    await wrapper.get('[data-testid="map-click-target"]').trigger("click");
    await wrapper.get('[data-testid="white-moth-site-code"]').setValue("ab001");

    expect(wrapper.get('[data-testid="white-moth-site-code-error"]').text()).toContain(
      "编号格式不正确",
    );
    expect(wrapper.get('[data-testid="white-moth-site-submit"]').attributes("disabled")).toBe(
      "",
    );
    await wrapper.get(".site-add-form").trigger("submit");
    expect(apiMocks.createWhiteMothSite).not.toHaveBeenCalled();
  });

  it("保存成功后刷新视图并切换到美国白蛾点位视图", async () => {
    apiMocks.listMapViews
      .mockResolvedValueOnce([
        {
          name: "虫情总览",
          columns: ["属地", "村", "调查日期"],
        },
      ])
      .mockResolvedValueOnce([
        {
          name: "虫情总览",
          columns: ["属地", "村", "调查日期"],
        },
        {
          name: "美国白蛾点位",
          columns: ["gid", "编号", "属地", "点位名称"],
        },
      ]);

    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("viewName")).toBe("虫情总览");
    });

    await wrapper.get('[data-testid="map-add-white-moth-site-button"]').trigger("click");
    await wrapper.get('[data-testid="map-click-target"]').trigger("click");
    await wrapper.get('[data-testid="white-moth-site-code"]').setValue("MQ001");
    await wrapper.get(".site-add-form").trigger("submit");

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("viewName")).toBe("美国白蛾点位");
      expect(getLeafletMapStub(wrapper).props("autoFitOnDataChange")).toBe(false);
    });
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

    await wrapper.get('[data-testid="map-add-white-moth-site-button"]').trigger("click");
    await wrapper.get('[data-testid="map-click-target"]').trigger("click");
    await wrapper.get('[data-testid="white-moth-site-code"]').setValue("MQ001");
    await wrapper.get(".site-add-form").trigger("submit");

    await vi.waitFor(() => {
      expect(apiMocks.createWhiteMothSite).toHaveBeenCalled();
      expect(getLeafletMapStub(wrapper).props("autoFitOnDataChange")).toBe(false);
    });
  });
});
