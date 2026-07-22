/**
 * 数据管理页表单纯逻辑（便于单测）。
 * 列元数据结构见 GET /api/data-manager/tables/{schema}/{table}/columns：
 * { name, data_type, is_nullable, has_default, is_primary_key, is_readonly,
 *   is_geometry, input_kind, enum_labels }
 */

/** 可出现在编辑表单中的列（排除自增、几何等只读列） */
export function editableColumns(columns) {
  return (columns || []).filter((col) => !col.is_readonly);
}

/** 可出现在数据表格中的列（几何列不展示） */
export function gridColumns(columns) {
  return (columns || []).filter((col) => !col.is_geometry);
}

/** 列是否为必填（不可为空、无默认值且不是只读列） */
export function isRequiredColumn(col) {
  return Boolean(col) && !col.is_nullable && !col.has_default && !col.is_readonly;
}

function normalizeDateTimeLocal(value) {
  if (typeof value !== "string") {
    return value == null ? "" : String(value);
  }
  // ISO 时间 → input[type=datetime-local] 需要的 YYYY-MM-DDTHH:mm
  const match = value.match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})/);
  return match ? `${match[1]}T${match[2]}` : value;
}

function normalizeDate(value) {
  if (typeof value !== "string") {
    return value == null ? "" : String(value);
  }
  const match = value.match(/^(\d{4}-\d{2}-\d{2})/);
  return match ? match[1] : value;
}

function emptyValueFor(col) {
  switch (col.input_kind) {
    case "bool":
      return false;
    case "number":
    case "date":
    case "datetime":
    case "select":
    case "text":
    default:
      return "";
  }
}

function rowValueFor(col, row) {
  const raw = row[col.name];
  switch (col.input_kind) {
    case "bool":
      return Boolean(raw);
    case "number":
      return raw === null || raw === undefined ? "" : raw;
    case "date":
      return normalizeDate(raw);
    case "datetime":
      return normalizeDateTimeLocal(raw);
    case "select":
      return raw === null || raw === undefined ? "" : String(raw);
    case "text":
    default:
      return raw === null || raw === undefined ? "" : String(raw);
  }
}

/**
 * 生成表单初始值。
 * 编辑时传入 row，用行数据填充；新增时不传，按 input_kind 给空值。
 */
export function buildInitialValues(columns, row) {
  const values = {};
  for (const col of editableColumns(columns)) {
    values[col.name] = row ? rowValueFor(col, row) : emptyValueFor(col);
  }
  return values;
}

/**
 * 前端必填校验，返回 { [列名]: 错误消息 }，空对象表示通过。
 * isCreate 目前与编辑共用同一套必填规则，保留参数以便后续区分。
 */
export function validateFormValues(columns, values, { isCreate } = {}) {
  void isCreate;
  const errors = {};
  for (const col of editableColumns(columns)) {
    if (!isRequiredColumn(col)) {
      continue;
    }
    if (col.input_kind === "bool") {
      // 布尔控件始终有值（true/false），不存在"未填写"
      continue;
    }
    const value = values?.[col.name];
    if (value === null || value === undefined || String(value).trim() === "") {
      errors[col.name] = `${col.name}为必填项`;
    }
  }
  return errors;
}

/**
 * 把表单值转换为提交给后端的 values：
 * 空字符串 → null，number 列转数值，bool 列转布尔。
 */
export function buildSubmitValues(columns, values) {
  const result = {};
  for (const col of editableColumns(columns)) {
    const raw = values?.[col.name];
    if (raw === null || raw === undefined || raw === "") {
      result[col.name] = null;
      continue;
    }
    switch (col.input_kind) {
      case "number": {
        const num = Number(raw);
        result[col.name] = Number.isNaN(num) ? null : num;
        break;
      }
      case "bool":
        result[col.name] = Boolean(raw);
        break;
      default:
        result[col.name] = typeof raw === "string" ? raw : String(raw);
    }
  }
  return result;
}

function isSameValue(a, b) {
  const na = a === undefined ? null : a;
  const nb = b === undefined ? null : b;
  if (na === nb) {
    return true;
  }
  return JSON.stringify(na) === JSON.stringify(nb);
}

/**
 * 对 update 变更日志计算字段级差异，返回 [{ field, before, after }]。
 * insert / delete 返回空数组。
 */
export function diffChangeLog(item) {
  if (!item || item.action !== "update") {
    return [];
  }
  const before = item.before || {};
  const after = item.after || {};
  const fields = [...new Set([...Object.keys(before), ...Object.keys(after)])];
  const changes = [];
  for (const field of fields) {
    const oldValue = before[field];
    const newValue = after[field];
    if (!isSameValue(oldValue, newValue)) {
      changes.push({
        field,
        before: oldValue === undefined ? null : oldValue,
        after: newValue === undefined ? null : newValue,
      });
    }
  }
  return changes;
}
