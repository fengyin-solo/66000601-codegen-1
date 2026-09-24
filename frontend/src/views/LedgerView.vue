<template>
  <div class="ledger">
    <div class="ledger-header">
      <h2>合约风险台账</h2>
      <p class="ledger-sub">
        <template v-if="loading">正在加载台账…</template>
        <template v-else-if="entries.length">
          在册合约 {{ entries.length }} 份 · 同一份合约多次审计已合并，展示最近一次审计的漏洞数量与时间
        </template>
        <template v-else>暂无在册合约</template>
      </p>
    </div>

    <div v-if="!loading && !entries.length" class="empty-state">
      <div class="empty-icon">📋</div>
      <p class="empty-title">台账暂无记录</p>
      <p class="empty-tip">前往「合约审计」粘贴 Solidity 代码并提交后，审计结果会自动汇入风险台账。</p>
    </div>

    <div v-else class="ledger-list">
      <div v-for="entry in entries" :key="entry.contractKey" class="ledger-card">
        <div class="ledger-row" @click="toggle(entry.contractKey)">
          <span class="expand-icon">{{ expanded.has(entry.contractKey) ? '▾' : '▸' }}</span>
          <div class="ledger-file">
            <span class="filename">{{ entry.filename }}</span>
            <span v-if="entry.auditCount > 1" class="audit-times">已审计 {{ entry.auditCount }} 次</span>
          </div>
          <div class="severity-badges">
            <span v-if="entry.severityCounts.critical" class="badge critical">严重 {{ entry.severityCounts.critical }}</span>
            <span v-if="entry.severityCounts.high" class="badge high">高危 {{ entry.severityCounts.high }}</span>
            <span v-if="entry.severityCounts.medium" class="badge medium">中危 {{ entry.severityCounts.medium }}</span>
            <span v-if="entry.severityCounts.low" class="badge low">低危 {{ entry.severityCounts.low }}</span>
            <span v-if="entry.vulnCount === 0" class="badge clean">未发现问题</span>
          </div>
          <div class="ledger-count" :class="{ zero: entry.vulnCount === 0 }">
            最近一次发现 {{ entry.vulnCount }} 个
          </div>
          <div class="ledger-time">{{ formatTime(entry.lastAuditAt) }}</div>
        </div>

        <div v-if="expanded.has(entry.contractKey)" class="ledger-detail">
          <template v-if="entry.vulnerabilities.length">
            <div v-for="(v, i) in entry.vulnerabilities" :key="i" class="vuln-item" :class="v.severity">
              <div class="vuln-head">
                <span class="vuln-type">{{ v.type }}</span>
                <span class="vuln-sev" :class="v.severity">{{ severityLabel(v.severity) }}</span>
                <span class="vuln-lines">
                  代码行号区间：第 {{ v.lineStart }}<template v-if="v.lineEnd > v.lineStart">–{{ v.lineEnd }}</template> 行
                </span>
              </div>
              <div class="vuln-desc">{{ v.description }}</div>
              <div class="vuln-fix">修复建议：{{ v.suggestion }}</div>
              <pre v-if="v.code" class="vuln-code">{{ v.code }}</pre>
            </div>
          </template>
          <div v-else class="clean-note">
            <span class="clean-icon">✅</span>
            <div>
              <div class="clean-title">该合约未发现问题</div>
              <div class="clean-desc">{{ entry.note || defaultCleanNote }}</div>
              <div class="clean-meta">结论基于 {{ formatTime(entry.lastAuditAt) }} 的最近一次审计。</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuditStore, type LedgerEntry, type Severity } from '@/store'

const store = useAuditStore()
const route = useRoute()
const expanded = ref<Set<string>>(new Set())
const loading = ref(true)
const defaultCleanNote = '该合约最近一次审计未命中任何已知漏洞模式，当前无在册风险项。'

const SEVERITY_RANK: Record<Severity, number> = { critical: 0, high: 1, medium: 2, low: 3 }

const entries = ref<LedgerEntry[]>([])

const SEVERITY_LABELS: Record<Severity, string> = {
  critical: '严重',
  high: '高危',
  medium: '中危',
  low: '低危'
}

function severityLabel(severity: string) {
  return SEVERITY_LABELS[severity as Severity] || severity
}

