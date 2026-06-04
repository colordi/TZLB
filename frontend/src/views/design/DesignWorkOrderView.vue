<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import WorkOrderCardList from "../../components/design/workorder/WorkOrderCardList.vue";
import WorkOrderEditDrawer from "../../components/design/workorder/WorkOrderEditDrawer.vue";
import WorkOrderExportDialog from "../../components/design/workorder/WorkOrderExportDialog.vue";
import WorkOrderFilters from "../../components/design/workorder/WorkOrderFilters.vue";
import WorkOrderImportDialog from "../../components/design/workorder/WorkOrderImportDialog.vue";
import WorkOrderStats from "../../components/design/workorder/WorkOrderStats.vue";
import WorkOrderTable from "../../components/design/workorder/WorkOrderTable.vue";
import {
  DESIGN_WORKORDER_RECORDS,
  DESIGN_WORKORDER_STATS,
  DESIGN_WORKORDER_STATUS_OPTIONS,
} from "../../fixtures/design/workorderRecords.js";
import "../../styles/design-workorder.css";

const searchQuery = ref("");
const statusFilter = ref("all");
const selectedIds = ref([]);
const activeOverlay = ref("");
const activeRecord = ref(null);
const exportContext = ref("");

const filteredRecords = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase("zh-CN");

  return DESIGN_WORKORDER_RECORDS.filter((record) => {
    if (statusFilter.value !== "all" && record.status !== statusFilter.value) {
      return false;
    }

    if (!query) {
      return true;
    }

    return [record.point, record.code, record.task, record.type].some((value) =>
      value.toLocaleLowerCase("zh-CN").includes(query),
    );
  });
});

const allVisibleSelected = computed(
  () =>
    filteredRecords.value.length > 0 &&
    filteredRecords.value.every((record) => selectedIds.value.includes(record.id)),
);

const pendingRecords = computed(() =>
  DESIGN_WORKORDER_RECORDS.filter((record) => record.status === "pending"),
);

function toggleRecord(id) {
  selectedIds.value = selectedIds.value.includes(id)
    ? selectedIds.value.filter((selectedId) => selectedId !== id)
    : [...selectedIds.value, id];
}

function toggleVisibleRecords() {
  const visibleIds = filteredRecords.value.map((record) => record.id);

  if (allVisibleSelected.value) {
    selectedIds.value = selectedIds.value.filter((id) => !visibleIds.includes(id));
    return;
  }

  selectedIds.value = [...new Set([...selectedIds.value, ...visibleIds])];
}

function clearSelection() {
  selectedIds.value = [];
}

function closeOverlay() {
  activeOverlay.value = "";
  activeRecord.value = null;
}

function openImportPreview() {
  activeOverlay.value = "import";
}

function openEditPreview(record) {
  activeRecord.value = record;
  activeOverlay.value = "edit";
}

function openExportPreview(context) {
  exportContext.value = context;
  activeOverlay.value = "export";
}

function handleKeydown(event) {
  if (event.key === "Escape" && activeOverlay.value) {
    closeOverlay();
  }
}

onMounted(() => window.addEventListener("keydown", handleKeydown));
onBeforeUnmount(() => window.removeEventListener("keydown", handleKeydown));
</script>

<template>
  <main class="design-workorder-page">
    <header class="design-workorder-page-head">
      <div>
        <p class="design-workorder-eyebrow">WORK ORDER CONTROL DESK</p>
        <h1>调查工单</h1>
        <p>从数据库导入调查记录，批量生成工单并导出标准化 Word 文档。</p>
      </div>
      <div class="design-workorder-page-actions" aria-label="工单静态操作预览">
        <button
          class="design-button is-secondary"
          type="button"
          data-testid="design-workorder-export-all"
          @click="openExportPreview(`全部 ${DESIGN_WORKORDER_RECORDS.length} 条记录`)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
            <path d="M7 3h7l5 5v13H7zM14 3v5h5M10 13h6m-6 4h6" />
          </svg>
          <span>批量导出</span>
        </button>
        <button
          class="design-button"
          type="button"
          data-testid="design-workorder-import"
          @click="openImportPreview"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
            <path d="M12 16V4m-4 4 4-4 4 4M5 14v5h14v-5" />
          </svg>
          <span>导入调查记录</span>
        </button>
      </div>
    </header>

    <WorkOrderFilters />
    <WorkOrderStats :stats="DESIGN_WORKORDER_STATS" />

    <section class="design-workorder-panel" aria-label="调查工单记录">
      <div class="design-workorder-toolbar">
        <label class="design-workorder-search">
          <span class="design-workorder-sr-only">搜索工单记录</span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="7" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <input
            v-model="searchQuery"
            type="search"
            placeholder="搜索点位名称、工单编号…"
            data-testid="design-workorder-search"
          />
        </label>

        <div class="design-workorder-segmented" aria-label="工单状态筛选">
          <button
            v-for="option in DESIGN_WORKORDER_STATUS_OPTIONS"
            :key="option.value"
            type="button"
            :class="{ 'is-active': statusFilter === option.value }"
            :data-testid="`design-workorder-status-${option.value}`"
            @click="statusFilter = option.value"
          >
            {{ option.label }}
          </button>
        </div>

        <span class="design-workorder-toolbar-separator" aria-hidden="true"></span>

        <button
          class="design-workorder-select-all"
          type="button"
          data-testid="design-workorder-select-all"
          @click="toggleVisibleRecords"
        >
          {{ allVisibleSelected ? "取消全选" : "全选" }}
        </button>
      </div>

      <WorkOrderTable
        :records="filteredRecords"
        :selected-ids="selectedIds"
        :all-selected="allVisibleSelected"
        @toggle="toggleRecord"
        @toggle-all="toggleVisibleRecords"
        @edit="openEditPreview"
        @export="(record) => openExportPreview(record.code || record.point)"
      />
      <WorkOrderCardList
        :records="filteredRecords"
        :selected-ids="selectedIds"
        @toggle="toggleRecord"
        @edit="openEditPreview"
        @export="(record) => openExportPreview(record.code || record.point)"
      />

      <div v-if="filteredRecords.length === 0" class="design-workorder-empty">
        当前筛选条件下没有工单记录。
      </div>

      <footer class="design-workorder-panel-foot">
        <span>共 <strong class="design-num">{{ filteredRecords.length }}</strong> 条记录</span>
        <span class="design-num">已选 <strong>{{ selectedIds.length }}</strong> 条</span>
      </footer>
    </section>

    <aside
      v-if="selectedIds.length"
      class="design-workorder-batch-bar"
      aria-label="已选工单摘要"
      data-testid="design-workorder-batch-bar"
    >
      <span>已选 <strong class="design-num">{{ selectedIds.length }}</strong> 条记录</span>
      <div>
        <button type="button" @click="clearSelection">取消选择</button>
        <button
          type="button"
          data-testid="design-workorder-export-selected"
          @click="openExportPreview(`${selectedIds.length} 条已选记录`)"
        >
          批量导出 Word
        </button>
        <button type="button" disabled title="静态预览不生成工单">批量生成工单</button>
      </div>
    </aside>

    <WorkOrderImportDialog
      v-if="activeOverlay === 'import'"
      :records="pendingRecords"
      @close="closeOverlay"
    />
    <WorkOrderExportDialog
      v-if="activeOverlay === 'export'"
      :context="exportContext"
      @close="closeOverlay"
    />
    <WorkOrderEditDrawer
      v-if="activeOverlay === 'edit' && activeRecord"
      :record="activeRecord"
      @close="closeOverlay"
    />
  </main>
</template>
