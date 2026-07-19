<script setup>
import { parseDate } from "@internationalized/date";
import { computed } from "vue";

import { Calendar } from "@/components/ui/calendar";
import { cn } from "@/lib/utils";

const props = defineProps({
  modelValue: {
    type: String,
    default: "",
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  id: {
    type: String,
    default: undefined,
  },
  class: {
    type: [String, Object, Array],
    default: undefined,
  },
});

const emit = defineEmits(["update:modelValue"]);

function toCalendarDate(value) {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return undefined;
  }
  try {
    return parseDate(value);
  } catch {
    return undefined;
  }
}

function toIsoString(value) {
  if (!value) {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  const month = String(value.month).padStart(2, "0");
  const day = String(value.day).padStart(2, "0");
  return `${value.year}-${month}-${day}`;
}

const calendarValue = computed({
  get() {
    return toCalendarDate(props.modelValue);
  },
  set(next) {
    emit("update:modelValue", toIsoString(next));
  },
});

const displayLabel = computed(() => {
  if (!props.modelValue) {
    return "未选择";
  }
  const [year, month, day] = props.modelValue.split("-");
  if (!year || !month || !day) {
    return props.modelValue;
  }
  return `${year}-${month}-${day}`;
});
</script>

<template>
  <div
    :id="id"
    data-testid="date-picker-inline"
    :class="
      cn(
        'inline-calendar w-full',
        disabled && 'pointer-events-none opacity-50',
        props.class,
      )
    "
  >
    <Calendar
      v-model="calendarValue"
      locale="zh-CN"
      weekday-format="narrow"
      :fixed-weeks="true"
      :disabled="disabled"
      class="p-0"
    />
    <p
      class="mt-2 border-t border-border/50 pt-2 text-center text-[12px] leading-5 text-muted-foreground"
      data-testid="date-picker-value"
    >
      {{ displayLabel }}
    </p>
  </div>
</template>
