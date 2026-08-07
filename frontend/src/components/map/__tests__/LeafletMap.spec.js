import { nextTick } from "vue";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LeafletMap from "../LeafletMap.vue";

const toastMocks = vi.hoisted(() => ({
  error: vi.fn(),
  info: vi.fn(),
}));

const geoMocks = vi.hoisted(() => ({
  watchPosition: vi.fn(),
  clearWatch: vi.fn(),
  getCurrentPosition: vi.fn(),
  success: null,
  failure: null,
  options: null,
}));

const leafletMocks = vi.hoisted(() => {
  const maps = [];
  const markers = [];

  function createLayer() {
    return {
      addTo: vi.fn(function addTo() {
        return this;
      }),
      bindPopup: vi.fn(function bindPopup() {
        return this;
      }),
      bindTooltip: vi.fn(function bindTooltip() {
        return this;
      }),
      bringToFront: vi.fn(),
      getBounds: vi.fn(() => ({
        isValid: vi.fn(() => false),
        pad: vi.fn(() => ({})),
      })),
      remove: vi.fn(),
    };
  }

  return {
    maps,
    markers,
    canvas: vi.fn(() => ({})),
    circleMarker: vi.fn(() => createLayer()),
    control: {
      zoom: vi.fn(() => ({
        addTo: vi.fn(function addTo() {
          return this;
        }),
        remove: vi.fn(),
      })),
    },
    DomEvent: {
      stopPropagation: vi.fn(),
    },
    divIcon: vi.fn((options) => options),
    featureGroup: vi.fn(() => createLayer()),
    geoJSON: vi.fn(() => createLayer()),
    layerGroup: vi.fn(() => createLayer()),
    map: vi.fn((element, options) => {
      const eventHandlers = {};
      const mapInstance = {
        element,
        options,
        bounds: null,
        boundsContains: () => true,
        currentZoom: 11,
        fitBounds: vi.fn(),
        getBounds: vi.fn(() => {
          const bounds = {
            contains: vi.fn((latlng) => mapInstance.boundsContains(latlng)),
          };
          if (mapInstance.bounds) {
            bounds.getEast = vi.fn(() => mapInstance.bounds.east);
            bounds.getNorth = vi.fn(() => mapInstance.bounds.north);
            bounds.getSouth = vi.fn(() => mapInstance.bounds.south);
            bounds.getWest = vi.fn(() => mapInstance.bounds.west);
          }
          return bounds;
        }),
        getZoom: vi.fn(() => mapInstance.currentZoom),
        latLngToLayerPoint: vi.fn(([lat, lng]) => {
          const scale = mapInstance.currentZoom / 14;
          return {
            x: Number(lng) * 100000 * scale,
            y: Number(lat) * -100000 * scale,
          };
        }),
        off: vi.fn(function off(event, handler) {
          if (!handler || eventHandlers[event] === handler) {
            delete eventHandlers[event];
          }
          return this;
        }),
        on: vi.fn(function on(event, handler) {
          eventHandlers[event] = handler;
          return this;
        }),
        remove: vi.fn(),
        setView: vi.fn(function setView() {
          return this;
        }),
        trigger(event, payload) {
          eventHandlers[event]?.(payload);
        },
        zoomIn: vi.fn(),
        zoomOut: vi.fn(),
      };
      maps.push(mapInstance);
      return mapInstance;
    }),
    marker: vi.fn((latlng, options) => {
      const markerInstance = {
        latlng,
        options,
        addTo: vi.fn(function addTo() {
          return this;
        }),
        bindTooltip: vi.fn(function bindTooltip() {
          return this;
        }),
        remove: vi.fn(),
        setLatLng: vi.fn(function setLatLng(nextLatLng) {
          this.latlng = nextLatLng;
          return this;
        }),
      };
      markers.push(markerInstance);
      return markerInstance;
    }),
    tileLayer: vi.fn(() => createLayer()),
  };
});

vi.mock("../../../composables/useToast.js", () => ({
  useToast: () => toastMocks,
}));

vi.mock("leaflet", () => ({
  default: leafletMocks,
}));

function mockPosition(latitude, longitude) {
  return {
    coords: {
      latitude,
      longitude,
    },
  };
}

function createPointFeature(code, longitude, latitude, properties = {}) {
  return {
    type: "Feature",
    geometry: {
      type: "Point",
      coordinates: [longitude, latitude],
    },
    properties: {
      编号: code,
      危害程度: "轻",
      调查日期: "",
      ...properties,
    },
  };
}

function createPolygonFeature(code, properties = {}) {
  return {
    type: "Feature",
    geometry: {
      type: "MultiPolygon",
      coordinates: [
        [
          [
            [116.72, 39.91],
            [116.75, 39.91],
            [116.75, 39.94],
            [116.72, 39.94],
            [116.72, 39.91],
          ],
        ],
      ],
    },
    properties: {
      编号: code,
      点位名称: "如意园",
      调查状态: "未调查",
      ...properties,
    },
  };
}

function getPointLabelMarkerCalls() {
  return leafletMocks.marker.mock.calls.filter(
    ([, options]) =>
      options?.interactive === false &&
      options?.keyboard === false &&
      options?.icon?.className === "map-point-label-marker",
  );
}

function getPointLabelMarkerHtml() {
  return getPointLabelMarkerCalls().map(([, options]) => options?.icon?.html || "");
}

function getPointClusterMarkerCalls() {
  return leafletMocks.marker.mock.calls.filter(
    ([, options]) => options?.icon?.className === "map-point-cluster-marker",
  );
}

function getLegendLabels(wrapper) {
  return wrapper.findAll(".map-legend .legend-item").map((item) => item.text());
}

async function openLegend(wrapper) {
  await wrapper.get('[data-testid="map-legend-expand-button"]').trigger("click");
}

function setMapViewport({ zoom = 11, contains = () => true } = {}) {
  const mapInstance = leafletMocks.maps[0];
  mapInstance.currentZoom = zoom;
  mapInstance.boundsContains = contains;
  return mapInstance;
}

function mountLeafletMap(props = {}) {
  return mount(LeafletMap, {
    props: {
      boundaryGeojson: {
        type: "FeatureCollection",
        features: [],
      },
      geojson: {
        type: "FeatureCollection",
        features: [],
      },
      viewName: "虫情总览",
      views: [{ name: "虫情总览", columns: [] }],
      ...props,
    },
  });
}

