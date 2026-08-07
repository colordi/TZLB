<script setup>
import { computed, onMounted, ref } from "vue";
import { RefreshCw, Save, Eye, EyeOff, GripVertical, Plus, Trash2 } from "@lucide/vue";

import {
  createTaskView,
  deleteTaskView,
  fetchLayers,
  fetchViewBuilderSources,
  previewTaskView,
  updateLayers,
} from "../api/admin.js";
import { fetchMapFilterOptions } from "../api/map.js";
import { isUnauthorizedError } from "../api/http.js";
import { useToast } from "../composables/useToast.js";
import PageHeader from "@/components/common/PageHeader.vue";
import ConfirmDialog from "@/components/common/ConfirmDialog.vue";
import { Badge } from "@/components/ui/badge";
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
import { NativeSelect } from "@/components/ui/native-select";
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

const { error, info } = useToast();
const loading = ref(false);
const saving = ref(false);
const viewLayers = ref([]);
const referenceLayers = ref([]);
const editCache = ref({});
const hasChanges = ref(false);
const filterOptionsByLayerKey = ref({});

const TASK_VIEW_PREFIX = "task_";
const GENERATION_OPTIONS = ["第一代", "第二代", "第三代"];

/* ── 任务图层构建器 ── */
const builderOpen = ref(false);
const builderSources = ref({ base_tables: [], related_tables: [] });
const builderSourcesLoading = ref(false);
const builderForm = ref(emptyBuilderForm());
const builderPreview = ref(null);
const builderPreviewLoading = ref(false);
const builderPublishing = ref(false);
const deleteTarget = ref(null);
const deletingTask = ref(false);

function emptyBuilderForm() {
  return {
    name_suffix: "",
    display_name: "",
    base_table: "",
    site_name_column: "",
    related_table: "",
    year: "",
    generation: "",
    codes_text: "",
  };
}

const selectedBaseTable = computed(
  () =>
    builderSources.value.base_tables.find(
      (table) => table.name === builderForm.value.base_table,
    ) || null,
);

const selectedRelatedTable = computed(
  () =>
    builderSources.value.related_tables.find(
      (table) => `${table.table_schema}.${table.name}` === builderForm.value.related_table,
    ) || null,
);

const siteNameColumnOptions = computed(() => {
  const base = selectedBaseTable.value;
  if (!base) return [];
  return base.columns.filter(
    (column) => !["geom", "gid", "fid", "id"].includes(column),
  );
});

const builderNameSuffixValid = computed(() =>
  /^[a-z0-9_]{1,40}$/.test(builderForm.value.name_suffix),
);

const canPreviewTaskView = computed(
  () =>
    builderNameSuffixValid.value &&
    builderForm.value.display_name.trim() !== "" &&
    builderForm.value.base_table !== "",
);

function isTaskLayer(layer) {
  return layer.layer_key.startsWith(TASK_VIEW_PREFIX);
}

async function openBuilder() {
  builderForm.value = emptyBuilderForm();
  builderPreview.value = null;
  builderOpen.value = true;
  if (builderSources.value.base_tables.length || builderSourcesLoading.value) return;
  builderSourcesLoading.value = true;
  try {
    builderSources.value = await fetchViewBuilderSources();
  } catch (err) {
    if (isUnauthorizedError(err)) return;
    error(`读取候选源表失败：${err.message || err}`, "加载失败");
  } finally {
    builderSourcesLoading.value = false;
  }
}

function onBuilderBaseTableChange() {
  const base = selectedBaseTable.value;
  builderForm.value.site_name_column = base?.site_name_column || "";
  builderPreview.value = null;
}

function parseCodeListText(text) {
  return text
    .split(/[\n,，;；]+/)
    .map((code) => code.trim())
    .filter((code) => code !== "");
}

function buildTaskViewPayload() {
  const form = builderForm.value;
  return {
    name: `${TASK_VIEW_PREFIX}${form.name_suffix}`,
    display_name: form.display_name.trim(),
    base_table: form.base_table,
    related_table: form.related_table || null,
    site_name_column: form.site_name_column || null,
    filters: {
      year: form.year.trim() || null,
      generation: form.generation || null,
      codes: parseCodeListText(form.codes_text),
    },
  };
}

