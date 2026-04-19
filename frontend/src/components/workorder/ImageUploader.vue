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
});

const emit = defineEmits(["update:images"]);
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
  <div
    class="image-uploader"
    tabindex="0"
    role="region"
    aria-label="图片上传"
    @drop="handleDrop"
    @dragover.prevent
    @paste="handlePaste"
  >
    <div class="uploader-header">
      <label>现场图片 ({{ imageCount }}/{{ maxCount }})</label>
      <span class="uploader-hint">支持点击、拖拽或粘贴</span>
    </div>

    <div class="uploader-dropzone">
      <label class="button-secondary dropzone-button">
        <input type="file" accept="image/*" multiple :disabled="busy" @change="handleFileChange" />
        选择图片
      </label>
      <span class="dropzone-text" v-if="remainingSlots > 0">还可以上传 {{ remainingSlots }} 张</span>
      <span class="dropzone-text text-warning" v-else>数量已达上限</span>
    </div>

    <div class="uploader-gallery" v-if="images.length > 0">
      <article v-for="(image, index) in images" :key="`${image}-${index}`" class="gallery-card">
        <img :src="image" :alt="`现场图片 ${index + 1}`" />
        <button
          type="button"
          class="gallery-remove"
          :disabled="busy"
          :aria-label="`删除第 ${index + 1} 张图片`"
          @click="removeImage(index)"
        >
          <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </article>
    </div>
  </div>
</template>

<style scoped>
.image-uploader {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  outline: none;
}

.uploader-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.uploader-header label {
  color: var(--color-muted);
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.uploader-hint {
  font-size: 0.75rem;
  color: var(--color-muted);
  opacity: 0.8;
}

.uploader-dropzone {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  border: 1px dashed var(--color-line-strong);
  border-radius: var(--radius-sm);
  background: var(--color-surface-container-low);
  transition: all 0.2s;
}

.image-uploader:focus-within .uploader-dropzone {
  border-color: var(--color-primary);
  background: var(--color-primary-mist);
}

.dropzone-button {
  position: relative;
  overflow: hidden;
  margin: 0;
  padding: 0.4rem 1rem;
  font-size: 0.85rem;
}

.dropzone-button input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.dropzone-text {
  font-size: 0.85rem;
  color: var(--color-muted);
}

.text-warning {
  color: var(--color-warning);
}

.uploader-gallery {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(6rem, 1fr));
  gap: 0.75rem;
  margin-top: 0.25rem;
}

.gallery-card {
  position: relative;
  aspect-ratio: 1;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--color-line);
  background: var(--color-surface-container);
}

.gallery-card img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.gallery-remove {
  position: absolute;
  top: 0.25rem;
  right: 0.25rem;
  width: 1.75rem;
  height: 1.75rem;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(186, 26, 26, 0.9);
  color: #fff;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  opacity: 0;
  transform: scale(0.9);
  transition: all 0.2s;
}

.gallery-card:hover .gallery-remove {
  opacity: 1;
  transform: scale(1);
}

.gallery-remove:hover {
  background: var(--color-danger);
}
</style>
