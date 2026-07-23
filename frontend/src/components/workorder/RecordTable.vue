<script setup>
import { computed } from "vue";
import { CircleAlert, LoaderCircle } from "@lucide/vue";

import EmptyState from "@/components/common/EmptyState.vue";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getVisibleFields } from "./fieldConfig.js";
import { toggleUidSelection } from "../../composables/workorder/useRecordSelection.js";

const props = defineProps({
  records: {
    type: Array,
    required: true,
  },
  pestType: {
    type: String,
    required: true,
  },
  busy: {
    type: Boolean,
    default: false,
  },
  busyLabel: {
    type: String,
    default: "正在导出…",
  },
  busyPercent: {
    type: Number,
    default: 0,
  },
  errors: {
    type: Array,
    default: () => [],
  },
  selectedUids: {
    type: Array,
    default: () => [],
  },
  serialOffset: {
    type: Number,
    default: 0,
  },
});

const emit = defineEmits(["row-click", "update:selectedUids"]);

// We only show these four specific columns as requested by the user.
const ALLOWED_KEYS = ["survey_date", "locality", "location_id", "location_name"];

// 保留列的展示宽度（被 ALLOWED_KEYS 裁掉的列不再保留死样式）
const COLUMN_WIDTH_CLASS = {
  survey_date: "w-[8.5rem]",
  locality: "w-[9rem]",
  location_id: "w-[7rem]",
  location_name: "w-[10rem]",
};

const fields = computed(() => {
  return getVisibleFields(props.pestType).filter((f) => ALLOWED_KEYS.includes(f.key));
});

const hasRows = computed(() => props.records.length > 0);

const isAllSelected = computed(() => {
  return (
    hasRows.value &&
    props.records.every((record) => props.selectedUids.includes(record.__uid))
  );
});

function toggleAll() {
  const visibleUids = props.records.map((record) => record.__uid);
  emit("update:selectedUids", toggleUidSelection(props.selectedUids, visibleUids));
}

function toggleSelection(uid) {
  const current = [...props.selectedUids];
  const pos = current.indexOf(uid);
  if (pos === -1) {
    current.push(uid);
  } else {
    current.splice(pos, 1);
  }
  emit("update:selectedUids", current);
}

function handleRowClick(uid) {
  emit("row-click", uid);
}
</script>

<template>
  <section class="relative min-w-0 overflow-hidden">
    <div
      v-if="busy"
      class="absolute inset-0 z-10 flex items-center justify-center bg-card/70 backdrop-blur-[2px]"
      aria-live="polite"
      data-testid="record-busy-overlay"
    >
      <div class="grid w-[min(360px,calc(100%-2rem))] grid-cols-[auto_1fr] items-center gap-x-3 gap-y-2 rounded-lg border bg-card p-4 text-sm shadow-sm">
        <LoaderCircle class="size-4 animate-spin text-primary" aria-hidden="true" />
        <div class="flex min-w-0 items-center justify-between gap-2">
          <strong class="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap">
            {{ busyLabel || "正在生成…" }}
          </strong>
          <span
            v-if="busyPercent > 0"
            class="shrink-0 font-semibold tabular-nums text-primary"
            data-testid="record-busy-percent"
          >
            {{ Math.round(busyPercent) }}%
          </span>
        </div>
        <div
          class="col-span-full h-2 overflow-hidden rounded-full bg-primary/10"
          role="progressbar"
          :aria-valuenow="Math.round(busyPercent)"
          aria-valuemin="0"
          aria-valuemax="100"
          data-testid="record-busy-progress"
        >
          <div
            class="h-full rounded-full bg-primary transition-[width] duration-150"
            :style="{ width: `${Math.max(0, Math.min(100, busyPercent))}%` }"
          />
        </div>
      </div>
    </div>

    <div v-if="hasRows" class="max-[900px]:hidden">
      <div class="overflow-hidden rounded-xl border bg-card shadow-sm">
        <Table class="min-w-[56rem]">
          <TableHeader>
            <TableRow class="hover:bg-transparent">
              <TableHead class="sticky top-0 z-10 w-10 bg-card pl-4">
                <Checkbox
                  :model-value="isAllSelected"
                  aria-label="全选当前页记录"
                  @update:model-value="toggleAll"
                />
              </TableHead>
              <TableHead class="sticky top-0 z-10 w-16 bg-card">序号</TableHead>
              <TableHead
                v-for="field in fields"
                :key="field.key"
                class="sticky top-0 z-10 bg-card"
                :class="COLUMN_WIDTH_CLASS[field.key]"
              >
                {{ field.label }}
              </TableHead>
            </TableRow>
          </TableHeader>

          <TableBody>
            <TableRow
              v-for="(record, index) in records"
              :key="record.__uid"
              class="cursor-pointer"
              @click="handleRowClick(record.__uid)"
            >
              <TableCell class="w-10 pl-4" @click.stop>
                <Checkbox
                  :model-value="selectedUids.includes(record.__uid)"
                  :aria-label="`选择 ${record.location_id || record.__uid}`"
                  @update:model-value="toggleSelection(record.__uid)"
                />
              </TableCell>
              <TableCell class="w-16">
                <span class="inline-flex h-8 min-w-9 items-center justify-center rounded-full bg-primary/10 px-3 text-xs font-semibold tracking-wide text-muted-foreground">
                  {{ String(serialOffset + index + 1).padStart(2, "0") }}
                </span>
              </TableCell>

              <TableCell
                v-for="field in fields"
                :key="field.key"
              >
                <div class="flex min-h-8 w-full items-center gap-2">
                  <span class="truncate text-sm font-medium">{{ record[field.key] || '-' }}</span>
                  <CircleAlert
                    v-if="errors[index]?.[field.key]"
                    class="size-3.5 shrink-0 text-destructive"
                    :aria-label="errors[index][field.key]"
                  />
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
    </div>

    <div v-if="hasRows" class="hidden max-[900px]:grid gap-3">
      <article
        v-for="(record, index) in records"
        :key="`mobile-${record.__uid}`"
        class="flex cursor-pointer flex-col gap-3 rounded-xl border bg-card p-4 shadow-sm"
        @click="handleRowClick(record.__uid)"
      >
        <header class="flex items-center gap-3">
          <div class="flex items-center justify-center" @click.stop>
            <Checkbox
              :model-value="selectedUids.includes(record.__uid)"
              :aria-label="`选择 ${record.location_id || record.__uid}`"
              @update:model-value="toggleSelection(record.__uid)"
            />
          </div>
          <span class="inline-flex h-8 min-w-9 items-center justify-center rounded-full bg-primary/10 px-3 text-xs font-semibold tracking-wide text-muted-foreground">
            {{ String(serialOffset + index + 1).padStart(2, "0") }}
          </span>
          <div>
            <strong class="block text-sm">{{ record.location_name || `现场记录 ${index + 1}` }}</strong>
            <p class="text-xs text-muted-foreground">{{ record.survey_date || '未填写日期' }}</p>
          </div>
        </header>

        <div class="grid gap-2.5">
          <div
            v-for="field in fields"
            :key="field.key"
            class="grid gap-1"
          >
            <span class="text-xs font-medium text-muted-foreground">
              {{ field.label }}<span v-if="field.required" class="ml-0.5 text-destructive">*</span>
            </span>
            <div class="truncate text-sm">{{ record[field.key] || '-' }}</div>
          </div>
        </div>
      </article>
    </div>

    <EmptyState
      v-if="!hasRows"
      title="暂无点位"
      description="请先通过上方导入入口添加点位，再生成工单。"
    />
  </section>
</template>
