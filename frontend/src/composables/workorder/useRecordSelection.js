import { computed, ref } from "vue";

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

export function useRecordSelection(records, validationErrors) {
  const selectedUids = ref([]);
  const searchQuery = ref("");
  const recordFilter = ref("all");

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

  const allVisibleSelected = computed(
    () =>
      filteredRecordUids.value.length > 0 &&
      filteredRecordUids.value.every((uid) => selectedUids.value.includes(uid)),
  );

  function toggleFilteredSelection() {
    selectedUids.value = toggleUidSelection(selectedUids.value, filteredRecordUids.value);
  }

  function clearSelection() {
    selectedUids.value = [];
  }

  return {
    selectedUids,
    searchQuery,
    recordFilter,
    filteredRecords,
    filteredRecordUids,
    filteredValidationErrors,
    allVisibleSelected,
    toggleFilteredSelection,
    clearSelection,
  };
}
