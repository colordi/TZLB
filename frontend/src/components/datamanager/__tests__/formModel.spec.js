import { describe, expect, it } from "vitest";

import {
  editableColumns,
  gridColumns,
  buildInitialValues,
  validateFormValues,
  buildSubmitValues,
  isRequiredColumn,
  diffChangeLog,
} from "../formModel.js";

function col(overrides = {}) {
  return {
    name: "字段",
    data_type: "text",
    is_nullable: true,
    has_default: false,
    is_primary_key: false,
    is_readonly: false,
    is_geometry: false,
    input_kind: "text",
    enum_labels: [],
    ...overrides,
  };
}

describe("datamanager/formModel editableColumns", () => {
  it("过滤只读列", () => {
    const columns = [
      col({ name: "id", is_readonly: true }),
      col({ name: "编号" }),
      col({ name: "geom", is_readonly: true, is_geometry: true, input_kind: "text" }),
    ];

    expect(editableColumns(columns).map((c) => c.name)).toEqual(["编号"]);
  });

  it("空输入返回空数组", () => {
    expect(editableColumns(null)).toEqual([]);
    expect(editableColumns(undefined)).toEqual([]);
  });
});

describe("datamanager/formModel gridColumns", () => {
  it("过滤几何列", () => {
    const columns = [
      col({ name: "编号" }),
      col({ name: "geom", is_geometry: true }),
      col({ name: "属地" }),
    ];

    expect(gridColumns(columns).map((c) => c.name)).toEqual(["编号", "属地"]);
  });
});

describe("datamanager/formModel isRequiredColumn", () => {
  it("不可为空且无默认值的非只读列为必填", () => {
    expect(
      isRequiredColumn(col({ is_nullable: false, has_default: false })),
    ).toBe(true);
  });

  it("可空、有默认值或只读的列非必填", () => {
    expect(isRequiredColumn(col({ is_nullable: true }))).toBe(false);
    expect(isRequiredColumn(col({ is_nullable: false, has_default: true }))).toBe(false);
    expect(isRequiredColumn(col({ is_nullable: false, is_readonly: true }))).toBe(false);
  });
});

describe("datamanager/formModel buildInitialValues", () => {
  const columns = [
    col({ name: "id", is_readonly: true, input_kind: "number" }),
    col({ name: "编号", input_kind: "text" }),
    col({ name: "年份", input_kind: "number" }),
    col({ name: "调查日期", input_kind: "date" }),
    col({ name: "修改时间", input_kind: "datetime" }),
    col({ name: "是否完成", input_kind: "bool" }),
    col({ name: "危害程度", input_kind: "select", enum_labels: ["轻", "中", "重"] }),
  ];

  it("新增时按 input_kind 生成空值", () => {
    const values = buildInitialValues(columns);

    expect(values).toEqual({
      编号: "",
      年份: "",
      调查日期: "",
      修改时间: "",
      是否完成: false,
      危害程度: "",
    });
    expect(values).not.toHaveProperty("id");
  });

  it("编辑时用行数据填充并规范化日期格式", () => {
    const row = {
      编号: "BM-01",
      年份: 2026,
      调查日期: "2026-07-01T00:00:00",
      修改时间: "2026-07-01T08:30:45+08:00",
      是否完成: 1,
      危害程度: "中",
    };

    const values = buildInitialValues(columns, row);

    expect(values["编号"]).toBe("BM-01");
    expect(values["年份"]).toBe(2026);
    expect(values["调查日期"]).toBe("2026-07-01");
    expect(values["修改时间"]).toBe("2026-07-01T08:30");
    expect(values["是否完成"]).toBe(true);
    expect(values["危害程度"]).toBe("中");
  });

  it("编辑时行内空值转为控件空值", () => {
    const values = buildInitialValues(columns, {
      编号: null,
      年份: null,
      调查日期: null,
      修改时间: null,
      是否完成: null,
      危害程度: null,
    });

    expect(values["编号"]).toBe("");
    expect(values["年份"]).toBe("");
    expect(values["是否完成"]).toBe(false);
  });
});

describe("datamanager/formModel validateFormValues", () => {
  const columns = [
    col({ name: "编号", is_nullable: false }),
    col({ name: "属地", is_nullable: true }),
    col({ name: "年份", is_nullable: false, has_default: true, input_kind: "number" }),
    col({ name: "是否完成", is_nullable: false, input_kind: "bool" }),
    col({ name: "id", is_nullable: false, is_readonly: true, input_kind: "number" }),
  ];

  it("必填列为空时返回错误消息", () => {
    const errors = validateFormValues(
      columns,
      { 编号: "", 属地: "", 年份: "", 是否完成: false },
      { isCreate: true },
    );

    expect(errors).toEqual({ 编号: "编号为必填项" });
  });

  it("必填列有值时校验通过", () => {
    const errors = validateFormValues(
      columns,
      { 编号: "BM-01", 属地: "", 年份: "", 是否完成: false },
      { isCreate: true },
    );

    expect(errors).toEqual({});
  });

  it("纯空白字符串视为未填写", () => {
    const errors = validateFormValues(
      columns,
      { 编号: "   ", 属地: "", 年份: "", 是否完成: false },
      { isCreate: false },
    );

    expect(errors).toHaveProperty("编号");
  });

  it("布尔必填列不参与空值校验", () => {
    const errors = validateFormValues(
      [col({ name: "是否完成", is_nullable: false, input_kind: "bool" })],
      { 是否完成: false },
      { isCreate: true },
    );

    expect(errors).toEqual({});
  });
});

describe("datamanager/formModel buildSubmitValues", () => {
  it("空字符串转 null，number 列转数值，bool 列转布尔", () => {
    const columns = [
      col({ name: "编号", input_kind: "text" }),
      col({ name: "年份", input_kind: "number" }),
      col({ name: "备注", input_kind: "text" }),
      col({ name: "是否完成", input_kind: "bool" }),
    ];

    const values = buildSubmitValues(columns, {
      编号: "BM-01",
      年份: "2026",
      备注: "",
      是否完成: 1,
    });

    expect(values).toEqual({
      编号: "BM-01",
      年份: 2026,
      备注: null,
      是否完成: true,
    });
  });
});

describe("datamanager/formModel diffChangeLog", () => {
  it("update 动作返回字段级差异", () => {
    const item = {
      action: "update",
      before: { 编号: "BM-01", 属地: "宋庄", 年份: 2025 },
      after: { 编号: "BM-01", 属地: "梨园", 年份: 2025 },
    };

    expect(diffChangeLog(item)).toEqual([
      { field: "属地", before: "宋庄", after: "梨园" },
    ]);
  });

  it("before/after 中缺失的键按 null 处理", () => {
    const item = {
      action: "update",
      before: { 编号: "BM-01" },
      after: { 编号: "BM-01", 备注: "新增备注" },
    };

    expect(diffChangeLog(item)).toEqual([
      { field: "备注", before: null, after: "新增备注" },
    ]);
  });

  it("insert / delete 动作返回空数组", () => {
    expect(diffChangeLog({ action: "insert", after: { a: 1 } })).toEqual([]);
    expect(diffChangeLog({ action: "delete", before: { a: 1 } })).toEqual([]);
    expect(diffChangeLog(null)).toEqual([]);
  });

  it("值未变化时返回空数组", () => {
    const item = {
      action: "update",
      before: { 编号: "BM-01", 年份: 2026 },
      after: { 编号: "BM-01", 年份: 2026 },
    };

    expect(diffChangeLog(item)).toEqual([]);
  });
});
