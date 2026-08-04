/**
 * ECharts 按需注册入口：只在 BaseChart 中引入一次。
 * 新增图型时在此补充 use() 注册。
 */
import * as echarts from "echarts/core";
import { BarChart, HeatmapChart, TreemapChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  BarChart,
  HeatmapChart,
  TreemapChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  VisualMapComponent,
  CanvasRenderer,
]);

export { echarts };
