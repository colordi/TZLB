<script setup>
import { onMounted, ref } from "vue";
import { LayoutDashboard, Users, Layers, Database, RefreshCw } from "@lucide/vue";

import { fetchDashboardStats } from "../api/admin.js";
import { isUnauthorizedError } from "../api/http.js";
import { useToast } from "../composables/useToast.js";

const { error } = useToast();
const loading = ref(false);
const stats = ref(null);

const kpiCards = [
  {
    key: "users",
    icon: Users,
    label: "用户",
    color: "var(--color-primary)",
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
    color: "var(--color-accent)",
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
    color: "var(--color-secondary, #6B8F3E)",
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
  <div class="admin-page">
    <div class="page-header">
      <div class="page-header-copy">
        <h1 class="page-title">管理概览</h1>
        <p class="page-desc">用户、图层及系统运行聚合信息</p>
      </div>
      <button
        type="button"
        class="btn btn-secondary"
        :disabled="loading"
        @click="loadStats"
      >
        <RefreshCw :size="16" :stroke-width="2" :class="{ 'is-spinning': loading }" />
        <span>{{ loading ? "加载中" : "刷新" }}</span>
      </button>
    </div>

    <div v-if="loading && !stats" class="skeleton-grid">
      <div v-for="i in 3" :key="i" class="skeleton-card"></div>
    </div>

    <div v-else class="kpi-grid">
      <div v-for="card in kpiCards" :key="card.label" class="kpi-card">
        <div class="kpi-card-head">
          <span class="kpi-icon" :style="{ background: card.color }">
            <component :is="card.icon" :size="20" :stroke-width="2" />
          </span>
          <span class="kpi-label">{{ card.label }}</span>
        </div>
        <div class="kpi-fields">
          <div v-for="field in card.fields" :key="field.label" class="kpi-field">
            <span class="kpi-field-value">{{ resolveCardValue(card, field) }}</span>
            <span class="kpi-field-label">{{ field.label }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-page {
  max-width: var(--content-width, 1200px);
  width: 100%;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-6, 1.5rem);
  margin-bottom: var(--space-8, 2rem);
}

.page-header-copy {
  min-width: 0;
}

.page-title {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--text-2xl, 1.5rem);
  font-weight: 700;
  color: var(--color-text);
}

.page-desc {
  margin: var(--space-1, 0.25rem) 0 0;
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-muted, #666);
}

/* KPI grid */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-6, 1.5rem);
}

.kpi-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg, 12px);
  background: var(--color-surface);
  overflow: hidden;
}

.kpi-card-head {
  display: flex;
  align-items: center;
  gap: var(--space-3, 0.75rem);
  padding: var(--space-5, 1.25rem) var(--space-6, 1.5rem) 0;
}

.kpi-icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-md, 8px);
  color: #fff;
  flex-shrink: 0;
}

.kpi-label {
  font-size: var(--text-base, 1rem);
  font-weight: 600;
  color: var(--color-text);
}

.kpi-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  padding: var(--space-4, 1rem) var(--space-6, 1.5rem) var(--space-5, 1.25rem);
}

.kpi-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 0.25rem);
  padding: var(--space-2, 0.5rem) 0;
}

.kpi-field-value {
  font-size: var(--text-2xl, 1.5rem);
  font-weight: 700;
  color: var(--color-text);
  line-height: 1.1;
}

.kpi-field-label {
  font-size: var(--text-xs, 0.75rem);
  color: var(--color-text-muted, #666);
}

/* skeleton */
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-6, 1.5rem);
}

.skeleton-card {
  height: 160px;
  border-radius: var(--radius-lg, 12px);
  background: var(--color-surface-container, #f0f0f0);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* refresh button */
.btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2, 0.5rem);
  min-height: 2.5rem;
  padding: 0.5rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 8px);
  font-size: var(--text-sm, 0.875rem);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--motion-fast, 150ms) var(--ease-standard, ease);
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--color-surface);
  color: var(--color-text);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-surface-container, #f0f0f0);
}

.is-spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
