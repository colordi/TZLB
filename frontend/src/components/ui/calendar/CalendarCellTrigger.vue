<script setup>
import { reactiveOmit } from "@vueuse/core";
import { CalendarCellTrigger, useForwardProps } from "reka-ui";
import { cn } from "@/lib/utils";

const props = defineProps({
  day: { type: Object, required: true },
  month: { type: Object, required: true },
  asChild: { type: Boolean, required: false },
  as: { type: null, required: false, default: "button" },
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
  <CalendarCellTrigger
    data-slot="calendar-cell-trigger"
    :class="
      cn(
        // Notion 风日期格：轻 hover、主题色选中、「今天」用小圆点标记
        'relative inline-flex size-7 cursor-pointer items-center justify-center rounded-md border-0 bg-transparent p-0 text-[13px] leading-none text-foreground/90 transition-colors duration-75',
        'hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/25',
        // Today：主题色文字 + 底部小圆点
        '[&[data-today]:not([data-selected])]:font-semibold [&[data-today]:not([data-selected])]:text-primary',
        '[&[data-today]:not([data-selected])]:after:absolute [&[data-today]:not([data-selected])]:after:bottom-[3px] [&[data-today]:not([data-selected])]:after:size-[3px] [&[data-today]:not([data-selected])]:after:rounded-full [&[data-today]:not([data-selected])]:after:bg-primary',
        // Selected
        'data-[selected]:bg-primary data-[selected]:font-medium data-[selected]:text-primary-foreground',
        'data-[selected]:hover:bg-primary data-[selected]:focus:bg-primary',
        // Outside / disabled
        'data-[outside-view]:text-muted-foreground/40',
        'data-[disabled]:text-muted-foreground/30 data-[disabled]:hover:bg-transparent',
        'data-[unavailable]:text-destructive data-[unavailable]:line-through',
        props.class,
      )
    "
    v-bind="forwardedProps"
  >
    <slot />
  </CalendarCellTrigger>
</template>
