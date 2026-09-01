import { ref } from "vue";

const STORAGE_KEY = "tzlb:date-point-complete-marks";
const MAX_MARK_AGE_MS = 60 * 24 * 60 * 60 * 1000;

/**
 * 日期现场照片「已拍齐」标记：纯前端 localStorage 持久化，
 * 按查询范围（害虫类型|年份|世代|日期）隔离，不依赖后端。
 */
export function usePointCompleteMarks() {
  const marks = ref(loadMarks());

  function loadMarks() {
    try {
      const raw = globalThis.localStorage?.getItem(STORAGE_KEY);
      if (!raw) {
        return {};
      }
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") {
        return {};
      }
      const cutoff = Date.now() - MAX_MARK_AGE_MS;
      const cleaned = {};
      for (const [scopeKey, entries] of Object.entries(parsed)) {
        if (!entries || typeof entries !== "object") {
          continue;
        }
        const alive = Object.fromEntries(
          Object.entries(entries).filter(([, markedAt]) => Number(markedAt) >= cutoff),
        );
        if (Object.keys(alive).length) {
          cleaned[scopeKey] = alive;
        }
      }
      return cleaned;
    } catch {
      return {};
    }
  }

  function persist() {
    try {
      globalThis.localStorage?.setItem(STORAGE_KEY, JSON.stringify(marks.value));
    } catch {
      // 存储不可用时静默降级，标记仅本次会话内有效
    }
  }

  function isComplete(scopeKey, code) {
    return Boolean(code && marks.value[scopeKey]?.[code]);
  }

  function toggleComplete(scopeKey, code) {
    if (!scopeKey || !code) {
      return;
    }
    const next = { ...marks.value };
    const entries = { ...(next[scopeKey] || {}) };
    if (entries[code]) {
      delete entries[code];
    } else {
      entries[code] = Date.now();
    }
    if (Object.keys(entries).length) {
      next[scopeKey] = entries;
    } else {
      delete next[scopeKey];
    }
    marks.value = next;
    persist();
  }

  /** 清除当前查询范围的全部标记，返回清除数量 */
  function resetScope(scopeKey) {
    const count = Object.keys(marks.value[scopeKey] || {}).length;
    if (!count) {
      return 0;
    }
    const next = { ...marks.value };
    delete next[scopeKey];
    marks.value = next;
    persist();
    return count;
  }

  return { isComplete, toggleComplete, resetScope };
}
