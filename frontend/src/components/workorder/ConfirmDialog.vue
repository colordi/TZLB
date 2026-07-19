<script setup>
import BaseDialog from "./BaseDialog.vue";
import { Button } from "@/components/ui/button";

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  title: {
    type: String,
    default: "请确认",
  },
  message: {
    type: String,
    default: "",
  },
  confirmText: {
    type: String,
    default: "确认删除",
  },
  cancelText: {
    type: String,
    default: "取消",
  },
  busy: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["confirm", "close"]);
</script>

<template>
  <BaseDialog
    :open="open"
    aria-label="操作确认"
    mask-class="confirm-dialog-mask"
    dialog-class="confirm-dialog-content max-w-md"
    @close="emit('close')"
  >
    <header class="modal-header border-b border-border px-5 py-4">
      <h2 class="text-base font-semibold">{{ title }}</h2>
    </header>
    <div class="modal-body px-5 py-4">
      <p class="confirm-message text-sm text-muted-foreground">{{ message }}</p>
    </div>
    <footer class="modal-footer border-t border-border px-5 py-4">
      <div class="footer-actions flex justify-end gap-2">
        <Button type="button" variant="outline" :disabled="busy" @click="emit('close')">
          {{ cancelText }}
        </Button>
        <Button
          type="button"
          variant="destructive"
          :disabled="busy"
          data-testid="confirm-dialog-confirm"
          @click="emit('confirm')"
        >
          {{ confirmText }}
        </Button>
      </div>
    </footer>
  </BaseDialog>
</template>
