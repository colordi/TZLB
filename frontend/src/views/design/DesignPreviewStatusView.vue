<script setup>
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { DESIGN_PREVIEW_STAGES } from "../../fixtures/design/previewStages.js";

const route = useRoute();

const activeStage = computed(
  () =>
    DESIGN_PREVIEW_STAGES.find((stage) => stage.key === route.meta.previewStage) ||
    DESIGN_PREVIEW_STAGES[0],
);
</script>

<template>
  <main class="design-status-page">
    <section class="design-status-panel">
      <header class="design-status-header">
        <div>
          <p class="design-status-eyebrow">OPENDESIGN · VUE MIGRATION</p>
          <h1>{{ route.meta.previewPage }}</h1>
          <p>{{ activeStage.description }}</p>
        </div>
        <span class="design-status-badge" :class="{ 'is-ready': activeStage.ready }">
          {{ activeStage.ready ? "基础已就绪" : "等待迁移" }}
        </span>
      </header>

      <nav class="design-status-nav" aria-label="设计预览迁移阶段">
        <RouterLink
          v-for="stage in DESIGN_PREVIEW_STAGES"
          :key="stage.key"
          :to="stage.to"
          class="design-status-link"
        >
          <span class="design-status-index">{{ stage.index }}</span>
          <span>
            <strong>{{ stage.label }}</strong>
            <small>{{ stage.ready ? "可检查" : "尚未开始" }}</small>
          </span>
        </RouterLink>
      </nav>

      <footer class="design-status-foot">
        <span>当前仅建立隔离预览基础，不连接真实 API。</span>
        <RouterLink to="/design">查看迁移状态</RouterLink>
      </footer>
    </section>
  </main>
</template>
