import type {
  RecoveryCase,
  CaseTrace,
  PaginatedCases,
  EvaluationReport,
  PolicyRule,
  GuardrailStatus,
  BatchRunResult
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const api = {
  async getHealth(): Promise<{ status: string; service: string; environment: string; kill_switch_active: boolean }> {
    const res = await fetch('http://localhost:8000/health');
    if (!res.ok) throw new Error('Health check failed');
    return res.json();
  },

  async getAnalyticsSummary(): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/analytics/summary`);
    if (!res.ok) throw new Error('Failed to fetch analytics summary');
    return res.json();
  },

  async getAnalyticsBreakdown(): Promise<EvaluationReport> {
    const res = await fetch(`${API_BASE_URL}/analytics/breakdown`);
    if (!res.ok) throw new Error('Failed to fetch analytics breakdown');
    return res.json();
  },

  async getCases(params: {
    status?: string;
    case_type?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedCases> {
    const query = new URLSearchParams();
    if (params.status) query.set('status', params.status);
    if (params.case_type) query.set('case_type', params.case_type);
    if (params.search) query.set('search', params.search);
    if (params.limit !== undefined) query.set('limit', params.limit.toString());
    if (params.offset !== undefined) query.set('offset', params.offset.toString());

    const res = await fetch(`${API_BASE_URL}/cases?${query.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch cases');
    return res.json();
  },

  async getCase(caseId: number): Promise<RecoveryCase> {
    const res = await fetch(`${API_BASE_URL}/cases/${caseId}`);
    if (!res.ok) throw new Error(`Failed to fetch case ${caseId}`);
    return res.json();
  },

  async getCaseTrace(caseId: number): Promise<CaseTrace> {
    const res = await fetch(`${API_BASE_URL}/cases/${caseId}/trace`);
    if (!res.ok) throw new Error(`Failed to fetch trace for case ${caseId}`);
    return res.json();
  },

  async getPolicies(): Promise<{ total_rules: number; rules: PolicyRule[] }> {
    const res = await fetch(`${API_BASE_URL}/policies`);
    if (!res.ok) throw new Error('Failed to fetch policies');
    return res.json();
  },

  async getGuardrailStatus(): Promise<GuardrailStatus> {
    const res = await fetch(`${API_BASE_URL}/guardrails/status`);
    if (!res.ok) throw new Error('Failed to fetch guardrail status');
    return res.json();
  },

  async toggleKillSwitch(active: boolean): Promise<GuardrailStatus> {
    const res = await fetch(`${API_BASE_URL}/guardrails/kill-switch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kill_switch_active: active }),
    });
    if (!res.ok) throw new Error('Failed to toggle kill switch');
    return res.json();
  },

  async triggerBatchRun(options: { concurrency?: number; limit?: number; seed_fresh?: boolean }): Promise<BatchRunResult> {
    const res = await fetch(`${API_BASE_URL}/cases/batch-run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        concurrency: options.concurrency ?? 5,
        limit: options.limit,
        seed_fresh: options.seed_fresh ?? false,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Batch orchestration failed' }));
      throw new Error(err.detail || 'Batch orchestration failed');
    }
    return res.json();
  },

  async ingestCase(payload: {
    case_type: string;
    source_reference: string;
    customer_id: string;
    amount: number;
    currency?: string;
    auto_process?: boolean;
    metadata?: Record<string, any>;
  }): Promise<RecoveryCase> {
    const res = await fetch(`${API_BASE_URL}/cases/ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Ingestion failed' }));
      throw new Error(err.detail || 'Ingestion failed');
    }
    return res.json();
  },
};
