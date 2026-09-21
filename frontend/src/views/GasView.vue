<template>
  <div class="gas">
    <h2>Gas 消耗分析</h2>
    <div ref="gasChart" class="chart-container"></div>
    <div class="gas-tips">
      <h3>Gas优化技巧</h3>
      <ul>
        <li>使用 <code>calldata</code> 代替 <code>memory</code> 存储函数参数</li>
        <li>使用 <code>short-circuit</code> 逻辑减少不必要的计算</li>
        <li>避免在循环中读取存储变量，缓存到内存</li>
        <li>使用事件而非存储来记录历史数据</li>
        <li>合理使用 <code>unchecked</code> 块跳过溢出检查</li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue"
import * as echarts from "echarts"

const gasChart = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null

onMounted(() => {
  if (gasChart.value) {
    chart = echarts.init(gasChart.value)
    chart.setOption({
      title: { text: "各函数Gas消耗对比", left: "center" },
      tooltip: {},
      xAxis: { type: "category", data: ["deposit", "withdraw", "transfer", "balanceOf", "totalSupply"] },
      yAxis: { type: "value", name: "Gas" },
      series: [{ type: "bar", data: [45000, 52000, 35000, 28000, 22000], itemStyle: { color: "#8b5cf6" } }]
    })
  }
})

onUnmounted(() => { chart?.dispose() })
</script>

<style scoped>
.gas { max-width: 1000px; }
.chart-container { height: 400px; background: white; border-radius: 12px; padding: 1rem; margin-bottom: 2rem; }
.gas-tips { background: white; border-radius: 12px; padding: 1.5rem; }
.gas-tips h3 { margin-bottom: 1rem; }
.gas-tips ul { list-style: none; }
.gas-tips li { padding: 0.5rem 0; color: #374151; border-bottom: 1px solid #f3f4f6; }
.gas-tips li:last-child { border-bottom: none; }
.gas-tips code { background: #f3f4f6; padding: 0.125rem 0.375rem; border-radius: 4px; font-family: monospace; color: #7c3aed; }
</style>