import { getPestConfig } from "./pestRegistry.js";

const FIELD_DEFINITIONS = {
  survey_date: {
    key: "survey_date",
    label: "调查日期",
    type: "date",
    required: true,
  },
  region: {
    key: "region",
    label: "区域",
    type: "select",
    options: ["乡镇", "城区"],
  },
  locality: {
    key: "locality",
    label: "属地",
    type: "text",
    required: true,
  },
  town_or_street: {
    key: "town_or_street",
    label: "属地",
    type: "text",
    required: true,
  },
  location_id: {
    key: "location_id",
    label: "编号",
    type: "text",
    required: true,
  },
  location_name: {
    key: "location_name",
    label: "点位名称",
    type: "text",
    required: true,
  },
  occurrence_position: {
    key: "occurrence_position",
    label: "发生位置",
    type: "text",
  },
  total_insect_count: {
    key: "total_insect_count",
    label: "总虫口数",
    type: "number",
  },
  damage_level: {
    key: "damage_level",
    label: "受害程度",
    type: "select",
    options: ["轻", "中", "重"],
  },
  pest_name: {
    key: "pest_name",
    label: "虫害类型",
    type: "text",
  },
  host_plant: {
    key: "host_plant",
    label: "寄主树种",
    type: "text",
  },
  green_space_type: {
    key: "green_space_type",
    label: "绿地性质",
    type: "text",
  },
  pest_hosts: {
    key: "pest_hosts",
    label: "危害寄主",
    type: "text",
  },
  damaged_plant_count: {
    key: "damaged_plant_count",
    label: "受害株数",
    type: "number",
  },
  web_nest_count: {
    key: "web_nest_count",
    label: "网幕数量",
    type: "number",
  },
  plot_type: {
    key: "plot_type",
    label: "地块类型",
    type: "text",
  },
  report_time: {
    key: "report_time",
    label: "上报时间",
    type: "date",
  },
  description: {
    key: "description",
    label: "详细情况描述",
    type: "textarea",
    required: true,
  },
  note: {
    key: "note",
    label: "备注",
    type: "text",
  },
};


function getFieldKeysByPest(pestType) {
  return getPestConfig(pestType).fieldKeys;
}

export function getVisibleFields(pestType) {
  return getFieldKeysByPest(pestType).map((key) => FIELD_DEFINITIONS[key]);
}

export { FIELD_DEFINITIONS, getFieldKeysByPest };
