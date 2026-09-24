<template>
  <div class="ledger">
    <div class="ledger-head">
      <h2>风险台账</h2>
      <button class="btn-refresh" @click="load" :disabled="loading">
        {{ loading ? "加载中..." : "刷新" }}
      </button>
    </div>

    <div v-if="error" class="state-box error">{{ error }}</div>

    <template v-else-if="loaded">
      <div v-if="entries.length === 0" class="state-box empty">
        台账暂无记录。提交合约完成一次审计后，风险会自动登记到这里。
      </div>

      <template v-else>
        <div class="summary">
          <div class="summary-item">
            <span class="summary-num">{{ entries.length }}</span>
            <span class="summary-label">合约总数</span>
          </div>
          <div v-for="sev in severityMeta" :key="sev.key" class="summary-item">
            <span class="summary-num" :class="sev.key">{{ totals[sev.key] }}</span>
            <span class="summary-label">{{ sev.label }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-num">{{ cleanCount }}</span>
            <span class="summary-label">未发现问题</span>
          </div>
        </div>

        <div class="contract-list">
          <div v-for="entry in entries" :key="entry.codeHash" class="contract-card">
            <div class="contract-row" @click="toggle(entry.codeHash)">
              <span class="caret" :class="{ open: openSet.has(entry.codeHash) }">▶</span>
              <span class="contract-name">{{ entry.filename }}</span>
              <span class="badges">
                <span
                  v-for="sev in severityMeta"
                  :key="sev.key"
                  v-show="entry.severityCounts[sev.key] > 0"
                  class="badge"
                  :class="sev.key"
                >{{ sev.short }} {{ entry.severityCounts[sev.key] }}</span>
                <span v-if="!entry.hasFindings" class="badge clean">✓ 未发现问题</span>
              </span>
              <span class="contract-meta">
                最近审计 {{ formatTime(entry.latestTime) }} · 共审计 {{ entry.auditCount }} 次 ·
                最近发现 <b :class="{ zero: !entry.hasFindings }">{{ entry.vulnCount }}</b> 个问题
              </span>
              <span class="score" :class="scoreClass(entry.latestScore)">{{ entry.latestScore }}分</span>
            </div>

            <div v-if="openSet.has(entry.codeHash)" class="contract-detail">
              <!-- 无问题合约：给出明确说明，不留空白 -->
              <div v-if="!entry.hasFindings" class="clean-detail">
                <div class="clean-title">✓ 最近一次审计未发现安全漏洞</div>
                <div class="clean-desc">
                  已按当前漏洞模式库（重入攻击、整数溢出、未授权访问、selfdestruct、tx.origin、精度损失等）完成扫描，
                  评分 {{ entry.latestScore }} 分。不代表绝对安全，建议结合人工复审与业务逻辑审计。
                </div>
                <div class="clean-meta">
                  最近审计时间：{{ formatTime(entry.latestTime) }} · 累计提交 {{ entry.auditCount }} 次
                </div>
              </div>

              <table v-else class="vuln-table">
                <thead>
                  <tr>
                    <th class="col-sev">严重程度</th>
                    <th class="col-type">漏洞</th>
                    <th class="col-lines">代码行号</th>
                    <th class="col-desc">说明</th>
                    <th class="col-fix">修复建议</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(v, i) in entry.vulnerabilities" :key="i">
                    <td>
                      <span class="badge" :class="v.severity">{{ severityLabel(v.severity) }}</span>
                    </td>
                    <td class="vuln-type">{{ v.type }}</td>
                    <td class="vuln-lines">
                      <code>{{ lineRange(v) }}</code>
                    </td>
                    <td class="vuln-desc">{{ v.description }}</td>
                    <td class="vuln-fix">{{ v.suggestion }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useAuditStore } from '@/store'

const store = useAuditStore()
const { ledger: entries } = storeToRefs(store)

const loading = ref(false)
const loaded = ref(false)
const error = ref('')
const openSet = reactive(new Set<string>())

const severityMeta = [
  { key: 'critical', label: '严重', short: '严重' },
  { key: 'high', label: '高危', short: '高危' },
  { key: 'medium', label: '中危', short: '中危' },
  { key: 'low', label: '低危', short: '低危' },
] as const

const totals = computed(() => {
  const t: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0 }
  for (const e of entries.value) {
    for (const k of Object.keys(t)) {
      const counts = e.severityCounts as Record<string, number>
      t[k] += counts[k] ?? 0
    }
  }
  return t
})

const cleanCount = computed(() => entries.value.filter(e => !e.hasFindings).length)

function toggle(hash: string) {
  if (openSet.has(hash)) openSet.delete(hash)
  else openSet.add(hash)
}

