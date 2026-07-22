/**
 * 数据管理页：业务表 → 虫种分组的纯逻辑（便于单测）。
 *
 * 匹配采用显式的 schema.表名 清单而非子串匹配：
 * "国槐点位基础表"含"国槐"但不含"国槐尺蠖"、"杨树点位基础表"是春尺蠖专用，
 * 子串匹配会归错组，因此规则集中维护在 PEST_TABLE_RULES 中，调整时只改这里。
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
];

/** 无法归入任何虫种的表进入的兜底分组名（固定排在最后） */
export const FALLBACK_GROUP = "通用";

function tableKey(table) {
  return `${table.schema_name}.${table.table_name}`;
}

/**
 * 把表清单按虫种分组，返回 [{ pest, tables: [...] }]。
 * 只返回非空分组；未匹配到任何虫种的表归入最后的"通用"分组。
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

  if (remaining.size > 0) {
    groups.push({ pest: FALLBACK_GROUP, tables: [...remaining.values()] });
  }

  return groups;
}

/**
 * 虫种 Tab 内二级表选择的简化显示名：
 * 去掉虫种前缀，并把"问题点位事件流水表 / 点位基础表"缩短为"事件流水表 / 点位基础表"。
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
  } else if (label.endsWith("点位基础表")) {
    label = "点位基础表";
  }
  return label || tableName;
}
