<script setup>
import { onMounted, ref, watch } from "vue";

import {
  getWhiteMothDailyStatistics,
  getWhiteMothGenerationSummary,
} from "../../api/statistics.js";
import { isUnauthorizedError } from "../../api/http.js";
import { useToast } from "../../composables/useToast.js";
import DailyStatisticsTable from "./DailyStatisticsTable.vue";
import GenerationSummaryCards from "./GenerationSummaryCards.vue";

const { error } = useToast();
const loading = ref(false);
const columns = ref([]);
const rows = ref([]);
const generationSummary = ref({ as_of_date: "", year: null, generations: [] });

const currentYear = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: 5 }, (_, index) => currentYear - 2 + index);
const GENERATION_OPTIONS = ["第一代", "第二代", "第三代"];

const selectedYear = ref(currentYear);
const selectedGeneration = ref("");

watch([selectedYear, selectedGeneration], () => {
  loadWhiteMothDailyStatistics();
});

async function loadWhiteMothDailyStatistics() {
  loading.value = true;
  try {
    const [result, summaryResult] = await Promise.all([
      getWhiteMothDailyStatistics({
        year: selectedYear.value,
        generation: selectedGeneration.value || undefined,
      }),
      getWhiteMothGenerationSummary(),
    ]);
    columns.value = Array.isArray(result.columns) ? result.columns : [];
    rows.value = Array.isArray(result.rows) ? result.rows : [];
    generationSummary.value = {
      as_of_date: summaryResult.as_of_date || "",
      year: summaryResult.year || null,
      generations: Array.isArray(summaryResult.generations) ? summaryResult.generations : [],
    };
  } catch (loadError) {
    columns.value = [];
    rows.value = [];
    generationSummary.value = { as_of_date: "", year: null, generations: [] };
    if (isUnauthorizedError(loadError)) {
      return;
    }
    error(`${loadError.message || loadError}`, "读取数据统计失败");
  } finally {
    loading.value = false;
  }
}

onMounted(loadWhiteMothDailyStatistics);
</script>

<template>
  <div class="flex flex-col gap-4">
    <GenerationSummaryCards :summary="generationSummary" :fallback-year="selectedYear" />
    <DailyStatisticsTable
      v-model:year="selectedYear"
      v-model:generation="selectedGeneration"
      title="美国白蛾每日信息统计"
      empty-text="暂无美国白蛾每日统计数据。"
      :columns="columns"
      :rows="rows"
      :loading="loading"
      :year-options="YEAR_OPTIONS"
      :generation-options="GENERATION_OPTIONS"
    />
  </div>
</template>
