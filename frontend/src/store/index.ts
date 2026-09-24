import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

export interface Vulnerability {
  type: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  line: number
  lineStart?: number
  lineEnd?: number
  description: string
  suggestion: string
  code?: string
}

export interface GasIssue {
  functionName: string
  currentGas: number
  optimizedGas: number
  suggestion: string
}

export interface AuditResult {
  id: string
  filename: string
  score: number
  vulnerabilities: Vulnerability[]
  gasIssues: GasIssue[]
  timestamp: string
  duplicated?: boolean
  auditCount?: number
  codeHash?: string
}

export interface SeverityCounts {
  critical: number
  high: number
  medium: number
  low: number
}

export interface LedgerEntry {
  codeHash: string
  filename: string
  latestScore: number
  vulnCount: number
  latestTime: string
  createdTime: string
  auditCount: number
  severityCounts: SeverityCounts
  hasFindings: boolean
  vulnerabilities: Vulnerability[]
}

export interface HistoryEntry {
  codeHash: string
  filename: string
  score: number
  vulnCount: number
  timestamp: string
  auditCount: number
  hasFindings: boolean
}

export const useAuditStore = defineStore('audit', () => {
  const results = ref<AuditResult[]>([])
  const currentResult = ref<AuditResult | null>(null)
  const patterns = ref<any[]>([])
  const ledger = ref<LedgerEntry[]>([])
  const history = ref<HistoryEntry[]>([])

  async function uploadAndAudit(code: string, filename: string) {
    const res = await axios.post('/api/audit', { code, filename })
    currentResult.value = res.data.data
    results.value.unshift(res.data.data)
    return res.data.data
  }

  async function fetchPatterns() {
    const res = await axios.get('/api/patterns')
    patterns.value = res.data.data
  }

  async function fetchLedger() {
    const res = await axios.get('/api/ledger')
    ledger.value = res.data.data
    return ledger.value
  }

  async function fetchHistory() {
    const res = await axios.get('/api/history')
    history.value = res.data.data
    return history.value
  }

  return {
    results, currentResult, patterns, ledger, history,
    uploadAndAudit, fetchPatterns, fetchLedger, fetchHistory,
  }
})
