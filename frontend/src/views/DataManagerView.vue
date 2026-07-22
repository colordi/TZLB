<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import {
  Bug,
  ChevronLeft,
  ChevronRight,
  Database,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Trash2,
} from "@lucide/vue";

import {
  fetchManageableTables,
  fetchTableColumns,
  fetchTableRows,
  createTableRow,
  updateTableRow,
  deleteTableRow,
  fetchChangeLogs,
} from "../api/dataManager.js";
import { isUnauthorizedError } from "../api/http.js";
import { useToast } from "../composables/useToast.js";
import {
  editableColumns,
  gridColumns,
  buildInitialValues,
  validateFormValues,
  buildSubmitValues,
  isRequiredColumn,
  diffChangeLog,
} from "../components/datamanager/formModel.js";
import {
  groupTablesByPest,
  shortTableLabel,
} from "../components/datamanager/tableGroups.js";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

/** 工具栏优先展示的过滤列，按顺序取表中存在的列 */
const PREFERRED_FILTER_COLUMNS = [
  "编号",
  "属地",
  "点位名称",
  "调查日期",
  "年份",
  "世代",
  "危害程度",
  "害虫类型",
];
const MAX_FILTER_INPUTS = 5;

const ACTION_LABELS = {
  insert: "新增",
  update: "修改",
  delete: "删除",
};
const ACTION_BADGE_VARIANTS = {
  insert: "default",
  update: "secondary",
  delete: "destructive",
};

const { error, success } = useToast();

/* ── 表清单与虫种分组 ────────────────────── */
const tables = ref([]);
const tablesLoading = ref(false);
const selectedTable = ref(null);
const activePest = ref("");

const pestGroups = computed(() => groupTablesByPest(tables.value));

const currentPestTables = computed(() => {
  return (
    pestGroups.value.find((g) => g.pest === activePest.value)?.tables || []
  );
});

/* ── 当前表数据 ─────────────────────────── */
const columns = ref([]);
const columnsLoading = ref(false);
const rows = ref([]);
const rowsTotal = ref(0);
const rowsLoading = ref(false);
const page = ref(1);
const pageSize = 20;

const tableColumns = computed(() => gridColumns(columns.value));
const formColumns = computed(() => editableColumns(columns.value));
const hasPrimaryKey = computed(() => Boolean(selectedTable.value?.has_primary_key));

const filterValues = reactive({});
const appliedFilters = ref({});
const filterableColumns = computed(() => {
  const names = new Set(columns.value.map((c) => c.name));
  return PREFERRED_FILTER_COLUMNS.filter((name) => names.has(name)).slice(
    0,
    MAX_FILTER_INPUTS,
  );
});

/* ── 新增 / 编辑 ────────────────────────── */
const showForm = ref(false);
const formMode = ref("create");
const editingRow = ref(null);
const formValues = ref({});
const formErrors = ref({});
const saving = ref(false);

/* ── 删除 ───────────────────────────────── */
const showDelete = ref(false);
const deletingRow = ref(null);
const deleting = ref(false);

/* ── 变更记录 ───────────────────────────── */
const activeTab = ref("rows");
const logs = ref([]);
const logsTotal = ref(0);
const logsLoading = ref(false);
const logsPage = ref(1);
const logsPageSize = 20;

const logsTotalPages = computed(() =>
  logsTotal.value > 0 ? Math.max(1, Math.ceil(logsTotal.value / logsPageSize)) : 1,
);

function formatNumber(value) {
  return Number(value || 0).toLocaleString("zh-CN");
}

function formatCell(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  if (typeof value === "boolean") {
    return value ? "是" : "否";
  }
  return String(value);
}

function pkOf(row) {
  const pk = {};
  for (const key of selectedTable.value?.primary_key || []) {
    pk[key] = row[key];
  }
  return pk;
}

function formatPk(pk) {
  if (!pk || typeof pk !== "object") {
    return "--";
  }
  const parts = Object.entries(pk).map(([k, v]) => `${k}=${v}`);
  return parts.length > 0 ? parts.join("，") : "--";
}

