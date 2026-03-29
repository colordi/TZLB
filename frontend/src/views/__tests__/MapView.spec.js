import { defineComponent } from "vue";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MapView from "../MapView.vue";

const apiMocks = vi.hoisted(() => ({
  listMapViews: vi.fn(),
  fetchMapView: vi.fn(),
  fetchMapFilterOptions: vi.fn(),
  fetchAdminBoundary: vi.fn(),
}));

vi.mock("../../api/map.js", () => ({
  listMapViews: apiMocks.listMapViews,
  fetchMapView: apiMocks.fetchMapView,
  fetchMapFilterOptions: apiMocks.fetchMapFilterOptions,
  fetchAdminBoundary: apiMocks.fetchAdminBoundary,
}));

const LeafletMapStub = defineComponent({
  name: "LeafletMap",
  props: {
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
    viewName: {
      type: String,
      default: "",
    },
  },
  template: "<div />",
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
        MapLegend: true,
      },
    },
  });
}

function getLeafletMapStub(wrapper) {
  return wrapper.getComponent(LeafletMapStub);
}

describe("MapView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.listMapViews.mockResolvedValue([
      {
        name: "虫情总览",
        columns: ["乡镇", "村", "调查日期"],
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
      townships: [],
      supports_township_filter: false,
      supports_survey_status_filter: false,
    });
    apiMocks.fetchAdminBoundary.mockResolvedValue({
      type: "FeatureCollection",
      features: [],
    });
  });

  it("初始加载后把默认选中 view 的 columns 传给 LeafletMap", async () => {
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      const mapStub = getLeafletMapStub(wrapper);

      expect(mapStub.props("viewName")).toBe("虫情总览");
      expect(mapStub.props("popupFields")).toEqual(["乡镇", "村", "调查日期"]);
    });
  });

  it("切换 view 后更新传给 LeafletMap 的 popupFields", async () => {
    const wrapper = mountMapView();

    await vi.waitFor(() => {
      const mapStub = getLeafletMapStub(wrapper);

      expect(mapStub.props("viewName")).toBe("虫情总览");
    });

    await wrapper.get(".map-view-field select").setValue("高风险点位");

    await vi.waitFor(() => {
      const mapStub = getLeafletMapStub(wrapper);

      expect(mapStub.props("viewName")).toBe("高风险点位");
      expect(mapStub.props("popupFields")).toEqual(["编号", "总虫口数"]);
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

    await wrapper.get(".map-view-field select").setValue("高风险点位");

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

    await wrapper.get(".map-view-field select").setValue("高风险点位");

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
});
