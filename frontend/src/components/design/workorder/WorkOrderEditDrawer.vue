<script setup>
import { reactive } from "vue";

import {
  DESIGN_WORKORDER_ATTACHMENTS,
  DESIGN_WORKORDER_EDITOR_DEFAULTS,
  DESIGN_WORKORDER_FILTERS,
  DESIGN_WORKORDER_HAZARD_LABELS,
} from "../../../fixtures/design/workorderRecords.js";

const props = defineProps({
  record: {
    type: Object,
    required: true,
  },
});

defineEmits(["close"]);

const draft = reactive({
  name: `海淀区${props.record.type}调查`,
  code: props.record.code || "待生成",
  type: props.record.type,
  assignee: DESIGN_WORKORDER_EDITOR_DEFAULTS.assignee,
  deadline: DESIGN_WORKORDER_EDITOR_DEFAULTS.deadline,
  point: props.record.point,
  coords: props.record.coords,
  host: DESIGN_WORKORDER_EDITOR_DEFAULTS.host,
  hazard: DESIGN_WORKORDER_HAZARD_LABELS[props.record.hazard],
  count: props.record.count,
  stage: DESIGN_WORKORDER_EDITOR_DEFAULTS.stage,
  notes: DESIGN_WORKORDER_EDITOR_DEFAULTS.notes,
});
</script>

<template>
  <div
    class="design-workorder-drawer-overlay"
    role="presentation"
    data-testid="design-workorder-edit-overlay"
    @click.self="$emit('close')"
  >
    <section
      class="design-workorder-edit-drawer"
      role="dialog"
      aria-modal="true"
      aria-labelledby="design-workorder-edit-title"
    >
      <header class="design-workorder-edit-head">
        <div>
          <p>LOCAL DRAFT · NOT SAVED</p>
          <h2 id="design-workorder-edit-title">
            {{ record.code ? "编辑工单" : "编辑调查记录" }}
          </h2>
          <span class="design-num">{{ record.code || "待生成" }}</span>
        </div>
        <button
          class="design-icon-button"
          type="button"
          aria-label="关闭编辑预览"
          @click="$emit('close')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="m6 6 12 12M18 6 6 18" />
          </svg>
        </button>
      </header>

      <div class="design-workorder-edit-scroll">
        <section class="design-workorder-edit-section">
          <h3>基本信息</h3>
          <div class="design-workorder-edit-grid">
            <label class="is-full">
              <span>工单名称</span>
              <input v-model="draft.name" class="design-input" />
            </label>
            <label>
              <span>工单编号</span>
              <input v-model="draft.code" class="design-input design-num" readonly />
            </label>
            <label>
              <span>害虫类型</span>
              <select v-model="draft.type" class="design-select">
                <option
                  v-for="option in DESIGN_WORKORDER_FILTERS.pestTypes.slice(1)"
                  :key="option"
                >
                  {{ option }}
                </option>
              </select>
            </label>
            <label>
              <span>负责人</span>
              <input v-model="draft.assignee" class="design-input" />
            </label>
            <label>
              <span>计划完成</span>
              <input v-model="draft.deadline" class="design-input design-num" type="date" />
            </label>
          </div>
        </section>

        <section class="design-workorder-edit-section">
          <h3>调查数据</h3>
          <div class="design-workorder-edit-grid">
            <label>
              <span>点位名称</span>
              <input v-model="draft.point" class="design-input" />
            </label>
            <label>
              <span>经纬度</span>
              <input v-model="draft.coords" class="design-input design-num" />
            </label>
            <label>
              <span>寄主树种</span>
              <select v-model="draft.host" class="design-select">
                <option>国槐</option>
                <option>白蜡</option>
                <option>杨树</option>
              </select>
            </label>
            <label>
              <span>危害等级</span>
              <select v-model="draft.hazard" class="design-select">
                <option>轻度</option>
                <option>中度</option>
                <option>重度</option>
              </select>
            </label>
            <label>
              <span>发现数量</span>
              <input v-model="draft.count" class="design-input design-num" type="number" />
            </label>
            <label>
              <span>虫态</span>
              <select v-model="draft.stage" class="design-select">
                <option>卵块</option>
                <option>幼虫</option>
                <option>成虫</option>
              </select>
            </label>
            <label class="is-full">
              <span>调查结论</span>
              <textarea v-model="draft.notes" class="design-textarea"></textarea>
            </label>
          </div>
        </section>

        <section class="design-workorder-edit-section">
          <h3>现场附件</h3>
          <div class="design-workorder-static-upload" role="note">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
              <path d="M12 16V4m-4 4 4-4 4 4M5 14v5h14v-5" />
            </svg>
            <strong>附件区静态预览</strong>
            <span>本阶段不读取本地文件、不上传，也不删除附件。</span>
          </div>

          <div class="design-workorder-file-list">
            <article v-for="file in DESIGN_WORKORDER_ATTACHMENTS" :key="file.id">
              <span>{{ file.type }}</span>
              <div>
                <strong>{{ file.name }}</strong>
                <small>{{ file.meta }}</small>
              </div>
              <span>只读</span>
            </article>
          </div>
        </section>
      </div>

      <footer class="design-workorder-edit-foot">
        <span>表单修改仅保留到关闭抽屉，不会持久化。</span>
        <div>
          <button class="design-button is-secondary" type="button" @click="$emit('close')">
            取消
          </button>
          <button
            class="design-button"
            type="button"
            data-testid="design-workorder-edit-save"
            @click="$emit('close')"
          >
            保存并关闭预览
          </button>
        </div>
      </footer>
    </section>
  </div>
</template>
