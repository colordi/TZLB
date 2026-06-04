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
  allSelected: {
    type: Boolean,
    default: false,
  },
});

defineEmits(["toggle", "toggle-all", "edit", "export"]);
</script>

<template>
  <div class="design-workorder-table-wrap">
    <table class="design-workorder-table">
      <thead>
        <tr>
          <th class="is-check">
            <input
              type="checkbox"
              aria-label="选择当前筛选结果"
              :checked="allSelected"
              @change="$emit('toggle-all')"
            />
          </th>
          <th>导入日期</th>
          <th>调查点位</th>
          <th>害虫类型</th>
          <th>统防统治任务</th>
          <th>虫口数</th>
          <th>危害等级</th>
          <th>工单状态</th>
          <th class="is-actions">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="record in records" :key="record.id">
          <td class="is-check">
            <input
              type="checkbox"
              :aria-label="`选择 ${record.point}`"
              :checked="selectedIds.includes(record.id)"
              @change="$emit('toggle', record.id)"
            />
          </td>
          <td class="design-num">{{ record.date }}</td>
          <td>
            <strong class="design-workorder-point">{{ record.point }}</strong>
            <span class="design-workorder-coords">{{ record.coords }}</span>
          </td>
          <td>{{ record.type }}</td>
          <td class="design-workorder-task">{{ record.task }}</td>
          <td class="design-num">{{ record.count }}</td>
          <td>
            <span class="design-workorder-hazard" :class="`is-${record.hazard}`">
              {{ DESIGN_WORKORDER_HAZARD_LABELS[record.hazard] }}
            </span>
          </td>
          <td>
            <span class="design-workorder-status" :class="`is-${record.status}`">
              {{ DESIGN_WORKORDER_STATUS_LABELS[record.status] }}
            </span>
          </td>
          <td>
            <div class="design-workorder-row-actions">
              <button
                class="design-icon-button"
                type="button"
                :aria-label="`编辑 ${record.point}`"
                :data-testid="`design-workorder-edit-${record.id}`"
                @click="$emit('edit', record)"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
                  <path d="M15 3h6v6M10 14 21 3M18 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h5" />
                </svg>
              </button>
              <button
                v-if="record.status === 'pending'"
                class="design-icon-button"
                type="button"
                disabled
                :aria-label="`生成 ${record.point} 工单，静态预览不可用`"
                title="静态预览不生成工单"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
                  <path d="M12 5v14m-7-7h14" />
                </svg>
              </button>
              <button
                v-else-if="record.status === 'generated' || record.status === 'reviewed'"
                class="design-icon-button"
                type="button"
                :aria-label="`导出 ${record.point} 工单`"
                :data-testid="`design-workorder-export-${record.id}`"
                @click="$emit('export', record)"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
                  <path d="M7 3h7l5 5v13H7zM14 3v5h5M10 13h6m-6 4h6" />
                </svg>
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
