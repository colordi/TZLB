<script setup>
import {
  ChevronLeft,
  ChevronRight,
  Image,
  ImageOff,
  Search,
  SearchX,
  Trash2,
  Upload,
} from "@lucide/vue";

import ConfirmDialog from "@/components/common/ConfirmDialog.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
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
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePointScreenshots } from "../../composables/workorder/usePointScreenshots.js";

const {
  PEST_TABS,
  PAGE_SIZE,
  STATUS_FILTERS,
  pestType,
  points,
  searchInput,
  searchQuery,
  statusFilter,
  loading,
  loadFailed,
  fileInput,
  uploadTarget,
  uploadingCode,
  dragOverCode,
  pendingDelete,
  deletingCode,
  currentPage,
  thumbnailUrls,
  thumbnailStates,
  lightbox,
  total,
  hasScreenshot,
  missing,
  operationBusy,
  statusFilterCount,
  filteredPoints,
  emptyFilterMessage,
  totalPages,
  paginatedPoints,
  pointKey,
  closeLightbox,
  openLightbox,
  loadPoints,
  applySearch,
  setStatusFilter,
  goToPage,
  selectPest,
  openFilePicker,
  onFileChange,
  onDragOver,
  onDragLeave,
  onDrop,
  requestDelete,
  closeDeleteDialog,
  confirmDelete,
  handleLightboxOpenChange,
} = usePointScreenshots();
</script>

