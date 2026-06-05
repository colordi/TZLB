<script setup>
defineProps({
  stats: {
    type: Array,
    required: true,
  },
});
</script>

<template>
  <section class="design-workorder-stats" aria-label="工单统计">
    <article
      v-for="stat in stats"
      :key="stat.key"
      class="design-workorder-stat"
      :class="`is-${stat.tone}`"
    >
      <span>{{ stat.label }}</span>
      <strong class="design-num">{{ stat.value }}</strong>
      <small>{{ stat.description }}</small>
    </article>
  </section>
</template>
