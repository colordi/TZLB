<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import { TreePine, Upload, MapPin, Filter, Layers, ChevronDown, LogOut } from "@lucide/vue";

import {
  getDefaultRouteForUser,
  userHasAnyRole,
  USER_ROLES,
} from "./auth/permissions.js";
import ToastViewport from "./components/ui/ToastViewport.vue";
import { useAuthSession } from "./composables/useAuthSession.js";
import { useToast } from "./composables/useToast.js";
import { mapStore, mapActions } from "./stores/mapStore.js";

const route = useRoute();
const router = useRouter();
const mobileNavOpen = ref(false);
const hideShell = computed(() => Boolean(route.meta?.hideShell));
const useFullBleedMain = computed(() => Boolean(route.meta?.fullBleed));
const isMapRoute = computed(() => route.path === "/map");
const loggingOut = ref(false);
const { user, signOut } = useAuthSession();
const { error, info } = useToast();

/* ---- user dropdown ---- */
const userDropdownOpen = ref(false);
const layerMenuOpen = ref(false);

/* ---- map context (reactive store, written by MapView) ---- */
const mapCtx = new Proxy(mapActions, {
  get(target, key) {
    return key in target ? target[key] : mapStore[key];
  },
});

const currentUserName = computed(() => user.value?.display_name || user.value?.username || "");
const homePath = computed(() => (user.value ? getDefaultRouteForUser(user.value) : "/workorder"));

const navItems = [
  {
    to: "/workorder",
    label: "工单录入",
    icon: "upload",
    requiredRoles: [USER_ROLES.ADMIN],
  },
  {
    to: "/map",
    label: "调查点位",
    icon: "pin",
  },
];
const visibleNavItems = computed(() =>
  navItems.filter((item) => !user.value || userHasAnyRole(user.value, item.requiredRoles)),
);

function closeMobileNav() {
  mobileNavOpen.value = false;
}

function toggleMobileNav() {
  mobileNavOpen.value = !mobileNavOpen.value;
}

function handleWindowKeydown(event) {
  if (event.key === "Escape") {
    closeMobileNav();
    userDropdownOpen.value = false;
    layerMenuOpen.value = false;
    if (mapCtx.ready) {
      mapCtx.setFilterPanelOpen(false);
    }
  }
}

function toggleUserDropdown() {
  userDropdownOpen.value = !userDropdownOpen.value;
}

function closeUserDropdown() {
  userDropdownOpen.value = false;
}

async function handleLogout() {
  if (loggingOut.value) {
    return;
  }

  loggingOut.value = true;
  try {
    await signOut();
    closeMobileNav();
    closeUserDropdown();
    info("您已安全退出当前账号。", "退出成功");
    await router.push("/login");
  } catch (logoutError) {
    error(`${logoutError.message || logoutError}`, "退出失败");
  } finally {
    loggingOut.value = false;
  }
}

watch(
  () => route.fullPath,
  () => {
    closeMobileNav();
    closeUserDropdown();
  },
);

watch(mobileNavOpen, (open) => {
  if (typeof document !== "undefined") {
    document.body.style.overflow = open ? "hidden" : "";
  }
});

/* ---- click outside to close popovers ---- */
function handleFilterCheckbox(fieldKey, optionValue, checked) {
  const current = [...(mapCtx.activeFilters[fieldKey] || [])];
  if (checked) {
    current.push(optionValue);
  } else {
    const idx = current.indexOf(optionValue);
    if (idx >= 0) current.splice(idx, 1);
  }
  mapCtx.setFilterValues(fieldKey, current);
}

function handleDocumentClick(event) {
  const target = event.target;

  /* user dropdown */
  if (userDropdownOpen.value && !target.closest(".user-dropdown-wrap")) {
    userDropdownOpen.value = false;
  }

  /* layer menu */
  if (layerMenuOpen.value && !target.closest(".map-layer-wrap")) {
    layerMenuOpen.value = false;
  }

  /* map filter popover */
  if (mapCtx.ready && mapCtx.isFilterPanelOpen && !target.closest(".map-filter-wrap")) {
    mapCtx.setFilterPanelOpen(false);
  }
}

