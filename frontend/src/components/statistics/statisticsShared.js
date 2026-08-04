import { isUnauthorizedError } from "../../api/http.js";

/** 统计页通用的年份选项：以今年为中心前后各 2 年。 */
export function buildYearOptions() {
  const currentYear = new Date().getFullYear();
  return Array.from({ length: 5 }, (_, index) => currentYear - 2 + index);
}

export function formatTodayIso() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

/** 统一的数据统计加载失败处理：401 由全局拦截，其余 toast 提示。 */
export function handleStatisticsLoadError(toastError, loadError) {
  if (isUnauthorizedError(loadError)) {
    return;
  }
  toastError(`${loadError.message || loadError}`, "读取数据统计失败");
}
