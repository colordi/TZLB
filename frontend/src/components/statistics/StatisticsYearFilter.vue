<script setup>
import { NativeSelect } from "@/components/ui/native-select";

const props = defineProps({
  modelValue: {
    type: Number,
    required: true,
  },
  yearOptions: {
    type: Array,
    required: true,
  },
  testid: {
    type: String,
    default: "data-statistics-year-filter",
  },
});

const emit = defineEmits(["update:modelValue"]);

function handleYearChange(event) {
  emit("update:modelValue", Number(event.target.value));
}
</script>

<template>
  <div class="flex items-center justify-end" aria-label="统计年份">
    <label class="flex items-center gap-2 text-sm text-muted-foreground">
      <span>统计年份</span>
      <NativeSelect
        :model-value="String(props.modelValue)"
        class="h-8 py-1"
        :data-testid="props.testid"
        @change="handleYearChange"
      >
        <option v-for="year in props.yearOptions" :key="year" :value="year">
          {{ year }}
        </option>
      </NativeSelect>
    </label>
  </div>
</template>
