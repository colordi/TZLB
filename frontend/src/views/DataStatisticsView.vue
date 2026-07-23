<script setup>
import { computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ChartColumn } from "@lucide/vue";

import PageHeader from "@/components/common/PageHeader.vue";
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
  <div class="mx-auto w-full max-w-6xl space-y-6">
    <PageHeader title="数据统计" description="查看各虫种的核心统计指标。" />

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
  </div>
</template>