onMounted(() => {
  window.addEventListener("keydown", handleWindowKeydown);
  document.addEventListener("click", handleDocumentClick);
});

onBeforeUnmount(() => {
  if (typeof document !== "undefined") {
    document.body.style.overflow = "";
  }
  window.removeEventListener("keydown", handleWindowKeydown);
  document.removeEventListener("click", handleDocumentClick);
});
</script>

<template>
  <div class="app-shell">
    <div v-if="!hideShell" class="app-backdrop" aria-hidden="true">
      <span class="backdrop-orb orb-left"></span>
      <span class="backdrop-orb orb-right"></span>
      <span class="backdrop-grid"></span>
    </div>

    <div class="shell-layout" :class="{ 'is-standalone': hideShell }">
      <!-- ===== HEADER: standard mode ===== -->
      <header v-if="!hideShell && !isMapRoute" class="site-header">
        <div class="site-header-shell">
          <RouterLink :to="homePath" class="site-brand">
            <div class="brand-icon-card" aria-hidden="true">
              <TreePine :size="21.6" :stroke-width="2" />
            </div>
            <div class="brand-copy">
              <strong>林业调查工作台</strong>
              <span>Forest Survey Workbench</span>
            </div>
          </RouterLink>

          <nav class="site-nav" aria-label="主导航">
            <RouterLink
              v-for="item in visibleNavItems"
              :key="item.to"
              :to="item.to"
              class="site-nav-link"
              :data-testid="`header-link-${item.to.slice(1)}`"
            >
              <Upload v-if="item.icon === 'upload'" :size="17.28" :stroke-width="2" />
              <MapPin v-else :size="17.28" :stroke-width="2" />
              <span>{{ item.label }}</span>
            </RouterLink>
          </nav>

          <div class="site-actions">
            <span v-if="currentUserName" class="user-pill">{{ currentUserName }}</span>
            <button type="button" class="logout-button" :disabled="loggingOut" @click="handleLogout">
              {{ loggingOut ? "退出中" : "退出登录" }}
            </button>
          </div>

          <button
            type="button"
            class="mobile-nav-toggle"
            data-testid="mobile-menu-trigger"
            :aria-expanded="mobileNavOpen ? 'true' : 'false'"
            aria-label="打开导航菜单"
            @click="toggleMobileNav"
          >
            <span></span>
            <span></span>
            <span></span>
          </button>
        </div>
      </header>

      <!-- ===== HEADER: map mode (compact toolbar) ===== -->
      <header v-if="!hideShell && isMapRoute" class="site-header map-header">
        <div class="site-header-shell site-header-shell--map">
          <!-- brand (compact) -->
          <RouterLink :to="homePath" class="site-brand site-brand--compact">
            <div class="brand-icon-card brand-icon-card--sm" aria-hidden="true">
              <TreePine :size="16" :stroke-width="2" />
            </div>
            <span class="brand-text-short">林业</span>
          </RouterLink>

          <!-- nav pills -->
          <nav class="map-nav-pills" aria-label="主导航">
            <RouterLink
              v-for="item in visibleNavItems"
              :key="item.to"
              :to="item.to"
              class="map-pill"
              :data-testid="`header-link-${item.to.slice(1)}`"
            >
              <Upload v-if="item.icon === 'upload'" :size="15" :stroke-width="2" />
              <MapPin v-else :size="15" :stroke-width="2" />
              <span>{{ item.label }}</span>
            </RouterLink>
          </nav>

          <!-- map toolbar controls (only when context is ready) -->
          <div v-if="mapCtx.ready" class="map-toolbar-controls">
            <!-- view select -->
            <div class="map-view-select-wrap">
              <select
                class="map-view-select"
                :value="mapCtx.selectedView"
                :disabled="mapCtx.loadingViews || !mapCtx.views.length"
                @change="mapCtx.setSelectedView($event.target.value)"
              >
                <option v-if="!mapCtx.views.length" value="">暂无可用视图</option>
                <option
                  v-for="view in mapCtx.views"
                  :key="view.name"
                  :value="view.name"
                >
                  {{ view.name }}
                </option>
              </select>
            </div>

            <!-- filter button -->
            <div class="map-filter-wrap">
              <button
                type="button"
                class="map-toolbar-btn"
                :class="{
                  'is-active': mapCtx.isFilterPanelOpen,
                  'has-badge': mapCtx.activeFilterCount > 0,
                }"
                aria-label="筛选配置"
                :aria-expanded="mapCtx.isFilterPanelOpen"
                @click.stop="mapCtx.toggleFilterPanel()"
              >
                <Filter :size="16" :stroke-width="2" />
                <span class="map-toolbar-btn-text">筛选</span>
                <span
                  v-if="mapCtx.activeFilterCount > 0"
                  class="map-filter-badge"
                >
                  {{ mapCtx.activeFilterCount }}
                </span>
              </button>

              <!-- filter panel popover -->
              <transition name="popover-fade">
                <div
                  v-if="mapCtx.isFilterPanelOpen"
                  class="map-filter-popover"
                  @click.stop
                >
                  <div class="filter-popover-inner">
                    <div
                      v-if="mapCtx.filterFields.length"
                      class="filter-fields"
                    >
                      <div
                        v-for="field in mapCtx.filterFields"
                        :key="field.key"
                        class="filter-field-item"
                        :class="{ 'is-open': mapCtx.openFilterMenus[field.key] }"
                      >
                        <button
                          type="button"
                          class="filter-field-trigger"
                          :class="{ 'is-open': mapCtx.openFilterMenus[field.key] }"
                          :disabled="mapCtx.loading || !field.options.length"
                          @click="mapCtx.toggleFilterMenu(field.key)"
                        >
                          <span class="filter-field-copy">
                            <span class="filter-field-label">{{ field.label }}</span>
                            <span
                              class="filter-field-summary"
                              :class="{ 'is-muted': !mapCtx.activeFilters[field.key]?.length }"
                            >
                              {{
                                !mapCtx.activeFilters[field.key]?.length
                                  ? '全部'
                                  : `已选 ${mapCtx.activeFilters[field.key].length} 项`
                              }}
                            </span>
                          </span>
                          <span class="filter-field-meta">
                            <span
                              v-if="mapCtx.activeFilters[field.key]?.length"
                              class="filter-field-count"
                            >
                              {{ mapCtx.activeFilters[field.key].length }}
                            </span>
                            <ChevronDown :size="14" :stroke-width="2" class="filter-field-chevron" />
                          </span>
                        </button>

                        <div
                          v-if="mapCtx.openFilterMenus[field.key]"
                          class="filter-option-dropdown"
                        >
                          <label
                            v-for="option in field.options"
                            :key="option.value"
                            class="filter-option"
                            :class="{ 'is-disabled': mapCtx.loading.value }"
                          >
                            <input
                              type="checkbox"
                              :value="option.value"
                              :checked="mapCtx.activeFilters[field.key]?.includes(option.value)"
                              :disabled="mapCtx.loading"
                              @change="handleFilterCheckbox(field.key, option.value, $event.target.checked)"
                            />
                            <span>{{ option.label }}</span>
                          </label>
                        </div>
                      </div>
                    </div>

                    <div v-else class="filter-empty-state">
                      当前视图暂无筛选字段
                    </div>

                    <div class="filter-actions">
                      <button
                        type="button"
                        class="filter-apply-btn"
                        :disabled="mapCtx.loading || !mapCtx.selectedView"
                        @click="mapCtx.applyFilter(); mapCtx.setFilterPanelOpen(false)"
                      >
                        应用筛选
                      </button>
                      <button
                        type="button"
                        class="filter-reset-btn"
                        :disabled="mapCtx.loading"
                        @click="mapCtx.resetFilter(); mapCtx.setFilterPanelOpen(false)"
                      >
                        清空
                      </button>
                    </div>
                  </div>
                </div>
              </transition>
            </div>

            <!-- layer menu -->
            <div class="map-layer-wrap">
              <button
                type="button"
                class="map-toolbar-btn"
                :class="{ 'is-active': layerMenuOpen }"
                aria-label="切换图层"
                aria-controls="map-layer-menu"
                :aria-expanded="layerMenuOpen"
                @click.stop="layerMenuOpen = !layerMenuOpen"
              >
                <Layers :size="16" :stroke-width="2" />
                <span class="map-toolbar-btn-text">图层</span>
              </button>

              <transition name="popover-fade">
                <div
                  v-if="layerMenuOpen"
                  id="map-layer-menu"
                  class="layer-menu-popup"
                  @click.stop
                >
                  <button
                    type="button"
                    class="layer-menu-item"
                    :class="{ 'is-active': mapCtx.basemapMode === 'standard' }"
                    @click="mapCtx.setBasemapMode('standard'); layerMenuOpen = false"
                  >
                    <strong>标准地图</strong>
                    <span>包含政区街道</span>
                  </button>
                  <button
                    type="button"
                    class="layer-menu-item"
                    :class="{ 'is-active': mapCtx.basemapMode === 'satellite' }"
                    @click="mapCtx.setBasemapMode('satellite'); layerMenuOpen = false"
                  >
                    <strong>卫星地图</strong>
                    <span>高分辨率影像</span>
                  </button>
                  <button
                    type="button"
                    class="layer-menu-item"
                    :class="{ 'is-active': mapCtx.showPointLabels }"
                    :aria-pressed="mapCtx.showPointLabels"
                    @click="mapCtx.togglePointLabels()"
                  >
                    <strong>显示编号</strong>
                    <span>{{ mapCtx.showPointLabels ? '当前已开启' : '当前已关闭' }}</span>
                  </button>
                </div>
              </transition>
            </div>
          </div>

          <!-- user dropdown -->
          <div class="user-dropdown-wrap">
            <button
              type="button"
              class="user-pill user-pill--map"
              :aria-expanded="userDropdownOpen"
              @click.stop="toggleUserDropdown"
            >
              <span>{{ currentUserName }}</span>
              <ChevronDown :size="14" :stroke-width="2" />
            </button>
            <transition name="popover-fade">
              <div v-if="userDropdownOpen" class="user-dropdown" @click.stop>
                <button
                  type="button"
                  class="dropdown-item"
                  :disabled="loggingOut"
                  @click="handleLogout"
                >
                  <LogOut :size="16" :stroke-width="2" />
                  <span>{{ loggingOut ? "退出中" : "退出登录" }}</span>
                </button>
              </div>
            </transition>
          </div>

          <!-- mobile hamburger -->
          <button
            type="button"
            class="mobile-nav-toggle"
            data-testid="mobile-menu-trigger"
            :aria-expanded="mobileNavOpen ? 'true' : 'false'"
            aria-label="打开导航菜单"
            @click="toggleMobileNav"
          >
            <span></span>
            <span></span>
            <span></span>
          </button>
        </div>
      </header>

      <!-- mobile drawer (same for both modes) -->
      <transition name="drawer-fade">
        <div
          v-if="mobileNavOpen"
          class="mobile-drawer-overlay"
          data-testid="mobile-drawer-overlay"
          @click="closeMobileNav"
        >
          <aside class="mobile-drawer" @click.stop>
            <div class="mobile-drawer-brand">
              <div class="brand-icon-card brand-icon-card-compact" aria-hidden="true">
                <TreePine :size="17.28" :stroke-width="2" />
              </div>
              <div class="brand-copy">
                <strong>林业调查工作台</strong>
                <span>Forest Survey Workbench</span>
              </div>
            </div>

            <nav class="drawer-nav" aria-label="移动端主导航">
              <RouterLink
                v-for="item in visibleNavItems"
                :key="`mobile-${item.to}`"
                :to="item.to"
                class="drawer-link"
                :data-testid="`drawer-link-${item.to.slice(1)}`"
              >
                <Upload v-if="item.icon === 'upload'" :size="17.28" :stroke-width="2" />
                <MapPin v-else :size="17.28" :stroke-width="2" />
                <span>{{ item.label }}</span>
              </RouterLink>
            </nav>

            <div class="drawer-actions">
              <span v-if="currentUserName" class="user-pill user-pill--drawer">
                {{ currentUserName }}
              </span>
              <button
                type="button"
                class="logout-button logout-button--drawer"
                :disabled="loggingOut"
                @click="handleLogout"
              >
                {{ loggingOut ? "退出中" : "退出登录" }}
              </button>
            </div>
          </aside>
        </div>
      </transition>

      <main
        class="site-main"
        :class="{ 'is-standalone': hideShell, 'is-full-bleed': useFullBleedMain }"
      >
        <RouterView />
      </main>
    </div>

    <ToastViewport />
  </div>