function installGeolocationMock() {
  geoMocks.watchPosition.mockImplementation((success, failure, options) => {
    geoMocks.success = success;
    geoMocks.failure = failure;
    geoMocks.options = options;
    return 42;
  });

  Object.defineProperty(window.navigator, "geolocation", {
    configurable: true,
    value: {
      watchPosition: geoMocks.watchPosition,
      clearWatch: geoMocks.clearWatch,
      getCurrentPosition: geoMocks.getCurrentPosition,
    },
  });
}

describe("LeafletMap 底图图层", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    leafletMocks.maps.length = 0;
    leafletMocks.markers.length = 0;
    installGeolocationMock();
  });

  it("地图移动和缩放后上报当前视窗", () => {
    const wrapper = mountLeafletMap();
    const mapInstance = leafletMocks.maps[0];

    mapInstance.bounds = {
      west: 116.2,
      south: 39.6,
      east: 116.8,
      north: 40,
    };
    mapInstance.currentZoom = 13;
    mapInstance.trigger("moveend");

    expect(wrapper.emitted("viewport-change")?.at(-1)?.[0]).toEqual({
      bbox: [116.2, 39.6, 116.8, 40],
      zoom: 13,
    });

    mapInstance.currentZoom = 14;
    mapInstance.trigger("zoomend");

    expect(wrapper.emitted("viewport-change")?.at(-1)?.[0]).toEqual({
      bbox: [116.2, 39.6, 116.8, 40],
      zoom: 14,
    });
  });

  it("标准底图只加载基础瓦片层", () => {
    mountLeafletMap({ basemapMode: "standard" });

    expect(leafletMocks.tileLayer).toHaveBeenCalledTimes(1);
    expect(leafletMocks.tileLayer).toHaveBeenCalledWith(
      expect.stringContaining("openstreetmap"),
      expect.objectContaining({ maxZoom: 19 }),
    );
  });

  it("初始化时关闭 Leaflet 默认 attribution 控件", () => {
    mountLeafletMap();

    expect(leafletMocks.maps[0].options).toEqual(
      expect.objectContaining({
        attributionControl: false,
        zoomControl: false,
      }),
    );
  });

  it("默认卫星底图会叠加天地图影像注记", () => {
    mountLeafletMap();

    expect(leafletMocks.tileLayer).toHaveBeenCalledTimes(2);
    expect(leafletMocks.tileLayer).toHaveBeenNthCalledWith(
      1,
      expect.stringContaining("World_Imagery"),
      expect.objectContaining({ maxZoom: 19 }),
    );
    expect(leafletMocks.tileLayer).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining("LAYER=cia"),
      expect.objectContaining({
        maxZoom: 19,
        maxNativeZoom: 18,
        attribution: "&copy; 天地图",
      }),
    );
  });

  it("切回标准底图会移除影像注记层", async () => {
    const wrapper = mountLeafletMap({ basemapMode: "satellite" });
    const annotationLayer = leafletMocks.tileLayer.mock.results[1].value;

    await wrapper.setProps({ basemapMode: "standard" });

    expect(annotationLayer.remove).toHaveBeenCalledTimes(1);
    expect(leafletMocks.tileLayer).toHaveBeenCalledTimes(3);
    expect(leafletMocks.tileLayer).toHaveBeenLastCalledWith(
      expect.stringContaining("openstreetmap"),
      expect.objectContaining({ maxZoom: 19 }),
    );
  });

  it("右上角图层面板可以切换底图和编号显示", async () => {
    const wrapper = mountLeafletMap({
      basemapMode: "satellite",
      referenceLayers: [
        {
          name: "通州区小区边界",
          label: "通州区小区边界",
          active: false,
          geojson: {
            type: "FeatureCollection",
            features: [],
          },
        },
      ],
      showPointLabels: true,
    });

    expect(wrapper.find("#map-layer-panel").exists()).toBe(false);

    await wrapper.get('[data-testid="map-layer-button"]').trigger("click");
    expect(wrapper.get("#map-layer-panel").text()).toContain("地图图层");
    expect(wrapper.get("#map-layer-panel").text()).toContain("基础图层");
    expect(wrapper.get("#map-layer-panel").text()).toContain("点位图层");
    expect(wrapper.get('[data-testid="map-layer-labels"]').classes()).toContain(
      "map-base-layer-option",
    );
    const baseLayerTestIds = wrapper
      .findAll("#map-layer-panel .map-base-layer-option")
      .map((item) => item.attributes("data-testid"));
    expect(baseLayerTestIds.at(-1)).toBe("map-layer-labels");
    expect(wrapper.find(".map-reference-layer-dot").exists()).toBe(false);

    await wrapper.get('[data-testid="map-layer-standard"]').trigger("click");
    expect(wrapper.emitted("update:basemapMode")).toEqual([["standard"]]);
    expect(wrapper.find("#map-layer-panel").exists()).toBe(false);

    await wrapper.get('[data-testid="map-layer-button"]').trigger("click");
    await wrapper.get('[data-testid="map-layer-labels"]').trigger("click");
    expect(wrapper.emitted("update:showPointLabels")).toEqual([[false]]);
  });

  it("点击地图空白处会关闭图层面板", async () => {
    const wrapper = mountLeafletMap();
    const mapInstance = leafletMocks.maps[0];

    await wrapper.get('[data-testid="map-layer-button"]').trigger("click");
    expect(wrapper.find("#map-layer-panel").exists()).toBe(true);

    mapInstance.trigger("click", {
      latlng: {
        lat: 39.7,
        lng: 116.5,
      },
    });
    await nextTick();

    expect(wrapper.find("#map-layer-panel").exists()).toBe(false);
    expect(wrapper.emitted("map-click")).toEqual([
      [
        {
          latitude: 39.7,
          longitude: 116.5,
        },
      ],
    ]);
  });

  it("图层面板的点位图层可以切换当前地图视图", async () => {
    const wrapper = mountLeafletMap({
      viewName: "虫情总览",
      views: [
        { name: "虫情总览", columns: [] },
        { name: "美国白蛾点位", columns: [] },
      ],
      geojson: {
        type: "FeatureCollection",
        features: [createPointFeature("MGB-001", 116.73, 39.92)],
      },
    });

    await wrapper.get('[data-testid="map-layer-button"]').trigger("click");

    const panel = wrapper.get("#map-layer-panel");
    expect(panel.text()).toContain("虫情总览");
    expect(panel.text()).toContain("1");
    expect(wrapper.findAll(".map-point-layer").map((item) => item.text())).not.toContain(
      "编号标签",
    );

    await wrapper.get('[data-testid="map-point-layer-美国白蛾点位"]').trigger("click");

    expect(wrapper.emitted("update:viewName")).toEqual([["美国白蛾点位"]]);
  });

  it("点位图层优先显示视图别名", async () => {
    const wrapper = mountLeafletMap({
      viewName: "task_guohuai_2026_gen1",
      views: [
        { name: "task_guohuai_2026_gen1", label: "国槐尺蠖2026年第一代调查", columns: [] },
        { name: "美国白蛾点位", columns: [] },
      ],
      geojson: {
        type: "FeatureCollection",
        features: [],
      },
    });

    await wrapper.get('[data-testid="map-layer-button"]').trigger("click");

    const panel = wrapper.get("#map-layer-panel");
    expect(panel.text()).toContain("国槐尺蠖2026年第一代调查");
    expect(panel.text()).not.toContain("task_guohuai_2026_gen1");
    // 未配置别名的图层仍显示图层键
    expect(panel.text()).toContain("美国白蛾点位");
  });

  it("右上角缩放按钮直接调用地图缩放方法", async () => {
    const wrapper = mountLeafletMap();
    const mapInstance = leafletMocks.maps[0];

    await wrapper.get('[data-testid="map-zoom-in-button"]').trigger("click");
    await wrapper.get('[data-testid="map-zoom-out-button"]').trigger("click");

    expect(mapInstance.zoomIn).toHaveBeenCalledTimes(1);
    expect(mapInstance.zoomOut).toHaveBeenCalledTimes(1);
  });
});

