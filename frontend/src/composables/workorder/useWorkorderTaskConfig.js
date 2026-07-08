import { computed, ref, watch } from "vue";

import {
  PEST_OPTIONS,
  getCurrentYear,
  getDefaultControlType,
  getDefaultTask,
  getGenerationFromTask,
  getTaskOptions,
  supportsSurveyImport,
} from "../../components/workorder/fieldConfig.js";

export function useWorkorderTaskConfig() {
  const pestType = ref("春尺蠖");
  const year = ref(getCurrentYear());

  const taskType = computed(() => getDefaultControlType(pestType.value));
  const taskName = ref(getDefaultTask(pestType.value, year.value));
  const taskOptions = computed(() => getTaskOptions(pestType.value, year.value));
  const generation = computed(() =>
    getGenerationFromTask(pestType.value, taskName.value, year.value),
  );
  const yearOptions = computed(() => {
    const current = getCurrentYear();
    return [current - 2, current - 1, current, current + 1];
  });
  const canImportSurvey = computed(() => supportsSurveyImport(pestType.value));

  watch(taskOptions, (options) => {
    if (!options.some((option) => option.value === taskName.value)) {
      taskName.value = options[0]?.value || "";
    }
  });

  function resetTaskName() {
    taskName.value = getDefaultTask(pestType.value, year.value);
  }

  return {
    PEST_OPTIONS,
    pestType,
    year,
    taskType,
    taskName,
    generation,
    taskOptions,
    yearOptions,
    canImportSurvey,
    resetTaskName,
  };
}
