<script setup>
import { onMounted, ref, watch } from "vue";

import { getWhiteMothDailyStatistics } from "../../api/statistics.js";
import { useToast } from "../../composables/useToast.js";
import DailyStatisticsTable from "./DailyStatisticsTable.vue";
import StatisticsYearFilter from "./StatisticsYearFilter.vue";
import { buildYearOptions, handleStatisticsLoadError } from "./statisticsShared.js";

const { error } = useToast();
const loading = ref(false);
const columns = ref([]);
const rows = ref([]);

const YEAR_OPTIONS = buildYearOptions();
const GENERATION_OPTIONS = ["第一代", "第二代", "第三代"];

const selectedYear = ref(new Date().getFullYear());
const selectedGeneration = ref("");

watch([selectedYear, selectedGeneration], () => {
  loadStatistics();
});

async function loadStatistics() {
  loading.value = true;
  try {
    const result = await getWhiteMothDailyStatistics({
      year: selectedYear.value,
      generation: selectedGeneration.value || undefined,
    });
    columns.value = Array.isArray(result.columns) ? result.columns : [];
    rows.value = Array.isArray(result.rows) ? result.rows : [];
  } catch (loadError) {
    columns.value = [];
    rows.value = [];
    handleStatisticsLoadError(error, loadError);
  } finally {
    loading.value = false;
  }
}

onMounted(loadStatistics);
</script>

<template>
  <div class="flex flex-col gap-4">
    <StatisticsYearFilter
      v-model="selectedYear"
      :year-options="YEAR_OPTIONS"
      testid="data-statistics-daily-year-filter"
    />
    <DailyStatisticsTable
      v-model:generation="selectedGeneration"
      title="美国白蛾每日信息统计"
      empty-text="暂无美国白蛾每日统计数据。"
      :columns="columns"
      :rows="rows"
      :loading="loading"
      :generation-options="GENERATION_OPTIONS"
    />
  </div>
</template>
