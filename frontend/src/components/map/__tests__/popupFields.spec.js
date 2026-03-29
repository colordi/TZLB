import { describe, expect, it } from "vitest";
import { buildPopupRows } from "../popupFields.js";

describe("buildPopupRows", () => {
  it("按照当前 view 的 columns 顺序输出字段", () => {
    const columns = ["村", "乡镇", "编号"];
    const properties = {
      村: "南村",
      乡镇: "东镇",
      编号: "001",
    };

    expect(buildPopupRows(columns, properties)).toEqual([
      ["村", "南村"],
      ["乡镇", "东镇"],
      ["编号", "001"],
    ]);
  });

  it("只展示 columns 中存在的字段，不把其他属性混进弹窗", () => {
    const columns = ["编号"];
    const properties = {
      编号: "001",
      extra: "不应显示",
    };

    expect(buildPopupRows(columns, properties)).toEqual([["编号", "001"]]);
  });

  it("空值使用 - 占位", () => {
    const columns = ["调查日期"];

    expect(buildPopupRows(columns, {})).toEqual([["调查日期", "-"]]);
  });
});
