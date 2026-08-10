import { afterEach, beforeAll } from "vitest";
import { enableAutoUnmount } from "@vue/test-utils";

import { resetAuthSessionState } from "../composables/useAuthSession.js";

function createMemoryStorage() {
  const store = new Map();
  return {
    get length() {
      return store.size;
    },
    clear() {
      store.clear();
    },
    getItem(key) {
      const value = store.get(String(key));
      return value === undefined ? null : value;
    },
    key(index) {
      return Array.from(store.keys())[index] ?? null;
    },
    removeItem(key) {
      store.delete(String(key));
    },
    setItem(key, value) {
      store.set(String(key), String(value));
    },
  };
}

function ensureLocalStorage() {
  const current = globalThis.localStorage;
  const usable =
    current &&
    typeof current.clear === "function" &&
    typeof current.getItem === "function" &&
    typeof current.setItem === "function";
  if (usable) {
    return;
  }
  const memory = createMemoryStorage();
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    enumerable: true,
    value: memory,
    writable: true,
  });
  if (typeof window !== "undefined") {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      enumerable: true,
      value: memory,
      writable: true,
    });
  }
}

beforeAll(() => {
  ensureLocalStorage();
});

enableAutoUnmount(afterEach);

afterEach(() => {
  document.body.innerHTML = "";
  ensureLocalStorage();
  window.localStorage.clear();
  resetAuthSessionState();
});