</template>

<style scoped>
/* ================================================================
   TOKENS — Friendly palette bindings
   ================================================================ */
.app-shell {
  min-height: 100vh;
  position: relative;
}

.app-backdrop {
  position: fixed;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  z-index: -1;
}

.backdrop-orb {
  position: absolute;
  border-radius: 999px;
  filter: blur(14px);
  opacity: 0.55;
}

.orb-left {
  width: 28rem;
  height: 28rem;
  top: -8rem;
  left: -10rem;
  background: radial-gradient(circle, rgba(47, 125, 70, 0.18), rgba(47, 125, 70, 0));
}

.orb-right {
  width: 32rem;
  height: 32rem;
  top: 14rem;
  right: -12rem;
  background: radial-gradient(circle, rgba(107, 143, 62, 0.16), rgba(107, 143, 62, 0));
}

.backdrop-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.35) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.35) 1px, transparent 1px);
  background-size: 4rem 4rem;
  mask-image: linear-gradient(to bottom, rgba(0, 0, 0, 0.3), transparent 72%);
  opacity: 0.18;
}

.shell-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.shell-layout.is-standalone {
  display: block;
}

/* ================================================================
   STANDARD HEADER
   ================================================================ */
.site-header {
  padding: 0.9rem clamp(0.85rem, 2vw, 1.35rem) 0;
}

