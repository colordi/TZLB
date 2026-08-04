<script setup>
import { onMounted, ref, watch } from "vue";

import { getWhiteMothGenerationSummary } from "../../api/statistics.js";
import { useToast } from "../../composables/useToast.js";
import GenerationSummaryCards from "./GenerationSummaryCards.vue";
import StatisticsYearFilter from "./StatisticsYearFilter.vue";
import { buildYearOptions, handleStatisticsLoadError } from "./statisticsShared.js";

const { error } = useToast();
const summary = ref({ as_of_date: "", year: null, generations: [] });

const YEAR_OPTIONS = buildYearOptions();
const selectedYear = ref(new Date().getFullYear());

watch(selectedYear, () => {
  loadSummary();
});

async function loadSummary() {
  try {
    const result = await getWhiteMothGenerationSummary({ year: selectedYear.value });
    summary.value = {
      as_of_date: result.as_of_date || "",
      year: result.year || null,
      generations: Array.isArray(result.generations) ? result.generations : [],
    };
  } catch (loadError) {
    summary.value = { as_of_date: "", year: null, generations: [] };
    handleStatisticsLoadError(error, loadError);
  }
}

onMounted(loadSummary);
</script>

<template>
  <div class="flex flex-col gap-4">
    <StatisticsYearFilter
      v-model="selectedYear"
      :year-options="YEAR_OPTIONS"
      testid="data-statistics-generation-year-filter"
    />
    <GenerationSummaryCards :summary="summary" :fallback-year="selectedYear" />
  </div>
</template>
