<script setup>
import { cn } from "@/lib/utils";

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
      :class="cn(
        'base-dialog-mask fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm',
        maskClass,
      )"
      role="presentation"
      @click.self="handleMaskClick"
      @keydown.esc.prevent="emit('close')"
    >
      <section
        :class="cn(
          'base-dialog-content flex max-h-[min(90vh,52rem)] w-full max-w-2xl flex-col overflow-hidden rounded-lg border border-border bg-background text-foreground shadow-lg',
          dialogClass,
        )"
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
