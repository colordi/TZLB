import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import DesignLoginView from "../design/DesignLoginView.vue";

describe("DesignLoginView", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("密码显示切换只更新本地展示状态", async () => {
    const wrapper = mount(DesignLoginView);
    const passwordInput = wrapper.get("#design-login-password");
    const toggleButton = wrapper.get(".design-login-password-toggle");

    expect(passwordInput.attributes("type")).toBe("password");
    expect(toggleButton.attributes("aria-pressed")).toBe("false");

    await toggleButton.trigger("click");

    expect(passwordInput.attributes("type")).toBe("text");
    expect(toggleButton.attributes("aria-pressed")).toBe("true");
  });

  it("提交静态表单时不调用真实接口", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const wrapper = mount(DesignLoginView);

    await wrapper.get("#design-login-username").setValue("preview-user");
    await wrapper.get("#design-login-password").setValue("preview-password");
    await wrapper.get("form").trigger("submit");

    expect(fetchMock).not.toHaveBeenCalled();
  });
});
