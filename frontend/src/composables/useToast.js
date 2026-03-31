import { reactive, readonly } from "vue";

const toastState = reactive({
  items: [],
});

let toastSeed = 0;

function removeToast(id) {
  const index = toastState.items.findIndex((item) => item.id === id);
  if (index >= 0) {
    toastState.items.splice(index, 1);
  }
}

function pushToast(payload) {
  const id = ++toastSeed;
  const toast = {
    id,
    type: payload.type || "info",
    title: payload.title || "提示",
    message: payload.message || "",
  };

  toastState.items.push(toast);

  const duration = Number(payload.duration ?? 2600);
  if (duration > 0) {
    window.setTimeout(() => {
      removeToast(id);
    }, duration);
  }

  return id;
}

export function useToast() {
  return {
    toasts: readonly(toastState.items),
    showToast(payload) {
      return pushToast(payload);
    },
    success(message, title = "操作成功") {
      return pushToast({ type: "success", title, message });
    },
    error(message, title = "操作失败") {
      return pushToast({ type: "error", title, message, duration: 3600 });
    },
    info(message, title = "提示") {
      return pushToast({ type: "info", title, message });
    },
    dismissToast: removeToast,
  };
}
