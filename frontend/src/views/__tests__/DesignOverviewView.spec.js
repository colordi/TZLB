import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import DesignOverviewView from "../design/DesignOverviewView.vue";

async function mountOverview() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/design/overview", component: DesignOverviewView },
      { path: "/design/login", component: { template: "<div>登录预览</div>" } },
      { path: "/design/map", component: { template: "<div>地图预览</div>" } },
      { path: "/design/workorder", component: { template: "<div>工单预览</div>" } },
    ],
  });

  await router.push("/design/overview");
  await router.isReady();

  return {
    router,
    wrapper: mount(DesignOverviewView, {
      global: {
        plugins: [router],
      },
    }),
  };
}

describe("DesignOverviewView", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("所有入口只指向隔离设计预览路由", async () => {
    const { wrapper } = await mountOverview();

    expect(wrapper.get('[data-testid="design-overview-entry-map"]').attributes("href")).toBe(
      "/design/map",
    );
    expect(wrapper.get('[data-testid="design-overview-entry-workorder"]').attributes("href")).toBe(
      "/design/workorder",
    );
  });

  it("点击地图入口不调用真实接口", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const { router, wrapper } = await mountOverview();

    await wrapper.get('[data-testid="design-overview-entry-map"]').trigger("click");
    await flushPromises();

    expect(router.currentRoute.value.fullPath).toBe("/design/map");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
