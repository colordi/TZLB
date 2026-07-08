import { computed, ref } from "vue";

import {
  normalizeRecordForPest,
  validateRecords,
} from "../../components/workorder/fieldConfig.js";

export function useWorkorderRecords(pestType) {
  const records = ref([]);

  const validationErrors = computed(() => validateRecords(records.value, pestType.value));

  function normalizeAll() {
    if (records.value.length) {
      records.value = records.value.map((record) =>
        normalizeRecordForPest(record, pestType.value),
      );
    }
  }

  function handleSurveyImport(importedRecords) {
    const normalizedRecords = importedRecords.map((record) =>
      normalizeRecordForPest(record, pestType.value),
    );
    records.value = records.value.concat(normalizedRecords);
    return normalizedRecords;
  }

  function handleUpdateRecord(uid, updatedRecord) {
    const index = records.value.findIndex((record) => record.__uid === uid);
    if (index === -1) return;
    const next = records.value.slice();
    next[index] = normalizeRecordForPest(
      { ...updatedRecord, __uid: records.value[index].__uid },
      pestType.value,
    );
    records.value = next;
  }

  function handleDeleteRecord(uid) {
    records.value = records.value.filter((record) => record.__uid !== uid);
  }

  function handleBatchDelete(uids) {
    if (!uids.length) return;
    const set = new Set(uids);
    records.value = records.value.filter((record) => !set.has(record.__uid));
  }

  return {
    records,
    validationErrors,
    normalizeAll,
    handleSurveyImport,
    handleUpdateRecord,
    handleDeleteRecord,
    handleBatchDelete,
  };
}