.site-header-shell {
  width: min(100%, var(--content-width));
  margin: 0 auto;
  min-height: var(--header-h-standard);
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.7rem 0.9rem 0.7rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--elev-ring);
  backdrop-filter: blur(20px);
}

.site-brand {
  display: inline-flex;
  align-items: center;
  gap: 0.9rem;
  min-width: 0;
  text-decoration: none;
}

.brand-icon-card {
  width: 3.05rem;
  height: 3.05rem;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: var(--color-accent-on);
  box-shadow: var(--elev-ring);
}

.brand-icon-card svg {
  width: 1.35rem;
  height: 1.35rem;
  color: currentColor;
}

.brand-icon-card-compact {
  width: 2.7rem;
  height: 2.7rem;
  border-radius: var(--radius-sm);
}

.brand-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.12rem;
}

.brand-copy strong {
  color: var(--color-ink);
  font-size: 1rem;
  line-height: 1.2;
  letter-spacing: var(--tracking-display);
  font-weight: 700;
}

.brand-copy span {
  color: var(--color-muted);
  font-size: 0.79rem;
}

.site-nav {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  flex-wrap: wrap;
}

.site-actions {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
}

.user-pill {
  display: inline-flex;
  align-items: center;
  min-height: 2.5rem;
  padding: 0.45rem 0.85rem;
  border-radius: var(--radius-pill);
  background: var(--color-primary);
  color: var(--color-accent-on);
  font-size: 0.88rem;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all var(--motion-fast) var(--ease-standard);
}

