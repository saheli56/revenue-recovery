import React from 'react';
import type { EvaluationReport } from '../types/api';

interface OverviewTabProps {
  report: EvaluationReport | null;
  loading: boolean;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({ report, loading }) => {
  if (loading || !report) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="flex flex-col items-center gap-2.5">
          <div className="w-5 h-5 border-2 border-zinc-400 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-xs text-zinc-500 font-mono">Computing metrics...</span>
        </div>
      </div>
    );
  }

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(val);
  };

  const recoveredCount = Object.values(report.case_type_breakdown).reduce(
    (acc, cur) => acc + cur.recovered_count,
    0
  );

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-zinc-800">
        <div>
          <h1 className="text-lg font-semibold text-zinc-100 tracking-tight">Recovery Performance & Accounting</h1>
          <p className="text-xs text-zinc-400 mt-0.5">Real-time outcome metrics computed across synthetic portfolio batch</p>
        </div>
        <div className="text-xs text-zinc-400 bg-zinc-900 px-2.5 py-1 rounded border border-zinc-800 font-mono">
          Average Resolution: <strong className="text-zinc-200">{report.time_to_recovery_distribution.average_seconds.toFixed(1)}s</strong>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
          <span className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider block mb-1">Total Recovered</span>
          <div className="text-2xl font-bold text-zinc-100 font-mono">
            {formatCurrency(report.total_recovered_amount)}
          </div>
          <div className="mt-1.5 text-xs text-zinc-400 font-mono">
            <strong className="text-zinc-200">{report.gross_recovery_rate_pct.toFixed(1)}%</strong> recovery rate ({recoveredCount} cases)
          </div>
        </div>

        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
          <span className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider block mb-1">Net Recovered Value</span>
          <div className="text-2xl font-bold text-zinc-100 font-mono">
            {formatCurrency(report.net_recovered_amount)}
          </div>
          <div className="mt-1.5 text-xs text-zinc-400 font-mono">
            After {formatCurrency(report.total_intervention_cost)} channel fees
          </div>
        </div>

        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
          <span className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider block mb-1">Cost ROI Multiplier</span>
          <div className="text-2xl font-bold text-zinc-100 font-mono">
            {report.roi_multiplier.toFixed(1)}x
          </div>
          <div className="mt-1.5 text-xs text-zinc-400 font-mono">
            Net return per ₹1 spent
          </div>
        </div>

        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
          <span className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider block mb-1">Guardrail Precision</span>
          <div className="text-2xl font-bold text-zinc-100 font-mono">
            {report.precision_metric.precision_score_pct.toFixed(1)}%
          </div>
          <div className="mt-1.5 text-xs text-zinc-400 font-mono">
            {report.precision_metric.correctly_excluded_cases} invalid risks halted
          </div>
        </div>
      </div>

      <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3.5">
          <div>
            <h2 className="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">4-Stage Pipeline Resolution</h2>
            <p className="text-[11px] text-zinc-400 mt-0.5">Automated path from transaction dropoff to settled recovery</p>
          </div>
          <span className="text-[10px] font-mono text-zinc-400 bg-zinc-950 px-2 py-0.5 rounded border border-zinc-800">
            Automated
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-2.5">
          <div className="p-3 rounded bg-zinc-950 border border-zinc-800 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-zinc-400 mb-1">
                <span className="text-[10px] font-mono font-medium uppercase text-zinc-400">1. Detect</span>
                <span className="text-[10px] font-mono text-zinc-500">{report.total_cases}</span>
              </div>
              <div className="text-xs font-medium text-zinc-200">Failed / Dropoff Events</div>
            </div>
            <div className="text-xs font-mono text-zinc-400 mt-2.5 pt-2 border-t border-zinc-800/80">
              {formatCurrency(report.total_at_risk_amount)}
            </div>
          </div>

          <div className="p-3 rounded bg-zinc-950 border border-zinc-800 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-zinc-400 mb-1">
                <span className="text-[10px] font-mono font-medium uppercase text-zinc-400">2. Filter</span>
                <span className="text-[10px] font-mono text-zinc-500">{report.precision_metric.total_disqualified_cases}</span>
              </div>
              <div className="text-xs font-medium text-zinc-200">Safety & Guardrails</div>
            </div>
            <div className="text-xs font-mono text-zinc-400 mt-2.5 pt-2 border-t border-zinc-800/80">
              Fraud/Duplicate Defense
            </div>
          </div>

          <div className="p-3 rounded bg-zinc-950 border border-zinc-800 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-zinc-400 mb-1">
                <span className="text-[10px] font-mono font-medium uppercase text-zinc-400">3. Intervene</span>
                <span className="text-[10px] font-mono text-zinc-500">{report.total_cases - report.precision_metric.total_disqualified_cases}</span>
              </div>
              <div className="text-xs font-medium text-zinc-200">Diagnosis & Actions</div>
            </div>
            <div className="text-xs font-mono text-zinc-400 mt-2.5 pt-2 border-t border-zinc-800/80">
              Bounded Policies
            </div>
          </div>

          <div className="p-3 rounded bg-zinc-950 border border-zinc-800 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between text-zinc-400 mb-1">
                <span className="text-[10px] font-mono font-medium uppercase text-zinc-400">4. Recover</span>
                <span className="text-[10px] font-mono text-zinc-500">{recoveredCount}</span>
              </div>
              <div className="text-xs font-medium text-zinc-200">Revenue Captured</div>
            </div>
            <div className="text-xs font-mono text-zinc-100 font-bold mt-2.5 pt-2 border-t border-zinc-800/80">
              {formatCurrency(report.total_recovered_amount)}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4 flex flex-col">
          <div className="mb-3">
            <h2 className="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">Performance by Problem Type</h2>
          </div>

          <div className="space-y-2.5 flex-1">
            {Object.entries(report.case_type_breakdown).map(([typeKey, b]) => {
              const formattedType = typeKey
                .split('_')
                .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                .join(' ');
              return (
                <div key={typeKey} className="p-2.5 rounded bg-zinc-950 border border-zinc-800">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-zinc-200">{formattedType}</span>
                    <span className="text-xs font-mono text-zinc-300 font-semibold">{b.recovery_rate_pct.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-zinc-900 rounded-full h-1 overflow-hidden mb-1.5">
                    <div
                      className="bg-zinc-400 h-1 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, Math.max(0, b.recovery_rate_pct))}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-zinc-500 font-mono">
                    <span>{b.recovered_count} / {b.total_cases} cases</span>
                    <span>{formatCurrency(b.recovered_amount)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4 flex flex-col">
          <div className="mb-3">
            <h2 className="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">Failure Reasons & Conversion</h2>
          </div>

          <div className="space-y-2 flex-1 overflow-y-auto max-h-72 pr-1">
            {Object.entries(report.root_cause_breakdown)
              .sort((a, b) => b[1].recovery_rate_pct - a[1].recovery_rate_pct)
              .slice(0, 6)
              .map(([causeKey, b]) => {
                const formattedCause = causeKey
                  .split('_')
                  .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                  .join(' ');
                return (
                  <div key={causeKey} className="p-2 rounded bg-zinc-950 border border-zinc-800 flex items-center justify-between">
                    <div>
                      <div className="text-xs font-medium text-zinc-300">{formattedCause}</div>
                      <div className="text-[10px] font-mono text-zinc-500">
                        {b.recovered_count} of {b.total_cases} resolved
                      </div>
                    </div>
                    <div className="text-right font-mono text-xs">
                      <div className="text-zinc-200 font-semibold">
                        {b.recovery_rate_pct.toFixed(0)}%
                      </div>
                      <div className="text-[10px] text-zinc-400">
                        {formatCurrency(b.recovered_amount)}
                      </div>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      </div>
    </div>
  );
};
