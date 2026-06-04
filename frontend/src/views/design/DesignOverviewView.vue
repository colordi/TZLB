<script setup>
import { RouterLink } from "vue-router";

import { DESIGN_OVERVIEW_ENTRIES } from "../../fixtures/design/overviewEntries.js";
import "../../styles/design-overview.css";
</script>

<template>
  <div class="design-overview-page">
    <main class="design-overview-main">
      <section class="design-overview-container" aria-labelledby="design-overview-title">
        <div class="design-overview-intro">
          <div>
            <p class="design-overview-eyebrow">统一调查数据与地图点位</p>
            <h1 id="design-overview-title">选择要进入的工作界面。</h1>
          </div>
          <p>
            从调查点位地图掌握区域风险，或进入工单录入完成现场记录、附件整理与标准化
            Word 导出。
          </p>
        </div>

        <div class="design-overview-grid">
          <RouterLink
            v-for="entry in DESIGN_OVERVIEW_ENTRIES"
            :key="entry.key"
            :to="entry.to"
            class="design-overview-card"
            :class="{ 'is-primary': entry.primary }"
            :data-testid="`design-overview-entry-${entry.key}`"
          >
            <span class="design-overview-card-icon" aria-hidden="true">
              <svg
                v-if="entry.key === 'map'"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.7"
              >
                <path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3Z" />
                <path d="M9 3v15m6-12v15" />
              </svg>
              <svg
                v-else
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.7"
              >
                <path d="M7 3h10v4H7zM5 5H4v16h16V5h-1M8 12h8M8 16h5" />
              </svg>
            </span>
            <h2>{{ entry.title }}</h2>
            <p>{{ entry.description }}</p>
            <span class="design-overview-card-meta">
              <span>{{ entry.eyebrow }}</span>
              <span>{{ entry.action }} →</span>
            </span>
          </RouterLink>
        </div>
      </section>
    </main>

    <footer class="design-overview-foot">
      <div class="design-overview-container">
        数据分级保护 · 操作全程留痕 · 北京市林业有害生物调查系统
      </div>
    </footer>
  </div>
</template>