describe("LeafletMap 实时定位", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    leafletMocks.maps.length = 0;
    leafletMocks.markers.length = 0;
    geoMocks.success = null;
    geoMocks.failure = null;
    geoMocks.options = null;
    installGeolocationMock();
  });

  it("挂载地图时不再创建缩放按钮控件", () => {
    mountLeafletMap();

    expect(leafletMocks.control.zoom).not.toHaveBeenCalled();
  });

  it("首次点击定位按钮会启动 watchPosition，不再调用一次性定位", async () => {
    const wrapper = mountLeafletMap();

    await wrapper.get('[data-testid="map-locate-button"]').trigger("click");

    expect(geoMocks.watchPosition).toHaveBeenCalledTimes(1);
    expect(geoMocks.getCurrentPosition).not.toHaveBeenCalled();
    expect(geoMocks.options).toEqual({
      enableHighAccuracy: true,
      timeout: 8000,
      maximumAge: 60_000,
    });
    expect(wrapper.get('[data-testid="map-locate-button"]').attributes("aria-pressed")).toBe(
      "true",
    );
    expect(wrapper.get('[data-testid="map-locate-button"]').attributes("aria-label")).toBe(
      "重新居中到当前位置",
    );
  });

  it("第一次位置回调会创建当前位置标记并居中", async () => {
    const wrapper = mountLeafletMap();
    const mapInstance = leafletMocks.maps[0];
    mapInstance.setView.mockClear();

    await wrapper.get('[data-testid="map-locate-button"]').trigger("click");
    geoMocks.success(mockPosition(39.92, 116.73));
    await nextTick();

    expect(leafletMocks.marker).toHaveBeenCalledTimes(1);
    expect(leafletMocks.marker).toHaveBeenCalledWith([39.92, 116.73], expect.any(Object));
    expect(mapInstance.setView).toHaveBeenCalledTimes(1);
    expect(mapInstance.setView).toHaveBeenCalledWith([39.92, 116.73], 13, { animate: true });
    expect(toastMocks.info).toHaveBeenCalledWith(
      "实时定位已开启，当前位置会持续更新。",
      "定位成功",
    );
  });

  it("后续位置回调只移动标记，不自动移动地图视图", async () => {
    const wrapper = mountLeafletMap();
    const mapInstance = leafletMocks.maps[0];
    mapInstance.setView.mockClear();

    await wrapper.get('[data-testid="map-locate-button"]').trigger("click");
    geoMocks.success(mockPosition(39.92, 116.73));
    mapInstance.setView.mockClear();
    geoMocks.success(mockPosition(39.93, 116.74));
    await nextTick();

    expect(leafletMocks.marker).toHaveBeenCalledTimes(1);
    expect(leafletMocks.markers[0].setLatLng).toHaveBeenCalledWith([39.93, 116.74]);
    expect(mapInstance.setView).not.toHaveBeenCalled();
  });

  it("实时定位已开启后再次点击按钮会重新居中到最新位置", async () => {
    const wrapper = mountLeafletMap();
    const mapInstance = leafletMocks.maps[0];
    mapInstance.setView.mockClear();

    await wrapper.get('[data-testid="map-locate-button"]').trigger("click");
    geoMocks.success(mockPosition(39.92, 116.73));
    mapInstance.setView.mockClear();
    await wrapper.get('[data-testid="map-locate-button"]').trigger("click");

    expect(geoMocks.watchPosition).toHaveBeenCalledTimes(1);
    expect(mapInstance.setView).toHaveBeenCalledTimes(1);
    expect(mapInstance.setView).toHaveBeenCalledWith([39.92, 116.73], 13, { animate: true });
  });

  it("实时定位开启但尚未收到位置时再次点击会提示等待", async () => {
    const wrapper = mountLeafletMap();

    await wrapper.get('[data-testid="map-locate-button"]').trigger("click");
    await wrapper.get('[data-testid="map-locate-button"]').trigger("click");

    expect(geoMocks.watchPosition).toHaveBeenCalledTimes(1);
    expect(toastMocks.info).toHaveBeenCalledWith("正在获取当前位置，请稍候。", "定位中");
  });

  it("组件卸载时会清理实时定位监听", async () => {
    const wrapper = mountLeafletMap();

    await wrapper.get('[data-testid="map-locate-button"]').trigger("click");
    wrapper.unmount();

    expect(geoMocks.clearWatch).toHaveBeenCalledWith(42);
  });

  it("定位权限被拒绝时会提示错误并关闭监听状态", async () => {
    const wrapper = mountLeafletMap();

    await wrapper.get('[data-testid="map-locate-button"]').trigger("click");
    geoMocks.failure({ code: 1 });
    await nextTick();
    geoMocks.failure({ code: 1 });

    expect(geoMocks.clearWatch).toHaveBeenCalledWith(42);
    expect(toastMocks.error).toHaveBeenCalledTimes(1);
    expect(toastMocks.error).toHaveBeenCalledWith(
      "未授予定位权限，请在浏览器中允许访问位置信息。",
      "定位失败",
    );
    expect(wrapper.get('[data-testid="map-locate-button"]').attributes("aria-pressed")).toBe(
      "false",
    );
  });

  it("添加点位模式下点击地图会抛出经纬度", () => {
    const wrapper = mountLeafletMap({
      whiteMothSiteAddMode: true,
    });
    const mapInstance = leafletMocks.maps[0];

    mapInstance.trigger("click", {
      latlng: {
        lat: 39.7,
        lng: 116.5,
      },
    });

    expect(wrapper.emitted("map-click")).toEqual([
      [
        {
          latitude: 39.7,
          longitude: 116.5,
        },
      ],
    ]);
  });

  it("未配置添加点位标签时不渲染添加按钮", () => {
    const wrapper = mountLeafletMap();

    expect(wrapper.find('[data-testid="map-add-site-button"]').exists()).toBe(false);
  });

  it("配置添加点位标签后渲染按钮并透出标签文案", async () => {
    const wrapper = mountLeafletMap({
      siteAddLabel: "添加其他害虫点位",
    });

    const addButton = wrapper.get('[data-testid="map-add-site-button"]');
    expect(addButton.attributes("aria-label")).toBe("添加其他害虫点位");

    await addButton.trigger("click");
    expect(wrapper.emitted("toggle-white-moth-site-add")).toHaveLength(1);

    await wrapper.setProps({ whiteMothSiteAddMode: true });
    expect(
      wrapper.get('[data-testid="map-add-site-button"]').attributes("aria-label"),
    ).toBe("取消添加其他害虫点位");
  });

  it("添加点位模式关闭时点击地图仍抛出经纬度用于关闭浮层", () => {
    const wrapper = mountLeafletMap();
    const mapInstance = leafletMocks.maps[0];

    mapInstance.trigger("click", {
      latlng: {
        lat: 39.7,
        lng: 116.5,
      },
    });

    expect(wrapper.emitted("map-click")).toEqual([
      [
        {
          latitude: 39.7,
          longitude: 116.5,
        },
      ],
    ]);
  });

  it("收到新增点位草稿坐标时渲染临时标记", () => {
    mountLeafletMap({
      whiteMothSiteDraftLocation: {
        latitude: 39.7,
        longitude: 116.5,
      },
    });

    expect(leafletMocks.marker).toHaveBeenCalledWith(
      [39.7, 116.5],
      expect.objectContaining({
        interactive: false,
        keyboard: false,
        icon: expect.objectContaining({
          className: "white-moth-site-draft-marker-wrapper",
        }),
      }),
    );
  });
});

