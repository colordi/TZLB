<script setup>
const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  ariaLabel: {
    type: String,
    default: "",
  },
  maskClass: {
    type: String,
    default: "base-dialog-mask",
  },
  dialogClass: {
    type: String,
    default: "base-dialog-content",
  },
  closeOnMaskClick: {
    type: Boolean,
    default: true,
  },
});

const emit = defineEmits(["close"]);

function handleMaskClick() {
  if (props.closeOnMaskClick) {
    emit("close");
  }
}
</script>

<template>
  <teleport to="body">
    <div
      v-if="open"
      :class="['base-dialog-mask', maskClass]"
      role="presentation"
      @click.self="handleMaskClick"
      @keydown.esc.prevent="emit('close')"
    >
      <section
        :class="['base-dialog-content', dialogClass]"
        role="dialog"
        aria-modal="true"
        :aria-label="ariaLabel"
        tabindex="0"
      >
        <slot />
      </section>
    </div>
  </teleport>
</template>

<style>
.base-dialog-mask {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
  background: rgba(29, 24, 54, 0.3);
  backdrop-filter: blur(4px);
}

.base-dialog-content {
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--elev-raised);
  overflow: hidden;
}
</style>
