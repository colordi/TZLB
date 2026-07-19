<script setup>
import { onMounted, ref } from "vue";
import { Users, Layers, Database, RefreshCw } from "@lucide/vue";

import { fetchDashboardStats } from "../api/admin.js";
import { isUnauthorizedError } from "../api/http.js";
import { useToast } from "../composables/useToast.js";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

const { error } = useToast();
const loading = ref(false);
const stats = ref(null);

const kpiCards = [
  {
    key: "users",
    icon: Users,
    label: "用户",
    fields: [
      { label: "总数", valueKey: "total" },
      { label: "管理员", valueKey: "admin_count" },
      { label: "调查员", valueKey: "investigator_count" },
      { label: "活跃", valueKey: "active_count" },
    ],
  },
  {
    key: "layers",
    icon: Layers,
    label: "图层元数据",
    fields: [
      { label: "总数", valueKey: "total" },
      { label: "点位图层", valueKey: "view_count" },
      { label: "参考图层", valueKey: "reference_count" },
    ],
  },
  {
    key: null,
    icon: Database,
    label: "数据库",
    fields: [
      { label: "地图视图", valueKey: "database_views" },
      { label: "参考空间表", valueKey: "database_reference_layers" },
    ],
  },
];

async function loadStats() {
  if (loading.value) return;
  loading.value = true;
  try {
    const data = await fetchDashboardStats();
    stats.value = data;
  } catch (err) {
    if (isUnauthorizedError(err)) return;
    error(`加载管理概览失败：${err.message || err}`, "加载失败");
  } finally {
    loading.value = false;
  }
}

function resolveCardValue(card, field) {
  if (!stats.value) return "--";
  if (card.key) {
    const group = stats.value[card.key];
    return group ? group[field.valueKey] ?? "--" : "--";
  }
  return stats.value[field.valueKey] ?? "--";
}

onMounted(() => {
  loadStats();
});
</script>

<template>
  <div class="mx-auto w-full max-w-6xl space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="space-y-1">
        <h1 class="text-2xl font-bold tracking-tight">管理概览</h1>
        <p class="text-sm text-muted-foreground">用户、图层及系统运行聚合信息</p>
      </div>
      <Button type="button" variant="outline" size="sm" :disabled="loading" @click="loadStats">
        <RefreshCw class="size-4" :class="{ 'animate-spin': loading }" />
        <span>{{ loading ? "加载中" : "刷新" }}</span>
      </Button>
    </div>

    <div v-if="loading && !stats" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <Skeleton v-for="i in 3" :key="i" class="h-40 rounded-xl" />
    </div>

    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <Card v-for="card in kpiCards" :key="card.label">
        <CardHeader class="flex flex-row items-center gap-3 space-y-0 pb-2">
          <span
            class="flex size-10 items-center justify-center rounded-md bg-primary text-primary-foreground"
          >
            <component :is="card.icon" class="size-5" />
          </span>
          <CardTitle class="text-base">{{ card.label }}</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="grid grid-cols-2 gap-3">
            <div v-for="field in card.fields" :key="field.label" class="space-y-0.5">
              <div class="text-xl font-semibold tabular-nums">
                {{ resolveCardValue(card, field) }}
              </div>
              <div class="text-xs text-muted-foreground">{{ field.label }}</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
