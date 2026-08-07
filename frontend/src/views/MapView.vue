<script setup>
import { ref } from "vue";

import ConfirmDialog from "../components/common/ConfirmDialog.vue";
import FeatureDetailPanel from "../components/map/FeatureDetailPanel.vue";
import LeafletMap from "../components/map/LeafletMap.vue";
import MapFilterPanel from "../components/map/MapFilterPanel.vue";
import MapSearchPanel from "../components/map/MapSearchPanel.vue";
import SiteEditorPanel from "../components/map/SiteEditorPanel.vue";
import { useMapView } from "../composables/map/useMapView.js";

const map = useMapView();
const searchPanelRef = ref(null);

const {
  views,
  selectedView,
  basemapMode,
  showPointLabels,
  geojson,
  loadingSearchIndex,
  loading,
  loadingViews,
  loadingFilterOptions,
  autoFitOnDataChange,
  selectedFeature,
  searchQuery,
  searchFocused,
  isSearchPanelOpen,
  surveyStatusFilter,
  isSurveyStatusFilterOpen,
  dynamicFilterValues,
  mapFocusRequest,
  siteDraftLocation,
  siteForm,
  whiteMothSiteCodeHint,
  loadingWhiteMothSiteCodeHint,
  otherPestSiteCodeHint,
  loadingOtherPestSiteCodeHint,
  isAddingSite,
  isSavingSite,
  showDeleteConfirm,
  isDeletingSite,
  deleteCheckLoading,
  featureTitle,
  featureRows,
  canDeleteSelectedSite,
  deleteConfirmMessage,
  searchResults,
  showSearchResults,
  supportsSurveyStatusFilter,
  visibleSurveyStatusOptions,
  dynamicFilterFields,
  currentView,
  activeSiteAddKind,
  siteAddLabel,
  siteAddTitle,
  whiteMothSiteCodeExample,
  resolvedWhiteMothSiteLocality,
  matchedWhiteMothSitePrefix,
  whiteMothSiteCodeHintText,
  otherPestSiteCodeExample,
  otherPestSiteLocalities,
  otherPestSiteCodeHintText,
  siteCodeError,
  siteLocationText,
  canSubmitSite,
  referenceLayersForMap,
  closeDeleteConfirm,
  requestDeleteSite,
  confirmDeleteSite,
  getSurveyStatusCount,
  onFeatureClick,
  selectSearchResult,
  toggleSearchPanel,
  toggleSurveyStatusFilterPanel,
  submitSearch,
  clearSearch,
  closeDetail,
  selectDynamicFilter,
  selectSurveyStatusFilter,
  toggleReferenceLayer,
  toggleSiteAdd,
  onMapClick,
  onSiteCodeInput,
  normalizeSiteCodeInput,
  applySuggestedSiteCode,
  cancelSiteAdd,
  submitSite,
} = map;

async function handleToggleSearch() {
  await toggleSearchPanel();
  if (isSearchPanelOpen.value) {
    await searchPanelRef.value?.focusSearchInput?.();
  }
}

function onSiteNameInput(value) {
  siteForm.value.siteName = value;
}

function onSiteLocalityInput(value) {
  siteForm.value.locality = value;
}
</script>

