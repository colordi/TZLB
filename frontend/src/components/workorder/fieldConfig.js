/** Workorder field configuration barrel (split into pestRegistry / fieldVisibility / record*). */

export {
  CONTROL_TYPE_OPTIONS,
  PEST_OPTIONS,
  PEST_REGISTRY,
  REQUIRED_FIELD_KEYS_BY_PEST,
  buildTask,
  getCurrentYear,
  getDefaultControlType,
  getDefaultTask,
  getGenerationFromTask,
  getGenerations,
  getPestConfig,
  getSurveyImportConfig,
  getTaskOptions,
  isChiHuo,
  isMeiGuoBaiE,
  supportsGeneration,
  supportsSurveyImport,
} from "./pestRegistry.js";

export { getVisibleFields } from "./fieldVisibility.js";

export {
  createEmptyRecord,
  createRecordUid,
  getTodayDate,
  normalizeDate,
  normalizeInputValue,
  normalizeRecordForPest,
  toPayloadRecord,
} from "./recordFactory.js";

export { hasValidationErrors, validateRecords } from "./recordValidation.js";