describe("LeafletMap 图例", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    leafletMocks.maps.length = 0;
    leafletMocks.markers.length = 0;
    installGeolocationMock();
  });

  it("含危害程度字段时只显示无、轻、中、重图例", async () => {
    const wrapper = mountLeafletMap({
      popupFields: ["编号", "危害程度", "调查状态"],
    });

    await openLegend(wrapper);

    expect(getLegendLabels(wrapper)).toEqual(["无", "轻", "中", "重"]);
    expect(wrapper.find(".map-status-legend").exists()).toBe(false);
  });

  it("不含危害程度字段时只显示危害点位图例", async () => {
    const wrapper = mountLeafletMap({
      popupFields: ["编号", "调查状态"],
    });

    await openLegend(wrapper);

    expect(getLegendLabels(wrapper)).toEqual(["危害点位"]);
    expect(wrapper.text()).not.toContain("未调查");
  });

  it("含调查日期字段时图例显示已调查与未调查", async () => {
    const wrapper = mountLeafletMap({
      popupFields: ["编号", "调查日期", "调查状态"],
    });

    await openLegend(wrapper);

    expect(getLegendLabels(wrapper)).toEqual(["已调查", "未调查"]);
  });

  it("危害程度与调查日期并存时图例附加未调查", async () => {
    const wrapper = mountLeafletMap({
      popupFields: ["编号", "危害程度", "调查日期"],
    });

    await openLegend(wrapper);

    expect(getLegendLabels(wrapper)).toEqual(["无", "轻", "中", "重", "未调查"]);
  });

  it("白蜡地块状态 view 显示其他、调查、伐除图例", async () => {
    const wrapper = mountLeafletMap({
      popupFields: ["编号", "地块状态"],
    });

    await openLegend(wrapper);

    expect(getLegendLabels(wrapper)).toEqual(["其他", "调查", "伐除"]);
  });

  it("图例默认隐藏，并通过图标按钮展开和收起", async () => {
    const wrapper = mountLeafletMap({
      popupFields: ["编号", "调查日期", "调查状态"],
      geojson: {
        type: "FeatureCollection",
        features: [createPointFeature("MGB-001", 116.73, 39.92)],
      },
    });

    expect(wrapper.find('[data-testid="map-legend-panel"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="map-legend-expand-button"]').attributes("aria-label")).toBe(
      "展开图例",
    );
    expect(wrapper.get('[data-testid="map-legend-expand-button"]').text()).toBe("");

    await openLegend(wrapper);

    expect(wrapper.get('[data-testid="map-legend-panel"]').text()).toContain("图例");
    expect(wrapper.get('[data-testid="map-legend-panel"]').text()).not.toContain("个调查点位");
    expect(wrapper.find('[data-testid="map-legend-expand-button"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="map-legend-collapse-button"]').classes()).toContain(
      "panel-header-title-group",
    );

    await wrapper.get('[data-testid="map-legend-collapse-button"]').trigger("click");

    expect(wrapper.find('[data-testid="map-legend-panel"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="map-legend-expand-button"]').attributes("aria-label")).toBe(
      "展开图例",
    );
    expect(wrapper.get('[data-testid="map-legend-expand-button"]').text()).toBe("");
  });
});

