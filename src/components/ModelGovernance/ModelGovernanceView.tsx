/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import {
  Cpu,
  AlertTriangle,
  Database,
  BarChart2,
  FileCode,
  Layers,
  Info,
} from 'lucide-react';

export const ModelGovernanceView: React.FC = () => {
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
          <span className="text-xs font-semibold text-[#B45309] bg-[#FEF3C7] px-2.5 py-1 rounded border border-[#FDE68A] flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5" />
            Audit: Not available (No independent audit performed)
          </span>
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
          <p className="text-lg font-bold font-mono tabular-nums text-[#142B4A] mt-0.5">
            Not implemented
          </p>
          <span className="text-[11px] text-[#64748B]">In-memory session log only; cryptographic ledger not implemented</span>
        </div>
      </div>

      {/* Transparency Disclaimer Notice */}
      <div className="p-3 bg-[#FEF3C7] border border-[#FDE68A] rounded text-xs text-[#B45309] space-y-1">
        <p className="font-semibold">Credibility & Transparency Notice:</p>
        <p>
          Current valuation estimates are produced exclusively by a provisional rule-based calculation using deterministic scorecard multipliers.
          Machine learning models, statistical prediction intervals, and cryptographic ledgers are not implemented in this prototype.
        </p>
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
