import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";

import { Button } from "../button";
import { Input } from "../input";
import { Label } from "../label";
import { Card, CardHeader, CardTitle, CardContent } from "../card";
import { Badge } from "../badge";
import { Separator } from "../separator";
import { Skeleton } from "../skeleton";

describe("shadcn-vue primitives smoke", () => {
  it("Button 可挂载", () => {
    const wrapper = mount(Button, {
      slots: { default: "保存" },
    });
    expect(wrapper.text()).toContain("保存");
    expect(wrapper.attributes("data-slot")).toBe("button");
  });

  it("Input + Label 可挂载", () => {
    const label = mount(Label, { slots: { default: "用户名" } });
    const input = mount(Input, {
      props: { modelValue: "admin", type: "text" },
      attrs: { id: "username" },
    });
    expect(label.text()).toBe("用户名");
    expect(input.element.value).toBe("admin");
  });

  it("Card 组合可挂载", () => {
    const wrapper = mount({
      components: { Card, CardHeader, CardTitle, CardContent },
      template: `
        <Card>
          <CardHeader>
            <CardTitle>标题</CardTitle>
          </CardHeader>
          <CardContent>内容</CardContent>
        </Card>
      `,
    });
    expect(wrapper.text()).toContain("标题");
    expect(wrapper.text()).toContain("内容");
  });

  it("Badge / Separator / Skeleton 可挂载", () => {
    expect(mount(Badge, { slots: { default: "标签" } }).text()).toBe("标签");
    expect(mount(Separator).exists()).toBe(true);
    expect(mount(Skeleton).exists()).toBe(true);
  });
});
