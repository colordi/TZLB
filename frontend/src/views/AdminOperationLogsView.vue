<script setup>
import { computed, onMounted, ref } from "vue";
import { RefreshCw, ShieldCheck, Shield } from "@lucide/vue";

import { fetchOperationLogs } from "../api/admin.js";
import { isUnauthorizedError } from "../api/http.js";
import { useToast } from "../composables/useToast.js";
import PageHeader from "@/components/common/PageHeader.vue";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

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

function goToPage(value) {
  if (value === currentPage.value) return;
  currentPage.value = value;
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
  <div class="mx-auto w-full max-w-6xl space-y-6">
    <PageHeader title="操作日志" :description="`点位删除操作记录，共 ${total} 条`">
      <template #actions>
        <Button type="button" variant="outline" size="sm" :disabled="loading" @click="load">
          <RefreshCw class="size-4" :class="{ 'animate-spin': loading }" />
          <span>刷新</span>
        </Button>
      </template>
    </PageHeader>

    <div class="overflow-hidden rounded-xl border bg-card shadow-sm">
      <div class="overflow-x-auto">
        <Table class="min-w-[56rem]">
        <TableHeader>
          <TableRow class="hover:bg-transparent">
            <TableHead>时间</TableHead>
            <TableHead>操作人</TableHead>
            <TableHead>角色</TableHead>
            <TableHead>动作</TableHead>
            <TableHead>点位编号</TableHead>
            <TableHead>点位名称</TableHead>
            <TableHead>属地</TableHead>
            <TableHead>坐标</TableHead>
            <TableHead>关联调查记录</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="log in logs" :key="log.id">
            <TableCell class="text-muted-foreground">
              {{ log.occurred_at ? new Date(log.occurred_at).toLocaleString("zh-CN") : "--" }}
            </TableCell>
            <TableCell>
              {{ log.operator_display_name }}
              <code class="ml-1 text-xs text-muted-foreground">{{ log.operator_username }}</code>
            </TableCell>
            <TableCell>
              <Badge :variant="log.operator_role === 'admin' ? 'default' : 'secondary'">
                <ShieldCheck v-if="log.operator_role === 'admin'" class="size-3.5" />
                <Shield v-else class="size-3.5" />
                {{ roleLabel[log.operator_role] || log.operator_role }}
              </Badge>
            </TableCell>
            <TableCell>{{ log.action }}</TableCell>
            <TableCell><code class="text-xs">{{ log.site_code }}</code></TableCell>
            <TableCell>{{ log.site_name || "--" }}</TableCell>
            <TableCell>{{ log.locality || "--" }}</TableCell>
            <TableCell class="text-muted-foreground">
              {{ formatCoordinate(log.longitude) }}, {{ formatCoordinate(log.latitude) }}
            </TableCell>
            <TableCell>
              <Badge :variant="log.survey_record_count > 0 ? 'destructive' : 'outline'">
                {{ log.survey_record_count }}
              </Badge>
            </TableCell>
          </TableRow>
          <TableRow v-if="logs.length === 0 && !loading">
            <TableCell colspan="9" class="h-24 text-center text-muted-foreground">
              暂无操作日志
            </TableCell>
          </TableRow>
          <TableRow v-if="loading">
            <TableCell colspan="9" class="h-24 text-center text-muted-foreground">
              加载中…
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-2 border-t px-4 py-3">
        <p class="text-sm text-muted-foreground">
          第 {{ Math.min((currentPage - 1) * pageSize + 1, total) }}–{{ Math.min(currentPage * pageSize, total) }} 条，共 {{ total }} 条
        </p>
        <Pagination
          :page="currentPage"
          :items-per-page="pageSize"
          :total="total"
          :sibling-count="1"
          :disabled="loading"
          show-edges
          class="mx-0 w-auto justify-end"
          @update:page="goToPage"
        >
          <PaginationContent v-slot="{ items }">
            <PaginationPrevious data-testid="logs-prev-page" />
            <template v-for="(item, index) in items" :key="index">
              <PaginationItem
                v-if="item.type === 'page'"
                :value="item.value"
                :is-active="item.value === currentPage"
              >
                {{ item.value }}
              </PaginationItem>
              <PaginationEllipsis v-else />
            </template>
            <PaginationNext data-testid="logs-next-page" />
          </PaginationContent>
        </Pagination>
      </div>
    </div>
  </div>
</template>
