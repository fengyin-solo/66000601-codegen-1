<template>
  <div class="patterns">
    <h2>漏洞模式库</h2>
    <div class="pattern-grid">
      <div v-for="p in patterns" :key="p.name" class="pattern-card">
        <div class="pattern-name">{{ p.name }}</div>
        <div class="pattern-severity" :class="p.severity">{{ p.severity }}</div>
        <div class="pattern-desc">{{ p.description }}</div>
        <div class="pattern-regex">正则: <code>{{ p.regex }}</code></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue"

const patterns = ref([
  { name: "重入攻击", severity: "critical", description: "使用低级call/send转移ETH，未做重入防护", regex: ".*\.call\{.*\}\(.*\).*;" },
  { name: "整数溢出", severity: "high", description: "Solidity 0.7中可能发生整数溢出", regex: "\+\s*=|\-\s*=|\*\s*=" },
  { name: "未授权访问", severity: "high", description: "关键函数缺少访问控制修饰符", regex: "function\s+\w+\s*\([^)]*\)\s*(?:public)?\s*(?:payable)?\s*\{[^}]*\}" },
  { name: "自杀指令", severity: "medium", description: "selfdestruct可被用于销毁合约", regex: "selfdestruct|suicide" },
  { name: "tx.origin钓鱼", severity: "high", description: "使用tx.origin进行身份验证可被钓鱼", regex: "tx\.origin" },
  { name: "精确度损失", severity: "medium", description: "除法运算可能导致精度损失", regex: "/\s*\d+" },
])
</script>

<style scoped>
.patterns { max-width: 1000px; }
.pattern-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; }
.pattern-card { background: white; border-radius: 12px; padding: 1.25rem; }
.pattern-name { font-weight: 600; margin-bottom: 0.5rem; }
.pattern-severity { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; margin-bottom: 0.75rem; }
.pattern-severity.critical { background: #fee2e2; color: #dc2626; }
.pattern-severity.high { background: #fef3c7; color: #d97706; }
.pattern-severity.medium { background: #dbeafe; color: #1d4ed8; }
.pattern-desc { color: #6b7280; font-size: 0.875rem; margin-bottom: 0.75rem; }
.pattern-regex { font-size: 0.75rem; }
.pattern-regex code { background: #f3f4f6; padding: 0.125rem 0.375rem; border-radius: 4px; font-family: monospace; }
</style>