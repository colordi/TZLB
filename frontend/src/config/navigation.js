import {
  ChartColumn,
  Database,
  FileSpreadsheet,
  HardDrive,
  Images,
  LayoutDashboard,
  Layers,
  MapPin,
  ScrollText,
  Table2,
  Upload,
  Users,
} from "@lucide/vue";

import { ROLES_ADMIN_AND_INVESTIGATOR, USER_ROLES } from "../auth/permissions.js";

/** 主导航分组（壳层侧栏 / 顶栏 / 移动菜单共用） */
export const NAV_GROUPS = [
  {
    label: "工单管理",
    items: [
      {
        to: "/workorder",
        label: "工单生成",
        icon: Upload,
        testId: "workorder",
        requiredRoles: [USER_ROLES.ADMIN],
      },
      {
        to: "/workorder-assets",
        label: "工单素材",
        icon: Images,
        testId: "workorder-assets",
        requiredRoles: ROLES_ADMIN_AND_INVESTIGATOR,
      },
    ],
  },
  {
    label: "调查任务",
    items: [
      {
        to: "/map",
        label: "调查点位",
        icon: MapPin,
        testId: "map",
      },
      {
        to: "/admin/layers",
        label: "任务图层",
        icon: Layers,
        testId: "admin-layers",
        requiredRoles: [USER_ROLES.ADMIN],
      },
    ],
  },
  {
    label: "数据管理",
    items: [
      {
        to: "/data-import",
        label: "数据导入",
        icon: FileSpreadsheet,
        testId: "data-import",
        requiredRoles: [USER_ROLES.ADMIN],
      },
      {
        to: "/data-export",
        label: "数据导出",
        icon: Database,
        testId: "data-export",
        requiredRoles: ROLES_ADMIN_AND_INVESTIGATOR,
      },
      {
        to: "/data-manager",
        label: "数据管理",
        icon: Table2,
        testId: "data-manager",
        requiredRoles: ROLES_ADMIN_AND_INVESTIGATOR,
      },
      {
        to: "/data-statistics",
        label: "数据统计",
        icon: ChartColumn,
        testId: "data-statistics",
        requiredRoles: ROLES_ADMIN_AND_INVESTIGATOR,
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
        to: "/admin/logs",
        label: "操作日志",
        icon: ScrollText,
        testId: "admin-logs",
        requiredRoles: [USER_ROLES.ADMIN],
      },
      {
        to: "/admin/storage",
        label: "存储配置",
        icon: HardDrive,
        testId: "admin-storage",
        requiredRoles: [USER_ROLES.ADMIN],
      },
    ],
  },
];
