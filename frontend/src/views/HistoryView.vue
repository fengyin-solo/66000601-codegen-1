<template>
  <div class="history">
    <div class="history-head">
      <h2>审计历史</h2>
      <div class="head-actions">
        <span class="count-hint">共 {{ history.length }} 份合约（与风险台账一致）</span>
        <button class="btn-sm primary" @click="goLedger">查看风险台账</button>
        <button class="btn-sm" @click="load" :disabled="loading">{{ loading ? "加载中..." : "刷新" }}</button>
      </div>
    </div>

    <div v-if="error" class="state-box error">{{ error }}</div>
    <div v-else-if="loaded && history.length === 0" class="state-box empty">
      暂无审计记录。前往「合约审计」粘贴代码并完成审计后，记录会出现在这里。
    </div>

    <div v-else class="history-list">
      <div v-for="item in history" :key="item.codeHash" class="history-card">
        <div class="history-file">{{ item.filename }}</div>
        <div class="history-findings">
          <span v-if="item.hasFindings" class="finding-badge">{{ item.vulnCount }} 个问题</span>
          <span v-else class="finding-badge clean">未发现问题</span>
          <span v-if="item.auditCount > 1" class="audit-times">已提交 {{ item.auditCount }} 次</span>
        </div>
        <div class="history-score" :class="item.score >= 70 ? 'high' : item.score >= 40 ? 'medium' : 'low'">{{ item.score }}分</div>
        <div class="history-time">{{ formatTime(item.timestamp) }}</div>
        <button class="btn-sm" @click="goLedger">查看详情</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useAuditStore } from '@/store'

const store = useAuditStore()
const { history } = storeToRefs(store)
const router = useRouter()

const loading = ref(false)
const loaded = ref(false)
const error = ref('')

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
    await store.fetchHistory()
    loaded.value = true
  } catch (e: any) {
    error.value = '历史记录加载失败，请确认后端服务已启动（' + (e?.message ?? '未知错误') + '）'
  } finally {
    loading.value = false
  }
}

function goLedger() {
  router.push('/ledger')
}

onMounted(load)
</script>

<style scoped>
.history { max-width: 900px; }
.history-head { display: flex; align-items: center; justify-content: space-between; }
.head-actions { display: flex; align-items: center; gap: 0.75rem; }
.count-hint { font-size: 0.82rem; color: #6b7280; }
.history-list { display: flex; flex-direction: column; gap: 1rem; margin-top: 1rem; }
.history-card { background: white; border-radius: 12px; padding: 1.25rem; display: flex; align-items: center; gap: 1rem; }
.history-file { flex: 1; font-weight: 600; }
.history-findings { display: flex; align-items: center; gap: 0.5rem; }
.finding-badge { padding: 0.2rem 0.6rem; border-radius: 9999px; font-size: 0.75rem; background: #fee2e2; color: #b91c1c; white-space: nowrap; }
.finding-badge.clean { background: #d1fae5; color: #065f46; }
.audit-times { font-size: 0.75rem; color: #6b7280; white-space: nowrap; }
.history-score { padding: 0.25rem 0.75rem; border-radius: 8px; font-weight: 600; font-size: 0.875rem; }
.history-score.high { background: #d1fae5; color: #065f46; }
.history-score.medium { background: #fef3c7; color: #92400e; }
.history-score.low { background: #fee2e2; color: #991b1b; }
.history-time { color: #6b7280; font-size: 0.875rem; white-space: nowrap; }
.btn-sm { background: #e5e7eb; border: none; padding: 0.35rem 0.85rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }
.btn-sm.primary { background: #8b5cf6; color: white; }
.btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }
.state-box { border-radius: 12px; padding: 2rem; text-align: center; margin-top: 1rem; }
.state-box.empty { background: white; color: #6b7280; border: 1px dashed #d1d5db; }
.state-box.error { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
</style>