function formatTime(value) {
  return value ? new Date(value).toLocaleString("zh-CN") : "--";
}

function pestOfTable(table) {
  const group = pestGroups.value.find((g) =>
    g.tables.some(
      (t) =>
        t.schema_name === table.schema_name && t.table_name === table.table_name,
    ),
  );
  return group?.pest || "";
}

/* ── 加载逻辑 ───────────────────────────── */
async function loadTables() {
  tablesLoading.value = true;
  try {
    tables.value = await fetchManageableTables();
    const stillThere =
      selectedTable.value &&
      tables.value.some(
        (t) =>
          t.schema_name === selectedTable.value.schema_name &&
          t.table_name === selectedTable.value.table_name,
      );
    if (stillThere) {
      activePest.value = pestOfTable(selectedTable.value);
    } else {
      selectedTable.value = null;
      const first = pestGroups.value[0];
      if (first && first.tables.length > 0) {
        activePest.value = first.pest;
        selectTable(first.tables[0]);
      }
    }
  } catch (err) {
    if (isUnauthorizedError(err)) return;
    error(`加载表清单失败：${err.message || err}`, "加载失败");
  } finally {
    tablesLoading.value = false;
  }
}

function selectPest(pest) {
  if (!pest || pest === activePest.value) {
    return;
  }
  activePest.value = pest;
  const group = pestGroups.value.find((g) => g.pest === pest);
  if (group && group.tables.length > 0) {
    selectTable(group.tables[0]);
  }
}

function selectTable(table) {
  if (
    selectedTable.value?.schema_name === table.schema_name &&
    selectedTable.value?.table_name === table.table_name
  ) {
    return;
  }
  selectedTable.value = table;
  columns.value = [];
  rows.value = [];
  rowsTotal.value = 0;
  page.value = 1;
  appliedFilters.value = {};
  for (const key of Object.keys(filterValues)) {
    delete filterValues[key];
  }
  logs.value = [];
  logsTotal.value = 0;
  logsPage.value = 1;
  loadColumns();
  loadRows();
  loadLogs();
}

async function loadColumns() {
  if (!selectedTable.value) return;
  columnsLoading.value = true;
  try {
    columns.value = await fetchTableColumns(
      selectedTable.value.schema_name,
      selectedTable.value.table_name,
    );
  } catch (err) {
    if (isUnauthorizedError(err)) return;
    error(`加载字段信息失败：${err.message || err}`, "加载失败");
  } finally {
    columnsLoading.value = false;
  }
}

async function loadRows() {
  if (!selectedTable.value) return;
  rowsLoading.value = true;
  try {
    const payload = await fetchTableRows(
      selectedTable.value.schema_name,
      selectedTable.value.table_name,
      { page: page.value, pageSize, filters: appliedFilters.value },
    );
    rows.value = payload.rows || [];
    rowsTotal.value = payload.total || 0;
  } catch (err) {
    if (isUnauthorizedError(err)) return;
    error(`加载数据失败：${err.message || err}`, "加载失败");
  } finally {
    rowsLoading.value = false;
  }
}

function applyFilters() {
  const filters = {};
  for (const name of filterableColumns.value) {
    const value = (filterValues[name] || "").trim();
    if (value) {
      filters[name] = value;
    }
  }
  appliedFilters.value = filters;
  page.value = 1;
  loadRows();
}

function resetFilters() {
  for (const key of Object.keys(filterValues)) {
    filterValues[key] = "";
  }
  applyFilters();
}

watch(page, () => {
  loadRows();
});

/* ── 新增 / 编辑 ────────────────────────── */
function openCreate() {
  formMode.value = "create";
  editingRow.value = null;
  formValues.value = buildInitialValues(columns.value);
  formErrors.value = {};
  showForm.value = true;
}

function openEdit(row) {
  formMode.value = "edit";
  editingRow.value = row;
  formValues.value = buildInitialValues(columns.value, row);
  formErrors.value = {};
  showForm.value = true;
}

function isPkColumn(col) {
  return Boolean(col.is_primary_key);
}

