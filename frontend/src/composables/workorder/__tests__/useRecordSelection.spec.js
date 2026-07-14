import { effectScope, ref } from "vue";
import { describe, expect, it } from "vitest";

import { useRecordSelection, WORKORDER_PAGE_SIZE } from "../useRecordSelection.js";

function buildRecord(id, name = `点位${id}`) {
  return {
    __uid: `uid-${id}`,
    location_id: id,
    location_name: name,
    locality: "测试乡镇",
    description: "",
    note: "",
  };
}

function withSelection(records, run) {
  const scope = effectScope();
  try {
    const validationErrors = ref(records.value.map(() => ({})));
    const selection = scope.run(() => useRecordSelection(records, validationErrors));
    return run(selection);
  } finally {
    scope.stop();
  }
}

describe("useRecordSelection 分页", () => {
  it("默认每页 10 条，翻页后返回对应切片", () => {
    const records = ref(
      Array.from({ length: 12 }, (_, index) => buildRecord(`ID${index + 1}`)),
    );

    withSelection(records, (selection) => {
      expect(WORKORDER_PAGE_SIZE).toBe(10);
      expect(selection.pagedRecords.value).toHaveLength(10);
      expect(selection.totalPages.value).toBe(2);
      expect(selection.serialOffset.value).toBe(0);

      selection.goToNextPage();
      expect(selection.currentPage.value).toBe(2);
      expect(selection.pagedRecords.value).toHaveLength(2);
      expect(selection.pagedRecords.value[0].location_id).toBe("ID11");
      expect(selection.serialOffset.value).toBe(10);
    });
  });

  it("搜索或筛选变化时回到第一页", () => {
    const records = ref(
      Array.from({ length: 15 }, (_, index) => buildRecord(`ID${index + 1}`, `名称${index + 1}`)),
    );

    withSelection(records, (selection) => {
      selection.goToPage(2);
      expect(selection.currentPage.value).toBe(2);

      selection.searchQuery.value = "名称1";
      expect(selection.currentPage.value).toBe(1);
    });
  });
});
