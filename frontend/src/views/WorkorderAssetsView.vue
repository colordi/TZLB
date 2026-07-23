<script setup>
import { ref } from "vue";

import DatePointImagePanel from "../components/workorder/DatePointImagePanel.vue";
import PointScreenshotPanel from "../components/workorder/PointScreenshotPanel.vue";
import PageHeader from "@/components/common/PageHeader.vue";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

const activeTab = ref("screenshots");
</script>

<template>
  <div class="mx-auto w-full max-w-6xl space-y-6">
    <PageHeader
      title="工单素材"
      description="管理点位截图与按日期归档的现场图片。素材写入磁盘后，供「工单录入」导入预填或生成时自动取用；上传本身不会向工单清单添加点位。"
    />

    <Tabs v-model="activeTab">
      <TabsList aria-label="素材类型">
        <TabsTrigger value="screenshots" data-testid="workorder-assets-tab-screenshots">
          点位截图
        </TabsTrigger>
        <TabsTrigger value="date-folder" data-testid="workorder-assets-tab-date-folder">
          日期现场照片
        </TabsTrigger>
      </TabsList>
    </Tabs>

    <PointScreenshotPanel v-if="activeTab === 'screenshots'" />
    <DatePointImagePanel v-else />
  </div>
</template>
