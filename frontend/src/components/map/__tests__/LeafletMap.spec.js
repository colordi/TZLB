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
      const mapInstance = {
        element,
        options,
        fitBounds: vi.fn(),
        getZoom: vi.fn(() => 11),
        remove: vi.fn(),
        setView: vi.fn(function setView() {
          return this;
        }),
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

function mountLeafletMap() {
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
});
