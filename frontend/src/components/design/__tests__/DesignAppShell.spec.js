import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { describe, expect, it } from "vitest";

import DesignAppShell from "../DesignAppShell.vue";

const OverviewStub = { template: "<div>概览内容</div>" };
const WorkorderStub = { template: "<div>工单内容</div>" };
const MapStub = { template: "<div>地图内容</div>" };

async function mountShell(initialPath = "/design/overview") {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/design/overview",
        component: OverviewStub,
        meta: { previewPage: "工作概览页" },
      },
      {
        path: "/design/workorder",
        component: WorkorderStub,
        meta: { previewPage: "调查工单页" },
      },
      {
        path: "/design/map",
        component: MapStub,
        meta: { previewPage: "调查点位地图页" },
      },
      {
        path: "/design",
        component: { template: "<div>迁移状态</div>" },
      },
    ],
  });

  await router.push(initialPath);
  await router.isReady();

  return {
    router,
    wrapper: mount(DesignAppShell, {
      global: {
        plugins: [router],
      },
      slots: {
        default: "<div>页面内容</div>",
      },
    }),
  };
}

describe("DesignAppShell", () => {
  it("桌面导航会高亮当前预览路由并展示静态账号摘要", async () => {
    const { wrapper } = await mountShell();

    expect(wrapper.get('[data-testid="design-nav-overview"]').classes()).toContain(
      "router-link-exact-active",
    );
    expect(wrapper.get('[data-testid="design-nav-workorder"]').attributes("href")).toBe(
      "/design/workorder",
    );
    expect(wrapper.get('[data-testid="design-nav-map"]').attributes("href")).toBe("/design/map");
    expect(wrapper.text()).toContain("李明远");
    expect(wrapper.text()).toContain("海淀区调查员");
  });

  it("移动菜单支持打开、遮罩关闭和切换路由后关闭", async () => {
    const { router, wrapper } = await mountShell();

    await wrapper.get('[data-testid="design-mobile-menu"]').trigger("click");
    expect(wrapper.get(".design-app-sidebar").classes()).toContain("is-mobile-open");
    expect(wrapper.find('[data-testid="design-sidebar-backdrop"]').exists()).toBe(true);

    await wrapper.get('[data-testid="design-sidebar-backdrop"]').trigger("click");
    expect(wrapper.get(".design-app-sidebar").classes()).not.toContain("is-mobile-open");

    await wrapper.get('[data-testid="design-mobile-menu"]').trigger("click");
    await wrapper.get('[data-testid="design-nav-map"]').trigger("click");
    await flushPromises();

    expect(router.currentRoute.value.fullPath).toBe("/design/map");
    expect(wrapper.get(".design-app-sidebar").classes()).not.toContain("is-mobile-open");
  });
});
