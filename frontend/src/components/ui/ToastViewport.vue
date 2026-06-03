<script setup>
import { useToast } from "../../composables/useToast.js";

const { dismissToast, toasts } = useToast();

const ICONS = {
  success: "✓",
  error: "!",
  info: "i",
};
</script>

<template>
  <teleport to="body">
    <div class="toast-viewport" aria-live="polite" aria-atomic="true">
      <transition-group name="toast-stack" tag="div" class="toast-stack">
        <article
          v-for="toast in toasts"
          :key="toast.id"
          class="toast-card"
          :class="`is-${toast.type}`"
        >
          <div class="toast-icon">{{ ICONS[toast.type] || ICONS.info }}</div>
          <div class="toast-copy">
            <strong>{{ toast.title }}</strong>
            <p v-if="toast.message">{{ toast.message }}</p>
          </div>
          <button
            type="button"
            class="toast-close"
            aria-label="关闭提示"
            @click="dismissToast(toast.id)"
          >
            ×
          </button>
        </article>
      </transition-group>
    </div>
  </teleport>
</template>

<style scoped>
.toast-viewport {
  position: fixed;
  top: 1.125rem;
  right: 1rem;
  z-index: 1600;
  pointer-events: none;
}

.toast-stack {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.toast-card {
  pointer-events: auto;
  width: min(24rem, calc(100vw - 2rem));
  display: grid;
  grid-template-columns: 2rem minmax(0, 1fr) 1.5rem;
  align-items: start;
  gap: 0.75rem;
  padding: 0.875rem 0.95rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  box-shadow: var(--elev-raised);
  backdrop-filter: blur(18px);
}

.toast-card.is-success {
  border-color: var(--color-success);
}

.toast-card.is-error {
  border-color: var(--color-danger);
}

.toast-card.is-info {
  border-color: var(--color-border);
}

.toast-icon {
  width: 2rem;
  height: 2rem;
  border-radius: var(--radius-pill);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  color: var(--color-ink-soft);
  font-size: 0.95rem;
  font-weight: 700;
}

.toast-card.is-error .toast-icon {
  background: rgba(229, 72, 77, 0.1);
  color: var(--color-danger);
}

.toast-copy {
  min-width: 0;
}

.toast-copy strong {
  display: block;
  color: var(--color-ink);
  font-size: 0.92rem;
}

.toast-copy p {
  margin-top: 0.18rem;
  color: var(--color-muted);
  font-size: 0.82rem;
  line-height: 1.55;
}

.toast-close {
  min-height: 0;
  width: 1.5rem;
  height: 1.5rem;
  padding: 0;
  border: none;
  border-radius: var(--radius-pill);
  background: transparent;
  color: var(--color-muted);
  box-shadow: none;
}

.toast-close:hover {
  background: var(--color-surface-container);
  color: var(--color-ink);
}

.toast-stack-enter-active,
.toast-stack-leave-active {
  transition: all 220ms ease;
}

.toast-stack-enter-from,
.toast-stack-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.98);
}

@media (max-width: 720px) {
  .toast-viewport {
    top: auto;
    right: 0.75rem;
    bottom: 0.75rem;
    left: 0.75rem;
  }

  .toast-card {
    width: 100%;
  }
}
</style>
