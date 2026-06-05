<script setup>
import { ref } from "vue";

import { DESIGN_WORKORDER_FILTERS } from "../../../fixtures/design/workorderRecords.js";

const dateFrom = ref(DESIGN_WORKORDER_FILTERS.dateFrom);
const dateTo = ref(DESIGN_WORKORDER_FILTERS.dateTo);
const pestType = ref(DESIGN_WORKORDER_FILTERS.pestTypes[0]);
const task = ref(DESIGN_WORKORDER_FILTERS.tasks[1]);
</script>

<template>
  <section class="design-workorder-controls" aria-label="工单范围筛选">
    <label class="design-workorder-field">
      <span>日期范围</span>
      <span class="design-workorder-date-range">
        <input v-model="dateFrom" class="design-input design-num" type="date" />
        <span>至</span>
        <input v-model="dateTo" class="design-input design-num" type="date" />
      </span>
    </label>

    <label class="design-workorder-field">
      <span>害虫类型</span>
      <select v-model="pestType" class="design-select">
        <option v-for="option in DESIGN_WORKORDER_FILTERS.pestTypes" :key="option">
          {{ option }}
        </option>
      </select>
    </label>

    <label class="design-workorder-field is-task">
      <span>统防统治任务</span>
      <select v-model="task" class="design-select">
        <option v-for="option in DESIGN_WORKORDER_FILTERS.tasks" :key="option">
          {{ option }}
        </option>
      </select>
    </label>
  </section>
</template>
