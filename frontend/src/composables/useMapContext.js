/**
 * Shared state bridge between App.vue header and MapView.
 * MapView provides the context object; App.vue injects it to render map toolbar controls.
 *
 * Usage:
 *   MapView.vue  →  provideMapContext({ views, selectedView, ... })
 *   App.vue      →  const mapCtx = injectMapContext()
 *                    // mapCtx is reactive: truthy when MapView provided, falsy otherwise
 *                    // Access: mapCtx.selectedView (auto-unwrapped ref)
 */
import { inject, provide, reactive } from "vue";

const MAP_CONTEXT_KEY = Symbol("mapContext");

/**
 * Provide the map context from MapView.
 * @param {Object} ctx — plain object with reactive refs and methods
 */
export function provideMapContext(ctx) {
  provide(MAP_CONTEXT_KEY, ctx);
}

const EMPTY = reactive({ ready: false });

/**
 * Inject the map context in App.vue.
 * Returns the context object (with reactive refs auto-unwrapped) when provided,
 * or a frozen sentinel `{ ready: false }` when not on the map page.
 *
 * Check with: `if (mapCtx.ready === false)` → not on map page.
 */
export function injectMapContext() {
  return inject(MAP_CONTEXT_KEY, EMPTY);
}
