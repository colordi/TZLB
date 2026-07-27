import {
  ADMIN_BOUNDARY_COLOR,
  HAZARD_POINT_COLOR,
  POINT_OUTLINE_COLOR,
  REFERENCE_LAYER_COLORS,
} from "../../../config/map-palette.js";
import {
  hasFeatureParcelStatusField,
  hasFeatureSeverityField,
  resolveFeatureParcelStatus,
  resolveFeatureSeverity,
} from "../popupFields.js";

export const HAZARD_POINT_STYLE = {
  key: "hazard-point",
  color: HAZARD_POINT_COLOR,
  radius: 8,
  label: "危害点位",
};

export const ADMIN_BOUNDARY_LAYER_NAME = "通州区行政区边界";

export const SURVEY_DATE_FIELD_KEYS = ["调查日期", "survey_date", "report_time"];

export function resolveBoundaryStyle() {
  return {
    color: ADMIN_BOUNDARY_COLOR,
    weight: 3,
    opacity: 0.72,
    fillOpacity: 0,
  };
}

export function hasSurveyDateField(fields = []) {
  const dateFieldKeys = new Set(SURVEY_DATE_FIELD_KEYS.map((field) => field.toLowerCase()));
  return (fields || []).some((field) => {
    const normalizedField = `${field ?? ""}`.trim();
    return dateFieldKeys.has(normalizedField.toLowerCase());
  });
}

export function hasFeatureCollectionFeatures(data) {
  return Array.isArray(data?.features) && data.features.length > 0;
}

export function resolveReferenceLayerColor(index = 0) {
  return REFERENCE_LAYER_COLORS[index % REFERENCE_LAYER_COLORS.length];
}

export function resolveReferenceLayerStyle(layer = {}, index = 0) {
  if (layer.name === ADMIN_BOUNDARY_LAYER_NAME) {
    return {
      ...resolveBoundaryStyle(),
      weight: 3.5,
      opacity: 0.88,
    };
  }

  const color = resolveReferenceLayerColor(index);
  return {
    color,
    fillColor: color,
    fillOpacity: 0.12,
    opacity: 0.82,
    weight: 1.5,
  };
}

export function isNeutralPointStyle(pointStyle = {}) {
  return pointStyle?.key === "level0" || pointStyle?.key === "parcel-default";
}

export function usesSeverityLegend(popupFields = []) {
  return hasFeatureSeverityField(popupFields);
}

export function usesParcelStatusLegend(popupFields = []) {
  return !usesSeverityLegend(popupFields) && hasFeatureParcelStatusField(popupFields);
}

export function usesSurveyCompletionMarkers(popupFields = []) {
  return hasSurveyDateField(popupFields);
}

export function resolvePointStyle(properties = {}, popupFields = []) {
  if (usesSeverityLegend(popupFields)) {
    return resolveFeatureSeverity(properties);
  }
  if (usesParcelStatusLegend(popupFields)) {
    return resolveFeatureParcelStatus(properties);
  }
  return HAZARD_POINT_STYLE;
}

export function resolveFeaturePathStyle(properties = {}, popupFields = []) {
  const pointStyle = resolvePointStyle(properties, popupFields);
  if (usesParcelStatusLegend(popupFields)) {
    if (pointStyle.key === "parcel-default") {
      return {
        color: POINT_OUTLINE_COLOR,
        fillColor: pointStyle.color,
        fillOpacity: 0.88,
        opacity: 0.98,
        weight: 1.5,
      };
    }

    return {
      color: POINT_OUTLINE_COLOR,
      fillColor: pointStyle.color,
      fillOpacity: 0.7,
      opacity: 0.98,
      weight: 1.5,
    };
  }

  const isNeutral = isNeutralPointStyle(pointStyle);

  return {
    color: POINT_OUTLINE_COLOR,
    fillColor: pointStyle.color,
    fillOpacity: isNeutral ? 0.52 : 0.36,
    opacity: isNeutral ? 0.78 : 0.95,
    weight: isNeutral ? 1.2 : 1.6,
  };
}

export function getPointRenderFeatures(features = [], popupFields = []) {
  return usesSeverityLegend(popupFields)
    ? [...features].sort((a, b) => {
        const sa = resolveFeatureSeverity(a.properties).key;
        const sb = resolveFeatureSeverity(b.properties).key;
        return sa.localeCompare(sb);
      })
    : [...features];
}

export function getTopmostPointFeatures(features = [], popupFields = []) {
  return getPointRenderFeatures(features, popupFields).reverse();
}

export function getLegendEntries(popupFields = []) {
  if (usesSeverityLegend(popupFields)) {
    return [
      resolveFeatureSeverity("无"),
      resolveFeatureSeverity("轻"),
      resolveFeatureSeverity("中"),
      resolveFeatureSeverity("重"),
    ];
  }

  if (usesParcelStatusLegend(popupFields)) {
    return [
      resolveFeatureParcelStatus({ 地块状态: "" }),
      resolveFeatureParcelStatus({ 地块状态: "调查" }),
      resolveFeatureParcelStatus({ 地块状态: "伐除" }),
    ];
  }

  return [HAZARD_POINT_STYLE];
}

export function getSurveyDateValue(properties = {}) {
  for (const key of SURVEY_DATE_FIELD_KEYS) {
    const value = `${properties?.[key] ?? ""}`.trim();
    if (value) {
      return value;
    }
  }
  return "";
}

export { POINT_OUTLINE_COLOR };
