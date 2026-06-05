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
  fetchMapFilterOptions: vi.fn(),
  fetchAdminBoundary: vi.fn(),
}));

vi.mock("../../api/map.js", () => ({
  listMapViews: apiMocks.listMapViews,
  fetchWhiteMothSiteCodeRules: apiMocks.fetchWhiteMothSiteCodeRules,
  createWhiteMothSite: apiMocks.createWhiteMothSite,
  fetchMapView: apiMocks.fetchMapView,
  fetchMapFilterOptions: apiMocks.fetchMapFilterOptions,
  fetchAdminBoundary: apiMocks.fetchAdminBoundary,
}));

const MapToolbarStub = defineComponent({
  name: "MapToolbar",
  props: {
    views: { type: Array, default: () => [] },
    viewName: { type: String, default: "" },
    loadingViews: { type: Boolean, default: false },
    filterFields: { type: Array, default: () => [] },
    activeFilters: { type: Object, default: () => ({}) },
    filterOptions: { type: Object, default: () => ({}) },
    basemapMode: { type: String, default: "satellite" },
    showPointLabels: { type: Boolean, default: true },
    loading: { type: Boolean, default: false },
  },
  emits: [
    "update:viewName",
    "update:basemapMode",
    "update:showPointLabels",
    "update:activeFilters",
    "apply-filters",
    "reset-filters",
  ],
  data() {
    return {
      isFilterPanelOpen: false,
    };
  },
  computed: {
    activeFilterCount() {
      return Object.values(this.activeFilters).reduce((count, values) => {
        const arr = Array.isArray(values) ? values : [values];
        return count + arr.filter((v) => v !== "" && v != null).length;
      }, 0);
    },
  },
  template: `
    <div class="map-toolbar">
      <div class="toolbar-row">
        <div class="toolbar-view-select">
          <select
            data-testid="view-select"
            class="view-select"
            :value="viewName"
            :disabled="loadingViews || !views.length"
            @change="$emit('update:viewName', $event.target.value)"
          >
            <option v-if="!views.length" value="">暂无可用视图</option>
            <option v-for="view in views" :key="view.name" :value="view.name">
              {{ view.name }}
            </option>
          </select>
        </div>
        <button
          v-if="filterFields.length > 0"
          type="button"
          class="toolbar-btn"
          data-testid="map-filter-toggle"
          :aria-expanded="isFilterPanelOpen"
          @click="isFilterPanelOpen = !isFilterPanelOpen"
        >
          筛选
          <span v-if="activeFilterCount > 0" class="filter-badge">{{ activeFilterCount }}</span>
        </button>
        <button
          type="button"
          class="toolbar-btn"
          data-testid="point-label-toggle"
          @click="$emit('update:showPointLabels', !showPointLabels)"
        >
          {{ showPointLabels ? "隐藏编号" : "显示编号" }}
        </button>
      </div>
      <div v-if="isFilterPanelOpen" class="filter-panel-content">
        <div v-for="field in filterFields" :key="field.key" class="filter-field-item">
          <button
            type="button"
            class="filter-field-trigger"
            :data-testid="'map-filter-trigger-' + field.key"
            :aria-expanded="false"
            @click="() => {}"
          >
            <span class="filter-field-label">{{ field.label }}</span>
          </button>
          <div :data-testid="'map-filter-' + field.key" class="filter-option-dropdown">
            <label v-for="option in field.options" :key="option.value" class="filter-option">
              <input
                type="checkbox"
                :value="option.value"
                :checked="activeFilters[field.key]?.includes(option.value)"
                :data-testid="'map-filter-' + field.key + '-' + option.value"
                @change="$emit('update:activeFilters', { ...activeFilters, [field.key]: [...(activeFilters[field.key] || []), option.value] })"
              />
              <span>{{ option.label }}</span>
            </label>
          </div>
        </div>
        <div class="filter-actions">
          <button type="button" data-testid="filter-apply" @click="$emit('apply-filters'); isFilterPanelOpen = false">
            应用筛选
          </button>
          <button type="button" data-testid="filter-reset" @click="$emit('reset-filters')">
            清空
          </button>
        </div>
      </div>
    </div>
  `,
});

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
        MapToolbar: MapToolbarStub,
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
    apiMocks.fetchMapFilterOptions.mockResolvedValue({
      localities: [],
      supports_locality_filter: false,
      supports_survey_status_filter: false,
    });
    apiMocks.fetchAdminBoundary.mockResolvedValue({
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

  it("点击编号开关后更新传给 LeafletMap 的 showPointLabels", async () => {
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("showPointLabels")).toBe(true);
      expect(mapStore.loadingViews).toBe(false);
      expect(apiMocks.fetchMapView).toHaveBeenCalled();
    });

    mapActions.togglePointLabels();
    await nextTick();
    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("showPointLabels")).toBe(false);
    });

    mapActions.togglePointLabels();
    await nextTick();
    await vi.waitFor(() => {
      expect(getLeafletMapStub(wrapper).props("showPointLabels")).toBe(true);
    });
  });

  it("切换 view 后更新传给 LeafletMap 的 popupFields", async () => {
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      const mapStub = getLeafletMapStub(wrapper);

      expect(mapStub.props("viewName")).toBe("虫情总览");
    });

    mapActions.setSelectedView("高风险点位");

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

    mapActions.setSelectedView("高风险点位");

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

    mapActions.setSelectedView("高风险点位");

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

  it("默认隐藏筛选配置内容，点击侧栏入口后显示", async () => {
    apiMocks.fetchMapFilterOptions.mockResolvedValue({
      filter_fields: [
        {
          key: "年份",
          label: "年份",
          type: "select",
          default_value: "2025",
          options: [
            { value: "2024", label: "2024" },
            { value: "2025", label: "2025" },
          ],
        },
      ],
    });

    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(apiMocks.fetchMapView).toHaveBeenCalled();
    });

    expect(mapStore.isFilterPanelOpen).toBe(false);

    mapActions.toggleFilterPanel();

    await vi.waitFor(() => {
      expect(mapStore.isFilterPanelOpen).toBe(true);
    });
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

  it("根据后端返回的动态筛选字段渲染控件并提交筛选条件", async () => {
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "国槐尺蠖幼虫历年发生情况",
        columns: ["编号", "属地", "年份", "危害程度"],
      },
    ]);
    apiMocks.fetchMapFilterOptions.mockResolvedValue({
      filter_fields: [
        {
          key: "年份",
          label: "年份",
          type: "select",
          default_value: "2025",
          options: [
            { value: "2024", label: "2024" },
            { value: "2025", label: "2025" },
          ],
        },
        {
          key: "危害程度",
          label: "危害程度",
          type: "select",
          default_value: "",
          options: [
            { value: "白", label: "白" },
            { value: "轻", label: "轻" },
            { value: "中", label: "中" },
            { value: "重", label: "重" },
          ],
        },
      ],
    });

    const wrapper = mountMapView();

    await vi.waitFor(() => {
      expect(apiMocks.fetchMapView).toHaveBeenCalledWith(
        "国槐尺蠖幼虫历年发生情况",
        {
          年份: ["2025"],
        },
      );
    });

    mapActions.setFilterPanelOpen(true);
    mapActions.toggleFilterMenu("年份");
    mapActions.toggleFilterMenu("危害程度");
    mapActions.setFilterValues("危害程度", ["中", "重"]);
    await nextTick();
    mapActions.applyFilter();

    await vi.waitFor(() => {
      expect(apiMocks.fetchMapView).toHaveBeenLastCalledWith(
        "国槐尺蠖幼虫历年发生情况",
        {
          年份: ["2025"],
          危害程度: ["中", "重"],
        },
      );
    });
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
