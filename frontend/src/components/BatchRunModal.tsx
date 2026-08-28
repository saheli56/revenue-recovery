import React, { useState } from 'react';
import { 
  X, 
  Play, 
  RefreshCw
} from 'lucide-react';
import type { BatchRunResult } from '../types/api';

interface BatchRunModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRunBatch: (options: { concurrency: number; limit?: number; seed_fresh: boolean }) => Promise<BatchRunResult>;
}

export const BatchRunModal: React.FC<BatchRunModalProps> = ({
  isOpen,
  onClose,
  onRunBatch,
}) => {
  if (!isOpen) return null;

  const [concurrency, setConcurrency] = useState(5);
  const [seedFresh, setSeedFresh] = useState(true);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<BatchRunResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleRun = async () => {
    setRunning(true);
    setErrorMsg(null);
    setResult(null);
    try {
      const res = await onRunBatch({
        concurrency,
        seed_fresh: seedFresh,
      });
      setResult(res);
    } catch (err: any) {
      setErrorMsg(err.message || 'Batch run failed');
    } finally {
      setRunning(false);
    }
  };

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(val);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs animate-fade-in">
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-lg flex flex-col shadow-2xl overflow-hidden animate-scale-in">
        <div className="p-4 border-b border-zinc-800 flex items-center justify-between bg-zinc-950">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-zinc-100">Execute Pipeline Batch Orchestrator</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4 text-xs">
          <p className="text-zinc-400 leading-relaxed">
            Runs portfolio cases concurrently through the 5-stage pipeline (Detector &rarr; Diagnoser &rarr; Strategist &rarr; Executor &rarr; Outcome) using bounded worker tasks.
          </p>

          <div className="space-y-3 bg-zinc-950 p-3 rounded border border-zinc-800 font-mono">
            <div>
              <label className="block text-[11px] text-zinc-400 mb-1.5 uppercase font-medium">
                Concurrency Worker Pool
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[1, 5, 10].map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setConcurrency(c)}
                    className={`py-1.5 px-3 rounded text-xs transition-colors cursor-pointer ${
                      concurrency === c
                        ? 'bg-zinc-100 text-zinc-950 font-semibold'
                        : 'bg-zinc-900 text-zinc-400 border border-zinc-800 hover:bg-zinc-800'
                    }`}
                  >
                    {c} Workers
                  </button>
                ))}
              </div>
            </div>

            <div className="pt-2 border-t border-zinc-800">
              <label className="flex items-center gap-2 cursor-pointer text-zinc-300">
                <input
                  type="checkbox"
                  checked={seedFresh}
                  onChange={(e) => setSeedFresh(e.target.checked)}
                  className="rounded bg-zinc-900 border-zinc-700 text-zinc-200"
                />
                <span className="text-[11px]">Re-seed fresh 150 synthetic records before orchestrating</span>
              </label>
            </div>
          </div>

          {errorMsg && (
            <div className="p-2.5 rounded bg-red-950/60 border border-red-800 text-xs font-mono text-red-300">
              {errorMsg}
            </div>
          )}

          {result && (
            <div className="p-3 bg-zinc-950 border border-zinc-800 font-mono space-y-2 rounded">
              <div className="text-emerald-400 text-xs font-bold font-mono">
                Orchestration Completed ({result.elapsed_seconds}s)
              </div>

              <div className="grid grid-cols-2 gap-1.5 text-[11px] text-zinc-400">
                <div>Evaluated: <strong className="text-zinc-200">{result.processed_count}</strong></div>
                <div>Recovered: <strong className="text-emerald-400">{result.recovered_count}</strong></div>
                <div>At-Risk Total: <strong className="text-zinc-200">{formatCurrency(result.total_at_risk_amount)}</strong></div>
                <div>Recovered Total: <strong className="text-emerald-400">{formatCurrency(result.total_recovered_amount)}</strong></div>
              </div>
            </div>
          )}

          <div className="flex gap-2 pt-1">
            <button
              onClick={onClose}
              className="flex-1 py-2 px-3 rounded bg-zinc-800 hover:bg-zinc-750 text-zinc-300 text-xs font-medium transition-colors cursor-pointer border border-zinc-700"
            >
              Close
            </button>
            <button
              onClick={handleRun}
              disabled={running}
              className="flex-2 py-2 px-3 rounded bg-zinc-100 hover:bg-zinc-200 text-zinc-950 text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              {running ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Orchestrating batch...</span>
                </>
              ) : (
                <>
                  <Play className="w-3 h-3 fill-zinc-950" />
                  <span>Execute Pipeline</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
