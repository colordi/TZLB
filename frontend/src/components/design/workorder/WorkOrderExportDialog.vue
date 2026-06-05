<script setup>
import { ref } from "vue";

import { DESIGN_WORKORDER_EXPORT_OPTIONS } from "../../../fixtures/design/workorderRecords.js";

defineProps({
  context: {
    type: String,
    required: true,
  },
});

defineEmits(["close"]);

const selectedOptions = ref(DESIGN_WORKORDER_EXPORT_OPTIONS.map((option) => option.key));
</script>

<template>
  <div
    class="design-workorder-overlay"
    role="presentation"
    data-testid="design-workorder-export-overlay"
    @click.self="$emit('close')"
  >
    <section
      class="design-workorder-dialog is-export"
      role="dialog"
      aria-modal="true"
      aria-labelledby="design-workorder-export-title"
    >
      <header class="design-workorder-dialog-head">
        <div>
          <p>WORD PACKAGE PREVIEW</p>
          <h2 id="design-workorder-export-title">导出 Word 工单</h2>
        </div>
        <button
          class="design-icon-button"
          type="button"
          aria-label="关闭导出预览"
          @click="$emit('close')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="m6 6 12 12M18 6 6 18" />
          </svg>
        </button>
      </header>

      <div class="design-workorder-dialog-body">
        <p class="design-workorder-dialog-note">
          当前范围：<strong>{{ context }}</strong>。选择项仅用于预览导出结构，不会生成或下载文件。
        </p>

        <div class="design-workorder-option-list">
          <label v-for="option in DESIGN_WORKORDER_EXPORT_OPTIONS" :key="option.key">
            <input v-model="selectedOptions" type="checkbox" :value="option.key" />
            <span>
              <strong>{{ option.label }}</strong>
              <small>{{ option.description }}</small>
            </span>
          </label>
        </div>
      </div>

      <footer class="design-workorder-dialog-foot">
        <span>本阶段不会调用下载或文档生成逻辑。</span>
        <div>
          <button class="design-button is-secondary" type="button" @click="$emit('close')">
            取消
          </button>
          <button
            class="design-button"
            type="button"
            data-testid="design-workorder-export-confirm"
            @click="$emit('close')"
          >
            完成导出预览
          </button>
        </div>
      </footer>
    </section>
  </div>
</template>
