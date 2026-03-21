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
    <div class="ambient ambient-one"></div>
    <div class="ambient ambient-two"></div>
    <div class="grain"></div>

    <header class="site-header">
      <div class="site-brand">
        <p class="site-kicker">Tongzhou Forestry Survey</p>
        <h1>林业调查工作台</h1>
      </div>

      <aside class="site-spotlight">
        <span>{{ pageMeta.section }}</span>
        <p v-if="pageMeta.blurb">{{ pageMeta.blurb }}</p>
      </aside>
    </header>

    <nav class="site-nav">
      <RouterLink to="/workorder" class="nav-link">
        工作单批量生成
      </RouterLink>
      <RouterLink to="/map" class="nav-link">
        调查点位展示
      </RouterLink>
    </nav>

    <main class="site-main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  position: relative;
  max-width: 1440px;
  margin: 0 auto;
  padding: 2rem clamp(1rem, 3vw, 2rem) 3rem;
}

.ambient {
  position: fixed;
  inset: auto;
  z-index: 0;
  border-radius: 999px;
  filter: blur(80px);
  opacity: 0.35;
  pointer-events: none;
}

.ambient-one {
  top: -7rem;
  right: 4rem;
  width: 18rem;
  height: 18rem;
  background: rgba(145, 168, 97, 0.46);
}

.ambient-two {
  bottom: 6rem;
  left: -3rem;
  width: 15rem;
  height: 15rem;
  background: rgba(188, 118, 68, 0.3);
}

.grain {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  opacity: 0.12;
  background-image:
    linear-gradient(rgba(14, 16, 12, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(14, 16, 12, 0.05) 1px, transparent 1px);
  background-size: 90px 90px;
  mask-image: radial-gradient(circle at center, rgba(0, 0, 0, 0.9), transparent 85%);
}

.site-header,
.site-nav,
.site-main {
  position: relative;
  z-index: 1;
}

.site-header {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(280px, 0.8fr);
  gap: 1rem;
  align-items: stretch;
}

.site-brand,
.site-spotlight {
  padding: 1.5rem;
  border-radius: 1.7rem;
  border: 1px solid rgba(53, 67, 48, 0.12);
  background:
    linear-gradient(135deg, rgba(248, 244, 232, 0.96), rgba(238, 233, 214, 0.92));
  box-shadow: var(--panel-shadow);
}

.site-kicker {
  margin: 0;
  font-size: 0.78rem;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: var(--accent);
}

.site-brand h1 {
  margin: 0.3rem 0 0;
  font-size: clamp(2.4rem, 4vw, 4.4rem);
}

.site-description,
.site-spotlight p {
  margin: 0;
  color: var(--muted);
  line-height: 1.75;
}

.site-spotlight {
  display: grid;
  align-content: center;
  gap: 0.4rem;
}

.site-spotlight span {
  font-size: clamp(1.15rem, 2vw, 1.55rem);
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--ink);
}

.site-nav {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin: 1rem 0 1.2rem;
}

.nav-link {
  padding: 0.8rem 1.2rem;
  border-radius: 999px;
  border: 1px solid rgba(53, 67, 48, 0.12);
  background: rgba(251, 248, 240, 0.82);
  color: var(--ink);
  text-decoration: none;
  font-weight: 600;
  transition: transform 180ms ease, background 180ms ease, box-shadow 180ms ease;
}

.nav-link:hover {
  transform: translateY(-1px);
  background: rgba(248, 244, 232, 0.96);
  box-shadow: 0 12px 28px rgba(33, 39, 26, 0.08);
}

.nav-link.router-link-active {
  background: linear-gradient(135deg, rgba(53, 67, 48, 0.92), rgba(84, 101, 68, 0.9));
  color: #f8f5ee;
  box-shadow: 0 18px 34px rgba(33, 39, 26, 0.16);
}

.site-main {
  display: grid;
}

@media (max-width: 920px) {
  .site-header {
    grid-template-columns: 1fr;
  }
}
</style>
