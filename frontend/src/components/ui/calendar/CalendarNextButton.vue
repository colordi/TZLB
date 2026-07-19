<script setup>
import { ChevronRight } from "@lucide/vue";
import { reactiveOmit } from "@vueuse/core";
import { CalendarNext, useForwardProps } from "reka-ui";
import { cn } from "@/lib/utils";

const props = defineProps({
  nextPage: { type: Function, required: false },
  asChild: { type: Boolean, required: false },
  as: { type: null, required: false },
  class: {
    type: [Boolean, null, String, Object, Array],
    required: false,
    skipCheck: true,
  },
});

const delegatedProps = reactiveOmit(props, "class");
const forwardedProps = useForwardProps(delegatedProps);
</script>

<template>
  <CalendarNext
    data-slot="calendar-next-button"
    :class="
      cn(
        'inline-flex size-6 cursor-pointer items-center justify-center rounded-[5px] border-0 bg-transparent p-0 text-muted-foreground transition-colors duration-75',
        'hover:bg-muted hover:text-foreground',
        props.class,
      )
    "
    v-bind="forwardedProps"
  >
    <slot>
      <ChevronRight class="size-3.5" />
    </slot>
  </CalendarNext>
</template>
