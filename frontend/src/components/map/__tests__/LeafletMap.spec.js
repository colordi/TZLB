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
    circleMarker: vi.fn(() => createLayer()),
    control: {
      zoom: vi.fn(() => ({
        addTo: vi.fn(function addTo() {
          return this;
        }),
        remove: vi.fn(),
      })),
    },
    divIcon: vi.fn((options) => options),
    geoJSON: vi.fn(() => createLayer()),
    layerGroup: vi.fn(() => createLayer()),
    map: vi.fn((element, options) => {
      const eventHandlers = {};
      const mapInstance = {
        element,
        options,
        boundsContains: () => true,
        currentZoom: 11,
        fitBounds: vi.fn(),
        getBounds: vi.fn(() => ({
          contains: vi.fn((latlng) => mapInstance.boundsContains(latlng)),
        })),
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

  it("标准底图只加载基础瓦片层", () => {
    mountLeafletMap({ basemapMode: "standard" });

    expect(leafletMocks.tileLayer).toHaveBeenCalledTimes(1);
    expect(leafletMocks.tileLayer).toHaveBeenCalledWith(
      expect.stringContaining("openstreetmap"),
      expect.objectContaining({ maxZoom: 19 }),
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

  it("添加点位模式关闭时点击地图不会抛出经纬度", () => {
    const wrapper = mountLeafletMap();
    const mapInstance = leafletMocks.maps[0];

    mapInstance.trigger("click", {
      latlng: {
        lat: 39.7,
        lng: 116.5,
      },
    });

    expect(wrapper.emitted("map-click")).toBeUndefined();
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

  it("含危害程度字段时只显示无、轻、中、重图例", () => {
    const wrapper = mountLeafletMap({
      popupFields: ["编号", "危害程度", "调查状态"],
    });

    expect(getLegendLabels(wrapper)).toEqual(["无", "轻", "中", "重"]);
    expect(wrapper.find(".map-status-legend").exists()).toBe(false);
  });

  it("不含危害程度字段时只显示危害点位图例", () => {
    const wrapper = mountLeafletMap({
      popupFields: ["编号", "调查日期", "调查状态"],
    });

    expect(getLegendLabels(wrapper)).toEqual(["危害点位"]);
    expect(wrapper.text()).not.toContain("未调查");
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

    expect(leafletMocks.marker).not.toHaveBeenCalled();
    expect(leafletMocks.circleMarker).toHaveBeenCalledWith(
      [39.92, 116.73],
      expect.objectContaining({
        radius: 11,
        fillColor: "#EC6D64",
        color: "#000000",
        weight: 1.45,
        fillOpacity: 0.88,
      }),
    );
  });

  it("危害程度 view 的未调查点位也按危害程度颜色渲染", () => {
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

    expect(leafletMocks.marker).not.toHaveBeenCalled();
    expect(leafletMocks.circleMarker).toHaveBeenCalledWith(
      [39.92, 116.73],
      expect.objectContaining({
        radius: 7,
        fillColor: "#68C17A",
        color: "#000000",
        weight: 1.45,
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
        fillColor: "#FFFFFF",
        color: "#000000",
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
        fillColor: "#EC6D64",
        color: "#000000",
        weight: 1.45,
      }),
    );
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
      color: "#000000",
      fillColor: "#F0C048",
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
      color: "#000000",
      fillColor: "#EC6D64",
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

  it("相近点位会合并为带数量的聚合标记", () => {
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
    const clusteredFeature = geoJsonCall[0].features[0];

    expect(geoJsonCall[0].features).toHaveLength(1);
    expect(clusteredFeature.properties.__isPointCluster).toBe(true);
    expect(clusteredFeature.properties.__clusterCount).toBe(3);

    geoJsonCall[1].pointToLayer(clusteredFeature, [39.9201, 116.7301]);

    expect(getPointClusterMarkerCalls()).toHaveLength(1);
    expect(getPointClusterMarkerCalls()[0][1].icon.html).toContain(">3<");
  });

  it("聚合标记点击后放大到聚合中心，不触发单点选择", () => {
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
    const clusteredFeature = geoJsonCall[0].features[0];
    const layer = {
      bindTooltip: vi.fn(),
      on: vi.fn((event, handler) => {
        layer[event] = handler;
      }),
    };

    geoJsonCall[1].onEachFeature(clusteredFeature, layer);
    layer.click();

    expect(layer.bindTooltip).toHaveBeenCalledWith("2 个点位", expect.any(Object));
    expect(mapInstance.setView).toHaveBeenCalledWith(
      [39.92005, 116.73005],
      13,
      { animate: true },
    );
    expect(wrapper.emitted("feature-click")).toBeUndefined();
  });

  it("放大到聚合上限后恢复显示单个点位", () => {
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
    expect(geoJsonCall[0].features[0].properties.__isPointCluster).toBeUndefined();
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

    expect(leafletMocks.layerGroup).not.toHaveBeenCalled();
    expect(getPointLabelMarkerCalls()).toHaveLength(0);
  });

  it("低缩放级别隐藏编号标签，放大后再渲染当前视口内编号", () => {
    mountLeafletMap({
      geojson: {
        type: "FeatureCollection",
        features: [createPointFeature("A-001", 116.73, 39.92)],
      },
      showPointLabels: true,
    });

    expect(leafletMocks.layerGroup).not.toHaveBeenCalled();
    expect(getPointLabelMarkerCalls()).toHaveLength(0);

    const mapInstance = setMapViewport({
      zoom: 13,
      contains: () => true,
    });

    mapInstance.trigger("zoomend");

    expect(leafletMocks.layerGroup).toHaveBeenCalledTimes(1);
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

  it("聚合中的点位不会继续渲染编号标签", () => {
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
    const mapInstance = setMapViewport({
      zoom: 14,
      contains: () => true,
    });

    mapInstance.trigger("zoomend");

    expect(getPointLabelMarkerCalls()).toHaveLength(0);
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

  it("当前视口内编号超过上限时最多只渲染100个", () => {
    const features = Array.from({ length: 260 }, (_, index) =>
      createPointFeature(`A-${index + 1}`, 116.5 + index * 0.001, 39.8 + index * 0.001),
    );

    mountLeafletMap({
      geojson: {
        type: "FeatureCollection",
        features,
      },
      showPointLabels: true,
    });
    const mapInstance = setMapViewport({
      zoom: 14,
      contains: () => true,
    });

    mapInstance.trigger("zoomend");

    expect(getPointLabelMarkerCalls()).toHaveLength(100);
  });

  it("缩放会重算聚合，平移只刷新编号标签", () => {
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

    mapInstance.trigger("zoomend");
    mapInstance.trigger("moveend");

    expect(leafletMocks.geoJSON).toHaveBeenCalledTimes(2);
    expect(leafletMocks.layerGroup).toHaveBeenCalledTimes(2);
    expect(getPointLabelMarkerCalls()).toHaveLength(2);
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
