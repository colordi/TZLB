export const DESIGN_MAP_STATUS_FILTERS = Object.freeze([
  Object.freeze({ key: "all", label: "全部点位", count: 127, tone: "all" }),
  Object.freeze({ key: "alert", label: "需紧急处置", count: 12, tone: "alert" }),
  Object.freeze({ key: "active", label: "调查进行中", count: 38, tone: "active" }),
  Object.freeze({ key: "new", label: "待复核", count: 29, tone: "new" }),
  Object.freeze({ key: "done", label: "已完成", count: 48, tone: "done" }),
]);

export const DESIGN_MAP_BASE_LAYERS = Object.freeze([
  Object.freeze({ key: "grid", label: "区域网格", enabled: true }),
  Object.freeze({ key: "roads", label: "道路与边界", enabled: true }),
  Object.freeze({ key: "water", label: "水系", enabled: true }),
  Object.freeze({ key: "points", label: "调查点位", enabled: true }),
  Object.freeze({ key: "risk", label: "风险热力", enabled: false }),
]);

export const DESIGN_MAP_POINT_LAYERS = Object.freeze([
  Object.freeze({ key: "american-moth", label: "美国白蛾监测", count: 82, color: "#16a34a" }),
  Object.freeze({ key: "pest-monitor", label: "林业有害生物普查", count: 45, color: "#2563eb" }),
  Object.freeze({ key: "ancient-tree", label: "古树名木资源", count: 36, color: "#9333ea" }),
  Object.freeze({ key: "wetland", label: "湿地生态监测", count: 28, color: "#0891b2" }),
  Object.freeze({ key: "fire-risk", label: "森林火险预警", count: 15, color: "#dc2626" }),
]);

export const DESIGN_MAP_DISTRICTS = Object.freeze([
  Object.freeze({ key: "haidian", label: "海淀区" }),
  Object.freeze({ key: "chaoyang", label: "朝阳区" }),
  Object.freeze({ key: "fengtai", label: "丰台区" }),
  Object.freeze({ key: "changping", label: "昌平区" }),
]);

export const DESIGN_MAP_MARKERS = Object.freeze([
  Object.freeze({ key: "m1", pointId: "p1", label: "香山公园东门林带", status: "alert" }),
  Object.freeze({ key: "m2", pointId: "p2", label: "圆明园西路防护林", status: "active" }),
  Object.freeze({ key: "m3", pointId: "p3", label: "丰台南苑湿地公园", status: "new" }),
  Object.freeze({ key: "m4", pointId: "p4", label: "朝阳东坝郊野公园", status: "active" }),
  Object.freeze({ key: "m5", pointId: "p5", label: "石景山永定河林带", status: "done" }),
  Object.freeze({ key: "m6", pointId: "p6", label: "昌平东小口森林公园", status: "alert" }),
]);

export const DESIGN_MAP_CLUSTERS = Object.freeze([
  Object.freeze({ key: "c1", pointId: "cluster1", label: "聚合点位 18 个", status: "active", count: 18 }),
  Object.freeze({ key: "c2", pointId: "cluster2", label: "聚合点位 9 个", status: "done", count: 9 }),
]);

export const DESIGN_MAP_MOBILE_ACTIONS = Object.freeze([
  Object.freeze({ key: "menu", label: "菜单" }),
  Object.freeze({ key: "filter", label: "筛选" }),
  Object.freeze({ key: "layers", label: "图层" }),
  Object.freeze({ key: "points", label: "点位" }),
]);

function createTimeline(statusLabel, conclusion) {
  return Object.freeze([
    Object.freeze({ time: "09:20", title: "现场调查", body: "采集样线、寄主树种和危害等级信息。" }),
    Object.freeze({ time: "11:40", title: statusLabel, body: "同步静态预览中的当前处置状态。" }),
    Object.freeze({ time: "15:10", title: "处理建议", body: conclusion }),
  ]);
}