async function submitForm() {
  const errors = validateFormValues(columns.value, formValues.value, {
    isCreate: formMode.value === "create",
  });
  formErrors.value = errors;
  if (Object.keys(errors).length > 0) {
    return;
  }
  const values = buildSubmitValues(columns.value, formValues.value);
  saving.value = true;
  try {
    if (formMode.value === "create") {
      await createTableRow(
        selectedTable.value.schema_name,
        selectedTable.value.table_name,
        values,
      );
      success("记录已新增。", "新增成功");
    } else {
      // 主键列通过 pk 参数传递，不放进 values 里更新
      const pk = pkOf(editingRow.value);
      for (const key of Object.keys(pk)) {
        delete values[key];
      }
      await updateTableRow(
        selectedTable.value.schema_name,
        selectedTable.value.table_name,
        pk,
        values,
      );
      success("记录已更新。", "更新成功");
    }
    showForm.value = false;
    await loadRows();
    await loadLogs();
  } catch (err) {
    if (isUnauthorizedError(err)) return;
    error(`${err.message || err}`, formMode.value === "create" ? "新增失败" : "更新失败");
  } finally {
    saving.value = false;
  }
}

/* ── 删除 ───────────────────────────────── */
function openDelete(row) {
  deletingRow.value = row;
  showDelete.value = true;
}

async function confirmDelete() {
  if (!deletingRow.value) return;
  deleting.value = true;
  try {
    await deleteTableRow(
      selectedTable.value.schema_name,
      selectedTable.value.table_name,
      pkOf(deletingRow.value),
    );
    success("记录已删除。", "删除成功");
    showDelete.value = false;
    deletingRow.value = null;
    await loadRows();
    await loadLogs();
  } catch (err) {
    if (isUnauthorizedError(err)) return;
    error(`${err.message || err}`, "删除失败");
  } finally {
    deleting.value = false;
  }
}

/* ── 变更记录 ───────────────────────────── */
async function loadLogs() {
  if (!selectedTable.value) return;
  logsLoading.value = true;
  try {
    const payload = await fetchChangeLogs({
      schemaName: selectedTable.value.schema_name,
      tableName: selectedTable.value.table_name,
      limit: logsPageSize,
      offset: (logsPage.value - 1) * logsPageSize,
    });
    logs.value = payload.items || [];
    logsTotal.value = payload.total || 0;
  } catch (err) {
    if (isUnauthorizedError(err)) return;
    error(`加载变更记录失败：${err.message || err}`, "加载失败");
  } finally {
    logsLoading.value = false;
  }
}

function goLogsPrev() {
  if (logsPage.value <= 1) return;
  logsPage.value -= 1;
  loadLogs();
}

function goLogsNext() {
  if (logsPage.value >= logsTotalPages.value) return;
  logsPage.value += 1;
  loadLogs();
}

onMounted(() => {
  loadTables();
});
</script>