.user-pill:hover {
  background: var(--color-accent-hover);
}

.logout-button {
  min-height: 2.9rem;
  padding: 0.65rem 1rem;
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-ink-soft);
  box-shadow: none;
  font-size: var(--text-sm);
}

.logout-button:hover {
  background: var(--color-surface-container);
  color: var(--color-ink);
  box-shadow: var(--elev-ring);
}

.site-nav-link,
.drawer-link {
  display: inline-flex;
  align-items: center;
  gap: 0.7rem;
  min-height: 3rem;
  padding: 0.72rem 1rem;
  border-radius: var(--radius-sm);
  color: var(--color-ink-soft);
  text-decoration: none;
  font-weight: 600;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard),
    box-shadow var(--motion-fast) var(--ease-standard);
}

.site-nav-link svg,
.drawer-link svg {
  width: 1.08rem;
  height: 1.08rem;
  color: currentColor;
  flex-shrink: 0;
}

.site-nav-link:hover,
.drawer-link:hover {
  background: var(--color-primary-container);
  color: var(--color-primary);
}

.site-nav-link.router-link-active,
.drawer-link.router-link-active {
  color: var(--color-accent-on);
  background: var(--color-accent);
  box-shadow: var(--elev-ring);
}

/* ================================================================
   MAP MODE HEADER
   ================================================================ */
