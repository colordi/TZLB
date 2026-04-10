<script setup>
import { computed, ref, watch } from "vue";
import { getVisibleFields, normalizeInputValue } from "./fieldConfig.js";
import ImageUploadDialog from "./ImageUploadDialog.vue";

const props = defineProps({
  open: Boolean,
  record: Object,
  pestType: String,
  busy: Boolean,
  error: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits(["close", "update", "delete"]);

const localRecord = ref(null);
const imageDialogOpen = ref(false);

const fields = computed(() => getVisibleFields(props.pestType));

watch(() => props.open, (isOpen) => {
  if (isOpen && props.record) {
    // Clone record deep enough for images
    localRecord.value = { ...props.record, images: [...(props.record.images || [])] };
  } else {
    imageDialogOpen.value = false;
  }
});

function updateField(field, value) {
  if (!localRecord.value) return;
  localRecord.value[field.key] = normalizeInputValue(field, value);
}

function handleSave() {
  emit("update", localRecord.value);
}

function handleDelete() {
  emit("delete");
}

function openImages() {
  imageDialogOpen.value = true;
}

function updateImages(images) {
  if (localRecord.value) {
    localRecord.value.images = images;
  }
}
</script>

<template>
  <div v-if="open" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <header class="modal-header">
        <h2>记录详情</h2>
        <button type="button" class="close-btn" @click="$emit('close')">
          <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </header>
      <div class="modal-body" v-if="localRecord">
        <div 
          v-for="field in fields" 
          :key="field.key" 
          class="field-block"
          :class="{'field-error': error[field.key]}"
        >
          <label>{{ field.label }}<span v-if="field.required">*</span></label>
          <select
            v-if="field.type === 'select'"
            class="modal-input"
            :disabled="busy"
            :value="localRecord[field.key]"
            @change="updateField(field, $event.target.value)"
          >
            <option value="">请选择</option>
            <option v-for="opt in field.options" :key="opt" :value="opt">{{ opt }}</option>
          </select>
          <textarea
            v-else-if="field.type === 'textarea'"
            class="modal-input modal-textarea"
            :disabled="busy"
            :value="localRecord[field.key]"
            @input="updateField(field, $event.target.value)"
          />
          <input
            v-else
            class="modal-input"
            :disabled="busy"
            :type="field.type"
            :value="localRecord[field.key]"
            @input="updateField(field, $event.target.value)"
          />
          <span v-if="error[field.key]" class="error-msg">{{ error[field.key] }}</span>
        </div>
      </div>
      <footer class="modal-footer">
        <button type="button" class="button-secondary btn-image" @click="openImages">
          现场图片 ({{ localRecord?.images?.length || 0 }}/4)
        </button>
        <div class="footer-actions">
          <button type="button" class="button-danger" :disabled="busy" @click="handleDelete">删除此条</button>
          <button type="button" @click="handleSave" :disabled="busy">保存修改</button>
        </div>
      </footer>
    </div>
    
    <ImageUploadDialog
      :open="imageDialogOpen"
      :images="localRecord?.images || []"
      :busy="busy"
      record-label="当前记录"
      @close="imageDialogOpen = false"
      @update:images="updateImages"
    />
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(18, 36, 25, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.modal-content {
  width: 100%;
  max-width: 32rem; /* 512px */
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  background: var(--color-surface-container-lowest);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-elevated);
  overflow: hidden;
  animation: scale-up 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes scale-up {
  0% { transform: scale(0.95); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

.modal-header {
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--color-surface-container);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--color-surface-container-lowest);
}

.modal-header h2 {
  font-family: var(--font-display);
  font-size: 1.25rem;
  color: var(--color-ink);
  font-weight: 800;
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 1.5rem;
  line-height: 1;
  color: var(--color-muted);
  cursor: pointer;
  padding: 0;
  box-shadow: none;
  border-radius: 50%;
  width: 2.25rem;
  height: 2.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.close-btn:hover {
  background: var(--color-surface-container-high);
  color: var(--color-ink);
  transform: none;
  box-shadow: none;
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  display: grid;
  gap: 1.25rem;
  grid-template-columns: 1fr;
}

.field-block {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.field-block label {
  color: var(--color-muted);
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.field-block label span {
  color: var(--color-danger);
  margin-left: 0.25rem;
}

.modal-input {
  width: 100%;
  min-height: 2.85rem;
  padding: 0.5rem 0.85rem;
  border: 1px solid var(--color-line-strong);
  border-radius: var(--radius-sm);
  background: transparent;
  font-family: var(--font-body);
  font-size: var(--text-sm);
  font-weight: 600;
  transition: all 0.2s;
}

.modal-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-mist);
  outline: none;
}

.modal-textarea {
  min-height: 5rem;
  resize: vertical;
}

.error-msg {
  color: var(--color-danger);
  font-size: 0.75rem;
  font-weight: 600;
}

.field-error .modal-input {
  border-color: var(--color-danger);
  background: rgba(186, 26, 26, 0.05);
}

.modal-footer {
  padding: 1.25rem 1.5rem;
  border-top: 1px solid var(--color-surface-container);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  background: var(--color-surface-container-low);
}

.footer-actions {
  display: flex;
  gap: 0.75rem;
  margin-left: auto;
}

.button-danger {
  padding: var(--space-3) 1.2rem;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--color-danger);
  font-weight: 700;
  cursor: pointer;
  border: none;
  box-shadow: none;
}
.button-danger:hover {
  background: rgba(186, 26, 26, 0.1);
  transform: none;
  box-shadow: none;
}

.btn-image {
  box-shadow: none;
  border-radius: var(--radius-xs);
  min-height: 2.5rem;
  padding: 0.25rem 1rem;
}
</style>
