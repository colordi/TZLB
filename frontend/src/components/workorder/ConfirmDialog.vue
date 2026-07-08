<script setup>
import BaseDialog from "./BaseDialog.vue";

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
    dialog-class="confirm-dialog-content"
    @close="emit('close')"
  >
    <header class="modal-header">
      <h2>{{ title }}</h2>
    </header>
    <div class="modal-body">
      <p class="confirm-message">{{ message }}</p>
    </div>
    <footer class="modal-footer">
      <div class="footer-actions">
        <button type="button" class="button-secondary" :disabled="busy" @click="emit('close')">
          {{ cancelText }}
        </button>
        <button
          type="button"
          class="button-danger"
          :disabled="busy"
          data-testid="confirm-dialog-confirm"
          @click="emit('confirm')"
        >
          {{ confirmText }}
        </button>
      </div>
    </footer>
  </BaseDialog>
</template>

<style>
.base-dialog-mask.confirm-dialog-mask {
  z-index: 320;
}

.base-dialog-content.confirm-dialog-content {
  width: 100%;
  max-width: 26rem;
  animation: scale-up 0.2s var(--ease-standard);
}

@keyframes scale-up {
  0% { transform: scale(0.95); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}
</style>

<style scoped>
.modal-header {
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
}

.modal-header h2 {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  color: var(--color-ink);
  font-weight: 700;
  margin: 0;
}

.modal-body {
  padding: var(--space-6);
}

.confirm-message {
  margin: 0;
  color: var(--color-ink-soft);
  font-size: var(--text-md);
  line-height: 1.6;
}

.modal-footer {
  padding: var(--space-5) var(--space-6);
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: var(--space-3);
  background: var(--color-surface-container-low);
}

.footer-actions {
  display: flex;
  gap: 0.75rem;
}

.button-danger {
  padding: var(--space-3) 1.2rem;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-danger);
  font-weight: 700;
  cursor: pointer;
  border: 1px solid var(--color-danger);
  box-shadow: none;
}
.button-danger:hover {
  background: rgba(229, 72, 77, 0.08);
  transform: none;
  box-shadow: none;
}
</style>
