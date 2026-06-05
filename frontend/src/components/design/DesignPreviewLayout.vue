<script setup>
import { computed } from "vue";
import { RouterView } from "vue-router";
import { useRoute } from "vue-router";

import DesignAppShell from "./DesignAppShell.vue";

const route = useRoute();
const useAppShell = computed(() => Boolean(route.meta.previewShell));
</script>

<template>
  <div class="design-preview-root">
    <DesignAppShell v-if="useAppShell">
      <RouterView />
    </DesignAppShell>
    <RouterView v-else />
  </div>
</template>

<style src="../../styles/design-preview.css"></style>
