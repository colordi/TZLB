<script setup>
import { RouterLink } from "vue-router";

import { DESIGN_NAV_GROUPS, DESIGN_PREVIEW_PROFILE } from "../../fixtures/design/navigation.js";

defineEmits(["close"]);
</script>

<template>
  <aside class="design-app-sidebar" aria-label="设计预览导航">
    <div class="design-app-brand-row">
      <RouterLink class="design-app-brand" to="/design/overview" @click="$emit('close')">
        <span class="design-app-brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
            <path d="M12 3 7 10h3l-4 6h5v5h2v-5h5l-4-6h3Z" />
          </svg>
        </span>
        <span class="design-app-brand-copy">
          <strong>林业调查工作台</strong>
          <span>FORESTRY SURVEY WORKBENCH</span>
        </span>
      </RouterLink>
      <button
        class="design-icon-button design-app-sidebar-close"
        type="button"
        aria-label="关闭菜单"
        @click="$emit('close')"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="m6 6 12 12M18 6 6 18" />
        </svg>
      </button>
    </div>

    <template v-for="group in DESIGN_NAV_GROUPS" :key="group.label">
      <div class="design-app-side-caption">{{ group.label }}</div>
      <nav class="design-app-side-nav" :aria-label="group.label">
        <template v-for="item in group.items" :key="item.key">
          <RouterLink
            v-if="item.to"
            :to="item.to"
            class="design-app-nav-item"
            :data-testid="`design-nav-${item.key}`"
            @click="$emit('close')"
          >
            <svg
              v-if="item.icon === 'overview'"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.7"
              aria-hidden="true"
            >
              <path d="M4 13h6V4H4Zm10 7h6v-9h-6ZM4 20h6v-3H4Zm10-13h6V4h-6Z" />
            </svg>
            <svg
              v-else-if="item.icon === 'workorder'"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.7"
              aria-hidden="true"
            >
              <path d="M7 3h10v4H7zM5 5H4v16h16V5h-1M8 12h8M8 16h5" />
            </svg>
            <svg
              v-else
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.7"
              aria-hidden="true"
            >
              <path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3Z" />
              <path d="M9 3v15m6-12v15" />
            </svg>
            <span>{{ item.label }}</span>
            <span v-if="item.count" class="design-app-nav-count">{{ item.count }}</span>
          </RouterLink>

          <span
            v-else
            class="design-app-nav-item is-placeholder"
            :data-testid="`design-nav-${item.key}`"
            aria-disabled="true"
          >
            <svg
              v-if="item.icon === 'analytics'"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.7"
              aria-hidden="true"
            >
              <path d="M4 19V9m5 10V5m5 14v-7m5 7V3" />
            </svg>
            <svg
              v-else
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.7"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="3" />
              <path
                d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H3v-4h.1a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3A1.7 1.7 0 0 0 10 3V3h4v.1a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9A1.7 1.7 0 0 0 21 10h.1v4H21a1.7 1.7 0 0 0-1.6 1Z"
              />
            </svg>
            <span>{{ item.label }}</span>
            <span class="design-app-placeholder-label">后续</span>
          </span>
        </template>
      </nav>
    </template>

    <div class="design-app-sidebar-foot">
      <div class="design-app-profile">
        <span class="design-app-avatar">{{ DESIGN_PREVIEW_PROFILE.initial }}</span>
        <span>
          <strong>{{ DESIGN_PREVIEW_PROFILE.name }}</strong>
          <span>{{ DESIGN_PREVIEW_PROFILE.role }}</span>
        </span>
      </div>
    </div>
  </aside>
</template>
