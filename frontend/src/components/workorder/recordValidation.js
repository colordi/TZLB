import { getPestConfig } from "./pestRegistry.js";
import { getFieldKeysByPest } from "./fieldVisibility.js";
import { normalizeRecordForPest } from "./recordFactory.js";

export function validateRecords(records, pestType) {
  const config = getPestConfig(pestType);

  return records.map((record) => {
    const current = normalizeRecordForPest(record, pestType);
    const errors = {};

    config.requiredFieldKeys.forEach((key) => {
      if (!`${current[key] ?? ""}`.trim()) {
        errors[key] = "必填";
      }
    });

    config.numberFieldKeys.forEach((key) => {
      if (!getFieldKeysByPest(pestType).includes(key) || current[key] === "") {
        return;
      }

      const numeric = Number(current[key]);
      if (!Number.isFinite(numeric) || numeric < 0) {
        errors[key] = "需为非负数字";
      }
    });

    if ((current.images || []).length > 4) {
      errors.images = "最多 4 张";
    }

    return errors;
  });
}

export function hasValidationErrors(errorList) {
  return errorList.some((entry) => Object.keys(entry).length > 0);
}
