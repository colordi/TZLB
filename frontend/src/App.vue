<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";

import ToastViewport from "./components/ui/ToastViewport.vue";
import { useAuthSession } from "./composables/useAuthSession.js";
import { useToast } from "./composables/useToast.js";

const route = useRoute();
const router = useRouter();
const mobileNavOpen = ref(false);
const hideShell = computed(() => Boolean(route.meta?.hideShell));
const loggingOut = ref(false);
const { user, signOut } = useAuthSession();
const { error, info } = useToast();

const currentUserName = computed(() => user.value?.display_name || user.value?.username || "");

const navItems = [
  {
    to: "/workorder",
    label: "工单录入",
    icon: "upload",
  },
  {
    to: "/map",
    label: "调查点位",
    icon: "pin",
  },
];

function closeMobileNav() {
  mobileNavOpen.value = false;
}

function toggleMobileNav() {
  mobileNavOpen.value = !mobileNavOpen.value;
}

function handleWindowKeydown(event) {
  if (event.key === "Escape") {
    closeMobileNav();
  }
}

async function handleLogout() {
  if (loggingOut.value) {
    return;
  }

  loggingOut.value = true;
  try {
    await signOut();
    closeMobileNav();
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
  },
);

watch(mobileNavOpen, (open) => {
  if (typeof document !== "undefined") {
    document.body.style.overflow = open ? "hidden" : "";
  }
});

onMounted(() => {
  window.addEventListener("keydown", handleWindowKeydown);
});

