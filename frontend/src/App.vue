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
      <div class="site-brand">
        <p class="site-kicker">Tongzhou Forestry Survey</p>
        <h1>林业调查工作台</h1>
        <p class="site-summary">工作单生成与地图监测一体化平台</p>
      </div>

      <aside class="site-context">
        <p class="context-label">当前模块</p>
        <h2>{{ pageMeta.section }}</h2>
        <p v-if="pageMeta.blurb">{{ pageMeta.blurb }}</p>
      </aside>
    </header>

    <nav class="site-nav">
      <div class="nav-track">
        <RouterLink to="/workorder" class="nav-link">
          工作单批量生成
        </RouterLink>
        <RouterLink to="/map" class="nav-link">
          调查点位展示
        </RouterLink>
      </div>
    </nav>

    <main class="site-main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  max-width: var(--content-width);
  margin: 0 auto;
  padding: 1.4rem clamp(1rem, 2.8vw, 2rem) 2.4rem;
}

.site-header {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(300px, 0.85fr);
  gap: 0.9rem;
  align-items: start;
  margin-bottom: 0.8rem;
}

.site-brand,
.site-context {
  padding: 1.3rem 1.45rem;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-lg);
  background: var(--surface-base);
  box-shadow: var(--shadow-card);
}

.site-kicker {
  margin: 0;
  font-size: 0.72rem;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: var(--muted-soft);
}

.site-brand h1 {
  margin: 0.4rem 0 0;
  font-size: clamp(2.15rem, 4vw, 3.9rem);
  line-height: 1.04;
}

.site-summary,
.site-context p {
  color: var(--muted);
  line-height: 1.65;
}

.site-summary {
  margin-top: 0.6rem;
}

.site-context {
  display: grid;
  gap: 0.35rem;
  align-content: start;
  min-height: 100%;
}

.context-label {
  font-size: 0.72rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--muted-soft);
}

.site-context h2 {
  font-size: clamp(1.3rem, 2vw, 1.7rem);
  line-height: 1.2;
}

.site-nav {
  margin-bottom: 1rem;
}

.nav-track {
  display: inline-grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.35rem;
  padding: 0.35rem;
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  background: rgba(249, 245, 237, 0.78);
  box-shadow: var(--shadow-soft);
}

.nav-link {
  padding: 0.75rem 1.15rem;
  border-radius: 999px;
  color: var(--ink);
  text-decoration: none;
  font-weight: 600;
  text-align: center;
  transition:
    background-color 160ms ease,
    color 160ms ease,
    box-shadow 160ms ease;
}

.nav-link:hover {
  background: rgba(255, 252, 246, 0.92);
}

.nav-link.router-link-active {
  background: var(--accent);
  color: #f8f5ee;
  box-shadow: 0 8px 18px rgba(65, 83, 50, 0.16);
}

.site-main {
  display: grid;
}

@media (max-width: 920px) {
  .site-header {
    grid-template-columns: 1fr;
  }

  .site-context {
    min-height: auto;
  }
}

@media (max-width: 640px) {
  .app-shell {
    padding: 1rem 0.85rem 1.8rem;
  }

  .site-brand,
  .site-context {
    padding: 1.1rem 1rem;
  }

  .site-brand h1 {
    font-size: 2rem;
  }

  .nav-track {
    width: 100%;
  }
}
</style>
