<script setup>
import { onMounted, ref, watch } from "vue";

import {
  getWhiteMothDailyStatistics,
  getWhiteMothGenerationSummary,
} from "../../api/statistics.js";
import { isUnauthorizedError } from "../../api/http.js";
import { useToast } from "../../composables/useToast.js";
import { NativeSelect } from "@/components/ui/native-select";
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

watch(selectedYear, () => {
  loadStatistics();
});

watch(selectedGeneration, () => {
  loadDailyStatistics();
});

function normalizeSummary(summaryResult) {
  return {
    as_of_date: summaryResult.as_of_date || "",
    year: summaryResult.year || null,
    generations: Array.isArray(summaryResult.generations) ? summaryResult.generations : [],
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

function handleYearChange(event) {
  selectedYear.value = Number(event.target.value);
}

async function loadStatistics() {
  await Promise.all([loadDailyStatistics(), loadGenerationSummary()]);
}

onMounted(loadStatistics);
</script>

<template>
  <div class="flex flex-col gap-4">
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
