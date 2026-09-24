import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import type { ApiResponse } from '@/types'

export type Severity = 'critical' | 'high' | 'medium' | 'low'

export interface Vulnerability {
  type: string
  severity: Severity
  line: number
  lineStart: number
  lineEnd: number
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
  contractKey?: string
  filename: string
  score: number
  vulnerabilities: Vulnerability[]
  gasIssues: GasIssue[]
  auditCount?: number
  timestamp: string
}

export interface LedgerEntry {
  contractKey: string
  filename: string
  score: number
  vulnCount: number
  severityCounts: Record<Severity, number>
  auditCount: number
  firstAuditAt: string
  lastAuditAt: string
  vulnerabilities: Vulnerability[]
  note: string | null
}

export interface HistoryItem {
  contractKey: string
  filename: string
  score: number
  vulnCount: number
  severityCounts: Record<Severity, number>
  auditCount: number
  timestamp: string
}

export const useAuditStore = defineStore('audit', () => {
  const results = ref<AuditResult[]>([])
  const currentResult = ref<AuditResult | null>(null)
  const patterns = ref<any[]>([])
  const ledger = ref<LedgerEntry[]>([])
  const history = ref<HistoryItem[]>([])

  async function uploadAndAudit(code: string, filename: string) {
    const res = await axios.post<ApiResponse<AuditResult>>('/api/audit', { code, filename })
    currentResult.value = res.data.data
    results.value.unshift(res.data.data)
    return res.data.data
  }

  async function fetchPatterns() {
    const res = await axios.get<ApiResponse<any[]>>('/api/patterns')
    patterns.value = res.data.data
  }

  async function fetchLedger() {
    const res = await axios.get<ApiResponse<LedgerEntry[]>>('/api/ledger')
    ledger.value = res.data.data
    return ledger.value
  }

  async function fetchHistory() {
    const res = await axios.get<ApiResponse<HistoryItem[]>>('/api/history')
    history.value = res.data.data
    return history.value
  }

  return {
    results,
    currentResult,
    patterns,
    ledger,
    history,
    uploadAndAudit,
    fetchPatterns,
    fetchLedger,
    fetchHistory
  }
})
