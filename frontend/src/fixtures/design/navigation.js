export const DESIGN_NAV_GROUPS = Object.freeze([
  Object.freeze({
    label: "业务管理",
    items: Object.freeze([
      Object.freeze({
        key: "overview",
        label: "工作概览",
        to: "/design/overview",
        icon: "overview",
      }),
      Object.freeze({
        key: "workorder",
        label: "调查工单",
        to: "/design/workorder",
        icon: "workorder",
        count: "18",
      }),
      Object.freeze({
        key: "map",
        label: "点位地图",
        to: "/design/map",
        icon: "map",
        count: "127",
      }),
    ]),
  }),
  Object.freeze({
    label: "数据与配置",
    items: Object.freeze([
      Object.freeze({
        key: "analytics",
        label: "统计分析",
        icon: "analytics",
        placeholder: true,
      }),
      Object.freeze({
        key: "settings",
        label: "基础配置",
        icon: "settings",
        placeholder: true,
      }),
    ]),
  }),
]);

export const DESIGN_PREVIEW_PROFILE = Object.freeze({
  initial: "李",
  name: "李明远",
  role: "海淀区调查员",
});
