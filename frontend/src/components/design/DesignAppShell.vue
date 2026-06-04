<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import DesignSidebar from "./DesignSidebar.vue";
import "../../styles/design-app-shell.css";

const route = useRoute();
const mobileMenuOpen = ref(false);

function closeMobileMenu() {
  mobileMenuOpen.value = false;
}

function handleKeydown(event) {
  if (event.key === "Escape") {
    closeMobileMenu();
  }
}

watch(
  () => route.fullPath,
  () => closeMobileMenu(),
);

onMounted(() => window.addEventListener("keydown", handleKeydown));
onBeforeUnmount(() => window.removeEventListener("keydown", handleKeydown));
</script>

<template>
  <div class="design-app-shell">
    <DesignSidebar :class="{ 'is-mobile-open': mobileMenuOpen }" @close="closeMobileMenu" />

    <button
      v-if="mobileMenuOpen"
      class="design-app-sidebar-backdrop"
      type="button"
      aria-label="关闭菜单"
      data-testid="design-sidebar-backdrop"
      @click="closeMobileMenu"
    ></button>

    <main class="design-app-main-shell">
      <header class="design-app-topbar">
        <button
          class="design-icon-button design-app-mobile-menu"
          type="button"
          aria-label="打开菜单"
          data-testid="design-mobile-menu"
          :aria-expanded="mobileMenuOpen"
          @click="mobileMenuOpen = true"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M4 7h16M4 12h16M4 17h16" />
          </svg>
        </button>

        <div class="design-app-breadcrumb">
          <span>设计预览</span>
          <span>/</span>
          <strong>{{ route.meta.previewPage || "工作界面" }}</strong>
        </div>

        <div class="design-app-topbar-actions">
          <span class="design-app-preview-badge">STATIC PREVIEW</span>
          <RouterLink class="design-app-status-link" to="/design">迁移状态</RouterLink>
        </div>
      </header>

      <div class="design-app-content">
        <slot />
      </div>
    </main>
  </div>
</template>
