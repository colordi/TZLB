import { computed, ref } from "vue";

import { validateRecords } from "../../components/workorder/fieldConfig.js";

export function useRecordDetailModal(records, validationErrors, pestType) {
  const activeRecordUid = ref(null);
  const showDetailModal = ref(false);

  const activeRecord = computed(() => {
    if (!activeRecordUid.value) return null;
    return records.value.find((record) => record.__uid === activeRecordUid.value) || null;
  });

  const activeRecordError = computed(() => {
    if (!activeRecordUid.value) return {};
    const index = records.value.findIndex((record) => record.__uid === activeRecordUid.value);
    if (index === -1) return {};
    return validationErrors.value[index] || {};
  });

  function openDetail(uid) {
    activeRecordUid.value = uid;
    showDetailModal.value = true;
  }

  function closeDetail() {
    showDetailModal.value = false;
    activeRecordUid.value = null;
  }

  return {
    activeRecordUid,
    showDetailModal,
    activeRecord,
    activeRecordError,
    openDetail,
    closeDetail,
  };
}