onBeforeUnmount(() => {
  if (typeof document !== "undefined") {
    document.body.style.overflow = "";
  }
  window.removeEventListener("keydown", handleWindowKeydown);
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
      <header v-if="!hideShell" class="site-header">
        <div class="site-header-shell">
          <RouterLink to="/workorder" class="site-brand">
            <div class="brand-icon-card" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                <path
                  d="M12 3.25 7.75 9h1.7l-2.85 4h2.14l-1.64 4.75h9.8L15.27 13h2.14l-2.85-4h1.69L12 3.25Zm0 2.62 1.7 2.28h-1.15l2.84 4h-1.9l1.16 3.35h-5.3l1.16-3.35H8.61l2.84-4h-1.15L12 5.87Z"
                />
              </svg>
            </div>

            <div class="brand-copy">
              <strong>林业调查工作台</strong>
              <span>Forest Survey Workbench</span>
            </div>
          </RouterLink>

          <nav class="site-nav" aria-label="主导航">
            <RouterLink
              v-for="item in navItems"
              :key="item.to"
              :to="item.to"
              class="site-nav-link"
              :data-testid="`header-link-${item.to.slice(1)}`"
            >
              <svg v-if="item.icon === 'upload'" viewBox="0 0 24 24" aria-hidden="true">
                <path
                  d="M12 3.5a.75.75 0 0 1 .75.75v8.19l2.72-2.72a.75.75 0 1 1 1.06 1.06l-4 4a.75.75 0 0 1-1.06 0l-4-4a.75.75 0 0 1 1.06-1.06l2.72 2.72V4.25A.75.75 0 0 1 12 3.5ZM5.25 15A.75.75 0 0 1 6 15.75v1.5c0 .41.34.75.75.75h10.5a.75.75 0 0 0 .75-.75v-1.5a.75.75 0 0 1 1.5 0v1.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 17.25v-1.5a.75.75 0 0 1 .75-.75Z"
                />
              </svg>
              <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                <path
                  d="M12 2.75A7.25 7.25 0 0 0 4.75 10c0 5.02 5.8 10.39 6.05 10.61a1.8 1.8 0 0 0 2.4 0c.25-.22 6.05-5.59 6.05-10.61A7.25 7.25 0 0 0 12 2.75Zm0 16.52C10.5 17.76 6.25 13.4 6.25 10a5.75 5.75 0 1 1 11.5 0c0 3.4-4.25 7.76-5.75 9.27Zm0-12.52A3.25 3.25 0 1 0 15.25 10 3.25 3.25 0 0 0 12 6.75Zm0 5A1.75 1.75 0 1 1 13.75 10 1.75 1.75 0 0 1 12 11.75Z"
                />
              </svg>
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
                <svg viewBox="0 0 24 24">
                  <path
                    d="M12 3.25 7.75 9h1.7l-2.85 4h2.14l-1.64 4.75h9.8L15.27 13h2.14l-2.85-4h1.69L12 3.25Zm0 2.62 1.7 2.28h-1.15l2.84 4h-1.9l1.16 3.35h-5.3l1.16-3.35H8.61l2.84-4h-1.15L12 5.87Z"
                  />
                </svg>
              </div>

              <div class="brand-copy">
                <strong>林业调查工作台</strong>
                <span>Forest Survey Workbench</span>
              </div>
            </div>

            <nav class="drawer-nav" aria-label="移动端主导航">
              <RouterLink
                v-for="item in navItems"
                :key="`mobile-${item.to}`"
                :to="item.to"
                class="drawer-link"
                :data-testid="`drawer-link-${item.to.slice(1)}`"
              >
                <svg v-if="item.icon === 'upload'" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M12 3.5a.75.75 0 0 1 .75.75v8.19l2.72-2.72a.75.75 0 1 1 1.06 1.06l-4 4a.75.75 0 0 1-1.06 0l-4-4a.75.75 0 0 1 1.06-1.06l2.72 2.72V4.25A.75.75 0 0 1 12 3.5ZM5.25 15A.75.75 0 0 1 6 15.75v1.5c0 .41.34.75.75.75h10.5a.75.75 0 0 0 .75-.75v-1.5a.75.75 0 0 1 1.5 0v1.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 17.25v-1.5a.75.75 0 0 1 .75-.75Z"
                  />
                </svg>
                <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M12 2.75A7.25 7.25 0 0 0 4.75 10c0 5.02 5.8 10.39 6.05 10.61a1.8 1.8 0 0 0 2.4 0c.25-.22 6.05-5.59 6.05-10.61A7.25 7.25 0 0 0 12 2.75Zm0 16.52C10.5 17.76 6.25 13.4 6.25 10a5.75 5.75 0 1 1 11.5 0c0 3.4-4.25 7.76-5.75 9.27Zm0-12.52A3.25 3.25 0 1 0 15.25 10 3.25 3.25 0 0 0 12 6.75Zm0 5A1.75 1.75 0 1 1 13.75 10 1.75 1.75 0 0 1 12 11.75Z"
                  />
                </svg>
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

      <main class="site-main" :class="{ 'is-standalone': hideShell }">
        <RouterView />
      </main>
    </div>

    <ToastViewport />
  </div>
</template>

<style scoped>
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
  background: radial-gradient(circle, rgba(107, 179, 111, 0.26), rgba(107, 179, 111, 0));
}

.orb-right {
  width: 32rem;
  height: 32rem;
  top: 14rem;
  right: -12rem;
  background: radial-gradient(circle, rgba(182, 219, 165, 0.35), rgba(182, 219, 165, 0));
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

.site-header {
  padding: 0.9rem clamp(0.85rem, 2vw, 1.35rem) 0;
}

.site-header-shell {
  width: min(100%, var(--content-width));
  margin: 0 auto;
  min-height: 4.95rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.7rem 0.9rem 0.7rem 1rem;
  border: 1px solid rgba(46, 125, 50, 0.12);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.74);
  box-shadow: 0 20px 42px rgba(18, 52, 29, 0.08);
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
  border-radius: 18px;
  background: linear-gradient(145deg, #63b98d, #2e7d32);
  color: #fff;
  box-shadow: 0 14px 32px rgba(46, 125, 50, 0.24);
}

.brand-icon-card svg {
  width: 1.35rem;
  height: 1.35rem;
  fill: currentColor;
}

.brand-icon-card-compact {
  width: 2.7rem;
  height: 2.7rem;
  border-radius: 16px;
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
  letter-spacing: -0.02em;
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
  border-radius: 999px;
  background: rgba(46, 125, 50, 0.08);
  color: var(--color-primary-strong);
  font-size: 0.88rem;
  font-weight: 700;
}

.logout-button {
  min-height: 2.9rem;
  padding: 0.65rem 1rem;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(46, 125, 50, 0.14);
  color: var(--color-ink-soft);
  box-shadow: none;
}

.logout-button:hover {
  background: #fff;
  color: var(--color-primary-strong);
  box-shadow: 0 12px 24px rgba(18, 52, 29, 0.08);
}

.site-nav-link,
.drawer-link {
  display: inline-flex;
  align-items: center;
  gap: 0.7rem;
  min-height: 3rem;
  padding: 0.72rem 1rem;
  border-radius: 18px;
  color: var(--color-ink-soft);
  text-decoration: none;
  font-weight: 700;
  transition:
    background-color 180ms ease,
    color 180ms ease,
    transform 180ms ease,
    box-shadow 180ms ease;
}

.site-nav-link svg,
.drawer-link svg {
  width: 1.08rem;
  height: 1.08rem;
  fill: currentColor;
  flex-shrink: 0;
}

.site-nav-link:hover,
.drawer-link:hover {
  background: rgba(46, 125, 50, 0.08);
  color: var(--color-primary-strong);
}

.site-nav-link.router-link-active,
.drawer-link.router-link-active {
  color: #fff;
  background: linear-gradient(135deg, #4ea67c, #2e7d32);
  box-shadow: 0 14px 28px rgba(46, 125, 50, 0.2);
}

.mobile-nav-toggle {
  display: none;
  min-height: 0;
  width: 2.9rem;
  height: 2.9rem;
  padding: 0;
  border: 1px solid rgba(46, 125, 50, 0.14);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.9);
  color: var(--color-ink);
  box-shadow: 0 12px 24px rgba(18, 52, 29, 0.08);
  flex-direction: column;
  gap: 0.26rem;
}

.mobile-nav-toggle span {
  width: 1.08rem;
  height: 2px;
  border-radius: 999px;
  background: currentColor;
}

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

.mobile-drawer-overlay {
  position: fixed;
  inset: 0;
  z-index: 180;
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

.drawer-fade-enter-active,
.drawer-fade-leave-active {
  transition: opacity 180ms ease;
}

.drawer-fade-enter-from,
.drawer-fade-leave-to {
  opacity: 0;
}

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
    background: rgba(18, 36, 25, 0.3);
    backdrop-filter: blur(8px);
  }

  .mobile-drawer {
    height: 100vh;
    padding: 1rem;
    background: rgba(255, 255, 255, 0.96);
    box-shadow: 0 24px 54px rgba(18, 52, 29, 0.18);
    display: flex;
    flex-direction: column;
    gap: 1rem;
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
