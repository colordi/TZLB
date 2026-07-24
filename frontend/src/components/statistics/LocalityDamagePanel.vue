<script setup>
import { computed } from "vue";
import {
  AlertTriangle,
  CheckCircle2,
  HandHelping,
  MapPinned,
  Trees,
} from "@lucide/vue";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/native-select";
import { Skeleton } from "@/components/ui/skeleton";

const props = defineProps({
  summary: {
    type: Object,
    default: () => ({
      year: null,
      generation: null,
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
    }),
  },
  loading: {
    type: Boolean,
    default: false,
  },
  generation: {
    type: String,
    default: "",
  },
  generationOptions: {
    type: Array,
    default: () => [],
  },
  asOfDate: {
    type: String,
    default: "",
  },
  severePlantThreshold: {
    type: [Number, String],
    default: 10,
  },
});

const emit = defineEmits([
  "update:generation",
  "update:asOfDate",
  "update:severePlantThreshold",
]);

const totals = computed(() => props.summary?.totals || {});
const threshold = computed(() => Number(props.severePlantThreshold) || 10);

// 后端已按 Excel 属地清单顺序返回，前端不再重排
const localities = computed(() =>
  Array.isArray(props.summary?.localities) ? props.summary.localities : [],
);

const kpiItems = computed(() => [
  {
    key: "damaged_points",
    label: "受害点位",
    value: totals.value.damaged_points,
    unit: "个",
    icon: MapPinned,
    hint: "台账问题点位合计",
  },
  {
    key: "damaged_plants",
    label: "累计受害株",
    value: totals.value.damaged_plants,
    unit: "株",
    icon: Trees,
    hint: "受害株数汇总",
  },
  {
    key: "completion_rate",
    label: "防治完成率",
    value: totals.value.completion_rate,
    unit: "%",
    icon: CheckCircle2,
    hint: `${formatNumber(totals.value.completed_points)} / ${formatNumber(totals.value.damaged_points)} 已完成`,
    isRate: true,
  },
  {
    key: "severe_points",
    label: "严重点位",
    value: totals.value.severe_points,
    unit: "个",
    icon: AlertTriangle,
    hint: `受害株 ≥ ${threshold.value}`,
  },
  {
    key: "collab_points",
    label: "协同点数",
    value: totals.value.collab_points,
    unit: "个",
    icon: HandHelping,
    hint: "备注含「协同」",
  },
]);

function formatNumber(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  return Number(value || 0).toLocaleString("zh-CN");
}

function formatRate(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  return `${Number(value || 0).toFixed(Number(value || 0) % 1 === 0 ? 0 : 1)}%`;
}

function completionTone(rate) {
  const value = Number(rate || 0);
  if (value >= 80) {
    return "text-success";
  }
  if (value >= 50) {
    return "text-warning-foreground";
  }
  return "text-destructive";
}

function completionBarClass(rate) {
  const value = Number(rate || 0);
  if (value >= 80) {
    return "bg-success";
  }
  if (value >= 50) {
    return "bg-warning";
  }
  return "bg-destructive";
}

function severeSites(item) {
  return Array.isArray(item?.severe_sites) ? item.severe_sites : [];
}

function handleGenerationChange(event) {
  emit("update:generation", event.target.value);
}

function handleAsOfDateChange(event) {
  emit("update:asOfDate", event.target.value);
}

function handleThresholdChange(event) {
  const raw = event.target.value;
  if (raw === "") {
    return;
  }
  const next = Number(raw);
  if (!Number.isFinite(next) || next < 1) {
    return;
  }
  emit("update:severePlantThreshold", Math.min(10000, Math.floor(next)));
}
</script>

