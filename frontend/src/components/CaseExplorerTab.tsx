import React from 'react';
import { 
  ChevronLeft, 
  ChevronRight, 
  RefreshCw
} from 'lucide-react';
import type { RecoveryCase } from '../types/api';

interface CaseExplorerTabProps {
  cases: RecoveryCase[];
  total: number;
  loading: boolean;
  limit: number;
  offset: number;
  searchQuery: string;
  statusFilter: string;
  typeFilter: string;
  onSearchChange: (query: string) => void;
  onStatusFilterChange: (status: string) => void;
  onTypeFilterChange: (type: string) => void;
  onPageChange: (newOffset: number) => void;
  onSelectCase: (caseId: number) => void;
  onRefresh: () => void;
}

export const CaseExplorerTab: React.FC<CaseExplorerTabProps> = ({
  cases,
  total,
  loading,
  limit,
  offset,
  searchQuery,
  statusFilter,
  typeFilter,
  onSearchChange,
  onStatusFilterChange,
  onTypeFilterChange,
  onPageChange,
  onSelectCase,
  onRefresh,
}) => {
  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(val);
  };

  const getStatusBadge = (status: string) => {
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
      case 'open':
      case 'detected_at_risk':
      case 'diagnosed':
      case 'decided':
        return (
          <span className="font-mono text-xs text-blue-400 bg-zinc-950 px-2 py-0.5 rounded border border-zinc-800">
            in_progress
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

  const formatCaseType = (type: string) => {
    switch (type) {
      case 'payment_failure':
        return 'Payment Failure';
      case 'checkout_abandonment':
        return 'Cart Abandonment';
      case 'subscription_failure':
        return 'Subscription Renewal';
      default:
        return type;
    }
  };

  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-zinc-800">
        <div>
          <h1 className="text-xl font-bold text-zinc-100 tracking-tight">Recovery Cases Explorer</h1>
          <p className="text-xs text-zinc-400 mt-0.5">Click on any transaction to inspect the step-by-step AI decision trail and safety audit log</p>
        </div>
        <div className="text-xs font-semibold text-zinc-400 bg-zinc-900 px-3 py-1.5 rounded border border-zinc-800">
          Showing <strong className="text-zinc-200">{cases.length}</strong> of <strong className="text-zinc-200">{total}</strong> total cases
        </div>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3.5 flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="flex-1 w-full flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            placeholder="Search reference ID, transaction ID, customer ID..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="flex-1 bg-zinc-950 border border-zinc-800 rounded px-3 py-1.5 text-xs text-zinc-200 placeholder-zinc-500 font-mono focus:outline-none focus:border-blue-500 transition-colors"
          />

          <div className="flex gap-2">
            <select
              value={statusFilter}
              onChange={(e) => onStatusFilterChange(e.target.value)}
              className="bg-zinc-950 border border-zinc-800 rounded px-3 py-1.5 text-xs text-zinc-300 focus:outline-none focus:border-blue-500 cursor-pointer"
            >
              <option value="">All Statuses</option>
              <option value="recovered">Recovered Only</option>
              <option value="stopped_by_policy">Stopped by Safety</option>
              <option value="escalated">Escalated</option>
              <option value="failed">Unrecoverable</option>
            </select>

            <select
              value={typeFilter}
              onChange={(e) => onTypeFilterChange(e.target.value)}
              className="bg-zinc-950 border border-zinc-800 rounded px-3 py-1.5 text-xs text-zinc-300 focus:outline-none focus:border-blue-500 cursor-pointer"
            >
              <option value="">All Problem Types</option>
              <option value="payment_failure">Payment Failures</option>
              <option value="checkout_abandonment">Cart Abandonment</option>
              <option value="subscription_failure">Subscription Renewals</option>
            </select>
          </div>
        </div>

        <button
          onClick={onRefresh}
          className="p-1.5 rounded bg-zinc-950 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-all cursor-pointer"
          title="Refresh list"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-zinc-300">
            <thead className="bg-zinc-950 text-zinc-400 border-b border-zinc-800 uppercase text-[11px] font-semibold tracking-wider">
              <tr>
                <th className="py-2.5 px-4">Case</th>
                <th className="py-2.5 px-4">Problem Type</th>
                <th className="py-2.5 px-4">Reference & Customer</th>
                <th className="py-2.5 px-4 text-right">Value (INR)</th>
                <th className="py-2.5 px-4 text-center">Engine Result</th>
                <th className="py-2.5 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-zinc-500 font-medium">
                    Loading cases repository...
                  </td>
                </tr>
              ) : cases.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-zinc-400">
                    No transactions match your search filters.
                  </td>
                </tr>
              ) : (
                cases.map((c) => (
                  <tr 
                    key={c.id} 
                    onClick={() => onSelectCase(c.id)}
                    className="hover:bg-zinc-850 cursor-pointer transition-colors"
                  >
                    <td className="py-3 px-4 font-mono font-bold text-zinc-100">#{c.id}</td>
                    <td className="py-3 px-4 font-medium text-zinc-200">
                      {formatCaseType(c.case_type)}
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-mono text-zinc-200 text-xs">{c.source_reference}</div>
                      <div className="font-mono text-zinc-400 text-[11px]">{c.customer_id}</div>
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-zinc-100">
                      {formatCurrency(c.amount)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {getStatusBadge(c.status)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => { e.stopPropagation(); onSelectCase(c.id); }}
                        className="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium transition-all cursor-pointer"
                      >
                        Inspect &rarr;
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="px-4 py-2.5 border-t border-zinc-800 bg-zinc-950 flex items-center justify-between text-xs text-zinc-400">
          <div>
            Showing <strong className="text-zinc-200">{cases.length}</strong> of <strong className="text-zinc-200">{total}</strong> records
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => onPageChange(Math.max(0, offset - limit))}
              disabled={offset === 0 || loading}
              className="p-1 rounded border border-zinc-800 hover:bg-zinc-800 text-zinc-400 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer transition-all"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-zinc-300 font-medium px-2">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => onPageChange(offset + limit)}
              disabled={offset + limit >= total || loading}
              className="p-1 rounded border border-zinc-800 hover:bg-zinc-800 text-zinc-400 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer transition-all"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
