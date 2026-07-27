<script setup>
import { X } from "@lucide/vue";

import { Button } from "@/components/ui/button";

defineProps({
  featureTitle: { type: String, default: "" },
  featureRows: { type: Array, default: () => [] },
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
      <footer v-if="canDelete" class="detail-footer">
        <Button
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
