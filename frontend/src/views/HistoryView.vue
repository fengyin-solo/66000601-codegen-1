<template>
  <div class="history">
    <h2>审计历史</h2>
    <p class="history-sub">
      <template v-if="loading">正在加载…</template>
      <template v-else-if="error">暂时无法获取审计历史，请确认后端服务已启动。</template>
      <template v-else>共 {{ history.length }} 条记录，与「风险台账」在册合约一一对应（同一份合约多次提交已合并）。</template>
    </p>

    <div v-if="!loading && !error && history.length === 0" class="empty-state">
      暂无审计记录，去「合约审计」提交一份合约试试。
    </div>

    <div v-else class="history-list">
      <div v-for="item in history" :key="item.contractKey" class="history-card">
        <div class="history-file">
          {{ item.filename }}
          <span v-if="item.auditCount > 1" class="times-tag">提交 {{ item.auditCount }} 次</span>
        </div>
        <div class="history-vulns" :class="item.vulnCount === 0 ? 'clean' : 'risk'">
          漏洞 {{ item.vulnCount }}
        </div>
        <div class="history-score" :class="item.score >= 70 ? 'high' : item.score >= 40 ? 'medium' : 'low'">{{ item.score }}分</div>
        <div class="history-time">{{ formatTime(item.timestamp) }}</div>
        <button class="btn-sm" @click="openLedger(item)">查看台账</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue"
import { useRouter } from "vue-router"
import { useAuditStore, type HistoryItem } from '@/store'

const router = useRouter()
const store = useAuditStore()
const history = ref<HistoryItem[]>([])
const loading = ref(true)
const error = ref(false)

function formatTime(iso: string) {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function openLedger(item: HistoryItem) {
  router.push({ path: '/ledger', query: { key: item.contractKey } })
}

onMounted(async () => {
  try {
    history.value = await store.fetchHistory()
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.history { max-width: 800px; }
.history-sub { color: #6b7280; font-size: 0.875rem; margin: 0.25rem 0 1.25rem; }
.empty-state { background: white; border-radius: 12px; padding: 2.5rem 1.5rem; text-align: center; color: #6b7280; }
.history-list { display: flex; flex-direction: column; gap: 1rem; }
.history-card { background: white; border-radius: 12px; padding: 1.25rem; display: flex; align-items: center; gap: 1rem; }
.history-file { flex: 1; font-weight: 600; display: flex; align-items: center; gap: 0.5rem; }
.times-tag { font-size: 0.75rem; color: #8b5cf6; background: #f5f3ff; padding: 0.125rem 0.5rem; border-radius: 9999px; font-weight: 400; }
.history-vulns { font-size: 0.875rem; padding: 0.25rem 0.625rem; border-radius: 8px; font-weight: 500; }
.history-vulns.risk { background: #fee2e2; color: #991b1b; }
.history-vulns.clean { background: #d1fae5; color: #065f46; }
.history-score { padding: 0.25rem 0.75rem; border-radius: 8px; font-weight: 600; font-size: 0.875rem; }
.history-score.high { background: #d1fae5; color: #065f46; }
.history-score.medium { background: #fef3c7; color: #92400e; }
.history-score.low { background: #fee2e2; color: #991b1b; }
.history-time { color: #6b7280; font-size: 0.875rem; }
.btn-sm { background: #e5e7eb; border: none; padding: 0.25rem 0.75rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }
.btn-sm:hover { background: #d1d5db; }
</style>
