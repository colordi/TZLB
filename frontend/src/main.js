import { createApp } from "vue";

import App from "./App.vue";
import router from "./router/index.js";
/* shadcn/Tailwind 入口在前；旧 styles.css 并存，业务页逐步迁移 */
import "./styles/shadcn.css";
import "./styles.css";

createApp(App).use(router).mount("#app");
