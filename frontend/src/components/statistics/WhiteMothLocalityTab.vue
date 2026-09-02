<script setup>
import { onMounted, ref, watch } from "vue";

import { getWhiteMothLocalitySummary } from "../../api/statistics.js";
import { useToast } from "../../composables/useToast.js";
import LocalityDamagePanel from "./LocalityDamagePanel.vue";
import StatisticsYearFilter from "./StatisticsYearFilter.vue";
import {
  formatTodayIso,
  handleStatisticsLoadError,
  useStatisticsYearOptions,
} from "./statisticsShared.js";

const EMPTY_LOCALITY_SUMMARY = {
  year: null,
  generation: null,
  as_of_date: "",
  severe_plant_threshold: 10,
  totals: {
    damaged_points: 0,
    damaged_plants: 0,
    completed_points: 0,
    completion_rate: 0,
    severe_points: 0,
    unfeedback_points: 0,
    collab_points: 0,
  },
  localities: [],
};

const { error } = useToast();
const loading = ref(false);
const summary = ref({ ...EMPTY_LOCALITY_SUMMARY });

const GENERATION_OPTIONS = ["第一代", "第二代", "第三代"];

const { yearOptions, selectedYear } = useStatisticsYearOptions("white-moth");
const selectedGeneration = ref("");
const selectedAsOfDate = ref(formatTodayIso());
const selectedSevereThreshold = ref(10);

watch([selectedYear, selectedGeneration, selectedAsOfDate, selectedSevereThreshold], () => {
  loadSummary();
});

function normalizeLocalitySummary(result) {
  return {
    year: result.year ?? null,
    generation: result.generation ?? null,
    as_of_date: result.as_of_date || selectedAsOfDate.value || "",
    severe_plant_threshold:
      result.severe_plant_threshold ?? selectedSevereThreshold.value ?? 10,
    totals: {
      damaged_points: result.totals?.damaged_points ?? 0,
      damaged_plants: result.totals?.damaged_plants ?? 0,
      completed_points: result.totals?.completed_points ?? 0,
      completion_rate: result.totals?.completion_rate ?? 0,
      severe_points: result.totals?.severe_points ?? 0,
      unfeedback_points: result.totals?.unfeedback_points ?? 0,
      collab_points: result.totals?.collab_points ?? 0,
    },
    localities: Array.isArray(result.localities) ? result.localities : [],
  };
}

async function loadSummary() {
  loading.value = true;
  try {
    const result = await getWhiteMothLocalitySummary({
      year: selectedYear.value,
      generation: selectedGeneration.value || undefined,
      asOfDate: selectedAsOfDate.value || undefined,
      severePlantThreshold: selectedSevereThreshold.value,
    });
    summary.value = normalizeLocalitySummary(result);
  } catch (loadError) {
    summary.value = {
      ...EMPTY_LOCALITY_SUMMARY,
      year: selectedYear.value,
      as_of_date: selectedAsOfDate.value,
      severe_plant_threshold: selectedSevereThreshold.value,
    };
    handleStatisticsLoadError(error, loadError);
  } finally {
    loading.value = false;
  }
}

onMounted(loadSummary);
</script>

<template>
  <div class="flex flex-col gap-4">
    <StatisticsYearFilter
      v-model="selectedYear"
      :year-options="yearOptions"
      testid="data-statistics-locality-year-filter"
    />
    <LocalityDamagePanel
      v-model:generation="selectedGeneration"
      v-model:as-of-date="selectedAsOfDate"
      v-model:severe-plant-threshold="selectedSevereThreshold"
      :summary="summary"
      :loading="loading"
      :generation-options="GENERATION_OPTIONS"
    />
  </div>
</template>
