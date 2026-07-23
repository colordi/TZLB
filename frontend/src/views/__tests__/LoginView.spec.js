import { defineComponent } from "vue";
import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { resetAuthSessionState } from "../../composables/useAuthSession.js";
import LoginView from "../LoginView.vue";

const MapStub = defineComponent({
  template: "<div>地图页</div>",
});

const WorkorderStub = defineComponent({
  template: "<div>工单页</div>",
});

async function mountLogin(initialPath = "/login") {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: "/login",
        component: LoginView,
      },
      {
        path: "/map",
        component: MapStub,
      },
      {
        path: "/workorder",
        component: WorkorderStub,
      },
    ],
  });

  router.push(initialPath);
  await router.isReady();

  const wrapper = mount(LoginView, {
    global: {
      plugins: [router],
    },
    attachTo: document.body,
  });

  await flushPromises();

  return { wrapper, router };
}

describe("LoginView", () => {
  let fetchMock;

  beforeEach(() => {
    window.localStorage.clear();
    resetAuthSessionState();
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    document.body.innerHTML = "";
  });

  it("会回填记住的用户名", async () => {
    window.localStorage.setItem("tzlb.rememberedUsername", "护林员甲");

    const { wrapper } = await mountLogin();

    expect(wrapper.get("#login-username").element.value).toBe("护林员甲");
    // reka Checkbox 用 data-state 表示勾选
    const remember = wrapper.get("#remember-me");
    expect(
      remember.attributes("data-state") === "checked" ||
        remember.element.getAttribute("aria-checked") === "true" ||
        remember.element.checked === true,
    ).toBe(true);
  });

  it("密码显示切换只更新本地输入框类型", async () => {
    const { wrapper } = await mountLogin();
    const passwordInput = wrapper.get("#login-password");
    const toggleButton = wrapper.get('[data-testid="login-password-toggle"]');

    expect(passwordInput.attributes("type")).toBe("password");
    expect(toggleButton.attributes("aria-pressed")).toBe("false");

    await toggleButton.trigger("click");

    expect(passwordInput.attributes("type")).toBe("text");
    expect(toggleButton.attributes("aria-pressed")).toBe("true");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("提交后会保存用户名并跳转到目标页面", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        user: {
          id: 1,
          username: "巡查员乙",
          display_name: "巡查员乙",
          is_active: true,
          last_login_at: null,
        },
      }),
    });

    const { wrapper, router } = await mountLogin("/login?redirect=%2Fworkorder");

    await wrapper.get("#login-username").setValue("巡查员乙");
    await wrapper.get("#login-password").setValue("secret");

    // 勾选记住我（reka Checkbox）
    const remember = wrapper.get("#remember-me");
    await remember.trigger("click");
    await flushPromises();

    await wrapper.get("form").trigger("submit.prevent");
    await flushPromises();

    expect(window.localStorage.getItem("tzlb.rememberedUsername")).toBe("巡查员乙");
    expect(router.currentRoute.value.fullPath).toBe("/workorder");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/login",
      expect.objectContaining({
        method: "POST",
        credentials: "same-origin",
      }),
    );
  });
});
