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
  border-radius: 18px;
  border: 1px solid rgba(46, 125, 50, 0.16);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 18px 40px rgba(22, 60, 33, 0.14);
  backdrop-filter: blur(18px);
}

.toast-card.is-success {
  border-color: rgba(46, 125, 50, 0.2);
}

.toast-card.is-error {
  border-color: rgba(211, 84, 48, 0.22);
}

.toast-card.is-info {
  border-color: rgba(70, 125, 103, 0.18);
}

.toast-icon {
  width: 2rem;
  height: 2rem;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(46, 125, 50, 0.1);
  color: var(--color-primary-strong);
  font-size: 0.95rem;
  font-weight: 700;
}

.toast-card.is-error .toast-icon {
  background: rgba(211, 84, 48, 0.1);
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
  border-radius: 999px;
  background: transparent;
  color: var(--color-muted);
  box-shadow: none;
}

.toast-close:hover {
  background: rgba(18, 52, 29, 0.08);
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
