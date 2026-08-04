import { computed, onMounted, reactive, ref, watch } from "vue";

import {
  fetchManageableTables,
  fetchTableColumns,
  fetchTableRows,
  createTableRow,
  updateTableRow,
  deleteTableRow,
  fetchChangeLogs,
} from "../../api/dataManager.js";
import { isUnauthorizedError } from "../../api/http.js";
import { useToast } from "../useToast.js";
import {
  editableColumns,
  gridColumns,
  buildInitialValues,
  validateFormValues,
  buildSubmitValues,
  isRequiredColumn,
  diffChangeLog,
} from "../../components/datamanager/formModel.js";
import {
  groupTablesByPest,
  shortTableLabel,
} from "../../components/datamanager/tableGroups.js";
import {
  PREFERRED_FILTER_COLUMNS,
  MAX_FILTER_INPUTS,
  buildFilterSpecs,
} from "../../components/datamanager/filterSpecs.js";

/**
 * Data manager page state: tables, rows, form CRUD, change logs.
 */
export function useDataManager() {
  const { error, success } = useToast();

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
  const filterRanges = reactive({});
  const appliedFilters = ref({});
  const filterSpecs = computed(() => buildFilterSpecs(columns.value));

  // 切表/列元数据加载后，为日期区间控件补齐 { from, to } 初值，避免 v-model 读到 undefined
  watch(
    filterSpecs,
    (specs) => {
      for (const spec of specs) {
        if (spec.kind === "date" && !filterRanges[spec.name]) {
          filterRanges[spec.name] = { from: "", to: "" };
        }
      }
    },
    { immediate: true },
  );

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
    for (const key of Object.keys(filterRanges)) {
      delete filterRanges[key];
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
    for (const spec of filterSpecs.value) {
      if (spec.kind === "date") {
        const range = filterRanges[spec.name] || {};
        const from = (range.from || "").trim();
        const to = (range.to || "").trim();
        if (from || to) {
          filters[spec.name] = {
            ...(from ? { from } : {}),
            ...(to ? { to } : {}),
          };
        }
      } else {
        const value = (filterValues[spec.name] || "").trim();
        if (value) {
          filters[spec.name] = value;
        }
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
    for (const key of Object.keys(filterRanges)) {
      filterRanges[key] = { from: "", to: "" };
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

  function goLogsPage(value) {
    if (value === logsPage.value) return;
    logsPage.value = value;
    loadLogs();
  }

  onMounted(() => {
    loadTables();
  });

  return {
    PREFERRED_FILTER_COLUMNS,
    MAX_FILTER_INPUTS,
    ACTION_LABELS,
    ACTION_BADGE_VARIANTS,
    tables,
    tablesLoading,
    selectedTable,
    activePest,
    pestGroups,
    currentPestTables,
    columns,
    columnsLoading,
    rows,
    rowsTotal,
    rowsLoading,
    page,
    pageSize,
    tableColumns,
    formColumns,
    hasPrimaryKey,
    filterValues,
    filterRanges,
    appliedFilters,
    filterSpecs,
    showForm,
    formMode,
    editingRow,
    formValues,
    formErrors,
    saving,
    showDelete,
    deletingRow,
    deleting,
    activeTab,
    logs,
    logsTotal,
    logsLoading,
    logsPage,
    logsPageSize,
    logsTotalPages,
    formatNumber,
    formatCell,
    pkOf,
    formatPk,
    formatTime,
    pestOfTable,
    loadTables,
    selectPest,
    selectTable,
    loadColumns,
    loadRows,
    applyFilters,
    resetFilters,
    openCreate,
    openEdit,
    isPkColumn,
    submitForm,
    openDelete,
    confirmDelete,
    loadLogs,
    goLogsPage,
    shortTableLabel,
    isRequiredColumn,
    diffChangeLog,
  };
}
