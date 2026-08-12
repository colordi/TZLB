import OtherPestsStatisticsPanel from "./OtherPestsStatisticsPanel.vue";
import SophoraInchwormStatisticsPanel from "./SophoraInchwormStatisticsPanel.vue";
import WhiteMothStatisticsPanel from "./WhiteMothStatisticsPanel.vue";

/**
 * 数据统计模块注册表。
 * 新增统计模块时：补充一条记录 + 对应 Panel 组件 + 后端 /api/statistics/<pest>/ 端点。
 */
export const STATISTICS_MODULES = Object.freeze([
  {
    value: "white-moth",
    label: "美国白蛾",
    disabled: false,
    component: WhiteMothStatisticsPanel,
  },
  { value: "poplar-inchworm", label: "春尺蠖", disabled: true, component: null },
  {
    value: "sophora-inchworm",
    label: "国槐尺蠖",
    disabled: false,
    component: SophoraInchwormStatisticsPanel,
  },
  {
    value: "other-pests",
    label: "其他害虫",
    disabled: false,
    component: OtherPestsStatisticsPanel,
  },
]);

export const DEFAULT_STATISTICS_MODULE = STATISTICS_MODULES[0].value;

export function resolveStatisticsModule(pest) {
  return (
    STATISTICS_MODULES.find((module) => module.value === pest && !module.disabled) || null
  );
}