async function handlePreviewTaskView() {
  builderPreviewLoading.value = true;
  try {
    builderPreview.value = await previewTaskView(buildTaskViewPayload());
  } catch (err) {
    builderPreview.value = null;
    if (isUnauthorizedError(err)) return;
    error(`预览失败：${err.message || err}`, "预览失败");
  } finally {
    builderPreviewLoading.value = false;
  }
}

async function handlePublishTaskView() {
  builderPublishing.value = true;
  try {
    await createTaskView(buildTaskViewPayload());
    info("任务图层已发布", "发布成功");
    builderOpen.value = false;
    builderPreview.value = null;
    await load();
  } catch (err) {
    if (isUnauthorizedError(err)) return;
    error(`发布任务图层失败：${err.message || err}`, "发布失败");
  } finally {
    builderPublishing.value = false;
  }
}

function requestDeleteTaskView(layer) {
  deleteTarget.value = layer;
}

async function handleDeleteTaskView() {
  if (!deleteTarget.value) return;
  deletingTask.value = true;
  try {
    await deleteTaskView(deleteTarget.value.layer_key);
    info(`任务图层 ${deleteTarget.value.layer_key} 已删除`, "删除成功");
    deleteTarget.value = null;
    await load();
  } catch (err) {
    if (isUnauthorizedError(err)) return;
    error(`删除任务图层失败：${err.message || err}`, "删除失败");
  } finally {
    deletingTask.value = false;
  }
}

