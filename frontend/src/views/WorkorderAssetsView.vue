<script setup>
import { ref } from "vue";
import { RouterLink } from "vue-router";
import { FolderUp } from "@lucide/vue";

import PointScreenshotPanel from "../components/workorder/PointScreenshotPanel.vue";
import { useDateFolderUpload } from "../composables/workorder/useDateFolderUpload.js";
import { useToast } from "../composables/useToast.js";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const toast = useToast();
const dateFolder = useDateFolderUpload();
const { dateFolderInput, dateFolderUploading } = dateFolder;
const activeTab = ref("screenshots");

function onDateFolderChange(event) {
  dateFolder.handleDateFolderChange(event, toast);
}

function onOpenDateFolderPicker() {
  dateFolder.openDateFolderPicker(false);
}
</script>

<template>
  <section class="workorder-assets-page mx-auto flex w-full max-w-6xl flex-col gap-4">
    <header class="space-y-1">
      <h1 class="text-2xl font-bold tracking-tight md:text-3xl">工单素材</h1>
      <p class="max-w-3xl text-sm text-muted-foreground">
        管理点位截图与按日期归档的现场图片。素材写入磁盘后，供
        <RouterLink class="font-medium text-primary underline-offset-4 hover:underline" to="/workorder">
          工单录入
        </RouterLink>
        导入预填或生成时自动取用；上传本身不会向工单清单添加点位。
      </p>
    </header>

    <div class="inline-flex w-fit rounded-md border p-0.5" role="tablist" aria-label="素材类型">
      <Button
        type="button"
        size="sm"
        :variant="activeTab === 'screenshots' ? 'default' : 'ghost'"
        data-testid="workorder-assets-tab-screenshots"
        @click="activeTab = 'screenshots'"
      >
        点位截图
      </Button>
      <Button
        type="button"
        size="sm"
        :variant="activeTab === 'date-folder' ? 'default' : 'ghost'"
        data-testid="workorder-assets-tab-date-folder"
        @click="activeTab = 'date-folder'"
      >
        日期图片文件夹
      </Button>
    </div>

    <PointScreenshotPanel v-if="activeTab === 'screenshots'" />

    <Card v-else aria-label="日期图片文件夹">
      <CardHeader class="pb-3">
        <CardTitle class="text-base">日期图片文件夹</CardTitle>
      </CardHeader>
      <CardContent class="space-y-4">
        <div class="space-y-2 text-sm text-muted-foreground">
          <p>
            选择名为 <code class="rounded bg-muted px-1 py-0.5 text-xs">YYYY-MM-DD</code>
            的文件夹上传到
            <code class="rounded bg-muted px-1 py-0.5 text-xs">images/日期/</code>。
          </p>
          <p>
            文件名建议以点位编号开头。美国白蛾生成工单时会自动从对应日期目录拼装现场图；其他害虫主要使用点位截图或清单内图片。
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            :disabled="dateFolderUploading"
            data-testid="date-image-folder-button"
            @click="onOpenDateFolderPicker"
          >
            <FolderUp class="size-4" />
            <span>{{ dateFolderUploading ? "正在上传…" : "选择日期文件夹上传" }}</span>
          </Button>
          <input
            ref="dateFolderInput"
            class="hidden"
            type="file"
            multiple
            webkitdirectory
            directory
            data-testid="date-image-folder-input"
            @change="onDateFolderChange"
          />
        </div>
      </CardContent>
    </Card>
  </section>
</template>
