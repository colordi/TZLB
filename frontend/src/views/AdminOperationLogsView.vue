<script setup>
import { computed, onMounted, ref } from "vue";
import { RefreshCw, ShieldCheck, Shield } from "@lucide/vue";

import { fetchOperationLogs } from "../api/admin.js";
import { isUnauthorizedError } from "../api/http.js";
import { useToast } from "../composables/useToast.js";

const { error } = useToast();
const loading = ref(false);
const logs = ref([]);
const total = ref(0);
const currentPage = ref(1);
const pageSize = 50;

const roleLabel = {
  admin: "管理员",
  investigator: "调查员",
};

const totalPages = computed(() =>
  total.value > 0 ? Math.max(1, Math.ceil(total.value / pageSize)) : 1,
);
const canPrev = computed(() => currentPage.value > 1);
const canNext = computed(() => currentPage.value < totalPages.value);

const logPageRange = computed(() => `第 ${currentPage.value} / ${totalPages.value} 页`);

async function load() {
  if (loading.value) return;
  loading.value = true;
  try {
    const payload = await fetchOperationLogs({
      limit: pageSize,
      offset: (currentPage.value - 1) * pageSize,
    });
    logs.value = payload.items || [];
    total.value = payload.total || 0;
    if (currentPage.value > totalPages.value) {
      currentPage.value = totalPages.value;
    }
  } catch (err) {
    if (isUnauthorizedError(err)) return;
    error(`加载操作日志失败：${err.message || err}`, "加载失败");
  } finally {
    loading.value = false;
  }
}

function goPrev() {
  if (!canPrev.value) return;
  currentPage.value -= 1;
  load();
}

function goNext() {
  if (!canNext.value) return;
  currentPage.value += 1;
  load();
}

function formatCoordinate(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "--";
  }
  return Number(value).toFixed(6);
}

onMounted(() => {
  load();
});
</script>

<template>
  <div class="admin-page">
    <div class="page-header">
      <div class="page-header-copy">
        <h1 class="page-title">操作日志</h1>
        <p class="page-desc">点位删除操作记录，共 {{ total }} 条</p>
      </div>
      <div class="page-actions">
        <button type="button" class="btn btn-secondary" :disabled="loading" @click="load">
          <RefreshCw :size="16" :stroke-width="2" :class="{ 'is-spinning': loading }" />
          <span>刷新</span>
        </button>
      </div>
    </div>

    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>时间</th>
            <th>操作人</th>
            <th>角色</th>
            <th>动作</th>
            <th>点位编号</th>
            <th>点位名称</th>
            <th>属地</th>
            <th>坐标</th>
            <th>关联调查记录</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.id">
            <td class="cell-muted">
              {{ log.occurred_at ? new Date(log.occurred_at).toLocaleString("zh-CN") : "--" }}
            </td>
            <td>
              {{ log.operator_display_name }}
              <code class="cell-username">{{ log.operator_username }}</code>
            </td>
            <td>
              <span class="badge" :class="log.operator_role === 'admin' ? 'badge-admin' : 'badge-investigator'">
                <ShieldCheck v-if="log.operator_role === 'admin'" :size="14" :stroke-width="2" />
                <Shield v-else :size="14" :stroke-width="2" />
                {{ roleLabel[log.operator_role] || log.operator_role }}
              </span>
            </td>
            <td>{{ log.action }}</td>
            <td><code>{{ log.site_code }}</code></td>
            <td>{{ log.site_name || "--" }}</td>
            <td>{{ log.locality || "--" }}</td>
            <td class="cell-muted">{{ formatCoordinate(log.longitude) }}, {{ formatCoordinate(log.latitude) }}</td>
            <td>
              <span
                class="badge"
                :class="log.survey_record_count > 0 ? 'badge-warn' : 'badge-muted'"
              >
                {{ log.survey_record_count }}
              </span>
            </td>
          </tr>
          <tr v-if="logs.length === 0 && !loading">
            <td colspan="9" class="cell-empty">暂无操作日志</td>
          </tr>
          <tr v-if="loading">
            <td colspan="9" class="cell-empty">加载中…</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="pager">
      <button
        type="button"
        class="btn btn-secondary pager-btn"
        :disabled="!canPrev || loading"
        @click="goPrev"
      >
        上一页
      </button>
      <span class="pager-info">{{ logPageRange }} · 共 {{ total }} 条</span>
      <button
        type="button"
        class="btn btn-secondary pager-btn"
        :disabled="!canNext || loading"
        @click="goNext"
      >
        下一页
      </button>
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
  margin-bottom: var(--space-6, 1.5rem);
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

.page-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3, 0.75rem);
  flex-shrink: 0;
}

.table-wrap {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg, 12px);
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 0.7rem 1rem;
  text-align: left;
  font-size: var(--text-sm, 0.875rem);
  vertical-align: top;
}

.data-table th {
  background: var(--color-surface-container, #f5f5f5);
  font-weight: 600;
  color: var(--color-text-muted, #666);
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}

.data-table td {
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text);
}

.data-table tr:last-child td {
  border-bottom: none;
}

.cell-muted {
  color: var(--color-text-muted, #666);
}

.cell-username {
  margin-left: 0.25rem;
  font-size: var(--text-xs, 0.75rem);
  color: var(--color-text-muted, #666);
}

.cell-empty {
  text-align: center;
  padding: 2rem !important;
  color: var(--color-text-muted, #666);
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-pill, 999px);
  font-size: var(--text-xs, 0.75rem);
  font-weight: 600;
  white-space: nowrap;
}

.badge-admin {
  background: #dbeafe;
  color: #1d4ed8;
}

.badge-investigator {
  background: #dcfce7;
  color: #16a34a;
}

.badge-warn {
  background: #fef3c7;
  color: #b45309;
}

.badge-muted {
  background: var(--color-surface-container, #f0f0f0);
  color: var(--color-text-muted, #666);
}

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

.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4, 1rem);
  margin-top: var(--space-5, 1.25rem);
}

.pager-btn {
  min-height: 2.25rem;
  padding: 0.4rem 0.9rem;
}

.pager-info {
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-muted, #666);
}
</style>