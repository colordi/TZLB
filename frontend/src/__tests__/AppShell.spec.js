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
  });

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

  it("登录页使用独立布局，不展示顶部导航", async () => {
    const { wrapper } = await mountApp("/login");

    expect(wrapper.find(".site-header").exists()).toBe(false);
    expect(wrapper.get('[data-testid="login-shell-stub"]').text()).toContain("登录页内容");
  });
});
