import React, { useState } from 'react';
import { 
  RefreshCw, 
  AlertOctagon,
  Check
} from 'lucide-react';
import type { PolicyRule, GuardrailStatus } from '../types/api';

interface PoliciesTabProps {
  policies: PolicyRule[];
  guardrailStatus: GuardrailStatus | null;
  loading: boolean;
  onToggleKillSwitch: (active: boolean) => Promise<void>;
}

export const PoliciesTab: React.FC<PoliciesTabProps> = ({
  policies,
  guardrailStatus,
  onToggleKillSwitch,
}) => {
  const [toggling, setToggling] = useState(false);

  const handleKillSwitch = async () => {
    if (!guardrailStatus) return;
    setToggling(true);
    try {
      await onToggleKillSwitch(!guardrailStatus.kill_switch_active);
    } finally {
      setToggling(false);
    }
  };

  const formatRootCauseName = (cause: string) => {
    return cause
      .split('_')
      .map(w => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-zinc-800">
        <div>
          <h1 className="text-lg font-semibold text-zinc-100 tracking-tight">Recovery Rules & Safety Guardrails</h1>
          <p className="text-xs text-zinc-400 mt-0.5">Deterministic policy decision table governing automated actions</p>
        </div>
        <div className="text-xs font-mono text-zinc-400 bg-zinc-900 px-2.5 py-1 rounded border border-zinc-800">
          <strong className="text-zinc-200">{policies.length}</strong> Active Rules Enforced
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="p-4 rounded-lg bg-zinc-900/60 border border-zinc-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase font-mono text-zinc-300">
                Global Kill Switch
              </span>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                guardrailStatus?.kill_switch_active
                  ? 'bg-red-950 text-red-400 border border-red-800'
                  : 'bg-zinc-950 text-zinc-400 border border-zinc-800'
              }`}>
                {guardrailStatus?.kill_switch_active ? 'HALTED' : 'NORMAL'}
              </span>
            </div>

            <p className="text-xs text-zinc-400 mb-4 leading-relaxed">
              Circuit breaker halts all automatic charge retries, payment link creations, and dunning dispatches across all stages.
            </p>
          </div>

          <button
            onClick={handleKillSwitch}
            disabled={toggling}
            className={`w-full py-2 px-3 rounded text-xs font-medium transition-colors flex items-center justify-center gap-1.5 cursor-pointer ${
              guardrailStatus?.kill_switch_active
                ? 'bg-zinc-100 text-zinc-950 hover:bg-zinc-200'
                : 'bg-red-950/80 hover:bg-red-900/80 text-red-200 border border-red-800/80'
            }`}
          >
            {toggling ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : guardrailStatus?.kill_switch_active ? (
              <>
                <Check className="w-3.5 h-3.5" /> Disengage Kill Switch (Resume Engine)
              </>
            ) : (
              <>
                <AlertOctagon className="w-3.5 h-3.5" /> Halt All Automated Actions
              </>
            )}
          </button>
        </div>

        <div className="p-4 rounded-lg bg-zinc-900/60 border border-zinc-800 lg:col-span-2 flex flex-col justify-between">
          <div>
            <span className="text-xs font-semibold uppercase font-mono text-zinc-300 block mb-3">
              Safety Guardrails & Velocity Invariants
            </span>

            <div className="grid grid-cols-3 gap-3">
              <div className="bg-zinc-950 p-3 rounded border border-zinc-800">
                <span className="text-[10px] text-zinc-500 font-mono uppercase block mb-1">Max Interventions</span>
                <span className="text-sm font-bold font-mono text-zinc-200">3 / 24h</span>
                <span className="text-[10px] text-zinc-500 font-mono block mt-1">Per unique customer</span>
              </div>

              <div className="bg-zinc-950 p-3 rounded border border-zinc-800">
                <span className="text-[10px] text-zinc-500 font-mono uppercase block mb-1">Cooldown Window</span>
                <span className="text-sm font-bold font-mono text-zinc-200">48 Hours</span>
                <span className="text-[10px] text-zinc-500 font-mono block mt-1">Between retry attempts</span>
              </div>

              <div className="bg-zinc-950 p-3 rounded border border-zinc-800">
                <span className="text-[10px] text-zinc-500 font-mono uppercase block mb-1">Action Constraints</span>
                <span className="text-sm font-bold font-mono text-zinc-200">Bounded Only</span>
                <span className="text-[10px] text-zinc-500 font-mono block mt-1">No unapproved actions</span>
              </div>
            </div>
          </div>

          <div className="mt-3 pt-3 border-t border-zinc-800 flex items-center justify-between text-xs text-zinc-500 font-mono">
            <span>Safety Invariants Active: Enforced Globally</span>
            <span>Gateway Timeout: 10s max</span>
          </div>
        </div>
      </div>

      <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
          <div>
            <h2 className="text-xs font-semibold text-zinc-200 uppercase tracking-wider font-mono">
              Policy Decision Registry ({policies.length} Rules)
            </h2>
          </div>
          <span className="text-[10px] font-mono text-zinc-500">
            Deterministic Decision Tree
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-zinc-300">
            <thead className="bg-zinc-950 text-zinc-400 border-b border-zinc-800 uppercase text-[10px] font-mono">
              <tr>
                <th className="py-2.5 px-4 font-medium">Policy Rule ID</th>
                <th className="py-2.5 px-4 font-medium">Trigger Root Cause</th>
                <th className="py-2.5 px-4 font-medium">Permitted Action Set</th>
                <th className="py-2.5 px-4 text-center font-medium">Max Retries</th>
                <th className="py-2.5 px-4 text-center font-medium">Cooldown</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800 font-mono">
              {policies.map((rule) => (
                <tr key={rule.rule_id} className="hover:bg-zinc-850">
                  <td className="py-2.5 px-4 text-zinc-300 font-semibold">{rule.rule_id}</td>
                  <td className="py-2.5 px-4 text-zinc-300 font-sans">{formatRootCauseName(rule.root_cause)}</td>
                  <td className="py-2.5 px-4">
                    <div className="flex flex-wrap gap-1">
                      {rule.allowed_actions.map((act) => (
                        <span key={act} className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-950 text-zinc-400 border border-zinc-800">
                          {act}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-2.5 px-4 text-center text-zinc-300">{rule.max_retries}</td>
                  <td className="py-2.5 px-4 text-center text-zinc-400">{rule.cooldown_hours}h</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
