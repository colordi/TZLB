import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import RecordTable from "../RecordTable.vue";
import { createEmptyRecord } from "../fieldConfig.js";

function buildRecord(overrides = {}) {
  return {
    ...createEmptyRecord("春尺蠖"),
    town_or_street: "城东镇",
    location_id: "CC-001",
    location_name: "城东林场A区",
    description: "虫情记录",
    ...overrides,
  };
}

describe("RecordTable", () => {
  it("复制记录时会向外发出包含新增记录的结果", async () => {
    const wrapper = mount(RecordTable, {
      props: {
        records: [buildRecord()],
        pestType: "春尺蠖",
      },
    });

    await wrapper.get('[data-testid="duplicate-record-0"]').trigger("click");

    const events = wrapper.emitted("update:records");
    expect(events).toBeTruthy();
    const latestRecords = events.at(-1)?.[0];
    expect(latestRecords).toHaveLength(2);
    expect(latestRecords[1].location_name).toBe("城东林场A区");
  });

  it("删除唯一记录时仍会保留一条空白记录", async () => {
    const wrapper = mount(RecordTable, {
      props: {
        records: [buildRecord()],
        pestType: "春尺蠖",
      },
    });

    await wrapper.get('[data-testid="delete-record-0"]').trigger("click");

    const events = wrapper.emitted("update:records");
    expect(events).toBeTruthy();
    const latestRecords = events.at(-1)?.[0];
    expect(latestRecords).toHaveLength(1);
    expect(latestRecords[0].location_name).toBe("");
  });
});
