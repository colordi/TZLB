import { createRouter, createWebHistory } from "vue-router";

import { ensureSessionLoaded } from "../composables/useAuthSession.js";
import LoginView from "../views/LoginView.vue";
import MapView from "../views/MapView.vue";
import WorkOrderView from "../views/WorkOrderView.vue";

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
    },
  },
  {
    path: "/map",
    name: "map",
    component: MapView,
    meta: {
      section: "调查点位",
      blurb: "",
    },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to) => {
  const requiresAuth = to.meta?.requiresAuth !== false;
  const currentUser = await ensureSessionLoaded();

  if (!requiresAuth && to.name === "login" && currentUser) {
    const redirect =
      typeof to.query.redirect === "string" &&
      to.query.redirect.startsWith("/") &&
      to.query.redirect !== "/login"
        ? to.query.redirect
        : "/map";
    return redirect;
  }

  if (requiresAuth && !currentUser) {
    return {
      name: "login",
      query: {
        redirect: to.fullPath,
      },
    };
  }

  return true;
});

router.afterEach((to) => {
  const title = to.meta?.section || "林业调查工作台";
  document.title = `${title} · 林业调查工作台`;
});

export default router;
