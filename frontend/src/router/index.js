import { createRouter, createWebHistory } from "vue-router";

import {
  canAccessRoute,
  getDefaultRouteForUser,
  USER_ROLES,
} from "../auth/permissions.js";
import { ensureSessionLoaded } from "../composables/useAuthSession.js";
import DataExportView from "../views/DataExportView.vue";
import DataStatisticsView from "../views/DataStatisticsView.vue";
import LoginView from "../views/LoginView.vue";
import MapView from "../views/MapView.vue";
import WorkOrderView from "../views/WorkOrderView.vue";
import DesignPreviewLayout from "../components/design/DesignPreviewLayout.vue";
import DesignLoginView from "../views/design/DesignLoginView.vue";
import DesignOverviewView from "../views/design/DesignOverviewView.vue";
import DesignMapView from "../views/design/DesignMapView.vue";
import DesignPreviewStatusView from "../views/design/DesignPreviewStatusView.vue";
import DesignWorkOrderView from "../views/design/DesignWorkOrderView.vue";

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
      blurb: "通过调查导入整理工单记录，补充图片后生成 Word 工作单。",
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
    name: "data-statistics",
    component: DataStatisticsView,
    meta: {
      section: "数据统计",
      blurb: "查看各虫种的核心统计指标。",
      requiredRoles: [USER_ROLES.ADMIN],
    },
  },
  {
    path: "/design",
    component: DesignPreviewLayout,
    meta: {
      section: "设计预览",
      hideShell: true,
      requiresAuth: false,
      skipSessionLoad: true,
    },
    children: [
      {
        path: "",
        name: "design-status",
        component: DesignPreviewStatusView,
        meta: {
          previewPage: "迁移状态",
          previewStage: "foundation",
        },
      },
      {
        path: "login",
        name: "design-login",
        component: DesignLoginView,
        meta: {
          section: "登录页设计预览",
          previewPage: "登录页",
          previewStage: "login",
        },
      },
      {
        path: "overview",
        name: "design-overview",
        component: DesignOverviewView,
        meta: {
          section: "工作概览设计预览",
          previewPage: "工作概览页",
          previewStage: "overview",
          previewShell: true,
        },
      },
      {
        path: "workorder",
        name: "design-workorder",
        component: DesignWorkOrderView,
        meta: {
          section: "工单页设计预览",
          previewPage: "调查工单页",
          previewStage: "workorder",
          previewShell: true,
        },
      },
      {
        path: "map",
        name: "design-map",
        component: DesignMapView,
        meta: {
          section: "地图页设计预览",
          previewPage: "调查点位地图页",
          previewStage: "map",
          previewShell: true,
          previewFullBleed: true,
        },
      },
    ],
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
