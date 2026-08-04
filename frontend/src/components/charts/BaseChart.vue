<script setup>
/**
 * 图表统一出口：所有 ECharts 图表经由此组件渲染（色值走 chart-palette.js，
 * option 由纯函数构建器给出）。测试环境中可被 stub，避免 jsdom 无 canvas 的问题。
 */
import VChart from "vue-echarts";
import "./echarts.js";

defineProps({
  option: {
    type: Object,
    required: true,
  },
  height: {
    type: String,
    default: "320px",
  },
  loading: {
    type: Boolean,
    default: false,
  },
});
</script>

<template>
  <VChart
    class="w-full overflow-hidden"
    :style="{ height }"
    :option="option"
    :loading="loading"
    autoresize
    data-testid="base-chart"
  />
</template>