<template>
  <Card data-testid="data-statistics-locality-panel">
    <CardHeader class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div class="space-y-1">
        <CardTitle class="text-base">各属地受害情况</CardTitle>
        <CardDescription>
          按乡镇街道汇总截至所选日期的受害点位、受害株、防治完成、严重与协同情况
          <span v-if="threshold">（严重：受害株 ≥ {{ threshold }}）</span>
        </CardDescription>
      </div>
      <div class="flex flex-wrap items-center gap-3" aria-label="属地统计筛选">
        <label class="flex items-center gap-2 text-sm text-muted-foreground">
          <span>截止日期</span>
          <input
            type="date"
            class="h-8 rounded-md border border-input bg-background px-2 text-sm text-foreground"
            :value="props.asOfDate"
            data-testid="data-statistics-locality-as-of-date"
            @change="handleAsOfDateChange"
          />
        </label>
        <label class="flex items-center gap-2 text-sm text-muted-foreground">
          <span>严重阈值</span>
          <input
            type="number"
            min="1"
            max="10000"
            step="1"
            class="h-8 w-16 rounded-md border border-input bg-background px-2 text-sm tabular-nums text-foreground"
            :value="threshold"
            data-testid="data-statistics-locality-severe-threshold"
            @change="handleThresholdChange"
          />
          <span class="text-xs">株</span>
        </label>
        <label class="flex items-center gap-2 text-sm text-muted-foreground">
          <span>世代</span>
          <NativeSelect
            :model-value="props.generation"
            class="h-8 py-1"
            data-testid="data-statistics-locality-generation-filter"
            @change="handleGenerationChange"
          >
            <option value="">全部</option>
            <option v-for="gen in props.generationOptions" :key="gen" :value="gen">
              {{ gen }}
            </option>
          </NativeSelect>
        </label>
      </div>
    </CardHeader>

    <CardContent class="space-y-5">
      <div
        class="grid gap-3 sm:grid-cols-2 lg:grid-cols-5"
        data-testid="data-statistics-locality-kpi"
      >
        <template v-if="props.loading">
          <Skeleton v-for="index in 5" :key="index" class="h-24 rounded-xl" />
        </template>
        <article
          v-for="item in kpiItems"
          v-else
          :key="item.key"
          class="rounded-xl border bg-card p-4 shadow-sm"
          :data-testid="`data-statistics-locality-kpi-${item.key}`"
        >
          <div class="flex items-center justify-between gap-2">
            <p class="text-sm text-muted-foreground">{{ item.label }}</p>
            <component :is="item.icon" class="size-4 text-muted-foreground" />
          </div>
          <div class="mt-2 flex items-baseline gap-1">
            <span class="text-2xl font-bold tracking-tight tabular-nums">
              {{ item.isRate ? formatRate(item.value).replace("%", "") : formatNumber(item.value) }}
            </span>
            <span class="text-sm text-muted-foreground">{{ item.unit }}</span>
          </div>
          <p class="mt-1 text-xs text-muted-foreground">{{ item.hint }}</p>
        </article>
      </div>

      <div v-if="props.loading" class="space-y-2" data-testid="data-statistics-locality-loading">
        <Skeleton v-for="index in 6" :key="index" class="h-20 rounded-lg" />
      </div>

      <div
        v-else-if="localities.length === 0"
        class="rounded-xl border border-dashed px-4 py-10 text-center text-sm text-muted-foreground"
        data-testid="data-statistics-locality-empty"
      >
        暂无属地受害数据。
      </div>

      <ol
        v-else
        class="space-y-2"
        data-testid="data-statistics-locality-list"
      >
        <li
          v-for="(item, index) in localities"
          :key="item.locality"
          class="rounded-xl border bg-card p-3 shadow-sm"
          :data-testid="`data-statistics-locality-row-${item.locality}`"
        >
          <div class="flex flex-col gap-3 sm:flex-row sm:items-start">
            <!-- 左侧：属地 + 紧凑完成率 -->
            <div class="flex shrink-0 items-start gap-3 sm:w-52">
              <span
                class="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-secondary text-xs font-semibold tabular-nums text-secondary-foreground"
              >
                {{ index + 1 }}
              </span>
              <div class="min-w-0 space-y-2">
                <div>
                  <p class="font-medium">{{ item.locality }}</p>
                  <p class="text-xs text-muted-foreground tabular-nums">
                    {{ formatNumber(item.damaged_points) }} 个点位 ·
                    {{ formatNumber(item.damaged_plants) }} 株 ·
                    协同 {{ formatNumber(item.collab_points) }}
                  </p>
                </div>
                <div class="flex items-center gap-2">
                  <div
                    class="h-1.5 w-16 shrink-0 overflow-hidden rounded-full bg-muted"
                    aria-hidden="true"
                  >
                    <div
                      class="h-full rounded-full transition-[width] duration-200"
                      :class="completionBarClass(item.completion_rate)"
                      :style="{ width: `${Math.min(100, Number(item.completion_rate || 0))}%` }"
                    />
                  </div>
                  <span
                    class="text-xs font-medium tabular-nums"
                    :class="completionTone(item.completion_rate)"
                    :data-testid="`data-statistics-locality-rate-${item.locality}`"
                  >
                    {{ formatRate(item.completion_rate) }}
                  </span>
                  <span class="text-xs text-muted-foreground tabular-nums">
                    {{ formatNumber(item.completed_points) }}/{{ formatNumber(item.damaged_points) }}
                  </span>
                </div>
              </div>
            </div>

            <!-- 右侧：严重点位名单 -->
            <div
              class="min-w-0 flex-1 border-t pt-3 sm:border-t-0 sm:border-l sm:pt-0 sm:pl-4"
              :data-testid="`data-statistics-locality-severe-${item.locality}`"
            >
              <div class="mb-1.5 flex items-center gap-2 text-xs text-muted-foreground">
                <AlertTriangle class="size-3.5 shrink-0 text-destructive" />
                <span>
                  严重点位
                  <span class="tabular-nums font-medium text-foreground">
                    {{ formatNumber(item.severe_points) }}
                  </span>
                </span>
              </div>
              <div
                v-if="severeSites(item).length === 0"
                class="text-xs text-muted-foreground"
              >
                无
              </div>
              <ul
                v-else
                class="flex max-h-24 flex-wrap gap-1.5 overflow-y-auto"
              >
                <li
                  v-for="site in severeSites(item)"
                  :key="site.code"
                >
                  <Badge
                    variant="outline"
                    class="max-w-full gap-1 font-normal border-destructive/25 bg-destructive/5 text-foreground"
                    :title="`${site.code} ${site.name}（${site.damaged_plants} 株）`"
                  >
                    <span class="shrink-0 font-mono text-[11px] tabular-nums">{{ site.code }}</span>
                    <span class="truncate text-muted-foreground">{{ site.name }}</span>
                  </Badge>
                </li>
              </ul>
            </div>
          </div>
        </li>
      </ol>
    </CardContent>
  </Card>
</template>
