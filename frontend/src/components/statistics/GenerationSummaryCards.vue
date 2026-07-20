<script setup>
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const props = defineProps({
  summary: {
    type: Object,
    default: () => ({ as_of_date: "", year: null, generations: [] }),
  },
  fallbackYear: {
    type: Number,
    default: null,
  },
});

function formatNumber(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  return Number(value || 0).toLocaleString("zh-CN");
}
</script>

<template>
  <Card data-testid="data-statistics-summary-panel">
    <CardHeader class="pb-3">
      <div class="flex flex-wrap items-baseline justify-between gap-2">
        <CardTitle class="text-base">
          {{ props.summary.year || props.fallbackYear }} 年各世代累计情况
        </CardTitle>
        <span v-if="props.summary.as_of_date" class="text-xs text-muted-foreground">
          截至 {{ props.summary.as_of_date }}
        </span>
      </div>
    </CardHeader>
    <CardContent>
      <div class="grid gap-3 md:grid-cols-3" data-testid="data-statistics-generation-summary">
        <article
          v-for="item in props.summary.generations"
          :key="item.generation"
          class="rounded-lg border p-4"
          :data-testid="`data-statistics-summary-${item.generation}`"
        >
          <h4 class="text-sm font-medium text-muted-foreground">{{ item.generation }}</h4>

          <div class="mt-2">
            <div class="flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold tabular-nums">
                {{ formatNumber(item.surveyed_points) }}
              </span>
              <span class="text-sm text-muted-foreground">个点位完成调查</span>
            </div>
            <p class="mt-0.5 text-xs text-muted-foreground">
              城区 {{ formatNumber(item.urban_surveyed_points) }} · 乡镇
              {{ formatNumber(item.town_surveyed_points) }}
            </p>
          </div>

          <dl class="mt-3 space-y-2 border-t pt-3 text-sm">
            <div class="flex items-baseline justify-between gap-2">
              <dt class="text-muted-foreground">发现受害点位</dt>
              <dd class="font-medium tabular-nums">
                {{ formatNumber(item.damaged_points) }} 个
              </dd>
            </div>
            <p class="-mt-1 text-right text-xs text-muted-foreground">
              城区 {{ formatNumber(item.urban_damaged_points) }} · 乡镇
              {{ formatNumber(item.town_damaged_points) }}
            </p>
            <div class="flex items-baseline justify-between gap-2">
              <dt class="text-muted-foreground">共下发派单</dt>
              <dd class="font-medium tabular-nums">
                {{ formatNumber(item.dispatch_count) }} 次
              </dd>
            </div>
          </dl>

          <div
            v-if="item.dispatch_frequency?.length"
            class="mt-3 flex flex-wrap gap-1.5"
          >
            <Badge
              v-for="frequency in item.dispatch_frequency"
              :key="frequency.dispatch_times"
              variant="secondary"
              class="font-normal"
            >
              {{ frequency.dispatch_times }} 次派单 {{ formatNumber(frequency.point_count) }} 个
            </Badge>
          </div>
          <p v-else class="mt-3 text-xs text-muted-foreground">暂无派单</p>
        </article>
      </div>
    </CardContent>
  </Card>
</template>