function createPointDetail({
  id,
  title,
  code,
  status,
  statusClass,
  district,
  level,
  pest,
  host,
  count,
  files,
  conclusion,
}) {
  return Object.freeze({
    id,
    title,
    code,
    status,
    statusClass,
    district,
    level,
    pest,
    host,
    count,
    files,
    conclusion,
    timeline: createTimeline(status, conclusion),
  });
}

export const DESIGN_MAP_POINT_DETAILS = Object.freeze({
  p1: createPointDetail({
    id: "p1",
    title: "香山公园东门林带",
    code: "BJ-HD-041 · 116.1907, 39.9953",
    status: "需紧急处置",
    statusClass: "alert",
    district: "海淀区",
    level: "中度",
    pest: "美国白蛾",
    host: "国槐",
    count: "24",
    files: "5",
    conclusion: "发现幼虫网幕 3 处，建议 48 小时内完成剪除与药剂防治，并于一周后复查。",
  }),
  p2: createPointDetail({
    id: "p2",
    title: "圆明园西路防护林",
    code: "BJ-HD-026 · 116.2921, 40.0118",
    status: "调查进行中",
    statusClass: "active",
    district: "海淀区",
    level: "轻度",
    pest: "国槐尺蠖",
    host: "国槐",
    count: "11",
    files: "3",
    conclusion: "局部叶片受食，暂未形成扩散，已安排连续三日监测。",
  }),
  p3: createPointDetail({
    id: "p3",
    title: "丰台南苑湿地公园",
    code: "BJ-FT-013 · 116.3974, 39.7948",
    status: "待复核",
    statusClass: "new",
    district: "丰台区",
    level: "待判定",
    pest: "疑似天牛",
    host: "杨树",
    count: "—",
    files: "2",
    conclusion: "发现新鲜排粪孔，需由区级技术人员复核虫种与危害范围。",
  }),
  p4: createPointDetail({
    id: "p4",
    title: "朝阳东坝郊野公园",
    code: "BJ-CY-033 · 116.5793, 39.9662",
    status: "调查进行中",
    statusClass: "active",
    district: "朝阳区",
    level: "轻度",
    pest: "美国白蛾",
    host: "白蜡",
    count: "7",
    files: "4",
    conclusion: "已完成第一轮样线调查，待补充北侧林带数据。",
  }),
  p5: createPointDetail({
    id: "p5",
    title: "石景山永定河林带",
    code: "BJ-SJS-008 · 116.1578, 39.8842",
    status: "已完成",
    statusClass: "done",
    district: "石景山区",
    level: "无明显危害",
    pest: "—",
    host: "杨树",
    count: "0",
    files: "3",
    conclusion: "本轮调查未发现明显虫害，纳入常规巡查周期。",
  }),
  p6: createPointDetail({
    id: "p6",
    title: "昌平东小口森林公园",
    code: "BJ-CP-052 · 116.4102, 40.0641",
    status: "需紧急处置",
    statusClass: "alert",
    district: "昌平区",
    level: "重度",
    pest: "美国白蛾",
    host: "杨树",
    count: "68",
    files: "8",
    conclusion: "连续林带发现多处网幕，存在扩散风险，建议立即组织集中处置。",
  }),
  cluster1: createPointDetail({
    id: "cluster1",
    title: "朝阳区中部聚合点位",
    code: "18 个点位 · 当前缩放级别",
    status: "调查进行中",
    statusClass: "active",
    district: "朝阳区",
    level: "轻度至中度",
    pest: "多种虫害",
    host: "国槐、白蜡",
    count: "18 点",
    files: "42",
    conclusion: "放大地图可查看聚合范围内的独立调查点位。",
  }),
  cluster2: createPointDetail({
    id: "cluster2",
    title: "门头沟东部聚合点位",
    code: "9 个点位 · 当前缩放级别",
    status: "已完成",
    statusClass: "done",
    district: "门头沟区",
    level: "无明显危害",
    pest: "—",
    host: "混交林",
    count: "9 点",
    files: "21",
    conclusion: "聚合范围内点位已完成本轮调查，可按区县查看汇总结果。",
  }),
});
