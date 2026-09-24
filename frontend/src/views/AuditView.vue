<template>
  <div class="audit">
    <h2>智能合约安全审计</h2>
    <div class="upload-section">
      <textarea v-model="contractCode" class="code-editor" placeholder="// 粘贴 Solidity 合约代码..."></textarea>
      <div class="toolbar">
        <input v-model="filename" placeholder="文件名.sol" class="filename-input" />
        <button @click="runAudit" class="btn-primary" :disabled="!contractCode || isAuditing">
          {{ isAuditing ? "审计中..." : "开始审计" }}
        </button>
      </div>
    </div>

    <div v-if="auditError" class="error-banner">{{ auditError }}</div>

    <div v-if="result" class="result-section">
      <div v-if="result.duplicated" class="dedup-tip">
        ℹ 该合约此前已提交过 {{ (result.auditCount ?? 1) - 1 }} 次，本次为第 {{ result.auditCount ?? 1 }} 次审计，已合并到台账同一条记录（不会产生重复条目）。
      </div>
      <div class="score-card" :class="scoreClass">
        <div class="score-label">安全评分</div>
        <div class="score-value">{{ result.score }}</div>
        <div class="score-grade">{{ scoreGrade }}</div>
      </div>
      <div class="vulnerabilities">
        <h3>发现漏洞 ({{ result.vulnerabilities.length }})</h3>
        <div v-if="result.vulnerabilities.length === 0" class="no-vuln">
          <div class="no-vuln-title">✓ 未发现安全漏洞</div>
          <div class="no-vuln-desc">
            已按当前漏洞模式库完成扫描，未匹配到已知风险模式。该结果不代表绝对安全，建议结合人工复审。
          </div>
        </div>
        <div v-for="(v, idx) in result.vulnerabilities" :key="idx" class="vuln-card" :class="v.severity">
          <div class="vuln-header">
            <span class="vuln-type">{{ v.type }}</span>
            <span class="vuln-severity" :class="v.severity">{{ severityLabel(v.severity) }}</span>
          </div>
          <div class="vuln-lines">代码行号：<code>{{ lineRange(v) }}</code></div>
          <div class="vuln-desc">{{ v.description }}</div>
          <div class="vuln-suggest">建议: {{ v.suggestion }}</div>
        </div>
      </div>
      <div v-if="result.gasIssues.length > 0" class="gas-section">
        <h3>Gas优化建议</h3>
        <div v-for="g in result.gasIssues" :key="g.functionName" class="gas-card">
          <div class="gas-fn">{{ g.functionName }}</div>
          <div class="gas-info">当前: {{ g.currentGas }} → 优化后: {{ g.optimizedGas }} ({{ Math.round((1-g.optimizedGas/g.currentGas)*100) }}%节省)</div>
          <div class="gas-suggest">{{ g.suggestion }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue"
import { useAuditStore } from '@/store'
import type { AuditResult } from '@/store'

const store = useAuditStore()

const contractCode = ref(`// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SimpleBank {
    mapping(address => uint) public balances;

    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint amount) public {
        require(balances[msg.sender] >= amount);
        (bool success,) = msg.sender.call{value: amount}("");
        require(success);
        balances[msg.sender] -= amount;
    }
}`)
const filename = ref("SimpleBank.sol")
const isAuditing = ref(false)
const result = ref<AuditResult | null>(null)
const auditError = ref('')

const scoreClass = computed(() => {
  if (!result.value) return ""
  if (result.value.score >= 80) return "score-high"
  if (result.value.score >= 50) return "score-medium"
  return "score-low"
})

const scoreGrade = computed(() => {
  if (!result.value) return ""
  if (result.value.score >= 90) return "Excellent"
  if (result.value.score >= 70) return "Good"
  if (result.value.score >= 50) return "Fair"
  return "Poor"
})

function severityLabel(sev: string) {
  return { critical: '严重', high: '高危', medium: '中危', low: '低危' }[sev] ?? sev
}

function lineRange(v: { lineStart?: number; lineEnd?: number; line: number }) {
  const start = v.lineStart ?? v.line
  return v.lineEnd && v.lineEnd !== start ? `${start}-${v.lineEnd}` : `${start}`
}

async function runAudit() {
  isAuditing.value = true
  auditError.value = ''
  try {
    result.value = await store.uploadAndAudit(contractCode.value, filename.value.trim() || '未命名合约.sol')
  } catch (e: any) {
    auditError.value = '审计失败，请确认后端服务已启动（' + (e?.response?.data?.detail ?? e?.message ?? '未知错误') + '）'
  } finally {
    isAuditing.value = false
  }
}
</script>

<style scoped>
.audit { max-width: 1000px; }
.code-editor { width: 100%; height: 300px; font-family: "Fira Code", monospace; font-size: 0.875rem; padding: 1rem; border: 1px solid #d1d5db; border-radius: 8px; background: #1e1e1e; color: #d4d4d4; resize: vertical; }
.toolbar { display: flex; gap: 1rem; margin: 1rem 0; align-items: center; }
.filename-input { padding: 0.5rem 1rem; border: 1px solid #d1d5db; border-radius: 8px; flex: 1; }
.btn-primary { background: #8b5cf6; color: white; border: none; padding: 0.625rem 1.5rem; border-radius: 8px; cursor: pointer; white-space: nowrap; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.error-banner { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; border-radius: 8px; padding: 0.75rem 1rem; margin-top: 1rem; }
.dedup-tip { background: #eef2ff; color: #3730a3; border: 1px solid #c7d2fe; border-radius: 8px; padding: 0.7rem 1rem; margin-bottom: 1rem; font-size: 0.85rem; }
.result-section { margin-top: 2rem; }
.score-card { border-radius: 16px; padding: 2rem; text-align: center; color: white; margin-bottom: 2rem; }
.score-high { background: linear-gradient(135deg, #10b981, #059669); }
.score-medium { background: linear-gradient(135deg, #f59e0b, #d97706); }
.score-low { background: linear-gradient(135deg, #ef4444, #dc2626); }
.score-label { font-size: 0.875rem; opacity: 0.9; margin-bottom: 0.5rem; }
.score-value { font-size: 4rem; font-weight: 800; }
.score-grade { font-size: 1.25rem; opacity: 0.9; }
.vulnerabilities h3, .gas-section h3 { margin-bottom: 1rem; font-size: 1.125rem; }
.no-vuln { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 1.25rem 1.5rem; }
.no-vuln-title { font-weight: 600; color: #15803d; margin-bottom: 0.4rem; }
.no-vuln-desc { font-size: 0.875rem; color: #374151; line-height: 1.6; }
.vuln-card { background: white; border-radius: 12px; padding: 1.25rem; margin-bottom: 1rem; border-left: 4px solid; }
.vuln-card.critical { border-color: #dc2626; }
.vuln-card.high { border-color: #f59e0b; }
.vuln-card.medium { border-color: #3b82f6; }
.vuln-card.low { border-color: #6b7280; }
.vuln-header { display: flex; justify-content: space-between; margin-bottom: 0.5rem; }
.vuln-type { font-weight: 600; }
.vuln-severity { padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }
.vuln-severity.critical { background: #fee2e2; color: #dc2626; }
.vuln-severity.high { background: #fef3c7; color: #b45309; }
.vuln-severity.medium { background: #dbeafe; color: #1d4ed8; }
.vuln-severity.low { background: #f3f4f6; color: #4b5563; }
.vuln-lines { font-size: 0.82rem; color: #6b7280; margin-bottom: 0.5rem; }
.vuln-lines code { background: #eef2ff; color: #4338ca; padding: 0.1rem 0.45rem; border-radius: 4px; font-family: monospace; }
.vuln-desc { color: #374151; margin-bottom: 0.5rem; }
.vuln-suggest { font-size: 0.875rem; color: #6b7280; }
.gas-card { background: white; border-radius: 12px; padding: 1.25rem; margin-bottom: 1rem; }
.gas-fn { font-weight: 600; color: #7c3aed; margin-bottom: 0.5rem; }
.gas-info { color: #059669; font-size: 0.875rem; margin-bottom: 0.5rem; }
.gas-suggest { font-size: 0.875rem; color: #6b7280; }
</style>
