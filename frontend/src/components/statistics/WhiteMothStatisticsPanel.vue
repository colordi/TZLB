<script setup>
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import WhiteMothDailyTab from "./WhiteMothDailyTab.vue";
import WhiteMothGenerationTab from "./WhiteMothGenerationTab.vue";
import WhiteMothLocalityTab from "./WhiteMothLocalityTab.vue";

// 各子 tab 独立维护自己的筛选器和数据，切换时不重置（unmount-on-hide=false）
</script>

<template>
  <Tabs default-value="generation" :unmount-on-hide="false" class="gap-4">
    <TabsList aria-label="美国白蛾统计板块">
      <TabsTrigger value="generation" data-testid="data-statistics-white-moth-tab-generation">
        世代汇总
      </TabsTrigger>
      <TabsTrigger value="locality" data-testid="data-statistics-white-moth-tab-locality">
        属地受害
      </TabsTrigger>
      <TabsTrigger value="daily" data-testid="data-statistics-white-moth-tab-daily">
        每日统计
      </TabsTrigger>
    </TabsList>

    <TabsContent value="generation">
      <WhiteMothGenerationTab />
    </TabsContent>
    <TabsContent value="locality">
      <WhiteMothLocalityTab />
    </TabsContent>
    <TabsContent value="daily">
      <WhiteMothDailyTab />
    </TabsContent>
  </Tabs>
</template>