<template>
  <section class="map-page">
    <div class="map-workspace">
      <MapSearchPanel
        ref="searchPanelRef"
        :is-search-panel-open="isSearchPanelOpen"
        :search-query="searchQuery"
        :show-search-results="showSearchResults"
        :search-results="searchResults"
        :loading-search-index="loadingSearchIndex"
        :loading-views="loadingViews"
        :selected-view="selectedView"
        :supports-survey-status-filter="supportsSurveyStatusFilter"
        :is-survey-status-filter-open="isSurveyStatusFilterOpen"
        :survey-status-filter="surveyStatusFilter"
        :loading-filter-options="loadingFilterOptions"
        @toggle-search="handleToggleSearch"
        @toggle-survey-status="toggleSurveyStatusFilterPanel"
        @update:search-query="searchQuery = $event"
        @update:search-focused="searchFocused = $event"
        @submit-search="submitSearch"
        @clear-search="clearSearch"
        @select-result="selectSearchResult"
      >
        <template #filters>
          <MapFilterPanel
            :visible="supportsSurveyStatusFilter && isSurveyStatusFilterOpen"
            :visible-survey-status-options="visibleSurveyStatusOptions"
            :survey-status-filter="surveyStatusFilter"
            :loading="loading"
            :loading-views="loadingViews"
            :loading-filter-options="loadingFilterOptions"
            :dynamic-filter-fields="dynamicFilterFields"
            :dynamic-filter-values="dynamicFilterValues"
            :get-survey-status-count="getSurveyStatusCount"
            @select-survey-status="selectSurveyStatusFilter"
            @select-dynamic-filter="selectDynamicFilter"
          />
        </template>
      </MapSearchPanel>

      <FeatureDetailPanel
        v-if="selectedFeature"
        :feature-title="featureTitle"
        :feature-rows="featureRows"
        :can-delete="canDeleteSelectedSite"
        :delete-check-loading="deleteCheckLoading"
        @close="closeDetail"
        @delete="requestDeleteSite"
      />

      <SiteEditorPanel
        v-if="isAddingSite && siteDraftLocation"
        :site-add-title="siteAddTitle"
        :site-location-text="siteLocationText"
        :active-site-add-kind="activeSiteAddKind"
        :site-form="siteForm"
        :is-saving-site="isSavingSite"
        :can-submit-site="canSubmitSite"
        :site-code-error="siteCodeError"
        :other-pest-site-code-example="otherPestSiteCodeExample"
        :other-pest-site-localities="otherPestSiteLocalities"
        :other-pest-site-code-hint-text="otherPestSiteCodeHintText"
        :other-pest-site-code-hint="otherPestSiteCodeHint"
        :loading-other-pest-site-code-hint="loadingOtherPestSiteCodeHint"
        :white-moth-site-code-example="whiteMothSiteCodeExample"
        :resolved-white-moth-site-locality="resolvedWhiteMothSiteLocality"
        :matched-white-moth-site-prefix="matchedWhiteMothSitePrefix"
        :white-moth-site-code-hint-text="whiteMothSiteCodeHintText"
        :white-moth-site-code-hint="whiteMothSiteCodeHint"
        :loading-white-moth-site-code-hint="loadingWhiteMothSiteCodeHint"
        @cancel="cancelSiteAdd"
        @submit="submitSite"
        @update:code="onSiteCodeInput"
        @update:site-name="onSiteNameInput"
        @update:locality="onSiteLocalityInput"
        @normalize-code="normalizeSiteCodeInput"
        @apply-suggested-code="applySuggestedSiteCode"
      />

      <section class="map-panel" aria-label="调查点位地图">
        <LeafletMap
          :auto-fit-on-data-change="autoFitOnDataChange"
          :basemap-mode="basemapMode"
          :geojson="geojson"
          :loading="loading"
          :loading-views="loadingViews"
          :map-focus-request="mapFocusRequest"
          :popup-fields="currentView.columns"
          :reference-layers="referenceLayersForMap"
          :show-point-labels="showPointLabels"
          :view-name="selectedView"
          :views="views"
          :white-moth-site-add-mode="isAddingSite"
          :white-moth-site-draft-location="siteDraftLocation"
          :white-moth-site-saving="isSavingSite"
          :site-add-label="siteAddLabel"
          @feature-click="onFeatureClick"
          @map-click="onMapClick"
          @toggle-reference-layer="toggleReferenceLayer"
          @toggle-white-moth-site-add="toggleSiteAdd"
          @update:basemap-mode="basemapMode = $event"
          @update:show-point-labels="showPointLabels = $event"
          @update:view-name="selectedView = $event"
        />
      </section>
    </div>
  </section>

  <ConfirmDialog
    :open="showDeleteConfirm"
    :busy="isDeletingSite"
    title="删除点位"
    confirm-text="确认删除"
    :message="deleteConfirmMessage"
    @close="closeDeleteConfirm"
    @confirm="confirmDeleteSite"
  />
</template>

<!-- 非 scoped：面板子组件内复用同一套 map-* / detail-* 布局类名 -->
<style src="./map-view.css"></style>
