import { createApp } from "vue";

import App from "./App.vue";
import router from "./router/index.js";
/* Claude + Tailwind 在前；styles.css 仅做旧变量桥接与遗留控件样式 */
import "./styles/shadcn.css";
import "./styles.css";

createApp(App).use(router).mount("#app");
