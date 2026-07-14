import { computed, ref, watch } from "vue";

export const WORKORDER_PAGE_SIZE = 10;

export function toggleUidSelection(currentUids, targetUids) {
  if (!targetUids.length) {
    return currentUids;
  }
  const currentSet = new Set(currentUids);
  const allSelected = targetUids.every((uid) => currentSet.has(uid));
  if (allSelected) {
    const targetSet = new Set(targetUids);
    return currentUids.filter((uid) => !targetSet.has(uid));
  }
  return Array.from(new Set([...currentUids, ...targetUids]));
}

export function useRecordSelection(records, validationErrors, pageSize = WORKORDER_PAGE_SIZE) {
  const selectedUids = ref([]);
  const searchQuery = ref("");
  const recordFilter = ref("all");
  const currentPage = ref(1);

  const errorByUid = computed(() => {
    const map = {};
    records.value.forEach((record, index) => {
      if (record?.__uid) {
        map[record.__uid] = validationErrors.value[index] || {};
      }
    });
    return map;
  });

  const filteredRecordItems = computed(() => {
    const query = searchQuery.value.trim().toLocaleLowerCase("zh-CN");

    return records.value
      .filter((record) => {
        if (!record?.__uid) {
          return false;
        }
        if (recordFilter.value === "selected" && !selectedUids.value.includes(record.__uid)) {
          return false;
        }
        if (recordFilter.value === "errors" && Object.keys(errorByUid.value[record.__uid] || {}).length === 0) {
          return false;
        }
        if (!query) {
          return true;
        }
        return [
          record.location_name,
          record.location_id,
          record.locality,
          record.description,
          record.note,
        ].some((value) => `${value || ""}`.toLocaleLowerCase("zh-CN").includes(query));
      })
      .map((record) => ({
        record,
        errors: errorByUid.value[record.__uid] || {},
      }));
  });

  const filteredRecords = computed(() => filteredRecordItems.value.map((item) => item.record));
  const filteredRecordUids = computed(() => filteredRecordItems.value.map((item) => item.record.__uid));
  const filteredValidationErrors = computed(() => filteredRecordItems.value.map((item) => item.errors));

  const totalPages = computed(() => {
    const total = filteredRecords.value.length;
    if (total <= 0) {
      return 1;
    }
    return Math.ceil(total / pageSize);
  });

  const serialOffset = computed(() => (currentPage.value - 1) * pageSize);

  const pagedRecordItems = computed(() => {
    const start = serialOffset.value;
    return filteredRecordItems.value.slice(start, start + pageSize);
  });

  const pagedRecords = computed(() => pagedRecordItems.value.map((item) => item.record));
  const pagedValidationErrors = computed(() => pagedRecordItems.value.map((item) => item.errors));

  const allVisibleSelected = computed(
    () =>
      pagedRecords.value.length > 0 &&
      pagedRecords.value.every((record) => selectedUids.value.includes(record.__uid)),
  );

  function toggleFilteredSelection() {
    const visibleUids = pagedRecords.value.map((record) => record.__uid);
    selectedUids.value = toggleUidSelection(selectedUids.value, visibleUids);
  }

  function clearSelection() {
    selectedUids.value = [];
  }

  function goToPage(page) {
    const next = Math.min(Math.max(1, Number(page) || 1), totalPages.value);
    currentPage.value = next;
  }

  function goToPrevPage() {
    goToPage(currentPage.value - 1);
  }

  function goToNextPage() {
    goToPage(currentPage.value + 1);
  }

  watch([searchQuery, recordFilter], () => {
    currentPage.value = 1;
  }, { flush: "sync" });

  watch(totalPages, (pages) => {
    if (currentPage.value > pages) {
      currentPage.value = pages;
    }
  }, { flush: "sync" });

  return {
    selectedUids,
    searchQuery,
    recordFilter,
    currentPage,
    pageSize,
    totalPages,
    serialOffset,
    filteredRecords,
    filteredRecordUids,
    filteredValidationErrors,
    pagedRecords,
    pagedValidationErrors,
    allVisibleSelected,
    toggleFilteredSelection,
    clearSelection,
    goToPage,
    goToPrevPage,
    goToNextPage,
  };
}
