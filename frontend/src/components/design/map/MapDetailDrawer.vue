<script setup>
defineProps({
  point: {
    type: Object,
    default: null,
  },
  open: {
    type: Boolean,
    default: false,
  },
});

defineEmits(["close"]);
</script>

<template>
  <aside
    v-if="point"
    class="design-map-detail-drawer"
    :class="{ 'is-open': open }"
    aria-label="点位详情"
    data-testid="design-map-detail-drawer"
  >
    <header class="design-map-detail-head">
      <div>
        <span class="design-map-status-badge" :class="`is-${point.statusClass}`">
          {{ point.status }}
        </span>
        <h2>{{ point.title }}</h2>
        <p>{{ point.code }}</p>
      </div>
      <button
        class="design-icon-button design-map-detail-close"
        type="button"
        aria-label="关闭点位详情"
        data-testid="design-map-detail-close"
        @click="$emit('close')"
      >
        ×
      </button>
    </header>

    <div class="design-map-detail-body">
      <section class="design-map-detail-section" aria-label="点位信息">
        <div class="design-map-detail-grid">
          <div>
            <span>所属区县</span>
            <strong>{{ point.district }}</strong>
          </div>
          <div>
            <span>危害等级</span>
            <strong>{{ point.level }}</strong>
          </div>
          <div>
            <span>主要虫害</span>
            <strong>{{ point.pest }}</strong>
          </div>
          <div>
            <span>寄主树种</span>
            <strong>{{ point.host }}</strong>
          </div>
          <div>
            <span>发现数量</span>
            <strong>{{ point.count }}</strong>
          </div>
          <div>
            <span>现场附件</span>
            <strong>{{ point.files }}</strong>
          </div>
        </div>
      </section>

      <section class="design-map-detail-section">
        <h3>调查结论</h3>
        <p class="design-map-detail-conclusion">{{ point.conclusion }}</p>
      </section>

      <section class="design-map-detail-section">
        <h3>处置时间线</h3>
        <ol class="design-map-timeline">
          <li v-for="item in point.timeline" :key="`${point.id}-${item.time}-${item.title}`">
            <time>{{ item.time }}</time>
            <div>
              <strong>{{ item.title }}</strong>
              <p>{{ item.body }}</p>
            </div>
          </li>
        </ol>
      </section>
    </div>
  </aside>
</template>
