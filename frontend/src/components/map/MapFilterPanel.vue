<script setup>
import { Button } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/native-select";

defineProps({
  visible: { type: Boolean, default: false },
  visibleSurveyStatusOptions: { type: Array, default: () => [] },
  surveyStatusFilter: { type: String, default: "all" },
  loading: { type: Boolean, default: false },
  loadingViews: { type: Boolean, default: false },
  loadingFilterOptions: { type: Boolean, default: false },
  dynamicFilterFields: { type: Array, default: () => [] },
  dynamicFilterValues: { type: Object, default: () => ({}) },
  getSurveyStatusCount: { type: Function, required: true },
});

const emit = defineEmits(["select-survey-status", "select-dynamic-filter"]);
</script>

<template>
  <div
    v-if="visible"
    class="map-survey-status-filter rounded-xl border bg-card/95 shadow-md backdrop-blur"
    data-testid="map-survey-status-filter"
    aria-label="调查状态筛选"
  >
    <div class="map-survey-status-segments" role="group" aria-label="调查状态">
      <Button
        v-for="option in visibleSurveyStatusOptions"
        :key="option.key"
        type="button"
        :variant="surveyStatusFilter === option.key ? 'default' : 'ghost'"
        size="sm"
        class="map-survey-status-option"
        :class="{ 'is-active': surveyStatusFilter === option.key }"
        :data-testid="`map-survey-status-${option.key}`"
        :aria-pressed="surveyStatusFilter === option.key"
        :disabled="loading || loadingViews || loadingFilterOptions"
        @click="emit('select-survey-status', option.key)"
      >
        <span class="map-survey-status-option-text">{{ option.label }}</span>
        <span class="map-survey-status-option-count">
          {{ getSurveyStatusCount(option.key) }}
        </span>
      </Button>
    </div>

    <div
      v-if="dynamicFilterFields.length"
      class="map-dynamic-filters"
      data-testid="map-dynamic-filters"
    >
      <label
        v-for="field in dynamicFilterFields"
        :key="field.key"
        class="map-dynamic-filter"
      >
        <span class="map-dynamic-filter-label">{{ field.label }}</span>
        <NativeSelect
          :model-value="dynamicFilterValues[field.key] || ''"
          :data-testid="`map-filter-${field.key}`"
          :disabled="loading || loadingFilterOptions"
          class="h-8 text-xs"
          @update:model-value="emit('select-dynamic-filter', field.key, $event)"
        >
          <option value="">全部</option>
          <option
            v-for="option in field.options"
            :key="option.value"
            :value="option.value"
          >
            {{ option.label }}
          </option>
        </NativeSelect>
      </label>
    </div>
  </div>
</template>