describe("LeafletMap 参考图层", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    leafletMocks.maps.length = 0;
    leafletMocks.markers.length = 0;
    installGeolocationMock();
  });

  it("渲染已启用的 reference 图层且不允许地图内选中", () => {
    const feature = createPolygonFeature("SQ-001", { 名称: "示范小区" });

    mountLeafletMap({
      referenceLayers: [
        {
          name: "通州区小区边界",
          label: "通州区小区边界",
          active: true,
          columns: ["名称"],
          geojson: {
            type: "FeatureCollection",
            features: [feature],
          },
        },
      ],
    });

    expect(leafletMocks.featureGroup).toHaveBeenCalledTimes(1);
    expect(leafletMocks.geoJSON).toHaveBeenCalledTimes(1);
    const geoJsonCall = leafletMocks.geoJSON.mock.calls[0];

    expect(geoJsonCall[0].features).toEqual([feature]);
    expect(geoJsonCall[1]).toMatchObject({
      interactive: false,
    });
    expect(geoJsonCall[1].onEachFeature).toBeUndefined();
  });

  it("点状 reference 图层也不允许地图内选中", () => {
    const feature = createPointFeature("REF-001", 116.73, 39.92);

    mountLeafletMap({
      referenceLayers: [
        {
          name: "参考点图层",
          label: "参考点图层",
          active: true,
          columns: ["编号"],
          geojson: {
            type: "FeatureCollection",
            features: [feature],
          },
        },
      ],
    });

    const geoJsonCall = leafletMocks.geoJSON.mock.calls[0];
    geoJsonCall[1].pointToLayer(feature, [39.92, 116.73]);

    expect(leafletMocks.circleMarker).toHaveBeenCalledWith(
      [39.92, 116.73],
      expect.objectContaining({
        interactive: false,
      }),
    );
  });

  it("点击 reference 图层菜单项时发出切换事件", async () => {
    const wrapper = mountLeafletMap({
      referenceLayers: [
        {
          name: "通州国槐图层",
          label: "通州国槐图层",
          active: false,
          loading: false,
          geojson: {
            type: "FeatureCollection",
            features: [],
          },
        },
      ],
    });

    await wrapper.get('[data-testid="map-layer-button"]').trigger("click");
    await wrapper.get('[data-testid="map-reference-layer-通州国槐图层"]').trigger("click");

    expect(wrapper.emitted("toggle-reference-layer")).toEqual([["通州国槐图层"]]);
  });

  it("切换 reference 图层时不触发地图自动缩放", async () => {
    const feature = createPolygonFeature("SQ-001", { 名称: "示范小区" });
    const wrapper = mountLeafletMap({
      referenceLayers: [
        {
          name: "通州区小区边界",
          label: "通州区小区边界",
          active: false,
          geojson: {
            type: "FeatureCollection",
            features: [],
          },
        },
      ],
    });
    const requestAnimationFrameSpy = vi.spyOn(window, "requestAnimationFrame");
    requestAnimationFrameSpy.mockClear();

    await wrapper.setProps({
      referenceLayers: [
        {
          name: "通州区小区边界",
          label: "通州区小区边界",
          active: true,
          geojson: {
            type: "FeatureCollection",
            features: [feature],
          },
        },
      ],
    });

    expect(requestAnimationFrameSpy).not.toHaveBeenCalled();
    requestAnimationFrameSpy.mockRestore();
  });
});

describe("LeafletMap 调查状态样式", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    leafletMocks.maps.length = 0;
    leafletMocks.markers.length = 0;
    installGeolocationMock();
  });

  it("有调查日期字段时，未调查点位渲染为灰色空心点", () => {
    const feature = createPointFeature("A-002", 116.74, 39.93, { 调查日期: "" });

    mountLeafletMap({
      popupFields: ["编号", "调查日期"],
      geojson: {
        type: "FeatureCollection",
        features: [feature],
      },
    });

    const geoJsonCall = leafletMocks.geoJSON.mock.calls[leafletMocks.geoJSON.mock.calls.length - 1];
    geoJsonCall[1].pointToLayer(feature, [39.93, 116.74]);

    expect(leafletMocks.circleMarker).toHaveBeenCalledWith(
      [39.93, 116.74],
      expect.objectContaining({
        radius: 8,
        fillColor: "#ffffff",
        color: "#9CA3AF",
        weight: 1.6,
        fillOpacity: 0.92,
      }),
    );
  });

  it("有调查日期字段时，已调查点位保持原有样式", () => {
    const feature = createPointFeature("A-001", 116.73, 39.92, { 调查日期: "2026-05-02" });

    mountLeafletMap({
      popupFields: ["编号", "调查日期"],
      geojson: {
        type: "FeatureCollection",
        features: [feature],
      },
    });

    const geoJsonCall = leafletMocks.geoJSON.mock.calls[leafletMocks.geoJSON.mock.calls.length - 1];
    geoJsonCall[1].pointToLayer(feature, [39.92, 116.73]);

    expect(leafletMocks.circleMarker).toHaveBeenCalledWith(
      [39.92, 116.73],
      expect.objectContaining({
        radius: 8,
        fillColor: "#ff0000",
        color: "#1F2933",
        weight: 1.45,
      }),
    );
  });

  it("没有调查日期字段时不应用未调查样式", () => {
    const feature = createPointFeature("A-001", 116.73, 39.92, { 调查日期: "" });

    mountLeafletMap({
      popupFields: ["编号", "调查状态"],
      geojson: {
        type: "FeatureCollection",
        features: [feature],
      },
    });

    const geoJsonCall = leafletMocks.geoJSON.mock.calls[leafletMocks.geoJSON.mock.calls.length - 1];
    geoJsonCall[1].pointToLayer(feature, [39.92, 116.73]);

    expect(leafletMocks.circleMarker).toHaveBeenCalledWith(
      [39.92, 116.73],
      expect.objectContaining({
        fillColor: "#ff0000",
        color: "#1F2933",
      }),
    );
  });

  it("未调查面要素渲染为灰边白填充", () => {
    const pendingFeature = createPolygonFeature("MGB-001", { 调查日期: "" });
    const surveyedFeature = createPolygonFeature("MGB-002", { 调查日期: "2026-05-02" });

    mountLeafletMap({
      popupFields: ["编号", "调查日期"],
      geojson: {
        type: "FeatureCollection",
        features: [pendingFeature, surveyedFeature],
      },
    });

    const geoJsonCall = leafletMocks.geoJSON.mock.calls[leafletMocks.geoJSON.mock.calls.length - 1];
    expect(geoJsonCall[1].style(pendingFeature)).toMatchObject({
      color: "#9CA3AF",
      fillColor: "#ffffff",
    });
    expect(geoJsonCall[1].style(surveyedFeature)).toMatchObject({
      color: "#1F2933",
      fillColor: "#ff0000",
    });
  });

  it("主点位图层使用 canvas 渲染器", () => {
    mountLeafletMap({
      popupFields: ["编号"],
      geojson: {
        type: "FeatureCollection",
        features: [createPointFeature("A-001", 116.73, 39.92)],
      },
    });

    expect(leafletMocks.canvas).toHaveBeenCalledWith({ padding: 0.5 });
    const geoJsonCall = leafletMocks.geoJSON.mock.calls[leafletMocks.geoJSON.mock.calls.length - 1];
    expect(geoJsonCall[1].renderer).toBe(leafletMocks.canvas.mock.results[0].value);
  });
});