function severityLabel(sev: string) {
  return severityMeta.find(s => s.key === sev)?.label ?? sev
}

function lineRange(v: { lineStart?: number; lineEnd?: number; line: number }) {
  const start = v.lineStart ?? v.line
  return v.lineEnd && v.lineEnd !== start ? `${start}-${v.lineEnd} 行` : `${start} 行`
}

function scoreClass(score: number) {
  if (score >= 80) return 'high'
  if (score >= 50) return 'medium'
  return 'low'
}

function formatTime(iso: string) {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    await store.fetchLedger()
    loaded.value = true
  } catch (e: any) {
    error.value = '台账加载失败，请确认后端服务已启动（' + (e?.message ?? '未知错误') + '）'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.ledger { max-width: 1100px; }
.ledger-head { display: flex; align-items: center; justify-content: space-between; }
.btn-refresh { background: #8b5cf6; color: white; border: none; padding: 0.4rem 1.1rem; border-radius: 8px; cursor: pointer; }
.btn-refresh:disabled { opacity: 0.5; cursor: not-allowed; }

.state-box { border-radius: 12px; padding: 2rem; text-align: center; margin-top: 1rem; }
.state-box.empty { background: white; color: #6b7280; border: 1px dashed #d1d5db; }
.state-box.error { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }

.summary { display: flex; gap: 1rem; margin: 1rem 0; }
.summary-item { background: white; border-radius: 12px; padding: 1rem 1.5rem; display: flex; flex-direction: column; align-items: center; min-width: 90px; }
.summary-num { font-size: 1.6rem; font-weight: 700; color: #111827; }
.summary-num.critical { color: #dc2626; }
.summary-num.high { color: #d97706; }
.summary-num.medium { color: #2563eb; }
.summary-num.low { color: #6b7280; }
.summary-label { font-size: 0.8rem; color: #6b7280; margin-top: 0.25rem; }

.contract-list { display: flex; flex-direction: column; gap: 0.75rem; }
.contract-card { background: white; border-radius: 12px; overflow: hidden; }
.contract-row { display: flex; align-items: center; gap: 0.75rem; padding: 1rem 1.25rem; cursor: pointer; user-select: none; }
.contract-row:hover { background: #faf9ff; }
.caret { font-size: 0.7rem; color: #9ca3af; transition: transform 0.15s; }
.caret.open { transform: rotate(90deg); }
.contract-name { font-weight: 600; min-width: 140px; }
.badges { display: flex; gap: 0.375rem; flex-wrap: wrap; }
.badge { padding: 0.15rem 0.6rem; border-radius: 9999px; font-size: 0.72rem; font-weight: 600; }
.badge.critical { background: #fee2e2; color: #dc2626; }
.badge.high { background: #fef3c7; color: #b45309; }
.badge.medium { background: #dbeafe; color: #1d4ed8; }
.badge.low { background: #f3f4f6; color: #4b5563; }
.badge.clean { background: #d1fae5; color: #065f46; }
.contract-meta { margin-left: auto; font-size: 0.8rem; color: #6b7280; white-space: nowrap; }
.contract-meta b { color: #dc2626; }
.contract-meta b.zero { color: #059669; }
.score { padding: 0.25rem 0.7rem; border-radius: 8px; font-weight: 700; font-size: 0.85rem; }
.score.high { background: #d1fae5; color: #065f46; }
.score.medium { background: #fef3c7; color: #92400e; }
.score.low { background: #fee2e2; color: #991b1b; }

.contract-detail { border-top: 1px solid #f3f4f6; padding: 1rem 1.25rem; background: #fcfcfe; }
.clean-detail { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; padding: 1rem 1.25rem; }
.clean-title { font-weight: 600; color: #15803d; margin-bottom: 0.4rem; }
.clean-desc { color: #374151; font-size: 0.85rem; line-height: 1.6; }
.clean-meta { margin-top: 0.5rem; font-size: 0.78rem; color: #6b7280; }

.vuln-table { width: 100%; border-collapse: collapse; font-size: 0.83rem; }
.vuln-table th { text-align: left; color: #6b7280; font-weight: 600; padding: 0.4rem 0.6rem; border-bottom: 1px solid #e5e7eb; }
.vuln-table td { padding: 0.6rem; vertical-align: top; border-bottom: 1px solid #f3f4f6; line-height: 1.5; }
.col-sev { width: 70px; }
.col-lines { width: 90px; }
.vuln-type { font-weight: 600; color: #111827; white-space: nowrap; }
.vuln-lines code { background: #eef2ff; color: #4338ca; padding: 0.1rem 0.45rem; border-radius: 4px; font-family: monospace; white-space: nowrap; }
.vuln-desc { color: #4b5563; }
.vuln-fix { color: #6d28d9; }
</style>
