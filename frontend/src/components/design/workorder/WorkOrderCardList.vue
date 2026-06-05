<script setup>
import {
  DESIGN_WORKORDER_HAZARD_LABELS,
  DESIGN_WORKORDER_STATUS_LABELS,
} from "../../../fixtures/design/workorderRecords.js";

defineProps({
  records: {
    type: Array,
    required: true,
  },
  selectedIds: {
    type: Array,
    required: true,
  },
});

defineEmits(["toggle", "edit", "export"]);
</script>

<template>
  <div class="design-workorder-cards">
    <article v-for="record in records" :key="record.id" class="design-workorder-card">
      <div class="design-workorder-card-head">
        <input
          type="checkbox"
          :aria-label="`选择 ${record.point}`"
          :checked="selectedIds.includes(record.id)"
          @change="$emit('toggle', record.id)"
        />
        <div>
          <strong>{{ record.point }}</strong>
          <span>{{ record.code || "未生成" }} · {{ record.task }}</span>
        </div>
        <span class="design-workorder-status" :class="`is-${record.status}`">
          {{ DESIGN_WORKORDER_STATUS_LABELS[record.status] }}
        </span>
      </div>

      <div class="design-workorder-card-meta">
        <span>
          <small>害虫类型</small>
          <strong>{{ record.type }}</strong>
        </span>
        <span>
          <small>虫口数</small>
          <strong class="design-num">{{ record.count }}</strong>
        </span>
        <span>
          <small>危害等级</small>
          <strong>
            <span class="design-workorder-hazard" :class="`is-${record.hazard}`">
              {{ DESIGN_WORKORDER_HAZARD_LABELS[record.hazard] }}
            </span>
          </strong>
        </span>
        <span>
          <small>导入日期</small>
          <strong class="design-num">{{ record.date }}</strong>
        </span>
      </div>

      <div class="design-workorder-card-actions">
        <button
          class="design-button is-secondary"
          type="button"
          :data-testid="`design-workorder-card-edit-${record.id}`"
          @click="$emit('edit', record)"
        >
          编辑
        </button>
        <button
          v-if="record.status === 'pending'"
          class="design-button"
          type="button"
          disabled
          title="静态预览不生成工单"
        >
          生成工单
        </button>
        <button
          v-else-if="record.status === 'generated' || record.status === 'reviewed'"
          class="design-button"
          type="button"
          :data-testid="`design-workorder-card-export-${record.id}`"
          @click="$emit('export', record)"
        >
          导出 Word
        </button>
      </div>
    </article>
  </div>
</template>
