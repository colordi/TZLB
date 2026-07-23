import { toast } from "vue-sonner";

/**
 * 全局提示统一走 vue-sonner（App.vue 挂载 <Toaster />）。
 * 本模块仅保留薄封装，维持既有调用签名：
 *   success(message, title?) / error(message, title?) / info(message, title?)
 * 规范见 docs/specs/frontend-design-system.md §6.3。
 */

const DEFAULT_DURATION = 2600;
const ERROR_DURATION = 3600;

export function useToast() {
  return {
    success(message, title = "操作成功") {
      return toast.success(title, {
        description: message,
        duration: DEFAULT_DURATION,
      });
    },
    error(message, title = "操作失败") {
      return toast.error(title, {
        description: message,
        duration: ERROR_DURATION,
      });
    },
    info(message, title = "提示") {
      return toast.info(title, {
        description: message,
        duration: DEFAULT_DURATION,
      });
    },
    /** 兼容旧签名；新代码请直接用 success/error/info */
    showToast(payload = {}) {
      const type = payload.type || "info";
      const fn = typeof toast[type] === "function" ? toast[type] : toast.info;
      return fn(payload.title || "提示", {
        description: payload.message || "",
        duration: Number(payload.duration ?? DEFAULT_DURATION),
      });
    },
    dismissToast(id) {
      toast.dismiss(id);
    },
  };
}
