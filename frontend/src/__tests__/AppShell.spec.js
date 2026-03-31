import { defineComponent } from "vue";
import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { describe, expect, it } from "vitest";

import App from "../App.vue";

const WorkorderStub = defineComponent({
  template: "<div>工单页内容</div>",
});

const MapStub = defineComponent({
  template: "<div>地图页内容</div>",
});

async function mountApp(initialPath = "/workorder") {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/workorder",
        component: WorkorderStub,
        meta: {
          section: "工单录入",
        },
      },
      {
        path: "/map",
        component: MapStub,
        meta: {
          section: "调查点位",
        },
      },
    ],
  });

  router.push(initialPath);
  await router.isReady();

  const wrapper = mount(App, {
    global: {
      plugins: [router],
      stubs: {
        ToastViewport: true,
      },
    },
  });

  await flushPromises();
  return { wrapper, router };
}

describe("App 壳层导航", () => {
  it("顶部导航会高亮当前路由，且不再展示当前页面卡片", async () => {
    const { wrapper } = await mountApp("/workorder");

    const activeLink = wrapper.get(".site-nav-link.router-link-active");
    expect(activeLink.text()).toContain("工单录入");
    expect(wrapper.find(".sidebar-context").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("当前页面");
  });

  it("移动抽屉点击遮罩后会关闭", async () => {
    const { wrapper } = await mountApp("/workorder");

    await wrapper.get('[data-testid="mobile-menu-trigger"]').trigger("click");
    expect(wrapper.find('[data-testid="mobile-drawer-overlay"]').exists()).toBe(true);

    await wrapper.get('[data-testid="mobile-drawer-overlay"]').trigger("click");
    await flushPromises();

    expect(wrapper.find('[data-testid="mobile-drawer-overlay"]').exists()).toBe(false);
  });

  it("移动抽屉在切换路由后会自动关闭", async () => {
    const { wrapper, router } = await mountApp("/workorder");

    await wrapper.get('[data-testid="mobile-menu-trigger"]').trigger("click");
    await wrapper.get('[data-testid="drawer-link-map"]').trigger("click");
    await flushPromises();

    expect(router.currentRoute.value.path).toBe("/map");
    expect(wrapper.find('[data-testid="mobile-drawer-overlay"]').exists()).toBe(false);
  });
});