<template>
  <div class="mx-auto w-full max-w-[90rem] space-y-4">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="space-y-1">
        <h1 class="text-2xl font-bold tracking-tight">数据管理</h1>
        <p class="text-sm text-muted-foreground">
          在线浏览与维护调查、台账和点位数据，支持逐行新增、编辑、删除并查看变更记录。
        </p>
      </div>
      <div class="page-actions flex items-center gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          :disabled="tablesLoading"
          @click="loadTables"
        >
          <RefreshCw class="size-4" :class="{ 'animate-spin': tablesLoading }" />
          <span>刷新</span>
        </Button>
      </div>
    </div>

    <div v-if="tablesLoading" class="flex flex-wrap gap-2">
      <Skeleton v-for="i in 5" :key="i" class="h-9 w-24" />
    </div>
    <div
      v-else-if="pestGroups.length === 0"
      class="flex flex-col items-center gap-2 rounded-xl border border-dashed py-16 text-muted-foreground"
    >
      <Database class="size-7" />
      <p class="text-sm">暂无可管理的表</p>
    </div>

    <template v-else>
      <!-- 一级 Tab：虫种 -->
      <Tabs :model-value="activePest" @update:model-value="selectPest">
        <TabsList>
          <TabsTrigger
            v-for="group in pestGroups"
            :key="group.pest"
            :value="group.pest"
            :data-testid="`pest-tab-${group.pest}`"
          >
            <Bug v-if="group.pest !== '通用'" class="size-4" />
            <span>{{ group.pest }}</span>
          </TabsTrigger>
        </TabsList>
      </Tabs>

      <!-- 二级：虫种下的具体表 -->
      <div class="flex flex-wrap gap-2" aria-label="表选择">
        <Button
          v-for="table in currentPestTables"
          :key="`${table.schema_name}.${table.table_name}`"
          type="button"
          size="sm"
          :variant="
            selectedTable?.schema_name === table.schema_name &&
            selectedTable?.table_name === table.table_name
              ? 'default'
              : 'outline'
          "
          :title="table.table_name"
          :data-testid="`table-button-${table.schema_name}-${table.table_name}`"
          @click="selectTable(table)"
        >
          <span>{{ shortTableLabel(table.table_name, activePest) }}</span>
          <Badge variant="secondary" class="ml-1 px-1.5 text-[10px]">
            {{ formatNumber(table.row_estimate) }}
          </Badge>
        </Button>
      </div>

      <template v-if="selectedTable">
        <!-- 工具栏 -->
        <div class="flex flex-wrap items-end gap-2 rounded-xl border bg-card p-3 shadow-sm">
          <div
            v-for="name in filterableColumns"
            :key="name"
            class="grid w-36 gap-1"
          >
            <Label :for="`filter-${name}`" class="text-xs text-muted-foreground">{{ name }}</Label>
            <Input
              :id="`filter-${name}`"
              v-model="filterValues[name]"
              :placeholder="`模糊匹配${name}`"
              @keyup.enter="applyFilters"
            />
          </div>
          <div class="flex items-center gap-2">
            <Button type="button" size="sm" :disabled="rowsLoading" @click="applyFilters">
              <Search class="size-4" />
              <span>查询</span>
            </Button>
            <Button type="button" variant="outline" size="sm" :disabled="rowsLoading" @click="resetFilters">
              <span>重置</span>
            </Button>
          </div>
          <div class="ml-auto flex items-center gap-2">
            <Button
              v-if="hasPrimaryKey"
              type="button"
              size="sm"
              :disabled="columnsLoading"
              data-testid="create-row-button"
              @click="openCreate"
            >
              <Plus class="size-4" />
              <span>新增记录</span>
            </Button>
          </div>
        </div>

        <div
          v-if="!hasPrimaryKey"
          class="rounded-xl border border-amber-300/60 bg-amber-50 px-4 py-2.5 text-sm text-amber-800"
          data-testid="no-pk-banner"
        >
          该表无主键，仅支持浏览，不能新增、编辑或删除记录。
        </div>

        <Tabs v-model="activeTab">
          <TabsList>
            <TabsTrigger value="rows">数据记录</TabsTrigger>
            <TabsTrigger value="logs">变更记录</TabsTrigger>
          </TabsList>

          <!-- 数据表格 -->
          <TabsContent value="rows">
            <div class="overflow-hidden rounded-xl border shadow-sm">
              <div class="overflow-x-auto">
                <Table class="data-table min-w-[56rem]">
                  <TableHeader>
                    <TableRow>
                      <TableHead v-for="col in tableColumns" :key="col.name">
                        {{ col.name }}
                      </TableHead>
                      <TableHead v-if="hasPrimaryKey" class="text-right">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow v-for="(row, rowIndex) in rows" :key="rowIndex">
                      <TableCell
                        v-for="col in tableColumns"
                        :key="col.name"
                        class="max-w-56 truncate"
                        :title="formatCell(row[col.name])"
                      >
                        {{ formatCell(row[col.name]) }}
                      </TableCell>
                      <TableCell v-if="hasPrimaryKey" class="text-right">
                        <div class="inline-flex items-center gap-1">
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            title="编辑"
                            @click="openEdit(row)"
                          >
                            <Pencil class="size-4" />
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            class="text-destructive hover:text-destructive"
                            title="删除"
                            @click="openDelete(row)"
                          >
                            <Trash2 class="size-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                    <TableRow v-if="rows.length === 0 && !rowsLoading">
                      <TableCell
                        :colspan="tableColumns.length + (hasPrimaryKey ? 1 : 0)"
                        class="h-24 text-center text-muted-foreground"
                      >
                        暂无数据
                      </TableCell>
                    </TableRow>
                    <TableRow v-if="rowsLoading">
                      <TableCell
                        :colspan="tableColumns.length + (hasPrimaryKey ? 1 : 0)"
                        class="h-24 text-center text-muted-foreground"
                      >
                        加载中…
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>

              <div class="flex flex-wrap items-center justify-between gap-2 border-t px-4 py-3">
                <p class="text-sm text-muted-foreground">
                  第 {{ rowsTotal === 0 ? 0 : Math.min((page - 1) * pageSize + 1, rowsTotal) }}–{{ Math.min(page * pageSize, rowsTotal) }} 条，共 {{ rowsTotal }} 条
                </p>
                <Pagination
                  v-model:page="page"
                  :items-per-page="pageSize"
                  :total="rowsTotal"
                  :sibling-count="1"
                  :disabled="rowsLoading"
                  show-edges
                  class="mx-0 w-auto justify-end"
                >
                  <PaginationContent v-slot="{ items }">
                    <PaginationPrevious />
                    <template v-for="(item, index) in items" :key="index">
                      <PaginationItem
                        v-if="item.type === 'page'"
                        :value="item.value"
                        :is-active="item.value === page"
                      >
                        {{ item.value }}
                      </PaginationItem>
                      <PaginationEllipsis v-else />
                    </template>
                    <PaginationNext />
                  </PaginationContent>
                </Pagination>
              </div>
            </div>
          </TabsContent>

          <!-- 变更记录 -->
          <TabsContent value="logs">
            <div class="overflow-hidden rounded-xl border shadow-sm">
              <div class="overflow-x-auto">
                <Table class="data-table min-w-[48rem]">
                  <TableHeader>
                    <TableRow>
                      <TableHead>时间</TableHead>
                      <TableHead>操作人</TableHead>
                      <TableHead>动作</TableHead>
                      <TableHead>主键</TableHead>
                      <TableHead>变更内容</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow v-for="log in logs" :key="log.id">
                      <TableCell class="whitespace-nowrap text-muted-foreground">
                        {{ formatTime(log.occurred_at) }}
                      </TableCell>
                      <TableCell>{{ log.operator_display_name || "--" }}</TableCell>
                      <TableCell>
                        <Badge :variant="ACTION_BADGE_VARIANTS[log.action] || 'outline'">
                          {{ ACTION_LABELS[log.action] || log.action }}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <code class="text-xs">{{ formatPk(log.pk) }}</code>
                      </TableCell>
                      <TableCell class="max-w-96">
                        <template v-if="log.action === 'update'">
                          <ul v-if="diffChangeLog(log).length > 0" class="space-y-0.5 text-xs">
                            <li v-for="change in diffChangeLog(log)" :key="change.field">
                              <span class="font-medium">{{ change.field }}</span>
                              <span class="text-muted-foreground">
                                ：{{ formatCell(change.before) }} → {{ formatCell(change.after) }}
                              </span>
                            </li>
                          </ul>
                          <span v-else class="text-xs text-muted-foreground">无字段变化</span>
                        </template>
                        <span v-else class="text-xs text-muted-foreground">
                          {{ log.action === "insert" ? "新增一条记录" : "删除该记录" }}
                        </span>
                      </TableCell>
                    </TableRow>
                    <TableRow v-if="logs.length === 0 && !logsLoading">
                      <TableCell colspan="5" class="h-24 text-center text-muted-foreground">
                        暂无变更记录
                      </TableCell>
                    </TableRow>
                    <TableRow v-if="logsLoading">
                      <TableCell colspan="5" class="h-24 text-center text-muted-foreground">
                        加载中…
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>

              <div class="flex items-center justify-between border-t px-4 py-3">
                <p class="text-sm text-muted-foreground">
                  第 {{ logsPage }} / {{ logsTotalPages }} 页，共 {{ logsTotal }} 条
                </p>
                <div class="flex items-center gap-1">
                  <Button
                    type="button"
                    variant="outline"
                    size="icon-sm"
                    :disabled="logsPage <= 1 || logsLoading"
                    aria-label="上一页"
                    @click="goLogsPrev"
                  >
                    <ChevronLeft class="size-4" />
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon-sm"
                    :disabled="logsPage >= logsTotalPages || logsLoading"
                    aria-label="下一页"
                    @click="goLogsNext"
                  >
                    <ChevronRight class="size-4" />
                  </Button>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </template>
    </template>

    <!-- 新增 / 编辑对话框 -->
    <Dialog v-model:open="showForm">
      <DialogContent class="max-h-[85vh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>
            {{ formMode === "create" ? "新增记录" : "编辑记录" }}
          </DialogTitle>
          <p class="text-sm text-muted-foreground">
            {{ selectedTable?.schema_name }}.{{ selectedTable?.table_name }}
          </p>
        </DialogHeader>
        <form class="grid gap-4" @submit.prevent="submitForm">
          <div v-for="col in formColumns" :key="col.name" class="grid gap-2">
            <Label :for="`field-${col.name}`">
              {{ col.name }}
              <span v-if="isRequiredColumn(col)" class="text-destructive">*</span>
              <span
                v-if="formMode === 'edit' && isPkColumn(col)"
                class="ml-1 text-xs text-muted-foreground"
              >（主键，不可修改）</span>
            </Label>

            <!-- 编辑时主键只读展示 -->
            <Input
              v-if="formMode === 'edit' && isPkColumn(col)"
              :id="`field-${col.name}`"
              :model-value="formatCell(editingRow?.[col.name])"
              disabled
            />
            <NativeSelect
              v-else-if="col.input_kind === 'select'"
              :id="`field-${col.name}`"
              v-model="formValues[col.name]"
            >
              <option value="">（空）</option>
              <option v-for="label in col.enum_labels" :key="label" :value="label">
                {{ label }}
              </option>
            </NativeSelect>
            <label
              v-else-if="col.input_kind === 'bool'"
              class="flex items-center gap-2 text-sm"
            >
              <Checkbox
                :id="`field-${col.name}`"
                v-model="formValues[col.name]"
              />
              <span>{{ formValues[col.name] ? "是" : "否" }}</span>
            </label>
            <Input
              v-else-if="col.input_kind === 'number'"
              :id="`field-${col.name}`"
              v-model="formValues[col.name]"
              type="number"
              step="any"
            />
            <Input
              v-else-if="col.input_kind === 'date'"
              :id="`field-${col.name}`"
              v-model="formValues[col.name]"
              type="date"
            />
            <Input
              v-else-if="col.input_kind === 'datetime'"
              :id="`field-${col.name}`"
              v-model="formValues[col.name]"
              type="datetime-local"
            />
            <Input
              v-else
              :id="`field-${col.name}`"
              v-model="formValues[col.name]"
              type="text"
            />

            <p v-if="formErrors[col.name]" class="text-xs text-destructive">
              {{ formErrors[col.name] }}
            </p>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" @click="showForm = false">取消</Button>
            <Button type="submit" :disabled="saving">
              {{ saving ? "保存中…" : "保存" }}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>

    <!-- 删除确认 -->
    <AlertDialog v-model:open="showDelete">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>确认删除该记录？</AlertDialogTitle>
          <AlertDialogDescription>
            将删除 {{ selectedTable?.schema_name }}.{{ selectedTable?.table_name }} 中主键为
            <code class="text-xs">{{ formatPk(pkOf(deletingRow || {})) }}</code>
            的记录，此操作不可撤销。
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel :disabled="deleting">取消</AlertDialogCancel>
          <AlertDialogAction
            class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            :disabled="deleting"
            @click="confirmDelete"
          >
            {{ deleting ? "删除中…" : "确认删除" }}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </div>
</template>
