import { createRouter, createWebHistory } from "vue-router";

import MapView from "../views/MapView.vue";
import WorkOrderView from "../views/WorkOrderView.vue";

const routes = [
  {
    path: "/",
    redirect: "/workorder",
  },
  {
    path: "/workorder",
    name: "workorder",
    component: WorkOrderView,
    meta: {
      section: "工单录入",
      blurb: "批量录入现场记录、嵌入照片并直接导出 Word 工作单。",
    },
  },
  {
    path: "/map",
    name: "map",
    component: MapView,
    meta: {
      section: "调查点位展示",
      blurb: "",
    },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.afterEach((to) => {
  const title = to.meta?.section || "林业调查工作台";
  document.title = `${title} · 林业调查工作台`;
});

export default router;
