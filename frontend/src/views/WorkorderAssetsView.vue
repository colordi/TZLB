<script setup>
import { ref } from "vue";
import { RouterLink } from "vue-router";

import DatePointImagePanel from "../components/workorder/DatePointImagePanel.vue";
import PointScreenshotPanel from "../components/workorder/PointScreenshotPanel.vue";
import { Button } from "@/components/ui/button";

const activeTab = ref("screenshots");
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
        日期现场照片
      </Button>
    </div>

    <PointScreenshotPanel v-if="activeTab === 'screenshots'" />
    <DatePointImagePanel v-else />
  </section>
</template>
