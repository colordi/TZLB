<script setup>
import { Filter, Search, X } from "@lucide/vue";
import { nextTick, ref } from "vue";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

defineProps({
  isSearchPanelOpen: { type: Boolean, default: false },
  searchQuery: { type: String, default: "" },
  showSearchResults: { type: Boolean, default: false },
  searchResults: { type: Array, default: () => [] },
  loadingSearchIndex: { type: Boolean, default: false },
  loadingViews: { type: Boolean, default: false },
  selectedView: { type: String, default: "" },
  supportsSurveyStatusFilter: { type: Boolean, default: false },
  isSurveyStatusFilterOpen: { type: Boolean, default: false },
  surveyStatusFilter: { type: String, default: "all" },
  loadingFilterOptions: { type: Boolean, default: false },
});

const emit = defineEmits([
  "toggle-search",
  "toggle-survey-status",
  "update:searchQuery",
  "update:searchFocused",
  "submit-search",
  "clear-search",
  "select-result",
]);

const searchInputRef = ref(null);

async function focusSearchInput() {
  await nextTick();
  const searchInputEl = searchInputRef.value?.$el ?? searchInputRef.value;
  searchInputEl?.focus?.({ preventScroll: true });
}

defineExpose({ focusSearchInput });
</script>

<template>
  <section class="map-search-panel" aria-label="地图点位搜索">
    <div
      class="map-control-stack rounded-xl border bg-card/95 shadow-md backdrop-blur"
      aria-label="地图快捷工具"
    >
      <Button
        type="button"
        variant="ghost"
        size="icon"
        class="map-control-icon-button"
        :class="{ 'is-active': isSearchPanelOpen || searchQuery }"
        data-testid="map-search-toggle"
        aria-label="搜索点位"
        aria-controls="map-search-popover"
        :aria-expanded="isSearchPanelOpen"
        :disabled="loadingViews || !selectedView"
        @click="emit('toggle-search')"
      >
        <Search aria-hidden="true" />
        <span
          v-if="searchQuery"
          class="map-control-icon-dot"
          aria-hidden="true"
        ></span>
      </Button>
      <Button
        v-if="supportsSurveyStatusFilter"
        type="button"
        variant="ghost"
        size="icon"
        class="map-control-icon-button"
        :class="{
          'is-active': isSurveyStatusFilterOpen || surveyStatusFilter !== 'all',
        }"
        data-testid="map-survey-status-toggle"
        aria-label="调查状态筛选"
        aria-controls="map-survey-status-filter"
        :aria-expanded="isSurveyStatusFilterOpen"
        :disabled="loadingViews || loadingFilterOptions"
        @click="emit('toggle-survey-status')"
      >
        <Filter aria-hidden="true" />
        <span
          v-if="surveyStatusFilter !== 'all'"
          class="map-control-icon-dot"
          aria-hidden="true"
        ></span>
      </Button>
    </div>

    <div class="map-panel-popovers">
      <div
        v-if="isSearchPanelOpen"
        id="map-search-popover"
        class="map-search-popover"
        data-testid="map-search-popover"
      >
        <form
          class="map-search-form rounded-xl border bg-card/95 shadow-md backdrop-blur"
          @submit.prevent="emit('submit-search')"
        >
          <Search :size="16" class="ml-1 shrink-0 text-muted-foreground" aria-hidden="true" />
          <Input
            ref="searchInputRef"
            :model-value="searchQuery"
            data-testid="map-search-input"
            type="text"
            autocomplete="off"
            enterkeyhint="search"
            aria-label="搜索编号、点位名称、属地"
            placeholder="搜索编号、点位名称、属地"
            :disabled="loadingViews || !selectedView"
            @focus="emit('update:searchFocused', true)"
            @update:model-value="emit('update:searchQuery', $event)"
          />
          <Button
            v-if="searchQuery"
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label="清空搜索"
            @click="emit('clear-search')"
          >
            <X aria-hidden="true" />
          </Button>
          <Button
            type="submit"
            size="sm"
            class="map-search-submit"
            :disabled="!`${searchQuery || ''}`.trim()"
          >
            搜索
          </Button>
        </form>

        <div
          v-if="showSearchResults"
          class="map-search-results rounded-xl border bg-card/95 shadow-md backdrop-blur"
          data-testid="map-search-results"
        >
          <Button
            v-for="result in searchResults"
            :key="result.key"
            type="button"
            variant="ghost"
            class="map-search-result"
            :data-testid="`map-search-result-${result.key}`"
            @mousedown.prevent="emit('select-result', result)"
          >
            <strong>{{ result.title }}</strong>
            <span>{{ result.meta || "当前视图点位" }}</span>
          </Button>
          <div
            v-if="searchResults.length === 0 && loadingSearchIndex"
            class="px-3 py-4 text-center text-xs text-muted-foreground"
          >
            正在加载点位…
          </div>
          <div
            v-else-if="searchResults.length === 0"
            class="px-3 py-4 text-center text-xs text-muted-foreground"
          >
            未找到匹配点位
          </div>
        </div>
      </div>

      <slot name="filters" />
    </div>
  </section>
</template>
