<script setup>
import { computed } from "vue";
import { X } from "@lucide/vue";
import { useToast } from "../../composables/useToast.js";
import { Button } from "@/components/ui/button";

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
    error(`${uploadError.message || uploadError}`, "图片读取失败");
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
    class="flex flex-col gap-3 rounded-md focus-visible:ring-3 focus-visible:ring-ring/50"
    tabindex="0"
    role="region"
    aria-label="图片上传"
    @drop="handleDrop"
    @dragover.prevent
    @paste="handlePaste"
  >
    <div class="flex items-baseline justify-between">
      <span class="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
        现场图片 ({{ imageCount }}/{{ maxCount }})
      </span>
      <span class="text-xs text-muted-foreground">支持点击、拖拽或粘贴</span>
    </div>

    <div class="flex items-center gap-4 rounded-md border border-dashed px-4 py-3 transition-colors focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50">
      <Button type="button" variant="outline" size="sm" class="relative overflow-hidden" as-child>
        <label>
          <input
            type="file"
            accept="image/*"
            multiple
            class="absolute inset-0 size-full cursor-pointer opacity-0"
            :disabled="busy"
            @change="handleFileChange"
          />
          选择图片
        </label>
      </Button>
      <span v-if="remainingSlots > 0" class="text-sm text-muted-foreground">
        还可以上传 {{ remainingSlots }} 张
      </span>
      <span v-else class="text-sm text-warning">数量已达上限</span>
    </div>

    <div v-if="images.length > 0" class="grid grid-cols-[repeat(auto-fill,minmax(6rem,1fr))] gap-3">
      <article
        v-for="(image, index) in images"
        :key="`${image}-${index}`"
        class="group relative aspect-square overflow-hidden rounded-md border bg-muted"
      >
        <img :src="image" :alt="`现场图片 ${index + 1}`" class="size-full object-cover" />
        <Button
          type="button"
          variant="destructive"
          size="icon-xs"
          class="absolute top-1 right-1 rounded-full opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
          :disabled="busy"
          :aria-label="`删除第 ${index + 1} 张图片`"
          @click="removeImage(index)"
        >
          <X class="size-3.5" />
        </Button>
      </article>
    </div>
  </div>
</template>
