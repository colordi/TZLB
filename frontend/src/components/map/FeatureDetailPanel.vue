<script setup>
import { Navigation, X } from "@lucide/vue";

import { Button } from "@/components/ui/button";

defineProps({
  featureTitle: { type: String, default: "" },
  featureRows: { type: Array, default: () => [] },
  externalMapUrl: { type: String, default: "" },
  canDelete: { type: Boolean, default: false },
  deleteCheckLoading: { type: Boolean, default: false },
});

const emit = defineEmits(["close", "delete"]);
</script>

<template>
  <aside class="detail-drawer">
    <article class="detail-card">
      <header class="detail-header">
        <span class="detail-title">{{ featureTitle || "点位详情" }}</span>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          class="shrink-0 text-muted-foreground"
          aria-label="关闭详情"
          @click="emit('close')"
        >
          <X aria-hidden="true" />
        </Button>
      </header>
      <div class="detail-divider"></div>
      <div class="detail-body">
        <div v-for="[label, value] in featureRows" :key="label" class="detail-row">
          <span class="detail-label">{{ label }}</span>
          <span class="detail-value">{{ value }}</span>
        </div>
      </div>
      <footer v-if="canDelete || externalMapUrl" class="detail-footer">
        <Button
          v-if="externalMapUrl"
          as-child
          variant="outline"
          class="w-full"
        >
          <a
            :href="externalMapUrl"
            target="_blank"
            rel="noopener noreferrer"
            data-testid="external-map-link"
          >
            <Navigation aria-hidden="true" />
            在地图应用中打开
          </a>
        </Button>
        <Button
          v-if="canDelete"
          type="button"
          variant="destructive"
          class="w-full"
          data-testid="site-delete-btn"
          :disabled="deleteCheckLoading"
          @click="emit('delete')"
        >
          {{ deleteCheckLoading ? "检查中…" : "删除点位" }}
        </Button>
      </footer>
    </article>
  </aside>
</template>
