/**
 * 数据管理页：业务表 → 虫种分组的纯逻辑（便于单测）。
 *
 * 匹配采用显式的 schema.表名 清单而非子串匹配：
 * "国槐点位基础表"含"国槐"但不含"国槐尺蠖"、"杨树点位基础表"是春尺蠖专用，
 * 子串匹配会归错组，因此规则集中维护在 PEST_TABLE_RULES 中，调整时只改这里。
 * 未匹配到任何规则的表不会出现在页面上——新增可管理表时必须在此显式归组。
 */

/** 虫种分组规则，数组顺序即 Tab 展示顺序 */
export const PEST_TABLE_RULES = [
  {
    pest: "春尺蠖",
    tables: [
      "survey.春尺蠖成虫调查表",
      "survey.春尺蠖幼虫调查表",
      "survey.春尺蠖围环调查表",
      "ledger.春尺蠖问题点位事件流水表",
      "sites.杨树点位基础表",
    ],
  },
  {
    pest: "国槐尺蠖",
    tables: [
      "survey.国槐尺蠖幼虫调查表",
      "ledger.国槐尺蠖问题点位事件流水表",
      "sites.国槐点位基础表",
    ],
  },
  {
    pest: "美国白蛾",
    tables: [
      "survey.美国白蛾调查表",
      "ledger.美国白蛾问题点位事件流水表",
      "sites.美国白蛾点位基础表",
      "sites.美国白蛾小区点位基础表",
    ],
  },
  {
    pest: "其他害虫",
    tables: [
      "survey.其他害虫调查表",
      "ledger.其他害虫问题点位事件流水表",
      "sites.其他害虫点位基础表",
    ],
  },
  {
    pest: "杨树食叶害虫",
    tables: [
      "survey.杨树食叶害虫调查表",
      "ledger.杨树食叶害虫问题点位事件流水表",
      "sites.杨树食叶害虫点位基础表",
    ],
  },
  {
    pest: "监测点位",
    tables: [
      "sites.监测点位基础表",
    ],
  },
];

function tableKey(table) {
  return `${table.schema_name}.${table.table_name}`;
}

/**
 * 把表清单按虫种分组，返回 [{ pest, tables: [...] }]。
 * 只返回非空分组；未匹配到任何规则的表不进入任何分组。
 * 各分组内表的顺序遵循 PEST_TABLE_RULES 中的声明顺序。
 */
export function groupTablesByPest(tables) {
  const remaining = new Map((tables || []).map((t) => [tableKey(t), t]));
  const groups = [];

  for (const rule of PEST_TABLE_RULES) {
    const matched = [];
    for (const key of rule.tables) {
      if (remaining.has(key)) {
        matched.push(remaining.get(key));
        remaining.delete(key);
      }
    }
    if (matched.length > 0) {
      groups.push({ pest: rule.pest, tables: matched });
    }
  }

  return groups;
}

/**
 * 虫种 Tab 内二级表选择的简化显示名：
 * 去掉虫种前缀，并把"问题点位事件流水表"缩短为"事件流水表"。
 * 点位基础表不做后缀缩短——同一虫种可能有多张点位表（如美国白蛾的小区点位表），
 * 前缀部分（杨树/国槐/小区）是区分依据，需保留。
 * 完整表名由页面通过 title 悬浮展示。
 */
export function shortTableLabel(tableName, pest) {
  if (!tableName) {
    return "";
  }
  let label =
    pest && tableName.startsWith(pest) ? tableName.slice(pest.length) : tableName;
  if (label.endsWith("问题点位事件流水表")) {
    label = "事件流水表";
  }
  return label || tableName;
}
