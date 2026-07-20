<script setup>
import { computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ChartColumn } from "@lucide/vue";

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  DEFAULT_STATISTICS_MODULE,
  resolveStatisticsModule,
  STATISTICS_MODULES,
} from "../components/statistics/pestModules.js";

const route = useRoute();
const router = useRouter();

const activeModule = computed(() => resolveStatisticsModule(route.params.pest));
const activePest = computed(() => activeModule.value?.value || DEFAULT_STATISTICS_MODULE);

watch(
  () => route.params.pest,
  (pest) => {
    if (!resolveStatisticsModule(pest)) {
      router.replace(`/data-statistics/${DEFAULT_STATISTICS_MODULE}`);
    }
  },
  { immediate: true },
);

function handleTabChange(value) {
  if (value && value !== route.params.pest) {
    router.push(`/data-statistics/${value}`);
  }
}
</script>

<template>
  <section class="data-statistics-page mx-auto flex w-full max-w-6xl flex-col gap-4">
    <header class="space-y-1">
      <h1 class="text-2xl font-bold tracking-tight md:text-3xl">数据统计</h1>
      <p class="max-w-3xl text-sm text-muted-foreground">查看各虫种的核心统计指标。</p>
    </header>

    <Tabs :model-value="activePest" @update:model-value="handleTabChange">
      <TabsList aria-label="虫种统计">
        <TabsTrigger
          v-for="module in STATISTICS_MODULES"
          :key="module.value"
          :value="module.value"
          :disabled="module.disabled"
          :data-testid="`data-statistics-pest-${module.value}`"
        >
          <ChartColumn class="size-4" />
          <span>{{ module.label }}</span>
        </TabsTrigger>
      </TabsList>
    </Tabs>

    <component :is="activeModule.component" v-if="activeModule?.component" />
  </section>
</template>