function formatTime(iso: string) {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function toggle(key: string) {
  const next = new Set(expanded.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  expanded.value = next
}

onMounted(async () => {
  try {
    const data = await store.fetchLedger()
    // 双保险：漏洞按严重程度排列（critical -> high -> medium -> low），同级按起始行号
    entries.value = [...data].map((entry) => ({
      ...entry,
      vulnerabilities: [...entry.vulnerabilities].sort(
        (a, b) => (SEVERITY_RANK[a.severity] ?? 99) - (SEVERITY_RANK[b.severity] ?? 99) || a.lineStart - b.lineStart
      )
    }))
  } finally {
    loading.value = false
  }

  // 从审计历史「查看详情」跳入时，自动展开对应合约
  const target = route.query.key
  if (typeof target === 'string' && entries.value.some((e) => e.contractKey === target)) {
    expanded.value = new Set([target])
  }
})
</script>

<style scoped>
.ledger { max-width: 1000px; }
.ledger-header { margin-bottom: 1.25rem; }
.ledger-header h2 { margin-bottom: 0.25rem; }
.ledger-sub { color: #6b7280; font-size: 0.875rem; }

.empty-state { background: white; border-radius: 12px; padding: 3rem 1.5rem; text-align: center; }
.empty-icon { font-size: 2.5rem; margin-bottom: 0.75rem; }
.empty-title { font-weight: 600; color: #374151; margin-bottom: 0.5rem; }
.empty-tip { color: #6b7280; font-size: 0.875rem; }

.ledger-list { display: flex; flex-direction: column; gap: 0.75rem; }
.ledger-card { background: white; border-radius: 12px; overflow: hidden; }
.ledger-row { display: flex; align-items: center; gap: 1rem; padding: 1rem 1.25rem; cursor: pointer; user-select: none; }
.ledger-row:hover { background: #f9fafb; }
.expand-icon { color: #9ca3af; font-size: 0.75rem; width: 1rem; flex-shrink: 0; }
.ledger-file { flex: 1; min-width: 0; display: flex; align-items: center; gap: 0.75rem; }
.filename { font-weight: 600; color: #111827; }
.audit-times { font-size: 0.75rem; color: #8b5cf6; background: #f5f3ff; padding: 0.125rem 0.5rem; border-radius: 9999px; }

.severity-badges { display: flex; gap: 0.375rem; flex-wrap: wrap; }
.badge { font-size: 0.75rem; padding: 0.125rem 0.5rem; border-radius: 9999px; }
.badge.critical { background: #fee2e2; color: #dc2626; }
.badge.high { background: #ffedd5; color: #ea580c; }
.badge.medium { background: #dbeafe; color: #2563eb; }
.badge.low { background: #f3f4f6; color: #4b5563; }
.badge.clean { background: #d1fae5; color: #059669; }

.ledger-count { font-size: 0.875rem; color: #dc2626; white-space: nowrap; }
.ledger-count.zero { color: #059669; }
.ledger-time { color: #6b7280; font-size: 0.8125rem; white-space: nowrap; min-width: 9rem; text-align: right; }

.ledger-detail { border-top: 1px solid #f3f4f6; padding: 0.5rem 1.25rem 1.25rem; }

.vuln-item { border-left: 4px solid; border-radius: 8px; background: #fafafa; padding: 0.875rem 1rem; margin-top: 0.75rem; }
.vuln-item.critical { border-color: #dc2626; background: #fef2f2; }
.vuln-item.high { border-color: #f59e0b; background: #fffbeb; }
.vuln-item.medium { border-color: #3b82f6; background: #eff6ff; }
.vuln-item.low { border-color: #6b7280; background: #f9fafb; }
.vuln-head { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem; flex-wrap: wrap; }
.vuln-type { font-weight: 600; color: #111827; }
.vuln-sev { font-size: 0.75rem; padding: 0.125rem 0.5rem; border-radius: 9999px; }
.vuln-sev.critical { background: #fee2e2; color: #dc2626; }
.vuln-sev.high { background: #ffedd5; color: #ea580c; }
.vuln-sev.medium { background: #dbeafe; color: #2563eb; }
.vuln-sev.low { background: #f3f4f6; color: #4b5563; }
.vuln-lines { font-size: 0.8125rem; color: #6b7280; font-family: monospace; margin-left: auto; }
.vuln-desc { color: #374151; font-size: 0.875rem; margin-bottom: 0.5rem; }
.vuln-fix { color: #059669; font-size: 0.875rem; margin-bottom: 0.5rem; }
.vuln-code { background: #1e1e1e; color: #d4d4d4; font-family: "Fira Code", monospace; font-size: 0.75rem; padding: 0.75rem; border-radius: 6px; overflow-x: auto; margin: 0; }

.clean-note { display: flex; gap: 0.75rem; align-items: flex-start; margin-top: 0.75rem; padding: 1rem; border-radius: 8px; background: #ecfdf5; border: 1px solid #a7f3d0; }
.clean-icon { font-size: 1.25rem; }
.clean-title { font-weight: 600; color: #065f46; margin-bottom: 0.25rem; }
.clean-desc { color: #047857; font-size: 0.875rem; margin-bottom: 0.25rem; }
.clean-meta { color: #6b7280; font-size: 0.75rem; }
</style>
