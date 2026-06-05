/**
 * Shared reactive store for the map context.
 *
 * MapView writes into this store; App.vue reads from it.
 * Because it's module-level reactive state, both components share the same
 * reactive reference — no provide/inject timing issues.
 */
import { reactive, readonly } from "vue";

const state = reactive({
  ready: false,
  views: [],
  selectedView: "",
  loadingViews: false,
  filterFields: [],
  activeFilters: {},
  openFilterMenus: {},
  loading: false,
  isFilterPanelOpen: false,
  activeFilterCount: 0,
});

/* ---- setters (called by MapView) ---- */

function setReady(val) {
  state.ready = val;
}

function setViews(val) {
  state.views = val;
}

function setSelectedView(val) {
  state.selectedView = val;
}

function setLoadingViews(val) {
  state.loadingViews = val;
}

function setFilterFields(val) {
  state.filterFields = val;
}

function setActiveFilters(val) {
  state.activeFilters = val;
}

function setOpenFilterMenus(val) {
  state.openFilterMenus = val;
}

function setLoading(val) {
  state.loading = val;
}

function setFilterPanelOpen(val) {
  state.isFilterPanelOpen = val;
}

function setActiveFilterCount(val) {
  state.activeFilterCount = val;
}

/* ---- convenience actions ---- */

function toggleFilterPanel() {
  state.isFilterPanelOpen = !state.isFilterPanelOpen;
}

function toggleFilterMenu(fieldKey) {
  const current = Boolean(state.openFilterMenus[fieldKey]);
  const next = { ...state.openFilterMenus };
  // close all others, toggle this one
  for (const k of Object.keys(next)) {
    next[k] = false;
  }
  if (!current) {
    next[fieldKey] = true;
  }
  state.openFilterMenus = next;
}

function setFilterMenuOpen(fieldKey, open) {
  const next = { ...state.openFilterMenus };
  if (open) {
    next[fieldKey] = true;
  } else {
    next[fieldKey] = false;
  }
  state.openFilterMenus = next;
}

function setFilterValues(fieldKey, values) {
  state.activeFilters = { ...state.activeFilters, [fieldKey]: values };
}

/* ---- actions to be wired from MapView ---- */
let _applyFilterFn = null;
let _resetFilterFn = null;

function registerFilterActions({ applyFilter, resetFilter }) {
  _applyFilterFn = applyFilter;
  _resetFilterFn = resetFilter;
}

function applyFilter() {
  if (_applyFilterFn) _applyFilterFn();
}

function resetFilter() {
  if (_resetFilterFn) _resetFilterFn();
}

/**
 * The readonly state object that App.vue should import.
 * Setters / actions are exported separately for MapView to call.
 */
export const mapStore = readonly(state);

export const mapActions = {
  setReady,
  setViews,
  setSelectedView,
  setLoadingViews,
  setFilterFields,
  setActiveFilters,
  setOpenFilterMenus,
  setLoading,
  setFilterPanelOpen,
  setActiveFilterCount,
  toggleFilterPanel,
  toggleFilterMenu,
  setFilterMenuOpen,
  setFilterValues,
  registerFilterActions,
  applyFilter,
  resetFilter,
};
