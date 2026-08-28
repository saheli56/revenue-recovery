import { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { OverviewTab } from './components/OverviewTab';
import { CaseExplorerTab } from './components/CaseExplorerTab';
import { PoliciesTab } from './components/PoliciesTab';
import { IngestSimulatorTab } from './components/IngestSimulatorTab';
import { CaseTraceModal } from './components/CaseTraceModal';
import { BatchRunModal } from './components/BatchRunModal';
import { api } from './services/api';
import type { 
  RecoveryCase, 
  CaseTrace, 
  EvaluationReport, 
  PolicyRule, 
  GuardrailStatus 
} from './types/api';

export function App() {
  const [activeTab, setActiveTab] = useState<'overview' | 'cases' | 'policies' | 'simulator'>('overview');
  
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [loadingReport, setLoadingReport] = useState<boolean>(true);

  const [cases, setCases] = useState<RecoveryCase[]>([]);
  const [totalCases, setTotalCases] = useState<number>(0);
  const [loadingCases, setLoadingCases] = useState<boolean>(true);
  const [caseLimit] = useState<number>(20);
  const [caseOffset, setCaseOffset] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');

  const [policies, setPolicies] = useState<PolicyRule[]>([]);
  const [guardrailStatus, setGuardrailStatus] = useState<GuardrailStatus | null>(null);
  const [loadingPolicies, setLoadingPolicies] = useState<boolean>(true);

  const [selectedTrace, setSelectedTrace] = useState<CaseTrace | null>(null);
  const [loadingTrace, setLoadingTrace] = useState<boolean>(false);

  const [isBatchModalOpen, setIsBatchModalOpen] = useState<boolean>(false);

  const loadAnalytics = async () => {
    setLoadingReport(true);
    try {
      const data = await api.getAnalyticsBreakdown();
      setReport(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingReport(false);
    }
  };

  const loadCases = async () => {
    setLoadingCases(true);
    try {
      const data = await api.getCases({
        status: statusFilter || undefined,
        case_type: typeFilter || undefined,
        search: searchQuery || undefined,
        limit: caseLimit,
        offset: caseOffset,
      });
      setCases(data.items);
      setTotalCases(data.total);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingCases(false);
    }
  };

  const loadPoliciesAndGuardrails = async () => {
    setLoadingPolicies(true);
    try {
      const [policiesData, guardrailsData] = await Promise.all([
        api.getPolicies(),
        api.getGuardrailStatus(),
      ]);
      setPolicies(policiesData.rules);
      setGuardrailStatus(guardrailsData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingPolicies(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
    loadPoliciesAndGuardrails();
  }, []);

  useEffect(() => {
    loadCases();
  }, [caseOffset, statusFilter, typeFilter, searchQuery]);

  const handleOpenTrace = async (caseId: number) => {
    setLoadingTrace(true);
    try {
      const traceData = await api.getCaseTrace(caseId);
      setSelectedTrace(traceData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingTrace(false);
    }
  };

  const handleToggleKillSwitch = async (active: boolean) => {
    const updated = await api.toggleKillSwitch(active);
    setGuardrailStatus(updated);
  };

  const handleBatchRunComplete = async (options: { concurrency: number; limit?: number; seed_fresh: boolean }) => {
    const result = await api.triggerBatchRun(options);
    await Promise.all([loadAnalytics(), loadCases()]);
    return result;
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      <Header
        activeTab={activeTab}
        onTabChange={setActiveTab}
        guardrailStatus={guardrailStatus}
        onOpenBatchModal={() => setIsBatchModalOpen(true)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6">
        {activeTab === 'overview' && (
          <OverviewTab
            report={report}
            loading={loadingReport}
          />
        )}

        {activeTab === 'cases' && (
          <CaseExplorerTab
            cases={cases}
            total={totalCases}
            loading={loadingCases}
            limit={caseLimit}
            offset={caseOffset}
            searchQuery={searchQuery}
            statusFilter={statusFilter}
            typeFilter={typeFilter}
            onSearchChange={(q) => { setSearchQuery(q); setCaseOffset(0); }}
            onStatusFilterChange={(s) => { setStatusFilter(s); setCaseOffset(0); }}
            onTypeFilterChange={(t) => { setTypeFilter(t); setCaseOffset(0); }}
            onPageChange={setCaseOffset}
            onSelectCase={handleOpenTrace}
            onRefresh={loadCases}
          />
        )}

        {activeTab === 'policies' && (
          <PoliciesTab
            policies={policies}
            guardrailStatus={guardrailStatus}
            loading={loadingPolicies}
            onToggleKillSwitch={handleToggleKillSwitch}
          />
        )}

        {activeTab === 'simulator' && (
          <IngestSimulatorTab
            onIngestSuccess={async () => {
              await Promise.all([loadAnalytics(), loadCases()]);
            }}
            onOpenTrace={handleOpenTrace}
            onIngestCase={api.ingestCase}
          />
        )}
      </main>

      <CaseTraceModal
        trace={selectedTrace}
        loading={loadingTrace}
        onClose={() => setSelectedTrace(null)}
      />

      <BatchRunModal
        isOpen={isBatchModalOpen}
        onClose={() => setIsBatchModalOpen(false)}
        onRunBatch={handleBatchRunComplete}
      />

      <footer className="border-t border-zinc-900 bg-zinc-950 py-4 text-xs font-mono text-zinc-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>Razorpay Recover &middot; Track 03 Production Specification</span>
          <span className="text-zinc-600">FastAPI &middot; SQLite aiosqlite &middot; React 19 &middot; Tailwind CSS</span>
        </div>
      </footer>
    </div>
  );
}

export default App;
