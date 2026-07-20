<script setup>
import { cn } from "@/lib/utils"

const props = defineProps({
  class: {
    type: [Boolean, null, String, Object, Array],
    required: false,
    skipCheck: true,
  },
})
</script>

<template>
  <ul
    data-slot="sidebar-menu"
    data-sidebar="menu"
    :class="cn('flex w-full min-w-0 list-none flex-col gap-1 p-0', props.class)"
  >
    <slot />
  </ul>
</template>
