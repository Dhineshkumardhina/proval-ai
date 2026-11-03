/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  FileCheck2,
  Lock,
  RefreshCw,
  Scale,
  Building,
  CheckCircle2,
  Info,
} from 'lucide-react';
import { ValuationCase } from '../../types/valuation';
import {
  fetchAIStatus,
  fetchAIUnderwriterBriefing,
  AIStatus,
  AIExplainCaseResponse,
} from '../../services/apiClient';

interface AIUnderwriterPanelProps {
  currentCase: ValuationCase;
}

export const AIUnderwriterPanel: React.FC<AIUnderwriterPanelProps> = ({ currentCase }) => {
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null);
  const [briefing, setBriefing] = useState<AIExplainCaseResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load AI configuration status on mount
  useEffect(() => {
    let active = true;
    fetchAIStatus().then((status) => {
      if (active && status) setAiStatus(status);
    });
    return () => {
      active = false;
    };
  }, []);

  // Fetch or generate underwriter briefing for current case
  const handleGenerateBriefing = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchAIUnderwriterBriefing(currentCase.id);
      if (res) {
        setBriefing(res);
      } else {
        setError('Unable to reach AI Underwriter service. Check backend connection.');
      }
    } catch (err: any) {
      setError(err?.message || 'Error synthesizing AI underwriter briefing.');
    } finally {
      setIsLoading(false);
    }
  };

  // Automatically trigger briefing load if none exists for this case
  useEffect(() => {
    handleGenerateBriefing();
  }, [currentCase.id]);

  const report = briefing?.report;

  return (
    <div className="bg-white rounded-md border border-[#E2E8F0] shadow-sm p-4 space-y-4">
      {/* Header and Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-[#E2E8F0]">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-[#EFF6FF] text-[#2563EB]">
            <Sparkles className="w-5 h-5 text-[#2563EB]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-[#142B4A]">AI Underwriter Assistant</h3>
              <span
                className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                  briefing?.provider === 'gemini'
                    ? 'bg-[#ECFDF5] text-[#047857] border-[#A7F3D0]'
                    : 'bg-[#F8FAFC] text-[#475569] border-[#CBD5E1]'
                }`}
              >
                {briefing?.provider === 'gemini'
                  ? `Active: ${briefing.model_name}`
                  : 'Grounded Deterministic Fallback'}
              </span>
            </div>
            <p className="text-[11px] text-[#64748B]">
              Evidence synthesis for institutional credit underwriters. Zero price fabrication.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleGenerateBriefing}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold bg-[#F1F5F9] hover:bg-[#E2E8F0] text-[#142B4A] transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            {isLoading ? 'Synthesizing...' : 'Re-analyze Case'}
          </button>
        </div>
      </div>

      {/* DPDP Act 2023 & Governance Banner */}
      <div className="bg-[#F8FAFC] rounded border border-[#CBD5E1] p-2.5 text-[11px] flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-[#334155]">
          <Lock className="w-4 h-4 text-[#2563EB] shrink-0" />
          <span>
            <strong>DPDP Act 2023 Guard Active:</strong> Personal identifiers (PAN, Aadhaar, Phone, Email, Names) are scrubbed before processing.
          </span>
        </div>
        {briefing && briefing.pii_redacted_count > 0 && (
          <span className="font-semibold text-[10px] px-2 py-0.5 rounded bg-[#EFF6FF] text-[#1D4ED8] border border-[#BFDBFE] shrink-0">
            {briefing.pii_redacted_count} PII Redacted
          </span>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="bg-[#FEF2F2] border border-[#FECACA] text-[#991B1B] p-3 rounded text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-[#DC2626]" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading state */}
      {isLoading && !report && (
        <div className="py-12 text-center space-y-2">
          <RefreshCw className="w-6 h-6 animate-spin text-[#2563EB] mx-auto" />
          <p className="text-xs font-medium text-[#64748B]">
            Synthesizing collateral valuation evidence and verifying legal compliance...
          </p>
        </div>
      )}

      {/* Briefing Content */}
      {report && (
        <div className="space-y-4 text-xs">
          {/* Executive Valuation Summary */}
          <div className="bg-[#EFF6FF]/50 border border-[#BFDBFE] p-3 rounded-md">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#1D4ED8] block mb-1">
              Executive Valuation Summary
            </span>
            <p className="text-[#1E293B] leading-relaxed">
              {report.valuation_summary}
            </p>
          </div>

          {/* Key Value & Risk Factors */}
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748B] block mb-2">
              Primary Value & Collateral Factors
            </span>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              {report.major_valuation_factors.map((factor, idx) => (
                <div
                  key={idx}
                  className="bg-[#F8FAFC] border border-[#E2E8F0] p-2.5 rounded flex flex-col justify-between"
                >
                  <div className="flex items-center justify-between gap-1 mb-1">
                    <span className="font-semibold text-[#142B4A] text-[11px]">
                      {factor.factor_name}
                    </span>
                    <span
                      className={`text-[9px] font-bold px-1.5 py-0.2 rounded ${
                        factor.impact === 'POSITIVE'
                          ? 'bg-[#DCFCE7] text-[#15803D]'
                          : factor.impact === 'NEGATIVE'
                          ? 'bg-[#FEE2E2] text-[#B91C1C]'
                          : 'bg-[#F1F5F9] text-[#64748B]'
                      }`}
                    >
                      {factor.impact}
                    </span>
                  </div>
                  <p className="text-[10.5px] text-[#475569] leading-snug">
                    {factor.details}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Comparable Evidence & Synthetic Provenance */}
          <div className="bg-white border border-[#E2E8F0] p-3 rounded-md">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748B] block mb-1 flex items-center gap-1.5">
              <Scale className="w-3.5 h-3.5 text-[#2563EB]" />
              Comparable Evidence & Provenance
            </span>
            <p className="text-[#334155] leading-relaxed text-[11px]">
              {report.comparable_evidence_analysis}
            </p>
          </div>

          {/* Micro-market & Location Considerations */}
          <div className="bg-white border border-[#E2E8F0] p-3 rounded-md">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#64748B] block mb-1 flex items-center gap-1.5">
              <Building className="w-3.5 h-3.5 text-[#0F766E]" />
              Micro-Market & Locality Dynamics
            </span>
            <p className="text-[#334155] leading-relaxed text-[11px]">
              {report.location_considerations}
            </p>
          </div>

          {/* Two-column Risks & Limitations Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Legal & Regulatory Due Diligence */}
            <div className="bg-[#FFFBEB] border border-[#FDE68A] p-3 rounded-md">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#B45309] block mb-1.5 flex items-center gap-1.5">
                <FileCheck2 className="w-3.5 h-3.5 text-[#D97706]" />
                Legal Due Diligence Checklist
              </span>
              <ul className="space-y-1 text-[10.5px] text-[#78350F]">
                {report.legal_regulatory_risks.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-1.5">
                    <span className="text-[#D97706] font-bold">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Data Quality & Heuristic Limitations */}
            <div className="bg-[#FEF2F2] border border-[#FECACA] p-3 rounded-md">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#991B1B] block mb-1.5 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-[#DC2626]" />
                Data Quality & Valuation Caveats
              </span>
              <ul className="space-y-1 text-[10.5px] text-[#7F1D1D]">
                {report.data_quality_concerns.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-1.5">
                    <span className="text-[#DC2626] font-bold">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Actionable Underwriter Verification Checklist */}
          <div className="bg-[#F8FAFC] border border-[#CBD5E1] p-3 rounded-md">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[#142B4A] block mb-1.5 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-[#2563EB]" />
              Actionable Underwriter Recommendations
            </span>
            <ul className="space-y-1.5 text-[11px] text-[#334155]">
              {report.underwriter_recommendations.map((rec, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="w-4 h-4 rounded-full bg-[#E2E8F0] text-[#142B4A] flex items-center justify-center font-bold text-[9px] shrink-0 mt-0.5">
                    {idx + 1}
                  </span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Underwriting Authority Mandate Banner */}
          <div className="bg-[#142B4A] text-white p-3 rounded-md text-[11px] flex items-center justify-between gap-3 shadow-sm">
            <div className="flex items-center gap-2">
              <Scale className="w-4 h-4 text-[#38BDF8] shrink-0" />
              <p className="leading-tight text-slate-200">
                <strong>Underwriting Policy Notice:</strong> {report.recommendation_decision_role}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

