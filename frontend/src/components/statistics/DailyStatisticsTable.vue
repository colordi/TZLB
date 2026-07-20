<script setup>
import { computed, ref, watch } from "vue";
import { ChevronLeft, ChevronRight, Inbox, LoaderCircle } from "@lucide/vue";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/native-select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const props = defineProps({
  title: { type: String, required: true },
  emptyText: { type: String, required: true },
  columns: { type: Array, default: () => [] },
  rows: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  generation: { type: String, default: "" },
  generationOptions: { type: Array, default: () => [] },
});

const emit = defineEmits(["update:generation"]);

const currentPage = ref(1);
const PAGE_SIZE = 7;

const totalPages = computed(() => Math.max(1, Math.ceil(props.rows.length / PAGE_SIZE)));

const paginatedRows = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE;
  return props.rows.slice(start, start + PAGE_SIZE);
});

watch(
  () => props.rows,
  () => {
    currentPage.value = 1;
  },
);

function formatNumber(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  return Number(value || 0).toLocaleString("zh-CN");
}

function formatCell(row, column) {
  const value = row[column.key];
  return column.type === "number" ? formatNumber(value) : value || "--";
}

function resolveColumnGroup(columnKey) {
  if (columnKey === "date") {
    return "日期";
  }
  if (
    columnKey === "daily_treatment_plants" ||
    columnKey === "cumulative_completed_points"
  ) {
    return "汇总";
  }
  if (columnKey.startsWith("urban_")) {
    return "城区";
  }
  if (columnKey.startsWith("town_")) {
    return "乡镇";
  }
  if (columnKey === "daily_dispatch_points") {
    return "派单";
  }
  return "";
}

const groupedColumns = computed(() => {
  const groups = [];
  let current = null;
  props.columns.forEach((column, index) => {
    const label = resolveColumnGroup(column.key);
    if (!current || current.label !== label) {
      current = { label, start: index, count: 1, columns: [column] };
      groups.push(current);
    } else {
      current.count += 1;
      current.columns.push(column);
    }
  });
  return groups;
});

const groupStartIndices = computed(() => {
  return new Set(groupedColumns.value.filter((g) => g.start > 0).map((g) => g.start));
});

const multiColumnGroupLabels = computed(() => {
  return new Set(groupedColumns.value.filter((g) => g.count > 1).map((g) => g.label));
});

function cellClass(column) {
  return {
    "text-right tabular-nums": column.type === "number",
    "whitespace-nowrap": column.type === "date",
  };
}

// 二级表头省略与分组名重复的前缀，如“城区当日受害点位数”→“当日受害点位数”
function subColumnLabel(column) {
  const group = resolveColumnGroup(column.key);
  if (group && column.label.startsWith(group)) {
    return column.label.slice(group.length);
  }
  return column.label;
}

function handleGenerationChange(event) {
  emit("update:generation", event.target.value);
}
</script>

<template>
  <Card data-testid="data-statistics-daily-panel">
    <CardHeader class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div class="space-y-1">
        <CardTitle class="text-base">{{ props.title }}</CardTitle>
        <CardDescription>{{ props.rows.length }} 条每日记录</CardDescription>
      </div>
      <div class="flex flex-wrap items-center gap-2" aria-label="筛选条件">
        <label class="flex items-center gap-2 text-sm text-muted-foreground">
          <span>世代</span>
          <NativeSelect
            :model-value="props.generation"
            class="h-8 py-1"
            data-testid="data-statistics-generation-filter"
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

    <CardContent class="space-y-4">
      <div
        v-if="props.loading"
        class="flex items-center justify-center gap-2 rounded-lg border border-dashed px-4 py-10 text-sm text-muted-foreground"
      >
        <LoaderCircle class="size-4 animate-spin text-muted-foreground/60" />
        <p>正在读取每日统计…</p>
      </div>
      <div
        v-else-if="props.rows.length === 0"
        class="flex items-center justify-center gap-2 rounded-lg border border-dashed px-4 py-10 text-sm text-muted-foreground"
      >
        <Inbox class="size-4 text-muted-foreground/50" />
        <p>{{ props.emptyText }}</p>
      </div>

      <div v-else class="rounded-md border">
        <Table class="min-w-[48rem]">
          <TableHeader>
            <TableRow class="bg-muted/50 hover:bg-muted/50">
              <template v-for="group in groupedColumns" :key="group.label">
                <TableHead
                  v-if="group.count === 1"
                  rowspan="2"
                  class="font-semibold text-muted-foreground"
                  :class="[cellClass(group.columns[0]), group.start > 0 ? 'border-l' : '']"
                >
                  {{ group.label }}
                </TableHead>
                <TableHead
                  v-else
                  :colspan="group.count"
                  class="text-center font-semibold text-muted-foreground"
                  :class="group.start > 0 ? 'border-l' : ''"
                >
                  {{ group.label }}
                </TableHead>
              </template>
            </TableRow>
            <TableRow class="bg-muted/30 hover:bg-muted/30">
              <template v-for="(column, index) in props.columns" :key="column.key">
                <TableHead
                  v-if="multiColumnGroupLabels.has(resolveColumnGroup(column.key))"
                  class="text-muted-foreground"
                  :class="[cellClass(column), groupStartIndices.has(index) ? 'border-l' : '']"
                >
                  {{ subColumnLabel(column) }}
                </TableHead>
              </template>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="(row, rowIndex) in paginatedRows"
              :key="row.date"
              :class="{ 'bg-primary/5 hover:bg-primary/10': rowIndex === 0 && currentPage === 1 }"
              :data-testid="`data-statistics-row-${row.date}`"
            >
              <TableCell
                v-for="(column, index) in columns"
                :key="column.key"
                :class="[
                  cellClass(column),
                  groupStartIndices.has(index) ? 'border-l' : '',
                  column.key === 'date' ? 'font-medium' : '',
                ]"
              >
                {{ formatCell(row, column) }}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>

      <nav
        v-if="totalPages > 1"
        class="flex items-center justify-end gap-3"
        aria-label="分页导航"
      >
        <Button
          type="button"
          variant="outline"
          size="sm"
          :disabled="currentPage === 1"
          data-testid="data-statistics-prev-page"
          @click="currentPage -= 1"
        >
          <ChevronLeft class="size-4" />
          <span>上一页</span>
        </Button>
        <span class="text-sm text-muted-foreground">
          第 {{ currentPage }} / {{ totalPages }} 页
        </span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          :disabled="currentPage === totalPages"
          data-testid="data-statistics-next-page"
          @click="currentPage += 1"
        >
          <span>下一页</span>
          <ChevronRight class="size-4" />
        </Button>
      </nav>
    </CardContent>
  </Card>
</template>
