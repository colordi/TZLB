import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import DesignMapView from "../design/DesignMapView.vue";

function mountMap() {
  return mount(DesignMapView);
}

describe("DesignMapView", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("渲染静态模拟地图和阶段 5.2 详情抽屉", () => {
    const wrapper = mountMap();

    expect(wrapper.get(".design-map-canvas").text()).toContain("海淀区");
    expect(wrapper.get('[data-testid="design-map-search"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="design-map-layer-button"]').exists()).toBe(true);
    expect(wrapper.find(".design-map-mobile-bar").exists()).toBe(true);
    expect(wrapper.get('[data-testid="design-map-detail-drawer"]').text()).toContain(
      "香山公园东门林带",
    );
    expect(wrapper.find(".leaflet-container").exists()).toBe(false);
  });

  it("状态筛选和筛选卡折叠只改变本地展示状态", async () => {
    const wrapper = mountMap();

    await wrapper.get('[data-testid="design-map-status-alert"]').trigger("click");

    expect(wrapper.get('[data-testid="design-map-status-alert"]').classes()).toContain(
      "is-active",
    );
    expect(wrapper.find(".design-map-marker.is-active.is-hidden").exists()).toBe(true);
    expect(wrapper.get('[data-testid="design-map-stage-note"]').text()).toContain("状态筛选");

    await wrapper.get('[data-testid="design-map-filter-toggle"]').trigger("click");
    expect(wrapper.get(".design-map-filter-card").classes()).toContain("is-collapsed");
  });

  it("图层面板和基础图层开关只影响静态画布样式", async () => {
    const wrapper = mountMap();

    await wrapper.get('[data-testid="design-map-layer-button"]').trigger("click");
    expect(wrapper.get(".design-map-layer-panel").classes()).toContain("is-open");

    const gridToggle = wrapper.find(".design-map-layer-group input[type='checkbox']");
    await gridToggle.setValue(false);

    expect(wrapper.get(".design-map-canvas").classes()).toContain("hide-grid");

    await wrapper.get('[data-testid="design-map-point-layer-american-moth"]').trigger("click");
    expect(
      wrapper.get('[data-testid="design-map-point-layer-american-moth"]').classes(),
    ).not.toContain("is-active");
  });

  it("点击代表点位切换本地点位详情", async () => {
    const wrapper = mountMap();

    await wrapper.get('[data-testid="design-map-point-p6"]').trigger("click");

    const drawer = wrapper.get('[data-testid="design-map-detail-drawer"]');
    expect(drawer.classes()).toContain("is-open");
    expect(drawer.text()).toContain("昌平东小口森林公园");
    expect(drawer.text()).toContain("重度");
    expect(drawer.text()).toContain("连续林带发现多处网幕");
    expect(wrapper.get('[data-testid="design-map-point-p6"]').classes()).toContain(
      "is-selected",
    );
    expect(wrapper.get('[data-testid="design-map-stage-note"]').text()).toContain(
      "昌平东小口森林公园",
    );
  });

  it("点击聚合点展示聚合范围详情", async () => {
    const wrapper = mountMap();

    await wrapper.get('[data-testid="design-map-point-cluster1"]').trigger("click");

    const drawer = wrapper.get('[data-testid="design-map-detail-drawer"]');
    expect(drawer.text()).toContain("朝阳区中部聚合点位");
    expect(drawer.text()).toContain("18 个点位 · 当前缩放级别");
    expect(drawer.text()).toContain("放大地图可查看聚合范围内的独立调查点位");
  });

  it("详情抽屉可关闭并可通过移动点位按钮重新打开", async () => {
    const wrapper = mountMap();

    await wrapper.get('[data-testid="design-map-detail-close"]').trigger("click");
    expect(wrapper.get('[data-testid="design-map-detail-drawer"]').classes()).not.toContain(
      "is-open",
    );

    await wrapper.get('[data-testid="design-map-mobile-points"]').trigger("click");
    expect(wrapper.get('[data-testid="design-map-detail-drawer"]').classes()).toContain(
      "is-open",
    );
  });

  it("预览交互不会请求真实接口", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const wrapper = mountMap();

    await wrapper.get('[data-testid="design-map-layer-button"]').trigger("click");
    await wrapper.get('[data-testid="design-map-mobile-layers"]').trigger("click");
    await wrapper.get('[data-testid="design-map-mobile-filter"]').trigger("click");
    await wrapper.get('[data-testid="design-map-status-new"]').trigger("click");
    await wrapper.get('[data-testid="design-map-point-p3"]').trigger("click");
    await wrapper.get('[data-testid="design-map-point-cluster2"]').trigger("click");

    expect(fetchMock).not.toHaveBeenCalled();
  });
});
