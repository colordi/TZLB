<script setup>
import {
  Bug,
  Database,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Trash2,
} from "@lucide/vue";

import EmptyState from "@/components/common/EmptyState.vue";
import PageHeader from "@/components/common/PageHeader.vue";
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
  DialogDescription,
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
import { useDataManager } from "../composables/datamanager/useDataManager.js";

const {
  PREFERRED_FILTER_COLUMNS, MAX_FILTER_INPUTS, ACTION_LABELS, ACTION_BADGE_VARIANTS, tables, tablesLoading, selectedTable, activePest, pestGroups, currentPestTables, columns, columnsLoading, rows, rowsTotal, rowsLoading, page, pageSize, tableColumns, formColumns, hasPrimaryKey, filterValues, filterRanges, appliedFilters, filterSpecs, showForm, formMode, editingRow, formValues, formErrors, saving, showDelete, deletingRow, deleting, activeTab, logs, logsTotal, logsLoading, logsPage, logsPageSize, logsTotalPages, formatNumber, formatCell, pkOf, formatPk, formatTime, pestOfTable, loadTables, selectPest, selectTable, loadColumns, loadRows, applyFilters, resetFilters, openCreate, openEdit, isPkColumn, submitForm, openDelete, confirmDelete, loadLogs, goLogsPage, shortTableLabel, isRequiredColumn, diffChangeLog
} = useDataManager();
</script>

<template>
  <div class="mx-auto w-full max-w-[90rem] space-y-6">
    <PageHeader
      title="数据管理"
      description="在线浏览与维护调查、台账和点位数据，支持逐行新增、编辑、删除并查看变更记录。"
    >
      <template #actions>
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
      </template>
    </PageHeader>

    <div v-if="tablesLoading" class="flex flex-wrap gap-2">
      <Skeleton v-for="i in 5" :key="i" class="h-9 w-24" />
    </div>
    <EmptyState
      v-else-if="pestGroups.length === 0"
      :icon="Database"
      title="暂无可管理的表"
    />

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
            v-for="spec in filterSpecs"
            :key="spec.name"
            class="grid gap-1"
            :class="spec.kind === 'date' ? 'w-auto' : 'w-36'"
          >
            <Label :for="`filter-${spec.name}`" class="text-xs text-muted-foreground">{{ spec.name }}</Label>
            <Input
              v-if="spec.kind !== 'date'"
              :id="`filter-${spec.name}`"
              v-model="filterValues[spec.name]"
              :placeholder="`模糊匹配${spec.name}`"
              @keyup.enter="applyFilters"
            />
            <div v-else class="flex items-center gap-1">
              <Input
                :id="`filter-${spec.name}`"
                v-model="filterRanges[spec.name].from"
                type="date"
                class="w-36"
                title="起始日期"
                @keyup.enter="applyFilters"
              />
              <span class="text-xs text-muted-foreground">至</span>
              <Input
                v-model="filterRanges[spec.name].to"
                type="date"
                class="w-36"
                title="截止日期"
                :aria-label="`${spec.name}截止日期`"
                @keyup.enter="applyFilters"
              />
            </div>
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
          class="rounded-xl border border-warning/40 bg-warning/10 px-4 py-2.5 text-sm text-warning-foreground"
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
            <div class="overflow-hidden rounded-xl border bg-card shadow-sm">
              <div class="overflow-x-auto">
                <Table class="min-w-[56rem]">
                  <TableHeader>
                    <TableRow class="hover:bg-transparent">
                      <TableHead v-for="col in tableColumns" :key="col.name">
                        {{ col.name }}
                      </TableHead>
                      <TableHead
                        v-if="hasPrimaryKey"
                        class="sticky right-0 border-l bg-card text-right"
                      >
                        操作
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow v-for="(row, rowIndex) in rows" :key="rowIndex" class="group">
                      <TableCell
                        v-for="col in tableColumns"
                        :key="col.name"
                        class="max-w-56 truncate"
                        :title="formatCell(row[col.name])"
                      >
                        {{ formatCell(row[col.name]) }}
                      </TableCell>
                      <TableCell
                        v-if="hasPrimaryKey"
                        class="sticky right-0 border-l bg-card text-right transition-colors group-hover:bg-muted/50"
                      >
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
            <div class="overflow-hidden rounded-xl border bg-card shadow-sm">
              <div class="overflow-x-auto">
                <Table class="min-w-[48rem]">
                  <TableHeader>
                    <TableRow class="hover:bg-transparent">
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

              <div class="flex flex-wrap items-center justify-between gap-2 border-t px-4 py-3">
                <p class="text-sm text-muted-foreground">
                  第 {{ logsPage }} / {{ logsTotalPages }} 页，共 {{ logsTotal }} 条
                </p>
                <Pagination
                  :page="logsPage"
                  :items-per-page="logsPageSize"
                  :total="logsTotal"
                  :sibling-count="1"
                  :disabled="logsLoading"
                  show-edges
                  class="mx-0 w-auto justify-end"
                  @update:page="goLogsPage"
                >
                  <PaginationContent v-slot="{ items }">
                    <PaginationPrevious />
                    <template v-for="(item, index) in items" :key="index">
                      <PaginationItem
                        v-if="item.type === 'page'"
                        :value="item.value"
                        :is-active="item.value === logsPage"
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
          <DialogDescription>
            {{ selectedTable?.schema_name }}.{{ selectedTable?.table_name }}
          </DialogDescription>
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
            variant="destructive"
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

