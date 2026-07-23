<script setup>
import { computed, ref, watch } from "vue";
import { getVisibleFields, normalizeInputValue } from "./fieldConfig.js";
import ImageUploader from "./ImageUploader.vue";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { Textarea } from "@/components/ui/textarea";

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

const fields = computed(() => getVisibleFields(props.pestType));

watch(() => props.open, (isOpen) => {
  if (isOpen && props.record) {
    // Clone record deep enough for images
    localRecord.value = { ...props.record, images: [...(props.record.images || [])] };
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

function updateImages(images) {
  if (localRecord.value) {
    localRecord.value.images = images;
  }
}

function handleOpenChange(value) {
  if (!value) {
    emit("close");
  }
}
</script>

<template>
  <Dialog :open="open" @update:open="handleOpenChange">
    <DialogContent class="max-h-[85vh] overflow-y-auto sm:max-w-xl">
      <DialogHeader>
        <DialogTitle>记录详情</DialogTitle>
        <DialogDescription class="sr-only">查看并编辑当前点位的调查记录。</DialogDescription>
      </DialogHeader>

      <div v-if="localRecord" class="grid gap-4">
        <div v-for="field in fields" :key="field.key" class="grid gap-2">
          <Label :for="`record-field-${field.key}`">
            {{ field.label }}
            <span v-if="field.required" class="text-destructive">*</span>
          </Label>
          <NativeSelect
            v-if="field.type === 'select'"
            :id="`record-field-${field.key}`"
            class="w-full"
            :disabled="busy"
            :aria-invalid="Boolean(error[field.key])"
            :model-value="localRecord[field.key]"
            @update:model-value="updateField(field, $event)"
          >
            <option value="">请选择</option>
            <option v-for="opt in field.options" :key="opt" :value="opt">{{ opt }}</option>
          </NativeSelect>
          <Textarea
            v-else-if="field.type === 'textarea'"
            :id="`record-field-${field.key}`"
            :disabled="busy"
            :aria-invalid="Boolean(error[field.key])"
            :model-value="localRecord[field.key]"
            @update:model-value="updateField(field, $event)"
          />
          <Input
            v-else
            :id="`record-field-${field.key}`"
            :disabled="busy"
            :type="field.type"
            :aria-invalid="Boolean(error[field.key])"
            :model-value="localRecord[field.key]"
            @update:model-value="updateField(field, $event)"
          />
          <p v-if="error[field.key]" class="text-xs text-destructive">{{ error[field.key] }}</p>
        </div>

        <div class="border-t border-dashed pt-4">
          <ImageUploader
            :images="localRecord.images || []"
            :busy="busy"
            @update:images="updateImages"
          />
        </div>
      </div>

      <DialogFooter>
        <Button type="button" variant="destructive" :disabled="busy" @click="handleDelete">
          删除此条
        </Button>
        <Button type="button" :disabled="busy" @click="handleSave">保存修改</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
