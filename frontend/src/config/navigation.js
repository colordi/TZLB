import {
  ChartColumn,
  Database,
  FileSpreadsheet,
  Images,
  LayoutDashboard,
  Layers,
  MapPin,
  ScrollText,
  Upload,
  Users,
} from "@lucide/vue";

import { USER_ROLES } from "../auth/permissions.js";

/** 主导航分组（壳层侧栏 / 顶栏 / 移动菜单共用） */
export const NAV_GROUPS = [
  {
    label: "业务管理",
    items: [
      {
        to: "/workorder",
        label: "工单录入",
        icon: Upload,
        testId: "workorder",
        requiredRoles: [USER_ROLES.ADMIN],
      },
      {
        to: "/map",
        label: "调查点位",
        icon: MapPin,
        testId: "map",
      },
    ],
  },
  {
    label: "数据管理",
    items: [
      {
        to: "/data-import",
        label: "调查数据导入",
        icon: FileSpreadsheet,
        testId: "data-import",
        requiredRoles: [USER_ROLES.ADMIN],
      },
      {
        to: "/workorder-assets",
        label: "工单素材",
        icon: Images,
        testId: "workorder-assets",
        requiredRoles: [USER_ROLES.ADMIN],
      },
      {
        to: "/data-export",
        label: "数据导出",
        icon: Database,
        testId: "data-export",
        requiredRoles: [USER_ROLES.ADMIN],
      },
      {
        to: "/data-statistics",
        label: "数据统计",
        icon: ChartColumn,
        testId: "data-statistics",
        requiredRoles: [USER_ROLES.ADMIN],
      },
    ],
  },
  {
    label: "管理后台",
    items: [
      {
        to: "/admin",
        label: "管理概览",
        icon: LayoutDashboard,
        testId: "admin",
        requiredRoles: [USER_ROLES.ADMIN],
      },
      {
        to: "/admin/users",
        label: "用户管理",
        icon: Users,
        testId: "admin-users",
        requiredRoles: [USER_ROLES.ADMIN],
      },
      {
        to: "/admin/layers",
        label: "图层管理",
        icon: Layers,
        testId: "admin-layers",
        requiredRoles: [USER_ROLES.ADMIN],
      },
      {
        to: "/admin/logs",
        label: "操作日志",
        icon: ScrollText,
        testId: "admin-logs",
        requiredRoles: [USER_ROLES.ADMIN],
      },
    ],
  },
];