<template>
  <section class="flex w-full flex-col gap-4">
    <Card aria-label="点位截图筛选">
      <CardContent class="space-y-4 p-4">
        <Tabs
          :model-value="pestType"
          class="point-screenshot-tabs w-fit"
          aria-label="害虫类型"
          @update:model-value="selectPest"
        >
          <TabsList>
            <TabsTrigger
              v-for="tab in PEST_TABS"
              :key="tab.pestType"
              :value="tab.pestType"
              :disabled="operationBusy"
              :data-testid="`point-screenshot-tab-${tab.pestType}`"
              @click="selectPest(tab.pestType)"
            >
              {{ tab.label }}
            </TabsTrigger>
          </TabsList>
        </Tabs>

        <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div
            class="flex flex-wrap gap-2"
            role="group"
            aria-label="按截图状态筛选"
            aria-live="polite"
          >
            <Button
              v-for="item in STATUS_FILTERS"
              :key="item.value"
              type="button"
              size="sm"
              :variant="statusFilter === item.value ? 'default' : 'outline'"
              class="gap-2"
              :class="{ 'is-active': statusFilter === item.value }"
              :aria-pressed="statusFilter === item.value"
              :disabled="operationBusy"
              :data-testid="item.testId"
              @click="setStatusFilter(item.value)"
            >
              {{ item.label }}
              <strong class="tabular-nums">{{ statusFilterCount[item.value] }}</strong>
            </Button>
          </div>

          <div class="flex min-w-[14rem] max-w-sm flex-1 items-center gap-2">
            <label class="relative flex-1">
              <span class="sr-only">搜索点位</span>
              <Search class="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                v-model="searchInput"
                type="search"
                class="h-8 pl-8"
                placeholder="搜索编号、名称、属地…"
                data-testid="point-screenshot-search"
                @keydown.enter="applySearch"
              />
            </label>
            <Button
              type="button"
              size="sm"
              class="h-8"
              :disabled="operationBusy"
              data-testid="point-screenshot-search-submit"
              @click="applySearch"
            >
              <Search class="size-3.5" />
              查询
            </Button>
          </div>
        </div>

        <p class="text-sm text-muted-foreground">
          输入条件后点击「查询」或按回车执行筛选；拖拽图片到对应点位所在行即可上传或替换截图。
        </p>
      </CardContent>
    </Card>

    <div v-if="loading" class="py-12 text-center text-sm text-muted-foreground" data-testid="point-screenshot-loading">
      正在加载点位…
    </div>
    <div v-else-if="loadFailed" class="py-12 text-center text-sm text-destructive">
      点位加载失败，请重新选择当前害虫类型后重试。
    </div>
    <EmptyState
      v-else-if="points.length === 0"
      :icon="ImageOff"
      title="当前害虫类型暂无点位。"
    />
    <EmptyState
      v-else-if="filteredPoints.length === 0"
      :icon="SearchX"
      :title="emptyFilterMessage"
    />

    <div v-else class="overflow-hidden rounded-xl border bg-card shadow-sm" aria-live="polite">
      <Table>
        <TableHeader>
          <TableRow class="hover:bg-transparent">
            <TableHead class="w-28">编号</TableHead>
            <TableHead>名称</TableHead>
            <TableHead>属地</TableHead>
            <TableHead>点位截图</TableHead>
            <TableHead class="w-24">状态</TableHead>
            <TableHead class="w-36 text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow
            v-for="point in paginatedPoints"
            :key="point.code"
            class="point-screenshot-row"
            :class="{ 'bg-primary/10 hover:bg-primary/10': dragOverCode === pointKey(point) }"
            :data-testid="`point-screenshot-row-${point.code}`"
            @dragover="onDragOver($event, point)"
            @dragleave="onDragLeave(point)"
            @drop="onDrop($event, point)"
          >
            <TableCell class="font-medium">{{ point.code }}</TableCell>
            <TableCell class="max-w-44 truncate">{{ point.name || "未命名点位" }}</TableCell>
            <TableCell class="max-w-44 truncate">{{ point.locality || "属地未填写" }}</TableCell>
            <TableCell>
              <button
                v-if="point.has_screenshot"
                type="button"
                class="block size-16 cursor-pointer overflow-hidden rounded border bg-muted focus-visible:ring-3 focus-visible:ring-ring/50"
                :disabled="operationBusy"
                :data-testid="`point-screenshot-preview-${point.code}`"
                :aria-label="`查看 ${point.code} 大图`"
                @click="openLightbox(point)"
              >
                <img
                  v-if="thumbnailUrls.get(pointKey(point))"
                  class="size-full object-cover"
                  :src="thumbnailUrls.get(pointKey(point))"
                  :alt="`${point.code} 点位截图缩略图`"
                />
                <div
                  v-else
                  class="flex size-full flex-col items-center justify-center gap-1 text-muted-foreground"
                >
                  <Image class="size-4" />
                  <span v-if="thumbnailStates.get(pointKey(point)) === 'loading'" class="text-xs">加载中…</span>
                  <span v-else class="text-xs">预览不可用</span>
                </div>
              </button>
              <div
                v-else
                class="flex size-16 flex-col items-center justify-center gap-1 rounded border border-dashed text-muted-foreground"
              >
                <ImageOff class="size-4" />
                <span class="text-xs">缺失</span>
              </div>
            </TableCell>
            <TableCell>
              <Badge :variant="point.has_screenshot ? 'default' : 'secondary'">
                {{ point.has_screenshot ? "已有截图" : "缺失" }}
              </Badge>
            </TableCell>
            <TableCell class="text-right">
              <div class="flex flex-col items-end gap-1.5">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  class="w-28 border-dashed"
                  :disabled="operationBusy"
                  :title="`${point.code}：拖拽图片到本行，或点击选择`"
                  :data-testid="point.has_screenshot
                    ? `point-screenshot-replace-${point.code}`
                    : `point-screenshot-upload-${point.code}`"
                  @click="openFilePicker(point)"
                >
                  <Upload class="size-3.5" />
                  {{ uploadingCode === pointKey(point)
                    ? "上传中…"
                    : point.has_screenshot ? "替换" : "上传" }}
                </Button>
                <Button
                  v-if="point.has_screenshot"
                  type="button"
                  size="sm"
                  variant="ghost"
                  class="w-28 text-destructive hover:bg-destructive/10 hover:text-destructive"
                  :disabled="operationBusy"
                  :data-testid="`point-screenshot-delete-${point.code}`"
                  @click="requestDelete(point)"
                >
                  <Trash2 class="size-3.5" />
                  {{ deletingCode === pointKey(point) ? "删除中…" : "删除" }}
                </Button>
              </div>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>

    <div
      v-if="!loading && !loadFailed && filteredPoints.length > 0 && totalPages > 1"
      class="flex flex-wrap items-center justify-center gap-3"
      aria-label="点位分页"
    >
      <span class="text-sm text-muted-foreground">
        第 {{ currentPage }} / {{ totalPages }} 页 · 共 {{ filteredPoints.length }} 条
      </span>
      <Pagination
        :page="currentPage"
        :items-per-page="PAGE_SIZE"
        :total="filteredPoints.length"
        :sibling-count="1"
        :disabled="operationBusy"
        show-edges
        class="mx-0 w-auto"
        @update:page="goToPage"
      >
        <PaginationContent v-slot="{ items }">
          <PaginationPrevious data-testid="point-screenshot-prev-page">
            <ChevronLeft class="size-4" />
            <span class="hidden sm:block">上一页</span>
          </PaginationPrevious>
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
          <PaginationNext data-testid="point-screenshot-next-page">
            <span class="hidden sm:block">下一页</span>
            <ChevronRight class="size-4" />
          </PaginationNext>
        </PaginationContent>
      </Pagination>
    </div>

    <input
      ref="fileInput"
      hidden
      type="file"
      accept="image/jpeg,image/png,image/webp"
      data-testid="point-screenshot-file-input"
      @change="onFileChange"
    />

    <ConfirmDialog
      :open="Boolean(pendingDelete)"
      title="删除点位截图"
      :message="pendingDelete
        ? `确认删除 ${pendingDelete.code}${pendingDelete.name ? `（${pendingDelete.name}）` : ''} 的点位截图吗？此操作不可撤销。`
        : ''"
      :busy="Boolean(deletingCode)"
      confirm-text="确认删除"
      @close="closeDeleteDialog"
      @confirm="confirmDelete"
    />

    <Dialog :open="Boolean(lightbox)" @update:open="handleLightboxOpenChange">
      <DialogContent class="sm:max-w-4xl" :show-close-button="false">
        <div v-if="lightbox" class="flex items-start justify-between gap-3">
          <div class="space-y-1">
            <DialogTitle class="text-base">{{ lightbox.code }}</DialogTitle>
            <DialogDescription>{{ lightbox.name || "未命名点位" }}</DialogDescription>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            data-testid="point-screenshot-lightbox-close"
            @click="closeLightbox"
          >
            关闭
          </Button>
        </div>
        <div
          v-if="lightbox"
          class="min-h-64"
          data-testid="point-screenshot-lightbox"
        >
          <div v-if="lightbox.loading" class="py-16 text-center text-sm text-muted-foreground">
            正在加载大图…
          </div>
          <div
            v-else-if="lightbox.error"
            class="py-16 text-center text-sm text-destructive"
          >
            大图加载失败，请稍后重试。
          </div>
          <img
            v-else-if="lightbox.url"
            class="mx-auto max-h-[70vh] w-auto max-w-full rounded-md"
            :src="lightbox.url"
            :alt="`${lightbox.code} 点位截图`"
            data-testid="point-screenshot-lightbox-image"
          />
        </div>
      </DialogContent>
    </Dialog>
  </section>
</template>

