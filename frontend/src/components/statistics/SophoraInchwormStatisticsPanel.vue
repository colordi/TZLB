<script setup>
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import SophoraGenerationTab from "./SophoraGenerationTab.vue";
import SophoraLocalityTab from "./SophoraLocalityTab.vue";
</script>

<template>
  <Tabs default-value="generation" :unmount-on-hide="false" class="gap-4">
    <TabsList aria-label="国槐尺蠖统计板块">
      <TabsTrigger
        value="generation"
        data-testid="data-statistics-sophora-tab-generation"
      >
        世代汇总
      </TabsTrigger>
      <TabsTrigger
        value="locality"
        data-testid="data-statistics-sophora-tab-locality"
      >
        属地受害
      </TabsTrigger>
    </TabsList>

    <TabsContent value="generation">
      <SophoraGenerationTab />
    </TabsContent>
    <TabsContent value="locality">
      <SophoraLocalityTab />
    </TabsContent>
  </Tabs>
</template>
