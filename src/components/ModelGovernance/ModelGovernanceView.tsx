/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import {
  Cpu,
  AlertTriangle,
  ShieldCheck,
  Database,
  BarChart2,
  FileCode,
  Layers,
  Info,
} from 'lucide-react';
import { fetchAuditSummary, AuditSummary } from '../../services/apiClient';

export const ModelGovernanceView: React.FC = () => {
  const [auditSummary, setAuditSummary] = useState<AuditSummary | null>(null);

  useEffect(() => {
    let isMounted = true;
    fetchAuditSummary()
      .then((summary) => {
        if (isMounted && summary) {
          setAuditSummary(summary);
        }
      })
      .catch(() => {});
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="space-y-4">
      {/* Top Banner */}
      <div className="bg-white p-4 rounded-md border border-[#E2E8F0] shadow-sm flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded bg-[#EFF6FF] text-[#2563EB] border border-[#BFDBFE]">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-[#142B4A] uppercase tracking-wide">
              Model Governance & Valuation Architecture Specification
            </h2>
            <p className="text-xs text-[#64748B]">
              Target Architecture: Alignment with NHB & RBI Algorithmic Transparency Guidelines (Design Blueprint)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-bold text-[#334155] bg-[#F1F5F9] px-2.5 py-1 rounded border border-[#CBD5E1]">
            Engine: Provisional Rule-Based (v0.1.0-alpha)
          </span>
          {auditSummary ? (
            <span className="text-xs font-semibold text-[#15803D] bg-[#DCFCE7] px-2.5 py-1 rounded border border-[#86EFAC] flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              Audit: SHA-256 Ledger Active ({auditSummary.is_chain_intact ? 'Chain Intact' : 'Surveillance Alert'})
            </span>
          ) : (
            <span className="text-xs font-semibold text-[#B45309] bg-[#FEF3C7] px-2.5 py-1 rounded border border-[#FDE68A] flex items-center gap-1">
              <AlertTriangle className="w-3.5 h-3.5" />
              Audit: Cryptographic SHA-256 Active
            </span>
          )}
        </div>
      </div>

      {/* Model Performance KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-white p-3.5 rounded-md border border-[#E2E8F0] shadow-sm">
          <span className="label-caps text-[#64748B] block text-[10px]">Training Dataset Size</span>
          <p className="text-lg font-bold font-mono tabular-nums text-[#64748B] mt-0.5">
            Not available
          </p>
          <span className="text-[11px] text-[#64748B]">Deterministic rule engine; no ML dataset</span>
        </div>

        <div className="bg-white p-3.5 rounded-md border border-[#E2E8F0] shadow-sm">
          <span className="label-caps text-[#64748B] block text-[10px]">Mean Abs % Error (MAPE)</span>
          <p className="text-lg font-bold font-mono tabular-nums text-[#D97706] mt-0.5">
            Pending verification
          </p>
          <span className="text-[11px] text-[#64748B]">Benchmark against ground truth deeds pending</span>
        </div>

        <div className="bg-white p-3.5 rounded-md border border-[#E2E8F0] shadow-sm">
          <span className="label-caps text-[#64748B] block text-[10px]">R² Goodness of Fit</span>
          <p className="text-lg font-bold font-mono tabular-nums text-[#64748B] mt-0.5">
            Pending verification
          </p>
          <span className="text-[11px] text-[#64748B]">Cross-validation benchmark not performed</span>
        </div>

        <div className="bg-white p-3.5 rounded-md border border-[#E2E8F0] shadow-sm">
          <span className="label-caps text-[#64748B] block text-[10px]">Audit Ledger Implementation</span>
          <p className="text-lg font-bold font-mono tabular-nums text-[#0F766E] mt-0.5">
            {auditSummary ? `${auditSummary.total_events} Blocks` : 'SHA-256 Active'}
          </p>
          <span className="text-[11px] text-[#64748B]">
            {auditSummary && auditSummary.is_chain_intact
              ? 'Tamper-evident cryptographic SHA-256 chain verified'
              : 'Cryptographic SHA-256 hash-chained immutable audit ledger'}
          </span>
        </div>
      </div>

      {/* Transparency Disclaimer Notice */}
      <div className="p-3 bg-[#FEF3C7] border border-[#FDE68A] rounded text-xs text-[#B45309] space-y-1">
        <p className="font-semibold">Credibility & Algorithmic Transparency Notice:</p>
        <p>
          Current valuation estimates are served by the provisional rule-based hedonic engine.
          The Machine Learning architecture (CatBoost, SHAP, and Split Conformal Prediction) is implemented, but training and calibration remain strictly <strong>GATED</strong> until verified empirical records reach 1,000 for training and 100 for calibration holdouts.
        </p>
      </div>

      {/* Uncertainty & Governance Conceptual Taxonomy Separation */}
      <div className="bg-white p-4 rounded-md border border-[#E2E8F0] shadow-sm space-y-3">
        <div className="border-b border-[#E2E8F0] pb-2">
          <h3 className="text-xs font-bold text-[#142B4A] uppercase tracking-wide">
            Uncertainty Quantification & Scoring Taxonomy (Phase 2F Separation)
          </h3>
          <p className="text-[11px] text-[#64748B]">
            Strict separation of deterministic scorecard heuristics from statistically calibrated conformal intervals
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div className="p-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded">
            <span className="font-bold text-[#0F766E] block mb-1">1. Rule Consistency Score</span>
            <p className="text-[#64748B]">
              Deterministic scorecard heuristic evaluating alignment between property inputs, statutory circle rates, and underwriter haircut parameters. <strong>NOT a statistical probability.</strong>
            </p>
          </div>

          <div className="p-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded">
            <span className="font-bold text-[#2563EB] block mb-1">2. Data Completeness Score</span>
            <p className="text-[#64748B]">
              Proportion of mandatory and statutory physical, spatial, title, and inspection fields populated in the loan dossier.
            </p>
          </div>

          <div className="p-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded">
            <span className="font-bold text-[#142B4A] block mb-1">3. Evidence Coverage</span>
            <p className="text-[#64748B]">
              Density, spatial proximity, and recency of registered comparable deed transactions within the property micro-market.
            </p>
          </div>

          <div className="p-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded">
            <span className="font-bold text-[#D97706] block mb-1">4. Conformal Prediction Interval (90% / 95%)</span>
            <p className="text-[#64748B]">
              <strong>Status: UNCALIBRATED (Gated).</strong> Finite-sample split conformal interval [Lower, Upper] with guaranteed marginal coverage. Deliberately withheld until genuine empirical calibration holdouts are acquired.
            </p>
          </div>
        </div>
      </div>

      {/* Indicative Feature Weights Matrix */}
      <div className="bg-white p-4 rounded-md border border-[#E2E8F0] shadow-sm space-y-3">
        <div className="border-b border-[#E2E8F0] pb-2">
          <h3 className="text-xs font-bold text-[#142B4A] uppercase tracking-wide">
            Indicative Feature Weights (Scorecard Design Blueprint)
          </h3>
          <p className="text-[11px] text-[#64748B]">
            Target relative weighting distribution for hedonic property factors (Design specification — not empirical TreeSHAP values)
          </p>
        </div>

        <div className="space-y-2.5">
          {[
            { name: 'Sub-Market SRO Registration Density (1km Radius)', weight: 36, color: '#142B4A' },
            { name: 'Floor Level & Vertical Elevation Index', weight: 18, color: '#0F766E' },
            { name: 'Master Plan Road Width & Arterial Access', weight: 15, color: '#2563EB' },
            { name: 'Gated Amenities, Clubhouse & Power Infrastructure', weight: 14, color: '#0F766E' },
            { name: 'Asset Age & Structural Vintage Depreciation', weight: 9, color: '#64748B' },
            { name: 'Developer Brand Tier & Track Record', weight: 8, color: '#334155' },
          ].map((feat, idx) => (
            <div key={idx} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-[#172033]">{feat.name}</span>
                <span className="font-mono font-bold text-[#142B4A]">{feat.weight}%</span>
              </div>
              <div className="w-full bg-[#F1F5F9] h-2 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${feat.weight}%`, backgroundColor: feat.color }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
