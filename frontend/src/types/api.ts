export type CaseType = 'payment_failure' | 'checkout_abandonment' | 'subscription_failure';

export type CaseStatus = 
  | 'open'
  | 'detected_at_risk'
  | 'excluded'
  | 'diagnosed'
  | 'decided'
  | 'recovered'
  | 'failed'
  | 'escalated'
  | 'stopped_by_policy'
  | 'stage_failure';

export type FinalStatus = 'recovered' | 'failed' | 'escalated' | 'stopped_by_policy';

export interface RecoveryCase {
  id: number;
  case_type: CaseType;
  source_reference: string;
  customer_id: string;
  amount: number;
  currency: string;
  status: CaseStatus;
  created_at: string;
}

export interface Diagnosis {
  id: number;
  case_id: number;
  root_cause: string;
  confidence: number;
  evidence: Record<string, any>;
  method: 'rule' | 'llm';
  created_at: string;
}

export interface Decision {
  id: number;
  case_id: number;
  diagnosis_id: number;
  chosen_action: string;
  justification: string;
  policy_rule_id: string;
  guardrail_checks_passed: boolean;
  created_at: string;
}

export interface Execution {
  id: number;
  decision_id: number;
  channel: string;
  external_reference?: string;
  status: string;
  raw_response: Record<string, any>;
  executed_at: string;
}

export interface Outcome {
  id: number;
  case_id: number;
  recovered: boolean;
  recovered_amount?: number;
  recovered_at?: string;
  final_status: FinalStatus;
}

export interface AuditLog {
  id: number;
  case_id: number;
  stage: string;
  event: string;
  payload: Record<string, any>;
  timestamp: string;
}

export interface CaseTrace {
  case: RecoveryCase;
  diagnoses: Diagnosis[];
  decisions: Decision[];
  executions: Execution[];
  outcomes: Outcome[];
  audit_logs: AuditLog[];
}

export interface PaginatedCases {
  items: RecoveryCase[];
  total: number;
  limit: number;
  offset: number;
}

export interface CaseTypeBreakdownItem {
  total_cases: number;
  at_risk_amount: number;
  recovered_amount: number;
  recovered_count: number;
  recovery_rate_pct: number;
}

export interface RootCauseBreakdownItem {
  total_cases: number;
  at_risk_amount: number;
  recovered_amount: number;
  recovered_count: number;
  recovery_rate_pct: number;
}

export interface ChannelCostBreakdownItem {
  actions_count: number;
  unit_cost: number;
  total_cost: number;
}

export interface ExceptionRecord {
  case_id: number;
  source_reference: string;
  case_type: string;
  amount: number;
  root_cause: string;
  final_status: string;
  stop_reason: string;
}

export interface EvaluationReport {
  generated_at: string;
  total_cases: number;
  total_at_risk_amount: number;
  total_recovered_amount: number;
  gross_recovery_rate_pct: number;
  total_intervention_cost: number;
  net_recovered_amount: number;
  roi_multiplier: number;
  precision_metric: {
    total_disqualified_cases: number;
    correctly_excluded_cases: number;
    false_action_count: number;
    precision_score_pct: number;
  };
  case_type_breakdown: Record<string, CaseTypeBreakdownItem>;
  root_cause_breakdown: Record<string, RootCauseBreakdownItem>;
  channel_cost_breakdown: Record<string, ChannelCostBreakdownItem>;
  time_to_recovery_distribution: {
    average_seconds: number;
    median_seconds: number;
    min_seconds: number;
    max_seconds: number;
    sample_size: number;
  };
  exception_list: ExceptionRecord[];
}

export interface PolicyRule {
  rule_id: string;
  root_cause: string;
  allowed_actions: string[];
  default_action: string;
  max_retries: number;
  cooldown_hours: number;
  template_justification: string;
}

export interface GuardrailStatus {
  kill_switch_active: boolean;
  daily_customer_cap: number;
  channel_timeout_seconds: number;
  total_active_policies: number;
}

export interface BatchRunResult {
  status: string;
  processed_count: number;
  total_cases: number;
  recovered_count: number;
  total_at_risk_amount: number;
  total_recovered_amount: number;
  net_recovery_rate_pct: number;
  elapsed_seconds: number;
  status_breakdown: Record<string, number>;
}
