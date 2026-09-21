<template>
  <div class="history">
    <h2>审计历史</h2>
    <div class="history-list">
      <div v-for="item in history" :key="item.id" class="history-card">
        <div class="history-file">{{ item.filename }}</div>
        <div class="history-score" :class="item.score >= 70 ? 'high' : item.score >= 40 ? 'medium' : 'low'">{{ item.score }}分</div>
        <div class="history-time">{{ item.timestamp }}</div>
        <button class="btn-sm">查看详情</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue"
const history = ref([
  { id: "1", filename: "SimpleBank.sol", score: 45, timestamp: "2026-09-21 10:30" },
  { id: "2", filename: "Token.sol", score: 78, timestamp: "2026-09-20 15:20" },
  { id: "3", filename: "Auction.sol", score: 32, timestamp: "2026-09-19 09:15" },
])
</script>

<style scoped>
.history { max-width: 800px; }
.history-list { display: flex; flex-direction: column; gap: 1rem; }
.history-card { background: white; border-radius: 12px; padding: 1.25rem; display: flex; align-items: center; gap: 1rem; }
.history-file { flex: 1; font-weight: 600; }
.history-score { padding: 0.25rem 0.75rem; border-radius: 8px; font-weight: 600; font-size: 0.875rem; }
.history-score.high { background: #d1fae5; color: #065f46; }
.history-score.medium { background: #fef3c7; color: #92400e; }
.history-score.low { background: #fee2e2; color: #991b1b; }
.history-time { color: #6b7280; font-size: 0.875rem; }
.btn-sm { background: #e5e7eb; border: none; padding: 0.25rem 0.75rem; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }
</style>