<script setup>
import { computed } from "vue";

import { useToast } from "../../composables/useToast.js";

const props = defineProps({
  busy: {
    type: Boolean,
    default: false,
  },
  images: {
    type: Array,
    default: () => [],
  },
  maxCount: {
    type: Number,
    default: 4,
  },
  open: {
    type: Boolean,
    default: false,
  },
  recordLabel: {
    type: String,
    default: "",
  },
});

const emit = defineEmits(["close", "update:images"]);
const { error, info, success } = useToast();

const imageCount = computed(() => props.images.length);
const remainingSlots = computed(() => Math.max(0, props.maxCount - imageCount.value));

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function updateImages(images) {
  emit("update:images", images.slice(0, props.maxCount));
}

async function appendFiles(files) {
  if (!files.length) {
    return;
  }

  if (remainingSlots.value <= 0) {
    info(`每条记录最多上传 ${props.maxCount} 张图片。`, "图片数量已达上限");
    return;
  }

  const acceptedFiles = files.slice(0, remainingSlots.value);
  if (acceptedFiles.length < files.length) {
    info(`已超过上限，仅保留前 ${acceptedFiles.length} 张。`, "部分图片未导入");
  }

  try {
    const encodedFiles = await Promise.all(acceptedFiles.map((file) => readFileAsBase64(file)));
    updateImages(props.images.concat(encodedFiles));
    success(`已导入 ${encodedFiles.length} 张图片。`, "图片已更新");
  } catch (uploadError) {
    error(`${uploadError}`, "图片读取失败");
  }
}

function collectImageFiles(fileList) {
  return Array.from(fileList || []).filter((file) => file?.type?.startsWith("image/"));
}

function handleFileChange(event) {
  const files = collectImageFiles(event.target.files);
  appendFiles(files);
  event.target.value = "";
}

function handlePaste(event) {
  const files = Array.from(event.clipboardData?.items || [])
    .filter((item) => item.kind === "file" && item.type.startsWith("image/"))
    .map((item) => item.getAsFile())
    .filter(Boolean);

  if (!files.length) {
    return;
  }

  event.preventDefault();
  appendFiles(files);
}

function handleDrop(event) {
  event.preventDefault();
  const files = collectImageFiles(event.dataTransfer?.files);
  appendFiles(files);
}

function removeImage(index) {
  updateImages(props.images.filter((_, imageIndex) => imageIndex !== index));
}
</script>

<template>
  <teleport to="body">
    <div
      v-if="open"
      class="image-dialog-mask"
      role="presentation"
      @click.self="emit('close')"
      @paste="handlePaste"
      @keydown.esc="emit('close')"
    >
      <section
        class="image-dialog"
        role="dialog"
        aria-modal="true"
        :aria-label="`${recordLabel}图片上传`"
        tabindex="0"
        @drop="handleDrop"
        @dragover.prevent
      >
        <header class="dialog-head">
          <div>
            <h3>{{ recordLabel }}图片上传</h3>
            <p>支持点击上传、拖拽图片到此处，或直接粘贴剪贴板内容。</p>
          </div>
          <button type="button" class="dialog-close" @click="emit('close')">×</button>
        </header>

        <div class="dialog-dropzone">
          <div class="dropzone-copy">
            <strong>拖拽到这里，或点击选择图片</strong>
            <p>当前 {{ imageCount }} / {{ maxCount }} 张，剩余 {{ remainingSlots }} 个位置</p>
          </div>
          <label class="button-secondary dropzone-button">
            <input type="file" accept="image/*" multiple :disabled="busy" @change="handleFileChange" />
            选择图片
          </label>
        </div>

        <div class="dialog-gallery">
          <article v-for="(image, index) in images" :key="`${image}-${index}`" class="gallery-card">
            <img :src="image" :alt="`现场图片 ${index + 1}`" />
            <button
              type="button"
              class="gallery-remove"
              :disabled="busy"
              :aria-label="`删除第 ${index + 1} 张图片`"
              @click="removeImage(index)"
            >
              删除
            </button>
          </article>

          <div v-if="images.length === 0" class="gallery-empty">
            <strong>还没有上传图片</strong>
            <p>图片将按当前记录一起导出到工作单模板中。</p>
          </div>
        </div>
      </section>
    </div>
  </teleport>
</template>

<style scoped>
.image-dialog-mask {
  position: fixed;
  inset: 0;
  z-index: 1500;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(18, 36, 25, 0.36);
  backdrop-filter: blur(8px);
}

.image-dialog {
  width: min(56rem, 100%);
  max-height: min(44rem, calc(100vh - 2rem));
  display: flex;
  flex-direction: column;
  gap: 1rem;
  overflow: auto;
  padding: 1.25rem;
  border: 1px solid rgba(46, 125, 50, 0.16);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.97);
  box-shadow: 0 30px 60px rgba(12, 35, 20, 0.18);
}

.dialog-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.dialog-head h3 {
  font-size: 1.4rem;
  line-height: 1.15;
}

.dialog-head p {
  margin-top: 0.32rem;
  color: var(--color-muted);
  font-size: 0.9rem;
}

.dialog-close {
  min-height: 0;
  width: 2.5rem;
  height: 2.5rem;
  padding: 0;
  border-radius: 999px;
  background: rgba(46, 125, 50, 0.08);
  color: var(--color-primary-strong);
  box-shadow: none;
}

.dialog-dropzone {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.1rem 1.2rem;
  border: 1px dashed rgba(46, 125, 50, 0.28);
  border-radius: 24px;
  background:
    linear-gradient(135deg, rgba(46, 125, 50, 0.08), rgba(46, 125, 50, 0.03)),
    rgba(245, 250, 243, 0.96);
}

.dropzone-copy strong {
  display: block;
  font-size: 1rem;
}

.dropzone-copy p {
  margin-top: 0.25rem;
  color: var(--color-muted);
}

.dropzone-button {
  position: relative;
  overflow: hidden;
  flex-shrink: 0;
}

.dropzone-button input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.dialog-gallery {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
  gap: 0.9rem;
}

.gallery-card,
.gallery-empty {
  border: 1px solid var(--color-line);
  border-radius: 22px;
  background: var(--color-bg-strong);
  overflow: hidden;
}

.gallery-card img {
  display: block;
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
}

.gallery-remove {
  width: calc(100% - 1rem);
  margin: 0.5rem;
  min-height: 2.6rem;
  border-radius: 14px;
  background: rgba(211, 84, 48, 0.1);
  color: var(--color-danger);
  box-shadow: none;
}

.gallery-empty {
  min-height: 12rem;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0.35rem;
  color: var(--color-muted);
}

@media (max-width: 760px) {
  .dialog-dropzone {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
