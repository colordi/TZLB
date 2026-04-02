import { afterEach } from "vitest";
import { enableAutoUnmount } from "@vue/test-utils";

import { resetAuthSessionState } from "../composables/useAuthSession.js";

enableAutoUnmount(afterEach);

afterEach(() => {
  document.body.innerHTML = "";
  window.localStorage.clear();
  resetAuthSessionState();
});
