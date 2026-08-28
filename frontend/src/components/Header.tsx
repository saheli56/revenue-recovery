import React from 'react';
import { 
  Play, 
  BarChart3, 
  Layers, 
  Sliders, 
  Terminal
} from 'lucide-react';
import type { GuardrailStatus } from '../types/api';

interface HeaderProps {
  activeTab: 'overview' | 'cases' | 'policies' | 'simulator';
  onTabChange: (tab: 'overview' | 'cases' | 'policies' | 'simulator') => void;
  guardrailStatus: GuardrailStatus | null;
  onOpenBatchModal: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onTabChange,
  guardrailStatus,
  onOpenBatchModal,
}) => {
  return (
    <header className="bg-zinc-950 border-b border-zinc-800 sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-14">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 rounded-md bg-zinc-100 flex items-center justify-center text-zinc-950 font-mono font-bold text-xs shadow-xs">
                RZ
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-zinc-100 tracking-tight">Razorpay Recover</span>
                  <span className="text-[10px] font-mono font-medium px-1.5 py-0.2 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
                    Track 03
                  </span>
                </div>
              </div>
            </div>

            <nav className="flex items-center gap-1 bg-zinc-900/50 p-1 rounded-md border border-zinc-800/80">
              <button
                onClick={() => onTabChange('overview')}
                className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium transition-all cursor-pointer ${
                  activeTab === 'overview'
                    ? 'bg-zinc-800 text-zinc-100 font-semibold'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850'
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5" />
                Performance
              </button>

              <button
                onClick={() => onTabChange('cases')}
                className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium transition-all cursor-pointer ${
                  activeTab === 'cases'
                    ? 'bg-zinc-800 text-zinc-100 font-semibold'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850'
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                Case Explorer
              </button>

              <button
                onClick={() => onTabChange('policies')}
                className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium transition-all cursor-pointer ${
                  activeTab === 'policies'
                    ? 'bg-zinc-800 text-zinc-100 font-semibold'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850'
                }`}
              >
                <Sliders className="w-3.5 h-3.5" />
                Rules & Guardrails
              </button>

              <button
                onClick={() => onTabChange('simulator')}
                className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium transition-all cursor-pointer ${
                  activeTab === 'simulator'
                    ? 'bg-zinc-800 text-zinc-100 font-semibold'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850'
                }`}
              >
                <Terminal className="w-3.5 h-3.5" />
                Live Sandbox
              </button>
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-xs font-mono">
              <span className={`w-1.5 h-1.5 rounded-full ${guardrailStatus?.kill_switch_active ? 'bg-red-400' : 'bg-emerald-400'}`} />
              <span className={guardrailStatus?.kill_switch_active ? 'text-red-400' : 'text-zinc-400'}>
                {guardrailStatus?.kill_switch_active ? 'Kill Switch' : 'Guardrails Normal'}
              </span>
            </div>

            <button
              onClick={onOpenBatchModal}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-zinc-100 hover:bg-zinc-200 active:bg-zinc-300 text-zinc-950 text-xs font-semibold transition-colors cursor-pointer"
            >
              <Play className="w-3 h-3 fill-zinc-950" />
              <span>Run Batch Test</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
