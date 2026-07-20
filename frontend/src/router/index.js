import { createRouter, createWebHistory } from "vue-router";

import {
  canAccessRoute,
  getDefaultRouteForUser,
  USER_ROLES,
} from "../auth/permissions.js";
import { ensureSessionLoaded } from "../composables/useAuthSession.js";
import DataExportView from "../views/DataExportView.vue";
import DataImportView from "../views/DataImportView.vue";
import DataStatisticsView from "../views/DataStatisticsView.vue";
import LoginView from "../views/LoginView.vue";
import MapView from "../views/MapView.vue";
import WorkorderAssetsView from "../views/WorkorderAssetsView.vue";
import WorkOrderView from "../views/WorkOrderView.vue";
import AdminDashboardView from "../views/AdminDashboardView.vue";
import AdminUsersView from "../views/AdminUsersView.vue";
import AdminLayersView from "../views/AdminLayersView.vue";
import AdminOperationLogsView from "../views/AdminOperationLogsView.vue";

const routes = [
  {
    path: "/",
    redirect: "/login",
  },
  {
    path: "/login",
    name: "login",
    component: LoginView,
    meta: {
      section: "登录",
      hideShell: true,
      requiresAuth: false,
      blurb: "进入林业调查工作台。",
    },
  },
  {
    path: "/workorder",
    name: "workorder",
    component: WorkOrderView,
    meta: {
      section: "工单录入",
      blurb: "从数据库选取调查记录，校对点位后批量生成 Word 工单。",
      requiredRoles: [USER_ROLES.ADMIN],
    },
  },
  {
    path: "/workorder/point-screenshots",
    redirect: "/workorder-assets",
  },
  {
    path: "/workorder-assets",
    name: "workorder-assets",
    component: WorkorderAssetsView,
    meta: {
      section: "工单素材",
      blurb: "管理点位截图与按日期归档的现场图片，供工单生成取用。",
      requiredRoles: [USER_ROLES.ADMIN],
    },
  },
  {
    path: "/data-import",
    name: "data-import",
    component: DataImportView,
    meta: {
      section: "调查数据导入",
      blurb: "通过 Excel 将调查/台账数据写入数据库，供工单录入时从库中选取。",
      requiredRoles: [USER_ROLES.ADMIN],
    },
  },
  {
    path: "/map",
    name: "map",
    component: MapView,
    meta: {
      section: "调查点位",
      blurb: "",
      fullBleed: true,
    },
  },
  {
    path: "/data-export",
    name: "data-export",
    component: DataExportView,
    meta: {
      section: "数据导出",
      blurb: "导出 survey 和 ledger 下的最新数据表。",
      requiredRoles: [USER_ROLES.ADMIN],
    },
  },
  {
    path: "/data-statistics",
    redirect: "/data-statistics/white-moth",
  },
  {
    path: "/data-statistics/:pest",
    name: "data-statistics",
    component: DataStatisticsView,
    meta: {
      section: "数据统计",
      blurb: "查看各虫种的核心统计指标。",
      requiredRoles: [USER_ROLES.ADMIN],
    },
  },
  {
    path: "/admin",
    name: "admin-dashboard",
    component: AdminDashboardView,
    meta: {
      section: "管理概览",
      blurb: "用户、图层及系统聚合信息。",
      requiredRoles: [USER_ROLES.ADMIN],
    },
  },
  {
    path: "/admin/users",
    name: "admin-users",
    component: AdminUsersView,
    meta: {
      section: "用户管理",
      blurb: "管理系统用户。",
      requiredRoles: [USER_ROLES.ADMIN],
    },
  },
  {
    path: "/admin/layers",
    name: "admin-layers",
    component: AdminLayersView,
    meta: {
      section: "图层管理",
      blurb: "管理地图图层元数据。",
      requiredRoles: [USER_ROLES.ADMIN],
    },
  },
  {
    path: "/admin/logs",
    name: "admin-logs",
    component: AdminOperationLogsView,
    meta: {
      section: "操作日志",
      blurb: "查看调查员与管理员的点位删除操作记录。",
      requiredRoles: [USER_ROLES.ADMIN],
    },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

function resolveAccessibleRedirect(user, redirect) {
  const target =
    typeof redirect === "string" && redirect.startsWith("/") && redirect !== "/login"
      ? redirect
      : getDefaultRouteForUser(user);
  const resolvedTarget = router.resolve(target);
  return canAccessRoute(user, resolvedTarget) ? target : getDefaultRouteForUser(user);
}

router.beforeEach(async (to) => {
  if (to.meta?.skipSessionLoad) {
    return true;
  }

  const requiresAuth = to.meta?.requiresAuth !== false;
  const currentUser = await ensureSessionLoaded();

  if (!requiresAuth && to.name === "login" && currentUser) {
    return resolveAccessibleRedirect(currentUser, to.query.redirect);
  }

  if (requiresAuth && !currentUser) {
    return {
      name: "login",
      query: {
        redirect: to.fullPath,
      },
    };
  }

  if (requiresAuth && !canAccessRoute(currentUser, to)) {
    const fallback = getDefaultRouteForUser(currentUser);
    return fallback === to.fullPath ? false : fallback;
  }

  return true;
});

router.afterEach((to) => {
  const title = to.meta?.section || "林业调查工作台";
  document.title = `${title} · 林业调查工作台`;
});

export default router;
