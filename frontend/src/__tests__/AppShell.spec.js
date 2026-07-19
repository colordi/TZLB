import { defineComponent } from "vue";
import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App.vue";
import { resetAuthSessionState, signIn } from "../composables/useAuthSession.js";

const WorkorderStub = defineComponent({
  template: "<div>工单页内容</div>",
});

const MapStub = defineComponent({
  template: "<div>地图页内容</div>",
});

const DataExportStub = defineComponent({
  template: "<div>数据导出页内容</div>",
});

const DataStatisticsStub = defineComponent({
  template: "<div>数据统计页内容</div>",
});

const LoginStub = defineComponent({
  template: '<div data-testid="login-shell-stub">登录页内容</div>',
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
      {
        path: "/data-import",
        component: DataExportStub,
        meta: {
          section: "调查数据导入",
        },
      },
      {
        path: "/workorder-assets",
        component: DataExportStub,
        meta: {
          section: "工单素材",
        },
      },
      {
        path: "/data-export",
        component: DataExportStub,
        meta: {
          section: "数据导出",
        },
      },
      {
        path: "/data-statistics",
        component: DataStatisticsStub,
        meta: {
          section: "数据统计",
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
        // 将 Teleport 就地渲染，避免 jsdom 卸载问题，同时保留下拉/Sheet 内容
        Teleport: {
          template: "<div class='teleport-stub'><slot /></div>",
        },
      },
    },
  });

  await flushPromises();
  return { wrapper, router };
}

describe("App 壳层导航", () => {
  beforeEach(() => {
    resetAuthSessionState();
    // Sidebar 默认展开
    document.cookie = "sidebar_state=true; path=/";
    // SidebarProvider 用 useMediaQuery；测试默认桌面宽度
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    resetAuthSessionState();
    document.cookie = "sidebar_state=; path=/; max-age=0";
  });

  it("侧栏导航会高亮当前路由，顶栏仅保留面包屑与账号，且不再展示当前页面卡片", async () => {
    const { wrapper } = await mountApp("/workorder");

    expect(wrapper.findAll(".site-header")).toHaveLength(1);
    expect(wrapper.findAll(".app-sidebar")).toHaveLength(1);
    expect(wrapper.find('[data-testid="header-link-workorder"]').exists()).toBe(false);

    const activeSidebar = wrapper.get(
      '[data-testid="sidebar-link-workorder"].router-link-active',
    );
    expect(activeSidebar.text()).toContain("工单录入");
    expect(wrapper.get(".site-section-title").text()).toContain("工单录入");
    expect(wrapper.text()).not.toContain("当前页面");
  });

  it("侧边栏折叠按钮位于品牌行并能切换折叠状态", async () => {
    const { wrapper } = await mountApp("/workorder");

    const brandRow = wrapper.get(".app-sidebar-brand-row");
    const toggleButton = brandRow.get(".sidebar-toggle-btn");
    const initialLabel = toggleButton.attributes("aria-label");
    expect(["收起侧边栏", "展开侧边栏"]).toContain(initialLabel);

    await toggleButton.trigger("click");
    await flushPromises();

    expect(toggleButton.attributes("aria-label")).not.toBe(initialLabel);
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

    await wrapper.get(".user-dropdown-wrap").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("退出登录");
  });

  it("移动端提供打开导航的入口", async () => {
    window.matchMedia = vi.fn().mockImplementation((query) => ({
      matches: String(query).includes("max-width"),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    const { wrapper } = await mountApp("/workorder");

    const trigger = wrapper.find('[data-testid="mobile-menu-trigger"]');
    expect(trigger.exists()).toBe(true);
    expect(trigger.attributes("aria-label")).toBe("打开导航菜单");
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
  });

  it("管理员账号展示数据管理准备入口与导出入口", async () => {
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

    expect(wrapper.get('[data-testid="sidebar-link-data-import"]').text()).toContain(
      "调查数据导入",
    );
    expect(wrapper.get('[data-testid="sidebar-link-workorder-assets"]').text()).toContain(
      "工单素材",
    );
    expect(wrapper.get('[data-testid="sidebar-link-data-export"]').text()).toContain(
      "数据导出",
    );
  });

  it("管理员账号展示数据统计入口", async () => {
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

    expect(wrapper.get('[data-testid="sidebar-link-data-statistics"]').text()).toContain(
      "数据统计",
    );
  });

  it("调查员账号不展示数据导出入口", async () => {
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

    expect(wrapper.find('[data-testid="sidebar-link-data-export"]').exists()).toBe(false);
  });

  it("调查员账号不展示数据统计入口", async () => {
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

    expect(wrapper.find('[data-testid="sidebar-link-data-statistics"]').exists()).toBe(
      false,
    );
  });

  it("地图页使用满宽主内容区", async () => {
    const { wrapper } = await mountApp("/map");

    expect(wrapper.get(".site-main").classes()).toContain("is-full-bleed");
  });

  it("地图页顶部栏不再展示图层选择与筛选入口", async () => {
    const { wrapper } = await mountApp("/map");

    await flushPromises();

    expect(wrapper.findAll(".site-header")).toHaveLength(1);
    expect(wrapper.get(".site-header").classes()).not.toContain("map-header");
    expect(wrapper.find(".site-header-shell--map").exists()).toBe(false);
    expect(wrapper.get(".site-brand").text()).toContain("林业调查工作台");
    expect(wrapper.find('button[aria-label="切换图层"]').exists()).toBe(false);
    expect(wrapper.find("#map-layer-menu").exists()).toBe(false);
    expect(wrapper.find(".map-view-select").exists()).toBe(false);
    expect(wrapper.find('button[aria-label="筛选配置"]').exists()).toBe(false);
  });

  it("登录页使用独立布局，不展示顶部导航", async () => {
    const { wrapper } = await mountApp("/login");

    expect(wrapper.find(".site-header").exists()).toBe(false);
    expect(wrapper.get('[data-testid="login-shell-stub"]').text()).toContain("登录页内容");
  });
});
