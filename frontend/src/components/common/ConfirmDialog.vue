<script setup>
/**
 * 统一确认弹窗（规范 §6.2）：基于 ui/alert-dialog，危险操作确认按钮用 destructive。
 * props：open / title / message / confirmText / cancelText / busy / destructive（默认 true）；
 * 事件：confirm / close / update:open。确认后是否关闭由调用方控制。
 *
 * 实现说明：reka-ui 的 AlertDialogAction 点击时会先触发 update:open(false) 再触发
 * 外部 @click。这里用 closePending 标记在同一事件循环内抵消这次自动关闭，
 * 保证「确认」只抛 confirm、「取消/ESC」才抛 close。
 */
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  title: {
    type: String,
    default: "请确认",
  },
  message: {
    type: String,
    default: "",
  },
  confirmText: {
    type: String,
    default: "确认删除",
  },
  cancelText: {
    type: String,
    default: "取消",
  },
  busy: {
    type: Boolean,
    default: false,
  },
  destructive: {
    type: Boolean,
    default: true,
  },
});

const emit = defineEmits(["confirm", "close"]);

let closePending = false;

function handleUpdateOpen(value) {
  if (value) {
    return;
  }
  closePending = true;
  queueMicrotask(() => {
    if (!closePending) {
      return;
    }
    closePending = false;
    emit("close");
  });
}

function handleConfirm() {
  closePending = false;
  emit("confirm");
}
</script>

<template>
  <AlertDialog :open="open" @update:open="handleUpdateOpen">
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>{{ title }}</AlertDialogTitle>
        <AlertDialogDescription>{{ message }}</AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel :disabled="busy">{{ cancelText }}</AlertDialogCancel>
        <AlertDialogAction
          :variant="destructive ? 'destructive' : 'default'"
          :disabled="busy"
          data-testid="confirm-dialog-confirm"
          @click="handleConfirm"
        >
          {{ confirmText }}
        </AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>
