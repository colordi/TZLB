import L from "leaflet";

import {
  LOCATE_MARKER_COLOR,
  LOCATE_MARKER_GLOW,
  LOCATE_MARKER_HALO,
  LOCATE_MARKER_PULSE,
  LOCATE_MARKER_RING,
  SURVEY_COMPLETION_COLOR,
} from "../../../config/map-palette.js";
import { escapeHtml } from "./html.js";

export const LOCATE_MARKER_HTML = `
  <div class="locate-user-marker">
    <span class="locate-user-marker__shadow"></span>
    <span class="locate-user-marker__body">
      <svg
        viewBox="0 0 24 24"
        fill="${LOCATE_MARKER_COLOR}"
        style="filter: drop-shadow(0 8px 12px ${LOCATE_MARKER_GLOW}) drop-shadow(0 0 0.5px ${LOCATE_MARKER_HALO});"
        aria-hidden="true"
      >
        <path
          d="M20.28 3.72a1 1 0 0 0-1.04-.24L5.58 8.03a1 1 0 0 0-.13 1.84l5.53 2.51 2.51 5.53a1 1 0 0 0 1.84-.13l4.55-13.66a1 1 0 0 0-.24-1.04Z"
        />
      </svg>
    </span>
  </div>
`;

export const WHITE_MOTH_SITE_DRAFT_MARKER_HTML = `
  <div class="white-moth-site-draft-marker">
    <span
      class="white-moth-site-draft-marker__pulse"
      style="background: ${LOCATE_MARKER_PULSE};"
    ></span>
    <span
      class="white-moth-site-draft-marker__dot"
      style="background: ${LOCATE_MARKER_COLOR}; box-shadow: 0 8px 16px ${LOCATE_MARKER_RING};"
    ></span>
  </div>
`;

export function buildPointLabelMarker(label, latlng) {
  const safeLabel = escapeHtml(label);

  return L.marker(latlng, {
    interactive: false,
    keyboard: false,
    icon: L.divIcon({
      className: "map-point-label-marker",
      html: `<span class="map-point-label-text">${safeLabel}</span>`,
      iconSize: [1, 1],
      iconAnchor: [0, 0],
    }),
  });
}

export function buildSurveyCompletionMarker(latlng) {
  return L.marker(latlng, {
    interactive: false,
    keyboard: false,
    icon: L.divIcon({
      className: "map-survey-completion-marker",
      html: `<span class="map-survey-completion-check" style="background: ${SURVEY_COMPLETION_COLOR};" aria-hidden="true">✓</span>`,
      iconSize: [16, 16],
      iconAnchor: [8, 8],
    }),
  });
}

export function buildLocateMarker(latlng) {
  return L.marker(latlng, {
    icon: L.divIcon({
      className: "locate-user-marker-wrapper",
      html: LOCATE_MARKER_HTML,
      iconSize: [32, 32],
      iconAnchor: [16, 16],
    }),
  });
}

export function buildDraftSiteMarker(location) {
  return L.marker([location.latitude, location.longitude], {
    interactive: false,
    keyboard: false,
    icon: L.divIcon({
      className: "white-moth-site-draft-marker-wrapper",
      html: WHITE_MOTH_SITE_DRAFT_MARKER_HTML,
      iconSize: [30, 30],
      iconAnchor: [15, 15],
    }),
  });
}
