import { ref } from "vue";

import { fetchStatisticsYears } from "../../api/statistics.js";
import { isUnauthorizedError } from "../../api/http.js";

let statisticsYearsPromise = null;

/** 各统计模块实际数据年份，整个统计页共享一次请求；失败时回退为空对象。 */
function loadStatisticsYears() {
  if (!statisticsYearsPromise) {
    statisticsYearsPromise = fetchStatisticsYears().catch(() => ({}));
  }
  return statisticsYearsPromise;
}

/**
 * 统计页年份筛选：选项为该模块在数据库中的实际数据年份（升序）。
 * 接口返回前或无数据时回退为 [当前年]；若选中值不在实际年份中，
 * 自动切换到最新年份，组件里 watch(selectedYear) 会随之重新加载。
 */
export function useStatisticsYearOptions(moduleKey) {
  const currentYear = new Date().getFullYear();
  const yearOptions = ref([currentYear]);
  const selectedYear = ref(currentYear);

  loadStatisticsYears().then((data) => {
    const years = Array.isArray(data?.[moduleKey]) ? data[moduleKey] : [];
    if (years.length === 0) {
      return;
    }
    yearOptions.value = years;
    if (!years.includes(selectedYear.value)) {
      selectedYear.value = years[years.length - 1];
    }
  });

  return { yearOptions, selectedYear };
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
