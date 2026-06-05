import { defineComponent, onMounted } from "vue";
import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App.vue";
import { resetAuthSessionState, signIn } from "../composables/useAuthSession.js";
import { mapActions } from "../stores/mapStore.js";

const WorkorderStub = defineComponent({
  template: "<div>工单页内容</div>",
});

const MapStub = defineComponent({
  setup() {
    onMounted(() => {
      mapActions.setReady(true);
      mapActions.setViews([{ name: "虫情总览" }]);
      mapActions.setSelectedView("虫情总览");
      mapActions.setBasemapMode("satellite");
      mapActions.setShowPointLabels(true);
    });
  },
  template: "<div>地图页内容</div>",
});

const LoginStub = defineComponent({
  template: "<div data-testid=\"login-shell-stub\">登录页内容</div>",
});

async function seedAuthUser(user) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        user,
      }),
    }),
  );
  await signIn({ username: user.username, password: "test-password" });
}

async function mountApp(initialPath = "/workorder", options = {}) {
  resetAuthSessionState();
  if (options.user) {
    await seedAuthUser(options.user);
  }

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/login",
        component: LoginStub,
        meta: {
          section: "登录",
          hideShell: true,
        },
      },
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
          fullBleed: true,
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
  beforeEach(() => {
    resetAuthSessionState();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    resetAuthSessionState();
    mapActions.setReady(false);
  });

  it("顶部导航会高亮当前路由，且不再展示当前页面卡片", async () => {
    const { wrapper } = await mountApp("/workorder");

    expect(wrapper.findAll(".site-header")).toHaveLength(1);
    expect(wrapper.findAll(".app-sidebar")).toHaveLength(1);
    expect(wrapper.get(".site-header").classes()).not.toContain("map-header");

    const activeLink = wrapper.get(".site-nav-link.router-link-active");
    expect(activeLink.text()).toContain("工单录入");
    const activeSidebarLink = wrapper.get(".app-sidebar-link.router-link-active");
    expect(activeSidebarLink.text()).toContain("工单录入");
    expect(wrapper.find(".sidebar-context").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("当前页面");
  });

  it("侧边栏折叠按钮位于品牌行并能切换折叠状态", async () => {
    const { wrapper } = await mountApp("/workorder");

    const brandRow = wrapper.get(".app-sidebar-brand-row");
    const toggleButton = brandRow.get(".sidebar-toggle-btn");
    expect(toggleButton.attributes("aria-label")).toBe("收起侧边栏");

    await toggleButton.trigger("click");
    await flushPromises();

    expect(wrapper.get(".app-sidebar").classes()).toContain("is-collapsed");
    expect(toggleButton.attributes("aria-label")).toBe("展开侧边栏");
  });

  it("普通页账号入口使用统一下拉菜单", async () => {
    const { wrapper } = await mountApp("/workorder", {
      user: {
        id: 1,
        username: "admin",
        display_name: "管理员",
        role: "admin",
        is_active: true,
        last_login_at: null,
      },
    });

    expect(wrapper.find(".logout-button:not(.logout-button--drawer)").exists()).toBe(false);

    await wrapper.get(".user-dropdown-wrap .user-pill").trigger("click");
    await flushPromises();

    const dropdown = wrapper.get(".user-dropdown");
    expect(dropdown.text()).toContain("退出登录");
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

  it("调查员账号不展示工单录入入口", async () => {
    const { wrapper } = await mountApp("/map", {
      user: {
        id: 2,
        username: "dc01",
        display_name: "调查员 dc01",
        role: "investigator",
        is_active: true,
        last_login_at: null,
      },
    });

    expect(wrapper.find('[data-testid="sidebar-link-workorder"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="sidebar-link-map"]').text()).toContain("调查点位");
    expect(wrapper.find('[data-testid="header-link-workorder"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="header-link-map"]').text()).toContain("调查点位");

    await wrapper.get('[data-testid="mobile-menu-trigger"]').trigger("click");
    expect(wrapper.find('[data-testid="drawer-link-workorder"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="drawer-link-map"]').text()).toContain("调查点位");
  });

  it("地图页使用满宽主内容区", async () => {
    const { wrapper } = await mountApp("/map");

    expect(wrapper.get(".site-main").classes()).toContain("is-full-bleed");
  });

  it("地图页顶部栏展示并展开图层菜单", async () => {
    const { wrapper } = await mountApp("/map");

    await flushPromises();

    expect(wrapper.findAll(".site-header")).toHaveLength(1);
    expect(wrapper.get(".site-header").classes()).not.toContain("map-header");
    expect(wrapper.find(".site-header-shell--map").exists()).toBe(false);
    expect(wrapper.get(".site-brand").text()).toContain("林业调查工作台");

    const layerButton = wrapper.get('button[aria-label="切换图层"]');
    expect(layerButton.text()).toContain("图层");

    await layerButton.trigger("click");
    await flushPromises();

    const layerMenu = wrapper.get("#map-layer-menu");
    expect(layerMenu.text()).toContain("标准地图");
    expect(layerMenu.text()).toContain("卫星地图");
    expect(layerMenu.text()).toContain("显示编号");
  });

  it("登录页使用独立布局，不展示顶部导航", async () => {
    const { wrapper } = await mountApp("/login");

    expect(wrapper.find(".site-header").exists()).toBe(false);
    expect(wrapper.get('[data-testid="login-shell-stub"]').text()).toContain("登录页内容");
  });
});