describe("LeafletMap 点位样式", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    leafletMocks.maps.length = 0;
    leafletMocks.markers.length = 0;
    installGeolocationMock();
  });

  it("危害程度 view 的已调查点位仍按危害程度颜色渲染", () => {
    const feature = {
      type: "Feature",
      geometry: { type: "Point", coordinates: [116.73, 39.92] },
      properties: {
        危害程度: "重",
        调查日期: "2026-05-02",
      },
    };

    mountLeafletMap({
      popupFields: ["编号", "危害程度", "调查日期"],
      geojson: {
        type: "FeatureCollection",
        features: [feature],
      },
    });

    const geoJsonCall = leafletMocks.geoJSON.mock.calls[leafletMocks.geoJSON.mock.calls.length - 1];
    geoJsonCall[1].pointToLayer(feature, [39.92, 116.73]);

    expect(leafletMocks.circleMarker).toHaveBeenCalledWith(
      [39.92, 116.73],
      expect.objectContaining({
        radius: 11,
        fillColor: "#ff0000",
        color: "#1F2933",
        weight: 1.45,
        fillOpacity: 0.88,
      }),
    );
  });

  it("危害程度 view 的未调查点位渲染为灰色空心点", () => {
    const feature = {
      type: "Feature",
      geometry: { type: "Point", coordinates: [116.73, 39.92] },
      properties: {
        危害程度: "轻",
        调查日期: "",
      },
    };

    mountLeafletMap({
      popupFields: ["编号", "危害程度", "调查日期"],
      geojson: {
        type: "FeatureCollection",
        features: [feature],
      },
    });

    const geoJsonCall = leafletMocks.geoJSON.mock.calls[leafletMocks.geoJSON.mock.calls.length - 1];
    geoJsonCall[1].pointToLayer(feature, [39.92, 116.73]);

    expect(leafletMocks.circleMarker).toHaveBeenCalledWith(
      [39.92, 116.73],
      expect.objectContaining({
        radius: 8,
        fillColor: "#ffffff",
        color: "#9CA3AF",
        weight: 1.6,
        fillOpacity: 0.92,
      }),
    );
  });

  it("危害程度 view 会把白、无、无需防治和空值都渲染为无等级", () => {
    const features = ["白", "无", "无需防治", ""].map((level, index) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [116.73 + index * 0.01, 39.92] },
      properties: {
        编号: `MGB-${index + 1}`,
        危害程度: level,
      },
    }));

    mountLeafletMap({
      popupFields: ["编号", "危害程度"],
      geojson: {
        type: "FeatureCollection",
        features,
      },
    });

    const geoJsonCall = leafletMocks.geoJSON.mock.calls[leafletMocks.geoJSON.mock.calls.length - 1];
    features.forEach((feature, index) => {
      geoJsonCall[1].pointToLayer(feature, [39.92, 116.73 + index * 0.01]);
    });

    expect(leafletMocks.circleMarker.mock.calls).toHaveLength(4);
    leafletMocks.circleMarker.mock.calls.forEach(([, options]) => {
      expect(options).toMatchObject({
        radius: 7,
        fillColor: "#ffffff",
        color: "#1F2933",
        weight: 1.45,
      });
    });
  });

  it("非危害程度 view 点位固定显示为红色，不受调查状态或属性影响", () => {
    const feature = {
      type: "Feature",
      geometry: { type: "Point", coordinates: [116.73, 39.92] },
      properties: {
        危害程度: "轻",
        调查状态: "调查",
        调查日期: "2026-05-02",
      },
    };

    mountLeafletMap({
      popupFields: ["编号", "调查日期", "调查状态"],
      geojson: {
        type: "FeatureCollection",
        features: [feature],
      },
    });

    const geoJsonCall = leafletMocks.geoJSON.mock.calls[leafletMocks.geoJSON.mock.calls.length - 1];
    geoJsonCall[1].pointToLayer(feature, [39.92, 116.73]);

    expect(leafletMocks.circleMarker).toHaveBeenCalledWith(
      [39.92, 116.73],
      expect.objectContaining({
        radius: 8,
        fillColor: "#ff0000",
        color: "#1F2933",
        weight: 1.45,
      }),
    );
  });

  it("地块状态 view 按调查、伐除和其他状态渲染点位颜色", () => {
    const features = [
      createPointFeature("BL-001", 116.73, 39.92, { 地块状态: "" }),
      createPointFeature("BL-002", 116.74, 39.93, { 地块状态: "调查" }),
      createPointFeature("BL-003", 116.75, 39.94, { 地块状态: "伐除" }),
      createPointFeature("BL-004", 116.76, 39.95, { 地块状态: "未调查" }),
    ];

    mountLeafletMap({
      popupFields: ["编号", "地块状态"],
      geojson: {
        type: "FeatureCollection",
        features,
      },
    });

    const geoJsonCall = leafletMocks.geoJSON.mock.calls[leafletMocks.geoJSON.mock.calls.length - 1];
    features.forEach((feature) => {
      const [lng, lat] = feature.geometry.coordinates;
      geoJsonCall[1].pointToLayer(feature, [lat, lng]);
    });

    expect(leafletMocks.circleMarker.mock.calls).toEqual([
      [
        [39.92, 116.73],
        expect.objectContaining({
          radius: 8,
          fillColor: "#ffffff",
          color: "#1F2933",
          weight: 1.45,
          fillOpacity: 0.96,
        }),
      ],
      [
        [39.93, 116.74],
        expect.objectContaining({
          radius: 8,
          fillColor: "#ff0000",
          color: "#1F2933",
          weight: 1.45,
          fillOpacity: 0.88,
        }),
      ],
      [
        [39.94, 116.75],
        expect.objectContaining({
          radius: 8,
          fillColor: "#000000",
          color: "#1F2933",
          weight: 1.45,
          fillOpacity: 0.88,
        }),
      ],
      [
        [39.95, 116.76],
        expect.objectContaining({
          radius: 8,
          fillColor: "#ffffff",
          color: "#1F2933",
          weight: 1.45,
          fillOpacity: 0.96,
        }),
      ],
    ]);
  });

  it("面状图层按当前 view 的危害配置决定颜色", () => {
    const severityFeature = createPolygonFeature("MGB-001", { 危害程度: "中" });
    const regularFeature = createPolygonFeature("MGB-002", { 调查状态: "未调查" });

    mountLeafletMap({
      popupFields: ["编号", "危害程度"],
      geojson: {
        type: "FeatureCollection",
        features: [severityFeature],
      },
    });

    let geoJsonCall = leafletMocks.geoJSON.mock.calls[leafletMocks.geoJSON.mock.calls.length - 1];
    expect(geoJsonCall[1].style(severityFeature)).toMatchObject({
      color: "#1F2933",
      fillColor: "#fbff05",
    });

    vi.clearAllMocks();
    leafletMocks.maps.length = 0;
    leafletMocks.markers.length = 0;
    installGeolocationMock();

    mountLeafletMap({
      popupFields: ["编号", "调查状态"],
      geojson: {
        type: "FeatureCollection",
        features: [regularFeature],
      },
    });

    geoJsonCall = leafletMocks.geoJSON.mock.calls[leafletMocks.geoJSON.mock.calls.length - 1];
    expect(geoJsonCall[1].style(regularFeature)).toMatchObject({
      color: "#1F2933",
      fillColor: "#ff0000",
    });
  });

  it("地块状态面图层按调查、伐除和其他状态渲染颜色", () => {
    const defaultFeature = createPolygonFeature("BL-001", { 地块状态: "" });
    const surveyedFeature = createPolygonFeature("BL-002", { 地块状态: "调查" });
    const removedFeature = createPolygonFeature("BL-003", { 地块状态: "伐除" });

    mountLeafletMap({
      popupFields: ["编号", "地块状态"],
      geojson: {
        type: "FeatureCollection",
        features: [defaultFeature, surveyedFeature, removedFeature],
      },
    });

    const geoJsonCall = leafletMocks.geoJSON.mock.calls[leafletMocks.geoJSON.mock.calls.length - 1];

    expect(geoJsonCall[1].style(defaultFeature)).toMatchObject({
      color: "#1F2933",
      fillColor: "#ffffff",
      fillOpacity: 0.88,
      opacity: 0.98,
      weight: 1.5,
    });
    expect(geoJsonCall[1].style(surveyedFeature)).toMatchObject({
      color: "#1F2933",
      fillColor: "#ff0000",
      fillOpacity: 0.7,
      opacity: 0.98,
      weight: 1.5,
    });
    expect(geoJsonCall[1].style(removedFeature)).toMatchObject({
      color: "#1F2933",
      fillColor: "#000000",
      fillOpacity: 0.7,
      opacity: 0.98,
      weight: 1.5,
    });
  });

  it("美国白蛾视图悬停提示优先显示编号", () => {
    const feature = createPolygonFeature("MGB-001", { id: 12, 点位名称: "如意园" });
    const layer = {
      bindTooltip: vi.fn(),
      bindPopup: vi.fn(),
      on: vi.fn(),
    };

    mountLeafletMap({
      viewName: "2026_美国白蛾第 1 代调查",
      views: [{ name: "2026_美国白蛾第 1 代调查", columns: ["id", "编号", "点位名称"] }],
      popupFields: ["id", "编号", "点位名称"],
      geojson: {
        type: "FeatureCollection",
        features: [feature],
      },
    });

    const geoJsonCall = leafletMocks.geoJSON.mock.calls[leafletMocks.geoJSON.mock.calls.length - 1];
    geoJsonCall[1].onEachFeature(feature, layer);

    expect(layer.bindTooltip).toHaveBeenCalledWith("MGB-001", expect.any(Object));
  });

  it("相近点位仍按原始坐标显示为多个独立点位", () => {
    const features = [
      createPointFeature("A-001", 116.7300, 39.9200),
      createPointFeature("A-002", 116.7301, 39.9201),
      createPointFeature("A-003", 116.7302, 39.9202),
    ];

    mountLeafletMap({
      popupFields: ["编号"],
      geojson: {
        type: "FeatureCollection",
        features,
      },
    });

    const geoJsonCall = leafletMocks.geoJSON.mock.calls[leafletMocks.geoJSON.mock.calls.length - 1];

    expect(geoJsonCall[0].features).toHaveLength(3);
    expect(geoJsonCall[0].features.map((feature) => feature.geometry.coordinates)).toEqual(
      features.map((feature) => feature.geometry.coordinates),
    );

    geoJsonCall[0].features.forEach((feature) => {
      const [lng, lat] = feature.geometry.coordinates;
      geoJsonCall[1].pointToLayer(feature, [lat, lng]);
    });

    expect(leafletMocks.circleMarker).toHaveBeenCalledTimes(3);
  });

  it("点击相近点位仍触发对应原始点位详情", () => {
    const features = [
      createPointFeature("A-001", 116.7300, 39.9200),
      createPointFeature("A-002", 116.7301, 39.9201),
    ];
    const wrapper = mountLeafletMap({
      popupFields: ["编号"],
      geojson: {
        type: "FeatureCollection",
        features,
      },
    });
    const mapInstance = leafletMocks.maps[0];
    const geoJsonCall = leafletMocks.geoJSON.mock.calls[leafletMocks.geoJSON.mock.calls.length - 1];
    const targetFeature = geoJsonCall[0].features[1];
    mapInstance.setView.mockClear();
    const layer = {
      bindTooltip: vi.fn(),
      on: vi.fn((event, handler) => {
        layer[event] = handler;
      }),
    };

    geoJsonCall[1].onEachFeature(targetFeature, layer);
    const originalEvent = { stopPropagation: vi.fn() };
    layer.click({ originalEvent });
    mapInstance.trigger("click", {
      latlng: {
        lat: 39.7,
        lng: 116.5,
      },
    });

    expect(layer.bindTooltip).toHaveBeenCalledWith("A-002", expect.any(Object));
    expect(leafletMocks.DomEvent.stopPropagation).toHaveBeenCalledWith(originalEvent);
    expect(mapInstance.setView).not.toHaveBeenCalled();
    expect(wrapper.emitted("feature-click")).toEqual([[features[1]]]);
    expect(wrapper.emitted("map-click")).toBeUndefined();
  });

  it("缩放后仍按原始坐标显示独立点位", () => {
    const features = [
      createPointFeature("A-001", 116.7300, 39.9200),
      createPointFeature("A-002", 116.7301, 39.9201),
    ];

    mountLeafletMap({
      popupFields: ["编号"],
      geojson: {
        type: "FeatureCollection",
        features,
      },
    });
    const mapInstance = setMapViewport({
      zoom: 18,
      contains: () => true,
    });

    mapInstance.trigger("zoomend");

    const geoJsonCall = leafletMocks.geoJSON.mock.calls[leafletMocks.geoJSON.mock.calls.length - 1];
    expect(geoJsonCall[0].features).toHaveLength(2);
    expect(geoJsonCall[0].features.map((feature) => feature.geometry.coordinates)).toEqual(
      features.map((feature) => feature.geometry.coordinates),
    );
  });
});

