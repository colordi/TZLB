import { describe, expect, it } from "vitest";

import {
  PEST_TABLE_RULES,
  groupTablesByPest,
  shortTableLabel,
} from "../tableGroups.js";

function makeTable(schemaName, tableName, extra = {}) {
  return {
    schema_name: schemaName,
    table_name: tableName,
    has_primary_key: true,
    primary_key: ["id"],
    row_estimate: 100,
    ...extra,
  };
}

/** 数据库中实际存在的全部可管理表 */
function allTables() {
  return [
    makeTable("survey", "春尺蠖成虫调查表"),
    makeTable("survey", "春尺蠖幼虫调查表"),
    makeTable("survey", "春尺蠖围环调查表"),
    makeTable("survey", "国槐尺蠖幼虫调查表"),
    makeTable("survey", "美国白蛾调查表"),
    makeTable("survey", "其他害虫调查表"),
    makeTable("survey", "杨树食叶害虫调查表"),
    makeTable("ledger", "春尺蠖问题点位事件流水表"),
    makeTable("ledger", "国槐尺蠖问题点位事件流水表"),
    makeTable("ledger", "美国白蛾问题点位事件流水表"),
    makeTable("ledger", "其他害虫问题点位事件流水表"),
    makeTable("ledger", "杨树食叶害虫问题点位事件流水表"),
    makeTable("sites", "杨树点位基础表"),
    makeTable("sites", "国槐点位基础表"),
    makeTable("sites", "美国白蛾点位基础表"),
    makeTable("sites", "美国白蛾小区点位基础表"),
    makeTable("sites", "其他害虫点位基础表"),
    makeTable("sites", "杨树食叶害虫点位基础表"),
    makeTable("sites", "监测点位基础表"),
  ];
}

describe("datamanager/tableGroups groupTablesByPest", () => {
  it("按固定虫种顺序分组，每组表数量正确", () => {
    const groups = groupTablesByPest(allTables());

    expect(groups.map((g) => g.pest)).toEqual([
      "春尺蠖",
      "国槐尺蠖",
      "美国白蛾",
      "其他害虫",
      "杨树食叶害虫",
      "监测点位",
    ]);
    expect(groups.map((g) => g.tables.length)).toEqual([5, 3, 4, 3, 3, 1]);
  });

  it("杨树点位基础表归入春尺蠖，国槐点位基础表归入国槐尺蠖", () => {
    const groups = groupTablesByPest(allTables());
    const byPest = Object.fromEntries(
      groups.map((g) => [g.pest, g.tables.map((t) => t.table_name)]),
    );

    expect(byPest["春尺蠖"]).toContain("杨树点位基础表");
    expect(byPest["国槐尺蠖"]).toContain("国槐点位基础表");
    expect(byPest["国槐尺蠖"]).not.toContain("杨树点位基础表");
  });

  it("杨树食叶害虫与美国白蛾小区点位表有明确归属", () => {
    const groups = groupTablesByPest(allTables());
    const byPest = Object.fromEntries(
      groups.map((g) => [g.pest, g.tables.map((t) => t.table_name)]),
    );

    expect(byPest["杨树食叶害虫"]).toEqual([
      "杨树食叶害虫调查表",
      "杨树食叶害虫问题点位事件流水表",
      "杨树食叶害虫点位基础表",
    ]);
    expect(byPest["美国白蛾"]).toContain("美国白蛾小区点位基础表");
    expect(byPest["监测点位"]).toEqual(["监测点位基础表"]);
  });

  it("全部可管理表都被分组覆盖，无遗漏", () => {
    const groups = groupTablesByPest(allTables());
    const groupedKeys = new Set(
      groups.flatMap((g) =>
        g.tables.map((t) => `${t.schema_name}.${t.table_name}`),
      ),
    );

    for (const table of allTables()) {
      expect(groupedKeys).toContain(`${table.schema_name}.${table.table_name}`);
    }
  });

  it("组内表顺序遵循规则清单的声明顺序", () => {
    const groups = groupTablesByPest(allTables());
    const spring = groups.find((g) => g.pest === "春尺蠖");

    expect(spring.tables.map((t) => `${t.schema_name}.${t.table_name}`)).toEqual([
      "survey.春尺蠖成虫调查表",
      "survey.春尺蠖幼虫调查表",
      "survey.春尺蠖围环调查表",
      "ledger.春尺蠖问题点位事件流水表",
      "sites.杨树点位基础表",
    ]);
  });

  it("未匹配任何规则的表不进入任何分组", () => {
    const groups = groupTablesByPest([
      makeTable("survey", "美国白蛾调查表"),
      makeTable("reference", "通州区行政区边界"),
    ]);

    expect(groups.map((g) => g.pest)).toEqual(["美国白蛾"]);
  });

  it("没有匹配表的虫种分组不出现", () => {
    const groups = groupTablesByPest([makeTable("survey", "美国白蛾调查表")]);

    expect(groups.map((g) => g.pest)).toEqual(["美国白蛾"]);
  });

  it("空清单返回空数组", () => {
    expect(groupTablesByPest([])).toEqual([]);
    expect(groupTablesByPest(undefined)).toEqual([]);
  });

  it("分组规则覆盖的表名全部唯一", () => {
    const keys = PEST_TABLE_RULES.flatMap((rule) => rule.tables);
    expect(new Set(keys).size).toBe(keys.length);
  });
});

describe("datamanager/tableGroups shortTableLabel", () => {
  it("去掉虫种前缀", () => {
    expect(shortTableLabel("春尺蠖成虫调查表", "春尺蠖")).toBe("成虫调查表");
    expect(shortTableLabel("美国白蛾调查表", "美国白蛾")).toBe("调查表");
  });

  it("事件流水表和点位基础表简化显示", () => {
    expect(shortTableLabel("美国白蛾问题点位事件流水表", "美国白蛾")).toBe(
      "事件流水表",
    );
    expect(shortTableLabel("美国白蛾点位基础表", "美国白蛾")).toBe("点位基础表");
  });

  it("表名不含虫种前缀时保留完整表名", () => {
    expect(shortTableLabel("杨树点位基础表", "春尺蠖")).toBe("杨树点位基础表");
    expect(shortTableLabel("国槐点位基础表", "国槐尺蠖")).toBe("国槐点位基础表");
  });

  it("同一虫种多张点位表时保留区分前缀", () => {
    expect(shortTableLabel("美国白蛾点位基础表", "美国白蛾")).toBe("点位基础表");
    expect(shortTableLabel("美国白蛾小区点位基础表", "美国白蛾")).toBe(
      "小区点位基础表",
    );
  });

  it("监测点位分组去掉监测点位前缀", () => {
    expect(shortTableLabel("监测点位基础表", "监测点位")).toBe("基础表");
  });

  it("空表名返回空字符串", () => {
    expect(shortTableLabel("", "春尺蠖")).toBe("");
    expect(shortTableLabel(undefined, "春尺蠖")).toBe("");
  });
});
