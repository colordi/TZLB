import { createApp } from "vue";

import App from "./App.vue";
import router from "./router/index.js";
/* 主题与 Tailwind 在前；styles.css 仅含全局基础层（重置/滚动条/动画） */
import "./styles/shadcn.css";
import "./styles.css";

createApp(App).use(router).mount("#app");