.map-header {
  position: sticky;
  top: 0;
  z-index: 1500;
  padding: 0.5rem clamp(0.5rem, 1.5vw, 0.85rem) 0;
}

.site-header-shell--map {
  min-height: var(--header-h-map);
  padding: 0.4rem 0.6rem;
  border-radius: var(--radius-md);
  gap: 0.5rem;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border-soft);
}

.site-brand--compact {
  gap: 0.4rem;
}

.brand-icon-card--sm {
  width: 2rem;
  height: 2rem;
  border-radius: var(--radius-sm);
}

.brand-icon-card--sm svg {
  width: 1rem;
  height: 1rem;
}

.brand-text-short {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--color-ink);
  letter-spacing: var(--tracking-display);
  white-space: nowrap;
}

/* nav pills */
.map-nav-pills {
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.map-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  height: 2rem;
  padding: 0 0.65rem;
  border-radius: var(--radius-pill);
  color: var(--color-ink-soft);
  text-decoration: none;
  font-size: 0.78rem;
  font-weight: 600;
  white-space: nowrap;
  transition: all var(--motion-fast) var(--ease-standard);
}

.map-pill svg {
  width: 0.85rem;
  height: 0.85rem;
  flex-shrink: 0;
}

.map-pill:hover {
  background: var(--color-primary);
  color: var(--color-accent-on);
}

.map-pill.router-link-active {
  background: var(--color-accent);
  color: var(--color-accent-on);
}

/* map toolbar controls (view select, filter, layer) */
.map-toolbar-controls {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin-left: auto;
}

.map-view-select-wrap {
  position: relative;
}

.map-view-select {
  appearance: none;
  min-width: 8rem;
  max-width: 14rem;
  height: 2rem;
  padding: 0 1.6rem 0 0.6rem;
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-ink);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--motion-fast) var(--ease-standard);
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23796f91' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.45rem center;
}

.map-view-select:hover {
  border-color: var(--color-line-strong);
}

.map-view-select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: var(--focus-ring);
}

.map-view-select:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* toolbar buttons (filter, layer) */
.map-toolbar-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  height: 2rem;
  padding: 0 0.55rem;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-ink-soft);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--motion-fast) var(--ease-standard);
}

.map-toolbar-btn:hover {
  background: var(--color-surface-container);
  color: var(--color-accent);
}

.map-toolbar-btn.is-active {
  background: var(--color-accent);
  color: var(--color-accent-on);
  border-color: var(--color-accent);
}

.map-toolbar-btn svg {
  flex-shrink: 0;
}

.map-filter-badge {
  min-width: 1rem;
  height: 1rem;
  padding: 0 4px;
  border-radius: var(--radius-pill);
  background: var(--color-danger);
  color: var(--color-surface);
  font-size: 0.6rem;
  font-weight: 700;
  line-height: 1rem;
  text-align: center;
}

/* user dropdown (map mode) */
.user-dropdown-wrap {
  position: relative;
}

.user-pill--map {
  height: 2rem;
  padding: 0 0.6rem;
  font-size: 0.78rem;
  gap: 0.25rem;
  border: 1px solid var(--border-soft);
  background: var(--color-surface);
  color: var(--color-ink-soft);
}

.user-pill--map svg {
  flex-shrink: 0;
  opacity: 0.6;
}

.user-dropdown {
  position: absolute;
  top: calc(100% + 0.35rem);
  right: 0;
  min-width: 10rem;
  padding: 0.35rem;
  background: var(--color-surface);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  box-shadow: var(--elev-raised);
  z-index: 2000;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.5rem 0.65rem;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-ink);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--motion-fast) var(--ease-standard);
}

.dropdown-item:hover {
  background: var(--color-surface-container-low);
}

.dropdown-item:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* filter popover */
.map-filter-wrap {
  position: relative;
}

