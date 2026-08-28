import React, { useState } from 'react';
import { 
  X, 
  ChevronDown, 
  ChevronRight, 
  Copy, 
  Check
} from 'lucide-react';
import type { CaseTrace } from '../types/api';

interface CaseTraceModalProps {
  trace: CaseTrace | null;
  loading: boolean;
  onClose: () => void;
}

export const CaseTraceModal: React.FC<CaseTraceModalProps> = ({ trace, loading, onClose }) => {
  const [copied, setCopied] = useState(false);
  const [expandedLogs, setExpandedLogs] = useState<Record<number, boolean>>({});

  if (!trace && !loading) return null;

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(val);
  };

  const handleCopyJson = () => {
    if (!trace) return;
    navigator.clipboard.writeText(JSON.stringify(trace, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const toggleLog = (id: number) => {
    setExpandedLogs(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const diagnosis = trace?.diagnoses?.[0];
  const decision = trace?.decisions?.[0];
  const execution = trace?.executions?.[0];
  const outcome = trace?.outcomes?.[0];

  const getStatusPill = (status: string) => {
    switch (status) {
      case 'recovered':
        return (
          <span className="font-mono text-xs text-emerald-400 bg-zinc-950 px-2 py-0.5 rounded border border-zinc-800">
            recovered
          </span>
        );
      case 'stopped_by_policy':
      case 'excluded':
        return (
          <span className="font-mono text-xs text-amber-400 bg-zinc-950 px-2 py-0.5 rounded border border-zinc-800">
            stopped_by_safety
          </span>
        );
      case 'escalated':
        return (
          <span className="font-mono text-xs text-purple-400 bg-zinc-950 px-2 py-0.5 rounded border border-zinc-800">
            escalated
          </span>
        );
      default:
        return (
          <span className="font-mono text-xs text-zinc-400 bg-zinc-950 px-2 py-0.5 rounded border border-zinc-800">
            unrecoverable
          </span>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/70 backdrop-blur-xs animate-fade-in">
      <div className="bg-zinc-900 border-l border-zinc-800 w-full max-w-2xl h-full flex flex-col shadow-2xl overflow-hidden animate-slide-in">
        <div className="p-4 border-b border-zinc-800 flex items-center justify-between bg-zinc-950">
          {loading || !trace ? (
            <div className="flex items-center gap-2 text-xs text-zinc-400 font-mono">
              <div className="w-3.5 h-3.5 border-2 border-zinc-500 border-t-transparent rounded-full animate-spin"></div>
              <span>Fetching case journey...</span>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <span className="text-sm font-bold font-mono text-zinc-100">Case #{trace.case.id}</span>
              {getStatusPill(outcome?.final_status || trace.case.status)}
            </div>
          )}

          <div className="flex items-center gap-2">
            {trace && (
              <button
                onClick={handleCopyJson}
                className="flex items-center gap-1 px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-mono transition-colors cursor-pointer"
                title="Copy full trace JSON"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copied ? 'Copied' : 'JSON'}</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1 rounded text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {trace && !loading && (
          <div className="p-5 overflow-y-auto space-y-5 flex-1 text-xs">
            <div className="bg-zinc-950 border border-zinc-800 rounded p-3 grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
              <div>
                <span className="text-[10px] text-zinc-500 uppercase block">Reference</span>
                <span className="text-zinc-200 text-xs">{trace.case.source_reference}</span>
              </div>
              <div>
                <span className="text-[10px] text-zinc-500 uppercase block">Customer</span>
                <span className="text-zinc-200 text-xs">{trace.case.customer_id}</span>
              </div>
              <div>
                <span className="text-[10px] text-zinc-500 uppercase block">Amount</span>
                <span className="text-emerald-400 text-xs font-bold">{formatCurrency(trace.case.amount)}</span>
              </div>
              <div>
                <span className="text-[10px] text-zinc-500 uppercase block">Type</span>
                <span className="text-zinc-300 text-xs">{trace.case.case_type}</span>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-2.5 font-mono">
                5-Stage Pipeline Journey
              </h4>

              <div className="border border-zinc-800 rounded bg-zinc-950 divide-y divide-zinc-800">
                <div className="p-3 flex items-start justify-between">
                  <div>
                    <span className="text-[10px] font-mono font-semibold uppercase text-zinc-400">1. Detector Stage</span>
                    <div className="text-xs font-semibold text-zinc-200 mt-0.5">
                      {trace.case.status === 'excluded' ? 'Disqualified by Guardrail' : 'Qualified Genuine at-Risk'}
                    </div>
                  </div>
                  <span className="text-[11px] font-mono text-zinc-500">
                    {trace.case.status === 'excluded' ? 'Fraud/Refund filter' : 'Passed security'}
                  </span>
                </div>

                <div className="p-3 flex items-start justify-between">
                  <div>
                    <span className="text-[10px] font-mono font-semibold uppercase text-zinc-400">2. Diagnosis Stage</span>
                    <div className="text-xs font-semibold text-zinc-200 mt-0.5">
                      {diagnosis ? (
                        <code className="text-blue-400 font-mono text-[11px] bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-800">
                          {diagnosis.root_cause}
                        </code>
                      ) : (
                        'N/A (Excluded)'
                      )}
                    </div>
                  </div>
                  {diagnosis && (
                    <div className="text-right font-mono text-[11px] text-zinc-400">
                      <div>Method: <strong className="text-zinc-200">{diagnosis.method}</strong></div>
                      <div>Confidence: <strong className="text-zinc-200">{(diagnosis.confidence * 100).toFixed(0)}%</strong></div>
                    </div>
                  )}
                </div>

                <div className="p-3 flex items-start justify-between">
                  <div>
                    <span className="text-[10px] font-mono font-semibold uppercase text-zinc-400">3. Strategist Stage</span>
                    <div className="text-xs font-semibold text-zinc-200 mt-0.5">
                      {decision ? (
                        <code className="text-purple-400 font-mono text-[11px] bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-800">
                          {decision.chosen_action}
                        </code>
                      ) : (
                        'N/A'
                      )}
                    </div>
                    {decision?.justification && (
                      <p className="text-xs text-zinc-400 font-sans mt-1.5 leading-relaxed bg-zinc-900 p-2.5 rounded border border-zinc-800">
                        {decision.justification}
                      </p>
                    )}
                  </div>
                  {decision && (
                    <span className="text-[11px] font-mono text-zinc-500">
                      Rule: {decision.policy_rule_id}
                    </span>
                  )}
                </div>

                <div className="p-3 flex items-start justify-between">
                  <div>
                    <span className="text-[10px] font-mono font-semibold uppercase text-zinc-400">4. Executor Stage</span>
                    <div className="text-xs font-semibold text-zinc-200 mt-0.5">
                      {execution ? (
                        <code className="text-zinc-200 font-mono text-[11px] bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-800">
                          {execution.channel}
                        </code>
                      ) : (
                        'None (Blocked/Halted)'
                      )}
                    </div>
                  </div>
                  {execution?.external_reference && (
                    <span className="text-[11px] font-mono text-zinc-400">
                      ID: {execution.external_reference}
                    </span>
                  )}
                </div>

                <div className="p-3 flex items-start justify-between bg-zinc-900/40">
                  <div>
                    <span className="text-[10px] font-mono font-semibold uppercase text-emerald-400">5. Final Outcome</span>
                    <div className="text-xs font-bold font-mono text-zinc-100 mt-0.5">
                      {outcome?.recovered ? (
                        <span className="text-emerald-400 font-bold">
                          {formatCurrency(outcome.recovered_amount || 0)} Recovered
                        </span>
                      ) : (
                        <span className="text-zinc-400">INR 0.00 Recovered ({outcome?.final_status || trace.case.status})</span>
                      )}
                    </div>
                  </div>
                  {outcome?.recovered_at && (
                    <span className="text-[11px] font-mono text-zinc-500">
                      {new Date(outcome.recovered_at).toLocaleTimeString()}
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-2.5 font-mono">
                Audit Log ({trace.audit_logs.length} Events)
              </h4>

              <div className="border border-zinc-800 rounded bg-zinc-950 divide-y divide-zinc-800">
                {trace.audit_logs.map((log) => {
                  const isExpanded = !!expandedLogs[log.id];
                  return (
                    <div key={log.id} className="p-2.5">
                      <div 
                        onClick={() => toggleLog(log.id)}
                        className="flex items-center justify-between cursor-pointer hover:text-zinc-200 transition-colors"
                      >
                        <div className="flex items-center gap-2 font-mono text-xs">
                          {isExpanded ? (
                            <ChevronDown className="w-3.5 h-3.5 text-zinc-500" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5 text-zinc-500" />
                          )}
                          <span className="font-bold uppercase bg-zinc-800 text-zinc-300 px-1.5 py-0.5 rounded text-[10px]">
                            {log.stage}
                          </span>
                          <span className="text-blue-400 font-semibold">
                            {log.event}
                          </span>
                        </div>

                        <span className="text-[11px] font-mono text-zinc-500">
                          {new Date(log.timestamp).toLocaleTimeString()}
                        </span>
                      </div>

                      {isExpanded && (
                        <pre className="mt-2 text-[11px] font-mono text-zinc-300 bg-zinc-900 p-2.5 rounded border border-zinc-800 overflow-x-auto">
                          {JSON.stringify(log.payload, null, 2)}
                        </pre>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
