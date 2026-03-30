<script setup>
import { computed } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";

const route = useRoute();

const pageMeta = computed(() => ({
  section: route.meta?.section || "林业调查工作台",
  blurb: route.meta?.blurb ?? "工作单生成与地图监测一体化控制台。",
}));
</script>

<template>
  <div class="app-shell">
    <header class="site-header">
      <div class="header-brand">
        <span class="brand-icon">🌲</span>
        <span class="brand-title">林业调查工作台</span>
      </div>

      <nav class="header-nav">
        <RouterLink to="/workorder" class="nav-link">
          工单录入
        </RouterLink>
        <RouterLink to="/map" class="nav-link">
          调查点位展示
        </RouterLink>
      </nav>

      <div class="header-actions">
        <span class="page-title">{{ pageMeta.section }}</span>
      </div>
    </header>

    <main class="site-main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.site-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid var(--border);
  background: var(--surface-base);
  box-shadow: var(--shadow-soft);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.brand-icon {
  font-size: 1.25rem;
}

.brand-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--ink);
}

.header-nav {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg);
}

.nav-link {
  padding: 0.5rem 1rem;
  border-radius: calc(var(--radius-sm) - 1px);
  color: var(--muted);
  text-decoration: none;
  font-weight: 500;
  font-size: 0.875rem;
  transition: all 150ms ease;
}

.nav-link:hover {
  color: var(--ink);
  background: var(--surface-muted);
}

.nav-link.router-link-active {
  background: var(--surface-base);
  color: var(--accent);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-shrink: 0;
}

.page-title {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--muted);
}

.site-main {
  flex: 1;
  padding: 1rem 1.5rem 1.5rem;
  display: flex;
  flex-direction: column;
}

@media (max-width: 768px) {
  .site-header {
    padding: 0.625rem 1rem;
  }

  .brand-title {
    display: none;
  }

  .nav-link {
    padding: 0.5rem 0.75rem;
    font-size: 0.8125rem;
  }

  .page-title {
    display: none;
  }

  .site-main {
    padding: 0.75rem 1rem 1rem;
  }
}
</style>