.map-filter-popover {
  position: absolute;
  top: calc(100% + 0.4rem);
  right: 0;
  min-width: 16rem;
  max-width: min(22rem, calc(100vw - 2rem));
  background: var(--color-surface);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  box-shadow: var(--elev-raised);
  z-index: 2000;
  overflow: hidden;
}

.filter-popover-inner {
  padding: 0.75rem;
  max-height: 50vh;
  overflow-y: auto;
}

.filter-fields {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.filter-field-item {
  position: relative;
}

.filter-field-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0.5rem 0.65rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  cursor: pointer;
  transition: all var(--motion-fast) var(--ease-standard);
}

.filter-field-trigger:hover {
  border-color: var(--color-line-strong);
}

.filter-field-trigger.is-open {
  border-color: var(--color-accent);
}

.filter-field-trigger:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.filter-field-copy {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.05rem;
  min-width: 0;
}

.filter-field-label {
  color: var(--color-ink);
  font-size: 0.78rem;
  font-weight: 600;
}

.filter-field-summary {
  color: var(--color-accent);
  font-size: 0.7rem;
  font-weight: 500;
}

.filter-field-summary.is-muted {
  color: var(--color-muted);
}

.filter-field-meta {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  flex-shrink: 0;
}

.filter-field-count {
  min-width: 1.15rem;
  height: 1.15rem;
  padding: 0 4px;
  border-radius: var(--radius-pill);
  background: var(--color-accent);
  color: var(--color-accent-on);
  font-size: 0.65rem;
  font-weight: 700;
  line-height: 1.15rem;
  text-align: center;
}

.filter-field-chevron {
  color: var(--color-muted);
  transition: transform 150ms ease;
}

.filter-field-item.is-open .filter-field-chevron {
  transform: rotate(180deg);
}

.filter-option-dropdown {
  margin-top: 0.35rem;
  padding: 0.4rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  max-height: 10rem;
  overflow-y: auto;
}

.filter-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.5rem;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--motion-fast) var(--ease-standard);
  font-size: 0.78rem;
  color: var(--color-ink);
}

.filter-option:hover {
  background: var(--color-surface-container-low);
}

.filter-option.is-disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.filter-option input[type='checkbox'] {
  width: 0.95rem;
  height: 0.95rem;
  accent-color: var(--color-accent);
  cursor: inherit;
}

.filter-empty-state {
  padding: 1.25rem 0.75rem;
  text-align: center;
  color: var(--color-muted);
  font-size: 0.82rem;
}

.filter-actions {
  display: flex;
  gap: 0.4rem;
  margin-top: 0.65rem;
  padding-top: 0.65rem;
  border-top: 1px solid var(--color-border);
}

.filter-apply-btn {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--color-accent);
  color: var(--color-accent-on);
  font-weight: 600;
  font-size: 0.82rem;
  cursor: pointer;
  transition: all var(--motion-fast) var(--ease-standard);
}

.filter-apply-btn:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.filter-apply-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.filter-reset-btn {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-ink-soft);
  font-weight: 500;
  font-size: 0.82rem;
  cursor: pointer;
  transition: all var(--motion-fast) var(--ease-standard);
}

.filter-reset-btn:hover:not(:disabled) {
  background: var(--color-surface-container-low);
}

.filter-reset-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* layer menu */
.map-layer-wrap {
  position: relative;
}

.layer-menu-popup {
  position: absolute;
  top: calc(100% + 0.4rem);
  right: 0;
  min-width: 12rem;
  padding: 0.35rem;
  background: var(--color-surface);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  box-shadow: var(--elev-raised);
  z-index: 2000;
  transform-origin: top right;
}

.layer-menu-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.1rem;
  width: 100%;
  padding: 0.45rem 0.6rem;
  border: 2px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-ink);
  text-align: left;
  cursor: pointer;
  transition: all var(--motion-fast) var(--ease-standard);
}

.layer-menu-item:hover {
  background: var(--color-surface-container-low);
}

.layer-menu-item.is-active {
  border-color: var(--color-accent);
  background: var(--color-surface-container-low);
}

.layer-menu-item strong {
  color: var(--color-ink);
  font-size: 0.78rem;
  font-weight: 600;
}

.layer-menu-item span {
  color: var(--color-muted);
  font-size: 0.68rem;
}

/* ================================================================
   MAIN / FULL-BLEED
   ================================================================ */
