export function buildPopupRows(columns = [], properties = {}) {
  return (columns || []).map((label) => {
    const value = properties?.[label];
    return [label, value === undefined || value === null || value === "" ? "-" : `${value}`];
  });
}
