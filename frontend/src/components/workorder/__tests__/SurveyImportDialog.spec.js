import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import SurveyImportDialog from "../SurveyImportDialog.vue";

function buildResponse(payload, ok = true) {
  return {
    ok,
    async json() {
      return payload;
    },
  };
}

describe("SurveyImportDialog", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("查询后默认全选并导入全部结果", async () => {
    global.fetch.mockResolvedValue(
      buildResponse([
        {
          survey_date: "2026-04-01",
          town_or_street: "于家务乡",
          location_id: "YF0069",
          location_name: "神仙村",
          total_insect_count: 50,
          damage_level: "重",
          note: "",
          description: "描述1",
        },
        {
          survey_date: "2026-04-01",
          town_or_street: "于家务乡",
          location_id: "YF0070",
          location_name: "前南定村",
          total_insect_count: 18,
          damage_level: "中",
          note: "需复查",
          description: "描述2",
        },
      ]),
    );

    const wrapper = mount(SurveyImportDialog, {
      props: {
        open: true,
      },
      global: {
        stubs: {
          teleport: true,
        },
      },
    });

    await wrapper.get("#survey-import-date").setValue("2026-04-01");
    await wrapper.get('[data-testid="survey-query-button"]').trigger("click");
    await flushPromises();

    expect(global.fetch).toHaveBeenCalledWith("/api/survey/candidates?date=2026-04-01");
    expect(wrapper.text()).toContain("共 2 条记录，已选择 2 条");

    await wrapper.get('[data-testid="survey-import-confirm"]').trigger("click");

    const events = wrapper.emitted("import");
    expect(events).toBeTruthy();
    expect(events[0][0]).toHaveLength(2);
    expect(events[0][0][1].location_id).toBe("YF0070");
  });

  it("查询无结果时显示空状态并禁用导入", async () => {
    global.fetch.mockResolvedValue(buildResponse([]));

    const wrapper = mount(SurveyImportDialog, {
      props: {
        open: true,
      },
      global: {
        stubs: {
          teleport: true,
        },
      },
    });

    await wrapper.get("#survey-import-date").setValue("2026-04-02");
    await wrapper.get('[data-testid="survey-query-button"]').trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("未找到可导入的调查记录");
    expect(wrapper.get('[data-testid="survey-import-confirm"]').attributes("disabled")).toBeDefined();
  });
});