.site-main {
  width: min(100%, var(--content-width));
  min-width: 0;
  margin: 0 auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 1rem clamp(0.85rem, 2vw, 1.35rem) 2rem;
}

.site-main.is-standalone {
  width: 100%;
  max-width: none;
  min-height: 100vh;
  padding: 0;
}

.site-main.is-full-bleed {
  width: 100%;
  max-width: none;
  min-height: 0;
  padding: 0;
}

/* ================================================================
   MOBILE DRAWER
   ================================================================ */
.mobile-drawer-overlay {
  position: fixed;
  inset: 0;
  z-index: 1800;
  display: none;
}

.mobile-drawer {
  width: min(var(--app-drawer-width), calc(100vw - 1.25rem));
}

.mobile-drawer-brand {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

.drawer-nav {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.drawer-actions {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.user-pill--drawer {
  justify-content: center;
}

.logout-button--drawer {
  width: 100%;
}

/* ================================================================
   POPOVER ANIMATION
   ================================================================ */
.popover-fade-enter-active,
.popover-fade-leave-active {
  transition: all 150ms var(--ease-standard);
}

.popover-fade-enter-from,
.popover-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.97);
}

.drawer-fade-enter-active,
.drawer-fade-leave-active {
  transition: opacity 180ms ease;
}

.drawer-fade-enter-from,
.drawer-fade-leave-to {
  opacity: 0;
}

/* ================================================================
   MOBILE NAV TOGGLE
   ================================================================ */
.mobile-nav-toggle {
  display: none;
  min-height: 0;
  width: 2.4rem;
  height: 2.4rem;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-ink);
  box-shadow: var(--elev-ring);
  flex-direction: column;
  gap: 0.26rem;
}

.mobile-nav-toggle span {
  width: 1.08rem;
  height: 2px;
  border-radius: 999px;
  background: currentColor;
}

/* ================================================================
   RESPONSIVE
   ================================================================ */
@media (max-width: 900px) {
  .site-header {
    padding-top: 0.65rem;
  }

  .site-header-shell {
    min-height: var(--app-mobile-header-height);
    padding: 0.55rem 0.75rem 0.55rem 0.85rem;
    border-radius: 22px;
  }

  .site-nav {
    display: none;
  }

  .site-actions {
    display: none;
  }

  .mobile-nav-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .site-main {
    padding-top: 0.85rem;
    padding-bottom: 1.6rem;
  }

  .mobile-drawer-overlay {
    display: flex;
    align-items: stretch;
    background: rgba(29, 24, 54, 0.3);
    backdrop-filter: blur(8px);
  }

  .mobile-drawer {
    height: 100vh;
    padding: 1rem;
    background: var(--color-surface);
    box-shadow: var(--elev-raised);
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
}

/* map mode responsive */
@media (max-width: 760px) {
  .map-header .site-header-shell--map {
    flex-wrap: wrap;
    gap: 0.35rem;
    padding: 0.35rem 0.5rem;
  }

  .map-nav-pills {
    display: none;
  }

  .map-toolbar-btn-text {
    display: none;
  }

  .map-view-select {
    min-width: 0;
    flex: 1;
    font-size: 0.75rem;
  }

  .map-filter-popover {
    position: fixed;
    top: auto;
    left: 0.5rem;
    right: 0.5rem;
    bottom: 0;
    max-width: 100%;
    border-radius: 16px 16px 0 0;
    max-height: 60vh;
  }

  .mobile-nav-toggle {
    display: inline-flex;
  }
}

@media (max-width: 640px) {
  .site-header-shell {
    gap: 0.7rem;
    min-height: 4rem;
  }

  .brand-icon-card {
    width: 2.7rem;
    height: 2.7rem;
    border-radius: 16px;
  }

  .brand-icon-card svg {
    width: 1.16rem;
    height: 1.16rem;
  }

  .brand-copy strong {
    font-size: 0.96rem;
  }

  .brand-copy span {
    font-size: 0.74rem;
  }

  .mobile-nav-toggle {
    width: 2.75rem;
    height: 2.75rem;
  }

  .mobile-drawer {
    padding: 0.95rem;
  }
}
</style>
