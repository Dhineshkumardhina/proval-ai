/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  TrendingDown,
  Activity,
  Layers,
  FileWarning,
  CheckCircle,
  Percent,
  Sliders,
} from 'lucide-react';
import { ValuationCase } from '../../types/valuation';
import { formatIndianCurrency } from '../../utils/valuationEngine';

interface RiskAuditDashboardProps {
  cases: ValuationCase[];
  onSelectCase: (caseId: string) => void;
}

export const RiskAuditDashboard: React.FC<RiskAuditDashboardProps> = ({
  cases,
  onSelectCase,
}) => {
  const [macroShockPct, setMacroShockPct] = useState<number>(10); // 10% price correction shock
  const [activeAuditTab, setActiveAuditTab] = useState<'VARIANCE' | 'LEGAL'>('VARIANCE');

  // Breaches: circle rate deviation > 15%
  const highVarianceCases = cases.filter((c) => {
    const dev = ((c.baseMarketRatePerSqFt - c.circleRatePerSqFt) / c.circleRatePerSqFt) * 100;
    return dev > 15;
  });

  // Legal & title charges
  const flaggedTitleCases = cases.filter((c) => c.encumbranceStatus !== 'NIL_ENCUMBRANCE');

  // Compute portfolio impact under macro shock (deterministic linear sensitivity)
  const totalOriginalAssessed = cases.reduce(
    (sum, c) => sum + c.baseMarketRatePerSqFt * c.carpetAreaSqFt,
    0
  );
  const stressedTotalAssessed = totalOriginalAssessed * (1 - macroShockPct / 100);
  const collateralStressLoss = totalOriginalAssessed - stressedTotalAssessed;

  return (
    <div className="space-y-4">
      {/* Top Banner */}
      <div className="bg-[#142B4A] text-white p-4 rounded-md shadow-sm flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-amber-400" />
            <h2 className="text-sm font-bold uppercase tracking-wider">
              Credit Risk & Collateral Audit Console
            </h2>
          </div>
          <p className="text-xs text-slate-300 mt-0.5">
            Surveillance of valuation deviations, title encumbrance discrepancies, and scenario stress testing (Prototype)
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <button
            onClick={() => setActiveAuditTab('VARIANCE')}
            className={`px-2.5 py-1 rounded font-semibold transition-colors ${
              activeAuditTab === 'VARIANCE'
                ? 'bg-amber-400 text-[#142B4A]'
                : 'bg-amber-500/20 text-amber-300 border border-amber-500/30 hover:bg-amber-500/30'
            }`}
          >
            {highVarianceCases.length} High-Variance Files
          </button>
          <button
            onClick={() => setActiveAuditTab('LEGAL')}
            className={`px-2.5 py-1 rounded font-semibold transition-colors ${
              activeAuditTab === 'LEGAL'
                ? 'bg-rose-400 text-[#142B4A]'
                : 'bg-rose-500/20 text-rose-300 border border-rose-500/30 hover:bg-rose-500/30'
            }`}
          >
            {flaggedTitleCases.length} Legal Flags
          </button>
        </div>
      </div>

      {/* Stress Testing Scenario Simulator */}
      <div className="bg-white p-4 rounded-md border border-[#E2E8F0] shadow-sm space-y-3">
        <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-2">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-[#2563EB]" />
            <h3 className="text-xs font-bold text-[#142B4A] uppercase tracking-wide">
              Portfolio Stress Testing & LTV Shock Matrix
            </h3>
          </div>
          <span className="text-xs font-semibold text-[#142B4A]">
            Shock Magnitude: <span className="text-[#DC2626] font-mono">-{macroShockPct}% Market Shock</span>
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-center">
          <div className="md:col-span-2 space-y-2">
            <label className="text-xs text-[#64748B] block">
              Simulate Sub-Market Price Correction Shock (-5% to -25%):
            </label>
            <input
              type="range"
              min="5"
              max="25"
              step="1"
              value={macroShockPct}
              onChange={(e) => setMacroShockPct(Number(e.target.value))}
              className="w-full h-2 bg-[#CBD5E1] rounded appearance-none cursor-pointer accent-[#DC2626]"
            />
            <div className="flex justify-between text-[10px] text-[#64748B]">
              <span>-5% Soft Correction</span>
              <span>-15% Moderate Downturn</span>
              <span>-25% Severe Real Estate Shock</span>
            </div>
          </div>

          <div className="bg-[#F8FAFC] p-3 rounded border border-[#E2E8F0]">
            <span className="label-caps text-[#64748B] block text-[10px]">Simulated Stress Loss</span>
            <p className="text-lg font-bold font-mono text-[#DC2626] tabular-nums mt-0.5">
              -{formatIndianCurrency(collateralStressLoss, 'short')}
            </p>
            <span className="text-[10px] text-[#64748B]">
              Deterministic haircut (not statistical VaR)
            </span>
          </div>

          <div className="bg-[#F8FAFC] p-3 rounded border border-[#E2E8F0]">
            <span className="label-caps text-[#64748B] block text-[10px]">Stressed Book LTV</span>
            <p className="text-lg font-bold font-mono text-[#B45309] tabular-nums mt-0.5">
              {(75 / (1 - macroShockPct / 100)).toFixed(1)}%
            </p>
            <span className="text-[10px] text-[#15803D]">
              Assumes 75.0% baseline LTV
            </span>
          </div>
        </div>
      </div>

      {/* High Variance & Deviation Audit Grid */}
      <div className="bg-white rounded-md border border-[#E2E8F0] shadow-sm overflow-hidden">
        <div className="p-3 bg-[#F8FAFC] border-b border-[#CBD5E1] flex items-center justify-between">
          <div className="flex items-center gap-2">
            {activeAuditTab === 'VARIANCE' ? (
              <>
                <AlertTriangle className="w-4 h-4 text-[#D97706]" />
                <h4 className="text-xs font-bold text-[#142B4A] uppercase tracking-wide">
                  Valuation Deviation Alerts (&gt;15% Ready Reckoner Spread)
                </h4>
              </>
            ) : (
              <>
                <FileWarning className="w-4 h-4 text-[#DC2626]" />
                <h4 className="text-xs font-bold text-[#142B4A] uppercase tracking-wide">
                  Legal & Title Encumbrance Flagged Files
                </h4>
              </>
            )}
          </div>
          <span className="text-[11px] text-[#64748B]">
            Demonstration scrutiny rules based on prudential loan-to-value guidelines
          </span>
        </div>

        <div className="divide-y divide-[#E2E8F0]">
          {activeAuditTab === 'VARIANCE' ? (
            highVarianceCases.map((c) => {
              const dev = Number(
                (((c.baseMarketRatePerSqFt - c.circleRatePerSqFt) / c.circleRatePerSqFt) * 100).toFixed(1)
              );

              return (
                <div
                  key={c.id}
                  onClick={() => onSelectCase(c.id)}
                  className="p-3 hover:bg-[#F1F5F9] transition-colors cursor-pointer flex flex-wrap items-center justify-between gap-3"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-[#142B4A]">
                        {c.applicationNo}
                      </span>
                      <span className="text-xs font-semibold text-[#172033]">
                        {c.projectName} ({c.city})
                      </span>
                      <span className="bg-[#FEF3C7] text-[#B45309] text-[10px] font-semibold px-2 py-0.2 rounded border border-[#FDE68A]">
                        +{dev}% Spread
                      </span>
                    </div>
                    <p className="text-[11px] text-[#64748B]">
                      Market Rate: ₹{c.baseMarketRatePerSqFt}/sqft vs Circle Rate: ₹{c.circleRatePerSqFt}/sqft | Borrower: {c.borrowerName}
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs font-bold text-[#142B4A]">
                      Loan: {formatIndianCurrency(c.loanRequested, 'short')}
                    </span>
                    <button className="px-2.5 py-1 text-xs font-semibold text-[#2563EB] bg-[#EFF6FF] rounded border border-[#BFDBFE] hover:bg-[#2563EB] hover:text-white transition-colors">
                      Review In Studio
                    </button>
                  </div>
                </div>
              );
            })
          ) : (
            flaggedTitleCases.map((c) => (
              <div
                key={c.id}
                onClick={() => onSelectCase(c.id)}
                className="p-3 hover:bg-[#F1F5F9] transition-colors cursor-pointer flex flex-wrap items-center justify-between gap-3 bg-[#FEF2F2]/40"
              >
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-[#142B4A]">
                      {c.applicationNo}
                    </span>
                    <span className="text-xs font-semibold text-[#172033]">
                      {c.projectName} ({c.city})
                    </span>
                    <span className="bg-[#FEE2E2] text-[#B91C1C] text-[10px] font-semibold px-2 py-0.2 rounded border border-[#FECACA]">
                      {c.encumbranceStatus}
                    </span>
                  </div>
                  <p className="text-[11px] text-[#64748B]">
                    Title Chain: {c.titleChainYears} Yrs | Borrower: {c.borrowerName} | Branch: {c.branch}
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs font-bold text-[#142B4A]">
                    Loan: {formatIndianCurrency(c.loanRequested, 'short')}
                  </span>
                  <button className="px-2.5 py-1 text-xs font-semibold text-[#DC2626] bg-[#FEF2F2] rounded border border-[#FECACA] hover:bg-[#DC2626] hover:text-white transition-colors">
                    Review In Studio
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
