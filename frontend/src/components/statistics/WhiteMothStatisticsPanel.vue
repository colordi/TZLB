<script setup>
import { onMounted, ref, watch } from "vue";

import {
  getWhiteMothDailyStatistics,
  getWhiteMothGenerationSummary,
  getWhiteMothLocalitySummary,
} from "../../api/statistics.js";
import { isUnauthorizedError } from "../../api/http.js";
import { useToast } from "../../composables/useToast.js";
import { NativeSelect } from "@/components/ui/native-select";
import DailyStatisticsTable from "./DailyStatisticsTable.vue";
import GenerationSummaryCards from "./GenerationSummaryCards.vue";
import LocalityDamagePanel from "./LocalityDamagePanel.vue";

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
    collab_points: 0,
  },
  localities: [],
};

function formatTodayIso() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

const { error } = useToast();
const loading = ref(false);
const localityLoading = ref(false);
const columns = ref([]);
const rows = ref([]);
const generationSummary = ref({ as_of_date: "", year: null, generations: [] });
const localitySummary = ref({ ...EMPTY_LOCALITY_SUMMARY });

const currentYear = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: 5 }, (_, index) => currentYear - 2 + index);
const GENERATION_OPTIONS = ["第一代", "第二代", "第三代"];

const selectedYear = ref(currentYear);
const selectedGeneration = ref("");
const selectedAsOfDate = ref(formatTodayIso());
const selectedSevereThreshold = ref(10);

watch(selectedYear, () => {
  loadStatistics();
});

watch(selectedGeneration, () => {
  loadFilteredStatistics();
});

watch([selectedAsOfDate, selectedSevereThreshold], () => {
  loadLocalitySummary();
});

function normalizeSummary(summaryResult) {
  return {
    as_of_date: summaryResult.as_of_date || "",
    year: summaryResult.year || null,
    generations: Array.isArray(summaryResult.generations) ? summaryResult.generations : [],
  };
}

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
      collab_points: result.totals?.collab_points ?? 0,
    },
    localities: Array.isArray(result.localities) ? result.localities : [],
  };
}

function handleLoadError(loadError) {
  if (isUnauthorizedError(loadError)) {
    return;
  }
  error(`${loadError.message || loadError}`, "读取数据统计失败");
}

async function loadDailyStatistics() {
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
    handleLoadError(loadError);
  } finally {
    loading.value = false;
  }
}

async function loadGenerationSummary() {
  try {
    const summaryResult = await getWhiteMothGenerationSummary({
      year: selectedYear.value,
    });
    generationSummary.value = normalizeSummary(summaryResult);
  } catch (loadError) {
    generationSummary.value = { as_of_date: "", year: null, generations: [] };
    handleLoadError(loadError);
  }
}

async function loadLocalitySummary() {
  localityLoading.value = true;
  try {
    const result = await getWhiteMothLocalitySummary({
      year: selectedYear.value,
      generation: selectedGeneration.value || undefined,
      asOfDate: selectedAsOfDate.value || undefined,
      severePlantThreshold: selectedSevereThreshold.value,
    });
    localitySummary.value = normalizeLocalitySummary(result);
  } catch (loadError) {
    localitySummary.value = {
      ...EMPTY_LOCALITY_SUMMARY,
      year: selectedYear.value,
      as_of_date: selectedAsOfDate.value,
      severe_plant_threshold: selectedSevereThreshold.value,
    };
    handleLoadError(loadError);
  } finally {
    localityLoading.value = false;
  }
}

function handleYearChange(event) {
  selectedYear.value = Number(event.target.value);
}

async function loadFilteredStatistics() {
  await Promise.all([loadDailyStatistics(), loadLocalitySummary()]);
}

async function loadStatistics() {
  await Promise.all([
    loadDailyStatistics(),
    loadGenerationSummary(),
    loadLocalitySummary(),
  ]);
}

onMounted(loadStatistics);
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="flex items-center justify-end" aria-label="统计年份">
      <label class="flex items-center gap-2 text-sm text-muted-foreground">
        <span>统计年份</span>
        <NativeSelect
          :model-value="String(selectedYear)"
          class="h-8 py-1"
          data-testid="data-statistics-year-filter"
          @change="handleYearChange"
        >
          <option v-for="year in YEAR_OPTIONS" :key="year" :value="year">
            {{ year }}
          </option>
        </NativeSelect>
      </label>
    </div>

    <GenerationSummaryCards :summary="generationSummary" :fallback-year="selectedYear" />
    <LocalityDamagePanel
      v-model:generation="selectedGeneration"
      v-model:as-of-date="selectedAsOfDate"
      v-model:severe-plant-threshold="selectedSevereThreshold"
      :summary="localitySummary"
      :loading="localityLoading"
      :generation-options="GENERATION_OPTIONS"
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
