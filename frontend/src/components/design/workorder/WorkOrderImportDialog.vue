<script setup>
import { ref } from "vue";

import {
  DESIGN_WORKORDER_FILTERS,
  DESIGN_WORKORDER_HAZARD_LABELS,
  DESIGN_WORKORDER_IMPORT_OPTIONS,
} from "../../../fixtures/design/workorderRecords.js";

defineProps({
  records: {
    type: Array,
    required: true,
  },
});

defineEmits(["close"]);

const selectedOptions = ref(DESIGN_WORKORDER_IMPORT_OPTIONS.map((option) => option.key));
</script>

<template>
  <div
    class="design-workorder-overlay"
    role="presentation"
    data-testid="design-workorder-import-overlay"
    @click.self="$emit('close')"
  >
    <section
      class="design-workorder-dialog is-import"
      role="dialog"
      aria-modal="true"
      aria-labelledby="design-workorder-import-title"
    >
      <header class="design-workorder-dialog-head">
        <div>
          <p>STATIC IMPORT PREVIEW</p>
          <h2 id="design-workorder-import-title">导入调查记录</h2>
        </div>
        <button
          class="design-icon-button"
          type="button"
          aria-label="关闭导入预览"
          @click="$emit('close')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="m6 6 12 12M18 6 6 18" />
          </svg>
        </button>
      </header>

      <div class="design-workorder-dialog-body">
        <p class="design-workorder-dialog-note">
          以下为
          <strong>{{ DESIGN_WORKORDER_FILTERS.dateFrom }} 至 {{ DESIGN_WORKORDER_FILTERS.dateTo }}</strong>
          期间的静态调查记录，共 <strong>{{ records.length }}</strong> 条。本预览不会写入数据。
        </p>

        <div class="design-workorder-import-preview">
          <table>
            <thead>
              <tr>
                <th>日期</th>
                <th>点位</th>
                <th>害虫类型</th>
                <th>统防统治任务</th>
                <th>虫口</th>
                <th>等级</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in records" :key="record.id">
                <td class="design-num">{{ record.date }}</td>
                <td>{{ record.point }}</td>
                <td>{{ record.type }}</td>
                <td>{{ record.task }}</td>
                <td class="design-num">{{ record.count }}</td>
                <td>
                  <span class="design-workorder-hazard" :class="`is-${record.hazard}`">
                    {{ DESIGN_WORKORDER_HAZARD_LABELS[record.hazard] }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="design-workorder-option-list">
          <label v-for="option in DESIGN_WORKORDER_IMPORT_OPTIONS" :key="option.key">
            <input v-model="selectedOptions" type="checkbox" :value="option.key" />
            <span>
              <strong>{{ option.label }}</strong>
              <small>{{ option.description }}</small>
            </span>
          </label>
        </div>
      </div>

      <footer class="design-workorder-dialog-foot">
        <span>仅展示导入确认流程，不连接数据库。</span>
        <div>
          <button class="design-button is-secondary" type="button" @click="$emit('close')">
            取消
          </button>
          <button
            class="design-button"
            type="button"
            data-testid="design-workorder-import-confirm"
            @click="$emit('close')"
          >
            确认并关闭预览
          </button>
        </div>
      </footer>
    </section>
  </div>
</template>
