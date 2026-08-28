import React, { useState } from 'react';
import { 
  Send, 
  RefreshCw, 
  ArrowRight
} from 'lucide-react';
import type { RecoveryCase } from '../types/api';

interface IngestSimulatorTabProps {
  onIngestSuccess: (caseId: number) => void;
  onOpenTrace: (caseId: number) => void;
  onIngestCase: (payload: any) => Promise<RecoveryCase>;
}

export const IngestSimulatorTab: React.FC<IngestSimulatorTabProps> = ({
  onIngestSuccess,
  onOpenTrace,
  onIngestCase,
}) => {
  const [caseType, setCaseType] = useState('payment_failure');
  const [amount, setAmount] = useState(2999);
  const [errorCode, setErrorCode] = useState('card_expired');
  const [customerNote, setCustomerNote] = useState('');
  const [isFraud, setIsFraud] = useState(false);
  const [isDuplicate, setIsDuplicate] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [ingestedCase, setIngestedCase] = useState<RecoveryCase | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handlePreset = (preset: 'card_expired' | 'hinglish' | 'fraud' | 'cart_abandon') => {
    setErrorMsg(null);
    if (preset === 'card_expired') {
      setCaseType('payment_failure');
      setAmount(4999);
      setErrorCode('card_expired');
      setCustomerNote('');
      setIsFraud(false);
      setIsDuplicate(false);
    } else if (preset === 'hinglish') {
      setCaseType('payment_failure');
      setAmount(1850);
      setErrorCode('technical_error');
      setCustomerNote('bhai paise debit ho gaye par booking confirm nahi hui OTP error tha');
      setIsFraud(false);
      setIsDuplicate(false);
    } else if (preset === 'fraud') {
      setCaseType('payment_failure');
      setAmount(95000);
      setErrorCode('gateway_declined');
      setCustomerNote('');
      setIsFraud(true);
      setIsDuplicate(false);
    } else if (preset === 'cart_abandon') {
      setCaseType('checkout_abandonment');
      setAmount(3499);
      setErrorCode('cart_abandoned');
      setCustomerNote('User selected UPI payment method and reached checkout but dropped off');
      setIsFraud(false);
      setIsDuplicate(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg(null);
    setIngestedCase(null);

    const randomSuffix = Math.random().toString(36).substring(2, 7);
    const sourceRef = `pay_${Date.now().toString().slice(-6)}_${randomSuffix}`;
    const custId = `cust_${randomSuffix}`;

    const metadata: Record<string, any> = {
      error_code: errorCode,
      is_fraud_flagged: isFraud,
      is_duplicate: isDuplicate,
    };
    if (customerNote) {
      metadata.notes = customerNote;
      metadata.customer_inquiry = customerNote;
    }

    try {
      const res = await onIngestCase({
        case_type: caseType,
        source_reference: sourceRef,
        customer_id: custId,
        amount: Number(amount),
        currency: 'INR',
        auto_process: true,
        metadata,
      });
      setIngestedCase(res);
      onIngestSuccess(res.id);
    } catch (err: any) {
      setErrorMsg(err.message || 'Ingestion failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-zinc-800">
        <div>
          <h1 className="text-xl font-bold text-zinc-100 tracking-tight">Live Test Sandbox</h1>
          <p className="text-xs text-zinc-400 mt-0.5">Test how the AI engine handles any checkout failure, customer note, or fraud pattern</p>
        </div>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <span className="text-xs font-bold uppercase tracking-wider text-zinc-400 block mb-2.5 font-mono">
          Preloaded Test Scenarios
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
          <button
            type="button"
            onClick={() => handlePreset('card_expired')}
            className="p-3 rounded bg-zinc-950 hover:bg-zinc-850 border border-zinc-800 text-left transition-all cursor-pointer flex flex-col justify-between"
          >
            <div className="text-zinc-200 text-xs font-semibold mb-1">
              Expired Card Failure
            </div>
            <p className="text-[11px] text-zinc-400">Tests sending updated payment link with alternative methods</p>
          </button>

          <button
            type="button"
            onClick={() => handlePreset('hinglish')}
            className="p-3 rounded bg-zinc-950 hover:bg-zinc-850 border border-zinc-800 text-left transition-all cursor-pointer flex flex-col justify-between"
          >
            <div className="text-zinc-200 text-xs font-semibold mb-1">
              Hinglish Support Note
            </div>
            <p className="text-[11px] text-zinc-400">Tests AI understanding conversational Hinglish support inquiries via Claude LLM</p>
          </button>

          <button
            type="button"
            onClick={() => handlePreset('fraud')}
            className="p-3 rounded bg-zinc-950 hover:bg-zinc-850 border border-zinc-800 text-left transition-all cursor-pointer flex flex-col justify-between"
          >
            <div className="text-red-400 text-xs font-semibold mb-1">
              Fraud Velocity Risk
            </div>
            <p className="text-[11px] text-zinc-400">Tests engine automatically halting on suspicious transactions</p>
          </button>

          <button
            type="button"
            onClick={() => handlePreset('cart_abandon')}
            className="p-3 rounded bg-zinc-950 hover:bg-zinc-850 border border-zinc-800 text-left transition-all cursor-pointer flex flex-col justify-between"
          >
            <div className="text-zinc-200 text-xs font-semibold mb-1">
              Cart Abandonment
            </div>
            <p className="text-[11px] text-zinc-400">Tests high-intent recovery with checkout completion link</p>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
          <h3 className="text-xs font-bold text-zinc-200 uppercase tracking-wide mb-3 font-mono">
            Transaction Parameters
          </h3>

          <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
            <div className="grid grid-cols-2 gap-3.5">
              <div>
                <label className="block text-zinc-300 font-medium mb-1">Problem Type</label>
                <select
                  value={caseType}
                  onChange={(e) => setCaseType(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-blue-500 cursor-pointer"
                >
                  <option value="payment_failure">Payment Failure</option>
                  <option value="checkout_abandonment">Cart Abandonment</option>
                  <option value="subscription_failure">Subscription Renewal</option>
                </select>
              </div>

              <div>
                <label className="block text-zinc-300 font-medium mb-1">Amount (INR)</label>
                <input
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(Number(e.target.value))}
                  required
                  min={1}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-blue-500 font-mono"
                />
              </div>
            </div>

            <div>
              <label className="block text-zinc-300 font-medium mb-1">Failure Reason / Error Code</label>
              <select
                value={errorCode}
                onChange={(e) => setErrorCode(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-800 rounded px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-blue-500 cursor-pointer"
              >
                <option value="card_expired">card_expired (Card validity ended)</option>
                <option value="insufficient_funds">insufficient_funds (Balance low)</option>
                <option value="issuer_timeout">issuer_timeout (Bank server slow)</option>
                <option value="authentication_failed">authentication_failed (Incorrect PIN/OTP)</option>
                <option value="otp_latency_timeout">otp_latency_timeout (SMS delayed)</option>
                <option value="cart_abandoned">cart_abandoned (Customer dropped off)</option>
                <option value="technical_error">technical_error (Ambiguous / Triggers Claude LLM)</option>
              </select>
            </div>

            <div>
              <label className="block text-zinc-300 font-medium mb-1">
                Customer Support Inquiry / Hinglish Chat Note (Triggers Claude LLM)
              </label>
              <input
                type="text"
                placeholder="e.g. bhai paise cut gaye par order book nahi hua please help"
                value={customerNote}
                onChange={(e) => setCustomerNote(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-800 rounded px-3 py-1.5 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-blue-500"
              />
            </div>

            <div className="flex items-center gap-5 pt-1">
              <label className="flex items-center gap-2 cursor-pointer text-zinc-300">
                <input
                  type="checkbox"
                  checked={isFraud}
                  onChange={(e) => setIsFraud(e.target.checked)}
                  className="rounded bg-zinc-950 border-zinc-800 text-red-500 focus:ring-red-500"
                />
                <span>Simulate Fraud Pattern</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer text-zinc-300">
                <input
                  type="checkbox"
                  checked={isDuplicate}
                  onChange={(e) => setIsDuplicate(e.target.checked)}
                  className="rounded bg-zinc-950 border-zinc-800 text-amber-500 focus:ring-amber-500"
                />
                <span>Duplicate Order</span>
              </label>
            </div>

            {errorMsg && (
              <div className="p-2.5 rounded bg-red-950/60 border border-red-800 text-xs text-red-300">
                {errorMsg}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2 px-3 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition-colors flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              {submitting ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Running through 5-stage pipeline...</span>
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  <span>Dispatch & Execute Pipeline</span>
                </>
              )}
            </button>
          </form>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-bold text-zinc-200 uppercase tracking-wide mb-3 font-mono">
              Execution Result
            </h3>

            {ingestedCase ? (
              <div className="space-y-3.5">
                <div className="p-3.5 bg-zinc-950 border border-zinc-800 rounded space-y-2">
                  <div className="text-emerald-400 font-bold text-xs font-mono">
                    Pipeline Execution Complete: Case #{ingestedCase.id}
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs text-zinc-400 pt-2 border-t border-zinc-800">
                    <div>Reference: <span className="text-zinc-200 font-mono">{ingestedCase.source_reference}</span></div>
                    <div>Customer: <span className="text-zinc-200 font-mono">{ingestedCase.customer_id}</span></div>
                    <div>Amount: <span className="text-emerald-400 font-mono">INR {ingestedCase.amount.toLocaleString()}</span></div>
                    <div>Status: <span className="text-zinc-100 font-mono font-bold">{ingestedCase.status}</span></div>
                  </div>
                </div>

                <button
                  onClick={() => onOpenTrace(ingestedCase.id)}
                  className="w-full py-2 px-3 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium flex items-center justify-center gap-1.5 transition-colors cursor-pointer border border-zinc-700"
                >
                  <span>Inspect Complete Decision & Audit Trail</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <div className="h-48 flex flex-col items-center justify-center text-zinc-500 text-xs border border-dashed border-zinc-800 rounded p-6 text-center">
                <span className="font-semibold text-zinc-400 font-mono">Awaiting Ingestion</span>
                <p className="text-[11px] text-zinc-500 mt-1 max-w-xs">
                  Select a test scenario above or click Dispatch to run the transaction through the engine.
                </p>
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-zinc-800 text-xs text-zinc-400 flex items-center justify-between font-mono text-[11px]">
            <span>Security Layer: Enforced</span>
            <span>Claude LLM Fallback: Ready</span>
          </div>
        </div>
      </div>
    </div>
  );
};