function formatPreviewCell(value) {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

const dragKey = ref(null);
const dragType = ref(null);
const dragOverKey = ref(null);
const dragOverPos = ref(null);

const layerTypeLabel = {
  view: "点位图层",
  reference: "参考图层",
};

const EXCLUDED_FILTER_KEYS = new Set(["属地", "调查状态"]);

const totalCount = computed(
  () => viewLayers.value.length + referenceLayers.value.length
);

function listFor(typeKey) {
  return typeKey === "view" ? viewLayers.value : referenceLayers.value;
}

function buildCache(data) {
  const cache = {};
  for (const layer of data) {
    cache[layer.id] = {
      display_name: layer.display_name || "",
      sort_order: layer.sort_order,
      default_visible: layer.default_visible,
      is_enabled: layer.is_enabled,
      default_filters: { ...(layer.default_filters || {}) },
    };
  }
  return cache;
}

async function loadFilterOptionsForViews(layers) {
  const enabledViewLayers = layers.filter(
    (l) => l.layer_type === "view" && l.is_enabled,
  );
  const results = await Promise.allSettled(
    enabledViewLayers.map((layer) => fetchMapFilterOptions(layer.layer_key)),
  );
  const optionsMap = {};
  enabledViewLayers.forEach((layer, idx) => {
    const result = results[idx];
    if (result.status === "fulfilled" && result.value) {
      optionsMap[layer.layer_key] = result.value;
    }
  });
  filterOptionsByLayerKey.value = optionsMap;
}

async function load() {
  if (loading.value) return;
  loading.value = true;
  try {
    const data = await fetchLayers();
    viewLayers.value = data.filter((l) => l.layer_type === "view");
    referenceLayers.value = data.filter((l) => l.layer_type === "reference");
    editCache.value = buildCache(data);
    hasChanges.value = false;
    await loadFilterOptionsForViews(data);
  } catch (err) {
    if (isUnauthorizedError(err)) return;
    error(`加载图层元数据失败：${err.message || err}`, "加载失败");
  } finally {
    loading.value = false;
  }
}

function getEdit(layer) {
  return editCache.value[layer.id] || {};
}

function markChanged() {
  hasChanges.value = true;
}

function configurableFieldsFor(layer) {
  const options = filterOptionsByLayerKey.value[layer.layer_key];
  if (!options) return [];
  return (options.filter_fields || []).filter(
    (field) => !EXCLUDED_FILTER_KEYS.has(field.key),
  );
}

function getFilterValue(layer, fieldKey) {
  return getEdit(layer).default_filters?.[fieldKey] || "";
}

function isStaleFilterValue(layer, field) {
  const value = getFilterValue(layer, field.key);
  if (!value) return false;
  return !field.options.some((option) => option.value === value);
}

function setFilterValue(layer, fieldKey, value) {
  const edit = getEdit(layer);
  const filters = { ...(edit.default_filters || {}) };
  if (value) {
    filters[fieldKey] = value;
  } else {
    delete filters[fieldKey];
  }
  edit.default_filters = filters;
  markChanged();
}

function toggleEnabled(layer) {
  const edit = getEdit(layer);
  edit.is_enabled = !edit.is_enabled;
  markChanged();
}

function toggleDefaultVisible(layer) {
  const edit = getEdit(layer);
  edit.default_visible = !edit.default_visible;
  markChanged();
}

/* ── 拖拽排序（组内，不跨 layer_type） ── */
function onDragStart(e, layer, typeKey) {
  dragKey.value = layer.layer_key;
  dragType.value = typeKey;
  e.dataTransfer.effectAllowed = "move";
  e.dataTransfer.setData("text/plain", layer.layer_key);
}

function onDragOver(e, layer, typeKey) {
  if (dragType.value !== typeKey) return;
  e.preventDefault();
  e.dataTransfer.dropEffect = "move";
  if (!dragKey.value || dragKey.value === layer.layer_key) {
    dragOverKey.value = null;
    dragOverPos.value = null;
    return;
  }
  const rect = e.currentTarget.getBoundingClientRect();
  const offset = e.clientY - rect.top;
  dragOverKey.value = layer.layer_key;
  dragOverPos.value = offset < rect.height / 2 ? "before" : "after";
}

function onDrop(e, targetLayer, typeKey) {
  e.preventDefault();
  if (!dragKey.value || dragType.value !== typeKey) {
    resetDrag();
    return;
  }
  const list = listFor(typeKey);
  const fromIdx = list.findIndex((l) => l.layer_key === dragKey.value);
  if (fromIdx === -1) {
    resetDrag();
    return;
  }
  const toIdx = list.findIndex((l) => l.layer_key === targetLayer.layer_key);
  if (toIdx === -1) {
    resetDrag();
    return;
  }
  const insertAfter = dragOverPos.value === "after";
  let target = insertAfter ? toIdx + 1 : toIdx;
  const [moved] = list.splice(fromIdx, 1);
  if (fromIdx < target) target -= 1;
  list.splice(target, 0, moved);
  reindex(list);
  markChanged();
  resetDrag();
}

function onDragEnd() {
  resetDrag();
}

function resetDrag() {
  dragKey.value = null;
  dragType.value = null;
  dragOverKey.value = null;
  dragOverPos.value = null;
}

function reindex(list) {
  list.forEach((layer, idx) => {
    layer.sort_order = idx;
    const edit = editCache.value[layer.id];
    if (edit) edit.sort_order = idx;
  });
}

async function handleSave() {
  saving.value = true;
  try {
    const items = [
      ...viewLayers.value,
      ...referenceLayers.value,
    ].map((layer) => {
      const edit = editCache.value[layer.id] || {};
      return {
        layer_key: layer.layer_key,
        layer_type: layer.layer_type,
        display_name: edit.display_name || null,
        sort_order: edit.sort_order ?? layer.sort_order,
        default_visible: edit.default_visible ?? layer.default_visible,
        is_enabled: edit.is_enabled ?? layer.is_enabled,
        default_filters: edit.default_filters || {},
      };
    });

    const updated = await updateLayers(items);
    viewLayers.value = updated.filter((l) => l.layer_type === "view");
    referenceLayers.value = updated.filter((l) => l.layer_type === "reference");
    editCache.value = buildCache(updated);
    hasChanges.value = false;
    info("图层元数据已更新", "保存成功");
  } catch (err) {
    error(`保存图层元数据失败：${err.message || err}`, "保存失败");
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  load();
});
</script>

<template>
  <div class="mx-auto w-full max-w-6xl space-y-6">
    <PageHeader
      title="图层管理"
      :description="`拖拽调整图层显示顺序，编辑别名与启用状态，共 ${totalCount} 项`"
    >
      <template #actions>
        <Button type="button" variant="outline" size="sm" :disabled="loading" @click="load">
          <RefreshCw class="size-4" :class="{ 'animate-spin': loading }" />
          <span>{{ loading ? "加载中" : "刷新" }}</span>
        </Button>
        <Button
          type="button"
          size="sm"
          :disabled="!hasChanges || saving"
          @click="handleSave"
        >
          <Save class="size-4" />
          <span>{{ saving ? "保存中…" : "保存更改" }}</span>
        </Button>
      </template>
    </PageHeader>

    <template v-for="(typeKey, typeIdx) in ['view', 'reference']" :key="typeKey">
      <div
        class="flex items-center gap-2"
        :class="typeIdx === 0 ? '' : 'mt-2'"
      >
        <h2 class="text-base font-semibold">{{ layerTypeLabel[typeKey] }}</h2>
        <Badge variant="secondary">{{ listFor(typeKey).length }}</Badge>
        <Button
          v-if="typeKey === 'view'"
          type="button"
          variant="outline"
          size="sm"
          class="ml-auto"
          @click="openBuilder"
        >
          <Plus class="size-4" />
          <span>新建任务图层</span>
        </Button>
      </div>

      <div class="overflow-hidden rounded-xl border bg-card shadow-sm">
        <div class="overflow-x-auto">
          <Table class="min-w-[48rem]">
            <TableHeader>
              <TableRow class="hover:bg-transparent">
                <TableHead class="w-10" />
                <TableHead class="w-14">序号</TableHead>
                <TableHead>显示名称</TableHead>
                <TableHead>图层键</TableHead>
                <TableHead class="w-28">状态</TableHead>
                <TableHead v-if="typeKey === 'reference'" class="w-32">默认显隐</TableHead>
                <TableHead v-if="typeKey === 'view'">默认筛选</TableHead>
                <TableHead v-if="typeKey === 'view'" class="w-20">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow
                v-for="(layer, index) in listFor(typeKey)"
                :key="layer.id"
                :class="cn(
                  !getEdit(layer).is_enabled && 'opacity-50',
                  dragKey === layer.layer_key && 'opacity-40',
                  dragOverKey === layer.layer_key && dragOverPos === 'before' && 'border-t-2 border-t-primary',
                  dragOverKey === layer.layer_key && dragOverPos === 'after' && 'border-b-2 border-b-primary',
                )"
                @dragover="onDragOver($event, layer, typeKey)"
                @drop="onDrop($event, layer, typeKey)"
                @dragend="onDragEnd"
              >
                <TableCell class="w-10 px-2">
                  <div
                    class="flex size-8 cursor-grab items-center justify-center rounded-md text-muted-foreground hover:bg-muted"
                    draggable="true"
                    title="拖拽排序"
                    @dragstart="onDragStart($event, layer, typeKey)"
                  >
                    <GripVertical class="size-4" />
                  </div>
                </TableCell>
                <TableCell class="text-muted-foreground tabular-nums">
                  {{ index + 1 }}
                </TableCell>
                <TableCell>
                  <Input
                    v-model="getEdit(layer).display_name"
                    class="h-8 min-w-[10rem] max-w-xs"
                    draggable="false"
                    :placeholder="layer.layer_key"
                    @input="markChanged"
                  />
                </TableCell>
                <TableCell>
                  <code class="text-xs text-muted-foreground">{{ layer.layer_key }}</code>
                </TableCell>
                <TableCell>
                  <Button
                    type="button"
                    size="sm"
                    :variant="getEdit(layer).is_enabled ? 'default' : 'outline'"
                    draggable="false"
                    :title="getEdit(layer).is_enabled ? '点击停用' : '点击启用'"
                    @click="toggleEnabled(layer)"
                  >
                    <Eye v-if="getEdit(layer).is_enabled" class="size-3.5" />
                    <EyeOff v-else class="size-3.5" />
                    {{ getEdit(layer).is_enabled ? "启用" : "停用" }}
                  </Button>
                </TableCell>
                <TableCell v-if="typeKey === 'reference'">
                  <Button
                    type="button"
                    size="sm"
                    :variant="getEdit(layer).default_visible ? 'secondary' : 'outline'"
                    draggable="false"
                    title="默认显隐"
                    @click="toggleDefaultVisible(layer)"
                  >
                    {{ getEdit(layer).default_visible ? "默认显示" : "默认隐藏" }}
                  </Button>
                </TableCell>
                <TableCell v-if="typeKey === 'view'">
                  <div
                    v-if="configurableFieldsFor(layer).length"
                    class="flex flex-wrap items-center gap-2"
                    data-testid="layer-default-filters"
                  >
                    <label
                      v-for="field in configurableFieldsFor(layer)"
                      :key="field.key"
                      class="flex items-center gap-1.5 text-xs text-muted-foreground"
                    >
                      <span class="whitespace-nowrap">{{ field.label }}</span>
                      <NativeSelect
                        class="h-8 py-1"
                        :model-value="getFilterValue(layer, field.key)"
                        :data-testid="`layer-filter-${field.key}`"
                        @change="setFilterValue(layer, field.key, $event.target.value)"
                      >
                        <option value="">全部</option>
                        <option
                          v-for="option in field.options"
                          :key="option.value"
                          :value="option.value"
                        >
                          {{ option.label }}
                        </option>
                        <option
                          v-if="isStaleFilterValue(layer, field)"
                          disabled
                          :value="getFilterValue(layer, field.key)"
                        >
                          {{ getFilterValue(layer, field.key) }}（当前无此值）
                        </option>
                      </NativeSelect>
                    </label>
                  </div>
                  <span v-else class="text-xs text-muted-foreground">—</span>
                </TableCell>
                <TableCell v-if="typeKey === 'view'">
                  <Button
                    v-if="isTaskLayer(layer)"
                    type="button"
                    variant="ghost"
                    size="sm"
                    class="text-destructive hover:text-destructive"
                    title="删除任务图层"
                    :data-testid="`delete-task-view-${layer.layer_key}`"
                    @click="requestDeleteTaskView(layer)"
                  >
                    <Trash2 class="size-4" />
                  </Button>
                  <span v-else class="text-xs text-muted-foreground">—</span>
                </TableCell>
              </TableRow>
              <TableRow v-if="listFor(typeKey).length === 0 && !loading">
                <TableCell :colspan="typeKey === 'view' ? 7 : 6" class="h-24 text-center text-muted-foreground">
                  暂无数据
                </TableCell>
              </TableRow>
              <TableRow v-if="loading && listFor(typeKey).length === 0">
                <TableCell :colspan="typeKey === 'view' ? 7 : 6" class="h-24 text-center text-muted-foreground">
                  加载中…
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </div>
    </template>

    <Dialog v-model:open="builderOpen">
      <DialogContent class="flex max-h-[85vh] flex-col sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>新建任务图层</DialogTitle>
          <DialogDescription>
            选择基础点位表与可选的调查/台账关联表，发布后自动出现在点位图层列表中。
          </DialogDescription>
        </DialogHeader>

        <div class="grid min-h-0 flex-1 gap-4 overflow-y-auto py-2 pr-1">
          <div class="grid gap-1.5">
            <label class="text-sm font-medium">任务名称</label>
            <Input
              v-model="builderForm.display_name"
              placeholder="如：美国白蛾2026年第一代巡查"
              @input="builderPreview = null"
            />
          </div>
          <div class="grid gap-1.5">
            <label class="text-sm font-medium">视图名称</label>
            <div class="flex items-center gap-2">
              <span class="shrink-0 text-sm text-muted-foreground">task_</span>
              <Input
                v-model="builderForm.name_suffix"
                placeholder="如 2026_baie_gen1（小写字母、数字、下划线）"
                @input="builderPreview = null"
              />
            </div>
            <p
              v-if="builderForm.name_suffix && !builderNameSuffixValid"
              class="text-xs text-destructive"
            >
              仅支持小写字母、数字、下划线，最长 40 字符
            </p>
          </div>
          <div class="grid gap-4 sm:grid-cols-2">
            <div class="grid gap-1.5">
              <label class="text-sm font-medium">基础点位表</label>
              <NativeSelect
                v-model="builderForm.base_table"
                class="w-full"
                @change="onBuilderBaseTableChange"
              >
                <option value="" disabled>请选择</option>
                <option
                  v-for="table in builderSources.base_tables"
                  :key="table.name"
                  :value="table.name"
                >
                  {{ table.name }}
                </option>
              </NativeSelect>
            </div>
            <div class="grid gap-1.5">
              <label class="text-sm font-medium">点位名称列</label>
              <NativeSelect
                v-model="builderForm.site_name_column"
                class="w-full"
                :disabled="!selectedBaseTable"
                @change="builderPreview = null"
              >
                <option value="">不使用</option>
                <option
                  v-for="column in siteNameColumnOptions"
                  :key="column"
                  :value="column"
                >
                  {{ column }}
                </option>
              </NativeSelect>
            </div>
          </div>
          <div class="grid gap-1.5">
            <label class="text-sm font-medium">关联调查/台账表（可选）</label>
            <NativeSelect
              v-model="builderForm.related_table"
              class="w-full"
              :disabled="!selectedBaseTable || !selectedBaseTable.has_join_key"
              @change="builderPreview = null"
            >
              <option value="">不关联，仅展示点位</option>
              <option
                v-for="table in builderSources.related_tables"
                :key="`${table.table_schema}.${table.name}`"
                :value="`${table.table_schema}.${table.name}`"
              >
                {{ table.table_schema }}.{{ table.name }}
              </option>
            </NativeSelect>
          </div>
          <div v-if="selectedRelatedTable" class="grid gap-4 sm:grid-cols-2">
            <div class="grid gap-1.5">
              <label class="text-sm font-medium">年份筛选（可选）</label>
              <Input
                v-model="builderForm.year"
                placeholder="如 2026"
                :disabled="!selectedRelatedTable.has_year"
                @input="builderPreview = null"
              />
            </div>
            <div class="grid gap-1.5">
              <label class="text-sm font-medium">世代筛选（可选）</label>
              <NativeSelect
                v-model="builderForm.generation"
                class="w-full"
                :disabled="!selectedRelatedTable.has_generation"
                @change="builderPreview = null"
              >
                <option value="">全部世代</option>
                <option
                  v-for="generation in GENERATION_OPTIONS"
                  :key="generation"
                  :value="generation"
                >
                  {{ generation }}
                </option>
              </NativeSelect>
            </div>
          </div>
          <div class="grid gap-1.5">
            <label class="text-sm font-medium">编号清单筛选（可选）</label>
            <Textarea
              v-model="builderForm.codes_text"
              class="min-h-20"
              placeholder="一行一个编号，也可用逗号分隔，如：&#10;YB001&#10;YB002"
              @input="builderPreview = null"
            />
            <p class="text-xs text-muted-foreground">
              填写后图层只包含清单内的点位，预览时会校验清单中未匹配的编号。
            </p>
          </div>

          <div
            v-if="builderPreview"
            class="space-y-2 rounded-lg border bg-muted/40 p-3"
            data-testid="task-view-preview"
          >
            <p class="text-sm">
              共
              <span class="font-semibold tabular-nums">{{ builderPreview.total }}</span>
              个点位
            </p>
            <template v-if="builderPreview.codes_total > 0">
              <p class="text-sm">
                编号清单
                <span class="font-semibold tabular-nums">{{ builderPreview.codes_total }}</span>
                个，匹配
                <span class="font-semibold tabular-nums">{{ builderPreview.codes_matched }}</span>
                个
              </p>
              <p
                v-if="builderPreview.codes_unmatched.length"
                class="text-xs text-destructive"
                data-testid="task-view-codes-unmatched"
              >
                未匹配编号：{{ builderPreview.codes_unmatched.slice(0, 20).join("、") }}<template v-if="builderPreview.codes_unmatched.length > 20">等
                  {{ builderPreview.codes_unmatched.length }} 个</template>
              </p>
            </template>
            <div
              v-if="builderPreview.sample_rows.length"
              class="grid max-h-40 grid-cols-1 gap-x-6 gap-y-1 overflow-auto rounded-md border bg-card p-3 text-xs sm:grid-cols-2"
              data-testid="task-view-preview-sample"
            >
              <div
                v-for="column in builderPreview.sample_columns"
                :key="column"
                class="flex items-baseline justify-between gap-3"
              >
                <span class="shrink-0 text-muted-foreground">{{ column }}</span>
                <span
                  class="truncate"
                  :title="formatPreviewCell(builderPreview.sample_rows[0][column])"
                >
                  {{ formatPreviewCell(builderPreview.sample_rows[0][column]) }}
                </span>
              </div>
            </div>
            <p v-else class="text-xs text-muted-foreground">
              当前筛选条件下没有匹配的点位。
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            :disabled="builderPublishing"
            @click="builderOpen = false"
          >
            取消
          </Button>
          <Button
            type="button"
            variant="secondary"
            :disabled="!canPreviewTaskView || builderPreviewLoading || builderPublishing"
            data-testid="preview-task-view"
            @click="handlePreviewTaskView"
          >
            {{ builderPreviewLoading ? "预览中…" : "预览" }}
          </Button>
          <Button
            type="button"
            :disabled="!builderPreview || builderPublishing"
            data-testid="publish-task-view"
            @click="handlePublishTaskView"
          >
            {{ builderPublishing ? "发布中…" : "发布" }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <ConfirmDialog
      :open="!!deleteTarget"
      title="删除任务图层"
      :message="`确定删除任务图层 ${deleteTarget?.layer_key} 吗？对应的数据库视图将被一并删除，此操作不可撤销。`"
      confirm-text="确认删除"
      :busy="deletingTask"
      @confirm="handleDeleteTaskView"
      @close="deleteTarget = null"
    />
  </div>
</template>