describe("LeafletMap 编号标签性能优化", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    leafletMocks.maps.length = 0;
    leafletMocks.markers.length = 0;
    installGeolocationMock();
  });

  it("关闭显示编号时不创建编号图层", () => {
    mountLeafletMap({
      geojson: {
        type: "FeatureCollection",
        features: [createPointFeature("A-001", 116.73, 39.92)],
      },
      showPointLabels: false,
    });

    expect(getPointLabelMarkerCalls()).toHaveLength(0);
  });

  it("缩放刷新后渲染当前视口内编号", () => {
    mountLeafletMap({
      geojson: {
        type: "FeatureCollection",
        features: [createPointFeature("A-001", 116.73, 39.92)],
      },
      showPointLabels: true,
    });

    expect(getPointLabelMarkerCalls()).toHaveLength(1);
    leafletMocks.marker.mockClear();

    const mapInstance = setMapViewport({
      zoom: 13,
      contains: () => true,
    });

    mapInstance.trigger("zoomend");

    expect(getPointLabelMarkerCalls()).toHaveLength(1);
    expect(getPointLabelMarkerCalls()[0][0]).toEqual([39.92, 116.73]);
  });

  it("刷新编号时仅渲染当前视口内编号", () => {
    mountLeafletMap({
      geojson: {
        type: "FeatureCollection",
        features: [
          createPointFeature("A-001", 116.73, 39.92, { 危害程度: "重" }),
          createPointFeature("B-002", 117.1, 40.1, { 危害程度: "白" }),
        ],
      },
      showPointLabels: true,
    });
    leafletMocks.marker.mockClear();
    leafletMocks.markers.length = 0;
    leafletMocks.layerGroup.mockClear();
    const mapInstance = setMapViewport({
      zoom: 14,
      contains: ([lat, lng]) => lat === 39.92 && lng === 116.73,
    });

    mapInstance.trigger("zoomend");

    expect(leafletMocks.layerGroup).toHaveBeenCalledTimes(1);
    expect(getPointLabelMarkerCalls()).toHaveLength(1);
    expect(getPointLabelMarkerCalls()[0][0]).toEqual([39.92, 116.73]);
    expect(getPointLabelMarkerHtml()[0]).toContain("A-001");
  });

  it("编号标签遮挡时自动换到无碰撞方位", () => {
    mountLeafletMap({
      geojson: {
        type: "FeatureCollection",
        features: [
          createPointFeature("A-001", 116.73, 39.92),
          createPointFeature("A-002", 116.7301, 39.9201),
        ],
      },
      showPointLabels: true,
    });

    const labelCalls = getPointLabelMarkerCalls();
    const labelHtml = getPointLabelMarkerHtml();

    // 视觉顶层点位优先占右侧，被遮挡点位自动换到左侧放置
    expect(labelCalls).toHaveLength(2);
    expect(labelCalls[0][0]).toEqual([39.9201, 116.7301]);
    expect(labelHtml[0]).toContain("A-002");
    expect(labelHtml[0]).toContain("map-point-label-text--right");
    expect(labelHtml[1]).toContain("A-001");
    expect(labelHtml[1]).toContain("map-point-label-text--left");
  });

  it("多边形点位也会在当前视口内渲染编号", () => {
    mountLeafletMap({
      geojson: {
        type: "FeatureCollection",
        features: [createPolygonFeature("MGB-001")],
      },
      showPointLabels: true,
    });
    leafletMocks.marker.mockClear();
    leafletMocks.markers.length = 0;
    leafletMocks.layerGroup.mockClear();
    const mapInstance = setMapViewport({
      zoom: 14,
      contains: () => true,
    });

    mapInstance.trigger("zoomend");

    expect(getPointLabelMarkerCalls()).toHaveLength(1);
    expect(getPointLabelMarkerCalls()[0][0]).toEqual([39.925, 116.735]);
    expect(getPointLabelMarkerHtml()[0]).toContain("MGB-001");
    expect(leafletMocks.markers[0].bindTooltip).not.toHaveBeenCalled();
  });

  it("编号标签无数量上限，未遮挡时全部渲染", () => {
    const features = Array.from({ length: 120 }, (_, index) =>
      createPointFeature(`A-${index + 1}`, 116.5 + index * 0.01, 39.8 + index * 0.01),
    );

    mountLeafletMap({
      geojson: {
        type: "FeatureCollection",
        features,
      },
      showPointLabels: true,
    });

    expect(getPointLabelMarkerCalls()).toHaveLength(120);
  });

  it("缩放和平移只刷新编号标签，不重建点位层", () => {
    mountLeafletMap({
      geojson: {
        type: "FeatureCollection",
        features: [createPointFeature("A-001", 116.73, 39.92)],
      },
      showPointLabels: true,
    });
    const mapInstance = setMapViewport({
      zoom: 14,
      contains: () => true,
    });

    expect(leafletMocks.geoJSON).toHaveBeenCalledTimes(1);
    expect(leafletMocks.layerGroup).toHaveBeenCalledTimes(1);
    expect(getPointLabelMarkerCalls()).toHaveLength(1);

    mapInstance.trigger("zoomend");

    expect(leafletMocks.geoJSON).toHaveBeenCalledTimes(1);
    expect(leafletMocks.layerGroup).toHaveBeenCalledTimes(2);

    mapInstance.trigger("moveend");

    expect(leafletMocks.geoJSON).toHaveBeenCalledTimes(1);
    expect(leafletMocks.layerGroup).toHaveBeenCalledTimes(3);
    expect(getPointLabelMarkerCalls()).toHaveLength(3);
  });

  it("切换显示编号开关时只影响编号图层", async () => {
    const wrapper = mountLeafletMap({
      geojson: {
        type: "FeatureCollection",
        features: [createPointFeature("A-001", 116.73, 39.92)],
      },
      showPointLabels: false,
    });
    setMapViewport({
      zoom: 14,
      contains: () => true,
    });

    expect(leafletMocks.geoJSON).toHaveBeenCalledTimes(1);

    await wrapper.setProps({ showPointLabels: true });

    expect(leafletMocks.geoJSON).toHaveBeenCalledTimes(1);
    expect(getPointLabelMarkerCalls()).toHaveLength(1);

    const firstLabelLayer = leafletMocks.layerGroup.mock.results[0].value;
    await wrapper.setProps({ showPointLabels: false });

    expect(leafletMocks.geoJSON).toHaveBeenCalledTimes(1);
    expect(firstLabelLayer.remove).toHaveBeenCalledTimes(1);
  });
});
