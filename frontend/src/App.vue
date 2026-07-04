<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import {
  TreePine,
  Upload,
  MapPin,
  Database,
  ChartColumn,
  LayoutDashboard,
  Users,
  Layers,
  ChevronDown,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
} from "@lucide/vue";

import {
  getDefaultRouteForUser,
  userHasAnyRole,
  USER_ROLES,
} from "./auth/permissions.js";
import ToastViewport from "./components/ui/ToastViewport.vue";
import { useAuthSession } from "./composables/useAuthSession.js";
import { useToast } from "./composables/useToast.js";

const route = useRoute();
const router = useRouter();
const mobileNavOpen = ref(false);
const sidebarCollapsed = ref(false);
const hideShell = computed(() => Boolean(route.meta?.hideShell));
const useFullBleedMain = computed(() => Boolean(route.meta?.fullBleed));
const loggingOut = ref(false);
const { user, signOut } = useAuthSession();
const { error, info } = useToast();

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value;
}

/* ---- user dropdown ---- */
const userDropdownOpen = ref(false);

const currentUserName = computed(() => user.value?.display_name || user.value?.username || "");
const homePath = computed(() => (user.value ? getDefaultRouteForUser(user.value) : "/workorder"));

const navGroups = [
  {
    label: "业务管理",
    items: [
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
    ],
  },
  {
    label: "数据管理",
    items: [
      {
        to: "/data-export",
        label: "数据导出",
        icon: "database",
        requiredRoles: [USER_ROLES.ADMIN],
      },
      {
        to: "/data-statistics",
        label: "数据统计",
        icon: "chart",
        requiredRoles: [USER_ROLES.ADMIN],
      },
    ],
  },
  {
    label: "管理后台",
    items: [
      {
        to: "/admin",
        label: "管理概览",
        icon: "dashboard",
        requiredRoles: [USER_ROLES.ADMIN],
      },
      {
        to: "/admin/users",
        label: "用户管理",
        icon: "users",
        requiredRoles: [USER_ROLES.ADMIN],
      },
      {
        to: "/admin/layers",
        label: "图层管理",
        icon: "layers",
        requiredRoles: [USER_ROLES.ADMIN],
      },
    ],
  },
];
const navIconComponents = {
  upload: Upload,
  pin: MapPin,
  database: Database,
  chart: ChartColumn,
  dashboard: LayoutDashboard,
  users: Users,
  layers: Layers,
};
function resolveNavIcon(icon) {
  return navIconComponents[icon] || MapPin;
}
const visibleNavGroups = computed(() =>
  navGroups
    .map((group) => ({
      ...group,
      items: group.items.filter(
        (item) => !user.value || userHasAnyRole(user.value, item.requiredRoles),
      ),
    }))
    .filter((group) => group.items.length > 0),
);
const visibleNavItems = computed(() =>
  visibleNavGroups.value.flatMap((group) => group.items),
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

function handleDocumentClick(event) {
  const target = event.target;

  /* user dropdown */
  if (userDropdownOpen.value && !target.closest(".user-dropdown-wrap")) {
    userDropdownOpen.value = false;
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

    <div class="shell-layout" :class="{ 'is-standalone': hideShell, 'has-sidebar': !hideShell }">
      <aside v-if="!hideShell" class="app-sidebar" :class="{ 'is-collapsed': sidebarCollapsed }" aria-label="主导航">
        <div class="app-sidebar-brand-row">
          <RouterLink :to="homePath" class="app-sidebar-brand">
            <span class="app-sidebar-brand-mark" aria-hidden="true">
              <TreePine :size="22" :stroke-width="2" />
            </span>
            <span class="app-sidebar-brand-copy">
              <strong>林业调查工作台</strong>
              <span>FORESTRY SURVEY WORKBENCH</span>
            </span>
          </RouterLink>
          <button
            type="button"
            class="sidebar-toggle-btn"
            :aria-label="sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
            :aria-expanded="!sidebarCollapsed"
            @click="toggleSidebar"
          >
            <PanelLeftOpen v-if="sidebarCollapsed" :size="18" :stroke-width="2" />
            <PanelLeftClose v-else :size="18" :stroke-width="2" />
          </button>
        </div>

        <template v-for="group in visibleNavGroups" :key="group.label">
          <div class="app-sidebar-caption">{{ group.label }}</div>
          <nav class="app-sidebar-nav" :aria-label="group.label">
            <RouterLink
              v-for="item in group.items"
              :key="`sidebar-${item.to}`"
              :to="item.to"
              class="app-sidebar-link"
              :data-testid="`sidebar-link-${item.to.slice(1)}`"
            >
              <component :is="resolveNavIcon(item.icon)" :size="18" :stroke-width="2" />
              <span>{{ item.label }}</span>
            </RouterLink>
          </nav>
        </template>

        <div class="app-sidebar-foot">
          <div class="app-sidebar-profile">
            <span class="app-sidebar-avatar" aria-hidden="true">
              {{ (currentUserName || "账").slice(0, 1) }}
            </span>
            <span v-if="!sidebarCollapsed">
              <strong>{{ currentUserName || "账号" }}</strong>
              <span>当前登录用户</span>
            </span>
          </div>
        </div>
      </aside>

      <header v-if="!hideShell" class="site-header">
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

          <div class="site-section-title">
            <span>工作台</span>
            <strong>{{ route.meta?.section || "工作界面" }}</strong>
          </div>

          <nav class="site-nav" aria-label="主导航">
            <RouterLink
              v-for="item in visibleNavItems"
              :key="item.to"
              :to="item.to"
              class="site-nav-link"
              :data-testid="`header-link-${item.to.slice(1)}`"
            >
              <component :is="resolveNavIcon(item.icon)" :size="17.28" :stroke-width="2" />
              <span>{{ item.label }}</span>
            </RouterLink>
          </nav>

          <div class="site-actions">
            <div class="user-dropdown-wrap">
              <button
                type="button"
                class="user-pill"
                :aria-expanded="userDropdownOpen"
                @click.stop="toggleUserDropdown"
              >
                <span>{{ currentUserName || "账号" }}</span>
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
                <component :is="resolveNavIcon(item.icon)" :size="17.28" :stroke-width="2" />
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

.shell-layout.has-sidebar {
  display: grid;
  grid-template-columns: 228px minmax(0, 1fr);
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
  background: var(--color-bg);
  transition: grid-template-columns 200ms ease;
}

.shell-layout.has-sidebar:has(.app-sidebar.is-collapsed) {
  grid-template-columns: 68px minmax(0, 1fr);
}

.shell-layout.is-standalone {
  display: block;
}

/* ================================================================
   DESKTOP SIDEBAR
   ================================================================ */
.app-sidebar {
  position: relative;
  z-index: 20;
  grid-row: 1 / -1;
  min-width: 0;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--color-nav);
  color: var(--color-surface);
  transition: width 200ms ease;
  width: 228px;
}

.app-sidebar.is-collapsed {
  width: 68px;
}

.app-sidebar.is-collapsed .app-sidebar-brand-copy,
.app-sidebar.is-collapsed .app-sidebar-caption,
.app-sidebar.is-collapsed .app-sidebar-link span,
.app-sidebar.is-collapsed .app-sidebar-nav .nav-count {
  opacity: 0;
  width: 0;
  overflow: hidden;
  white-space: nowrap;
}

.app-sidebar.is-collapsed .app-sidebar-brand {
  justify-content: center;
  padding: 0;
}

.app-sidebar.is-collapsed .app-sidebar-brand-row {
  flex-direction: column;
  justify-content: center;
  gap: 10px;
  min-height: 96px;
  padding: 12px 0;
}

.app-sidebar.is-collapsed .app-sidebar-link {
  justify-content: center;
  padding: 0;
}

.app-sidebar.is-collapsed .app-sidebar-link svg {
  margin: 0;
}

.app-sidebar.is-collapsed .app-sidebar-profile {
  justify-content: center;
}

.app-sidebar.is-collapsed .app-sidebar-profile span {
  display: none;
}

.app-sidebar.is-collapsed .app-sidebar-foot {
  padding: var(--space-6) var(--space-2);
}

.app-sidebar-brand-row {
  min-height: 68px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px 0 0;
  border-bottom: 1px solid color-mix(in oklch, var(--color-surface) 12%, transparent);
}

.app-sidebar-brand {
  min-width: 0;
  display: flex;
  align-items: center;
  flex: 1;
  gap: 11px;
  padding: 0 18px;
  color: inherit;
  text-decoration: none;
}

.app-sidebar-brand-mark {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border: 1px solid color-mix(in oklch, var(--color-surface) 22%, transparent);
  border-radius: 9px;
  background: color-mix(in oklch, var(--color-surface) 7%, transparent);
}

.app-sidebar-brand-copy {
  min-width: 0;
}

.app-sidebar-brand-copy strong,
.app-sidebar-brand-copy span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-sidebar-brand-copy strong {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  letter-spacing: 0.03em;
}

.app-sidebar-brand-copy span {
  color: color-mix(in oklch, var(--color-surface) 62%, transparent);
  font-size: var(--text-2xs);
  letter-spacing: 0.06em;
}

.app-sidebar-caption {
  padding: 20px 18px 8px;
  color: color-mix(in oklch, var(--color-surface) 48%, transparent);
  font-family: var(--font-mono);
  font-size: var(--text-2xs);
  letter-spacing: 0.12em;
}

.app-sidebar-nav {
  display: grid;
  gap: var(--space-1);
  padding: 0 var(--space-4);
}

.app-sidebar-link {
  min-height: 42px;
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 0 var(--space-5);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  color: color-mix(in oklch, var(--color-surface) 72%, transparent);
  font-size: var(--text-md);
  font-weight: 650;
  text-decoration: none;
  transition:
    background var(--motion-base) ease,
    border-color var(--motion-base) ease,
    color var(--motion-base) ease;
}

.app-sidebar-link:hover {
  background: color-mix(in oklch, var(--color-surface) 7%, transparent);
  color: var(--color-surface);
}

.app-sidebar-link.router-link-active {
  border-color: color-mix(in oklch, var(--color-surface) 13%, transparent);
  background: color-mix(in oklch, var(--color-surface) 10%, transparent);
  color: var(--color-surface);
}

.app-sidebar-foot {
  margin-top: auto;
  padding: var(--space-6) var(--space-4);
  border-top: 1px solid color-mix(in oklch, var(--color-surface) 12%, transparent);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.sidebar-toggle-btn {
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  min-height: 32px;
  box-sizing: border-box;
  padding: 0;
  border: 1px solid color-mix(in oklch, var(--color-surface) 15%, transparent);
  border-radius: 8px;
  background: color-mix(in oklch, var(--color-nav) 86%, var(--color-surface));
  color: color-mix(in oklch, var(--color-surface) 80%, transparent);
  cursor: pointer;
  transition:
    background var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard);
}

.sidebar-toggle-btn:hover {
  transform: none;
  box-shadow: none;
  background: color-mix(in oklch, var(--color-surface) 15%, transparent);
  border-color: color-mix(in oklch, var(--color-surface) 25%, transparent);
  color: var(--color-surface);
}

.sidebar-toggle-btn svg {
  width: 18px;
  height: 18px;
}

.app-sidebar-profile {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3);
  border-radius: var(--radius-md);
}

.app-sidebar-avatar {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: var(--radius-round);
  background: color-mix(in oklch, var(--color-surface) 14%, transparent);
  font-size: var(--text-sm);
  font-weight: 700;
}

.app-sidebar-profile strong,
.app-sidebar-profile span {
  display: block;
  line-height: 1.35;
}

.app-sidebar-profile strong {
  font-size: var(--text-sm);
}

.app-sidebar-profile span span {
  color: color-mix(in oklch, var(--color-surface) 52%, transparent);
  font-size: var(--text-2xs);
}

/* ================================================================
   UNIFIED HEADER
   ================================================================ */
.site-header {
  position: sticky;
  top: 0;
  z-index: 1500;
  grid-column: 2;
  min-width: 0;
  padding: 0;
}

.site-header-shell {
  width: 100%;
  min-height: 68px;
  display: flex;
  align-items: center;
  gap: var(--space-6);
  padding: 0 var(--space-10);
  border-bottom: 1px solid var(--color-border);
  background: color-mix(in oklch, var(--color-surface) 94%, transparent);
  box-shadow: none;
  backdrop-filter: blur(12px);
}

.site-brand {
  display: none;
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
  display: none;
  align-items: center;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.site-section-title {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.site-section-title span {
  color: var(--color-text-muted);
}

.site-section-title strong {
  min-width: 0;
  overflow: hidden;
  color: var(--color-text);
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.site-section-title span::after {
  margin-left: var(--space-3);
  color: var(--color-border);
  content: "/";
}

.site-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  min-width: 0;
}

.context-tools.is-empty {
  display: none;
}

.site-actions {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.user-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  min-height: 2.45rem;
  max-width: 12rem;
  padding: 0.45rem 0.75rem;
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-ink-soft);
  font-size: 0.84rem;
  font-weight: 600;
  border: 1px solid var(--color-border);
  cursor: pointer;
  transition: all var(--motion-fast) var(--ease-standard);
}

.user-pill:hover {
  background: var(--color-surface-container);
  color: var(--color-ink);
}

.user-pill span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.site-nav-link,
.drawer-link {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  min-height: 2.45rem;
  padding: 0.55rem 0.85rem;
  border-radius: var(--radius-pill);
  color: var(--color-ink-soft);
  text-decoration: none;
  font-size: 0.88rem;
  font-weight: 600;
  white-space: nowrap;
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


.user-dropdown-wrap {
  position: relative;
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

/* ================================================================
   MAIN / FULL-BLEED
   ================================================================ */
.site-main {
  grid-column: 2;
  width: 100%;
  min-width: 0;
  margin: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: var(--space-10);
  overflow: auto;
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
  max-width: none;
}

.logout-button--drawer {
  width: 100%;
  min-height: 2.9rem;
  padding: 0.65rem 1rem;
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-ink-soft);
  box-shadow: none;
  font-size: var(--text-sm);
}

.logout-button--drawer:hover {
  background: var(--color-surface-container);
  color: var(--color-ink);
  box-shadow: var(--elev-ring);
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
  .shell-layout.has-sidebar {
    display: flex;
    overflow: visible;
  }

  .app-sidebar {
    display: none;
  }

  .site-header {
    padding: 0.65rem clamp(0.85rem, 2vw, 1.35rem) 0;
  }

  .site-header-shell {
    width: min(100%, var(--content-width));
    margin: 0 auto;
    min-height: var(--app-mobile-header-height);
    padding: 0.55rem 0.75rem 0.55rem 0.85rem;
    border: 1px solid var(--color-border);
    border-radius: 22px;
    box-shadow: var(--elev-ring);
  }

  .site-brand {
    display: inline-flex;
  }

  .site-section-title {
    display: none;
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

@media (max-width: 760px) {
  .mobile-nav-toggle {
    display: inline-flex;
  }
}

@media (max-width: 640px) {
  .site-header-shell {
    gap: 0.7rem;
    min-height: 4rem;
  }

  .brand-copy span {
    display: none;
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

  .mobile-nav-toggle {
    width: 2.75rem;
    height: 2.75rem;
  }

  .mobile-drawer {
    padding: 0.95rem;
  }
}
</style>
