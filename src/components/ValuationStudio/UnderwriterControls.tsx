/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  Sliders,
  ShieldAlert,
  Percent,
  CheckCircle,
  FileCheck,
  Building,
  RotateCcw,
  Sparkles,
} from 'lucide-react';
import { ValuationCase } from '../../types/valuation';
import { ValuationResult, formatIndianCurrency } from '../../utils/valuationEngine';

interface UnderwriterControlsProps {
  currentCase: ValuationCase;
  valuation: ValuationResult;
  onUpdateParams: (newParams: Partial<ValuationCase>) => void;
  onOpenSignOffModal: () => void;
  onReferCommittee: (reason: string) => void;
}

export const UnderwriterControls: React.FC<UnderwriterControlsProps> = ({
  currentCase,
  valuation,
  onUpdateParams,
  onOpenSignOffModal,
  onReferCommittee,
}) => {
  const [rationaleNote, setRationaleNote] = useState<string>(
    'Valuation grounded in 5 sample comparables within 1km. Clear 30-year title chain and high-floor orientation justify baseline assessment (synthetic demonstration case).'
  );
  const [showReferModal, setShowReferModal] = useState<boolean>(false);
  const [referReason, setReferReason] = useState<string>('Deviation from circle rate exceeds internal policy threshold (25%).');

  return (
    <div className="bg-white rounded-md border border-[#E2E8F0] shadow-sm p-3.5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-2">
        <div className="flex items-center gap-2">
          <Sliders className="w-4 h-4 text-[#2563EB]" />
          <div>
            <h4 className="text-xs font-bold text-[#142B4A] uppercase tracking-wide">
              Underwriter Stress Testing & Policy Overrides
            </h4>
            <p className="text-[11px] text-[#64748B]">
              Institutional haircut adjustment, distress discount, and sanction bounds
            </p>
          </div>
        </div>

        <button
          onClick={() => {
            onUpdateParams({
              underwriterHaircutPct: 0,
              distressDiscountPct: 18,
              ltvRatioPct: 75,
              legalRiskPenaltyPct: 0,
            });
          }}
          className="flex items-center gap-1 text-[11px] text-[#64748B] hover:text-[#142B4A]"
          title="Reset to Model Default"
        >
          <RotateCcw className="w-3 h-3" />
          Reset Baseline
        </button>
      </div>

      {/* Interactive Sliders & Inputs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Haircut Slider */}
        <div className="bg-[#F8FAFC] p-2.5 rounded border border-[#E2E8F0] space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="label-caps text-[#64748B]">Underwriter Haircut</span>
            <span
              className={`font-mono text-xs font-bold tabular-nums ${
                currentCase.underwriterHaircutPct < 0
                  ? 'text-[#B91C1C]'
                  : currentCase.underwriterHaircutPct > 0
                  ? 'text-[#15803D]'
                  : 'text-[#142B4A]'
              }`}
            >
              {currentCase.underwriterHaircutPct > 0 ? '+' : ''}
              {currentCase.underwriterHaircutPct}%
            </span>
          </div>
          <input
            type="range"
            min="-15"
            max="10"
            step="1"
            value={currentCase.underwriterHaircutPct}
            onChange={(e) => onUpdateParams({ underwriterHaircutPct: Number(e.target.value) })}
            className="w-full h-1.5 bg-[#CBD5E1] rounded-lg appearance-none cursor-pointer accent-[#2563EB]"
          />
          <div className="flex justify-between text-[10px] text-[#64748B]">
            <span>-15% (Conservative)</span>
            <span>+10% (Premium)</span>
          </div>
        </div>

        {/* Forced Sale / Distress Discount */}
        <div className="bg-[#F8FAFC] p-2.5 rounded border border-[#E2E8F0] space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="label-caps text-[#64748B]">Distress Liquidation Discount</span>
            <span className="font-mono text-xs font-bold text-[#142B4A] tabular-nums">
              {currentCase.distressDiscountPct}%
            </span>
          </div>
          <input
            type="range"
            min="10"
            max="35"
            step="1"
            value={currentCase.distressDiscountPct}
            onChange={(e) => onUpdateParams({ distressDiscountPct: Number(e.target.value) })}
            className="w-full h-1.5 bg-[#CBD5E1] rounded-lg appearance-none cursor-pointer accent-[#142B4A]"
          />
          <div className="flex justify-between text-[10px] text-[#64748B]">
            <span>10% (High Liquidity)</span>
            <span>35% (Deep Distress)</span>
          </div>
        </div>

        {/* Permissible LTV Bound */}
        <div className="bg-[#F8FAFC] p-2.5 rounded border border-[#E2E8F0] space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="label-caps text-[#64748B]">Sanction LTV Limit</span>
            <span className="font-mono text-xs font-bold text-[#2563EB] tabular-nums">
              {currentCase.ltvRatioPct}%
            </span>
          </div>
          <input
            type="range"
            min="50"
            max="80"
            step="1"
            value={currentCase.ltvRatioPct}
            onChange={(e) => onUpdateParams({ ltvRatioPct: Number(e.target.value) })}
            className="w-full h-1.5 bg-[#CBD5E1] rounded-lg appearance-none cursor-pointer accent-[#2563EB]"
          />
          <div className="flex justify-between text-[10px] text-[#64748B]">
            <span>50% (Conservative)</span>
            <span>80% (NHB Max Cap)</span>
          </div>
        </div>
      </div>

      {/* Real-time Recalculated Sanction Summary Bar */}
      <div className="bg-[#142B4A] text-white p-3 rounded-md grid grid-cols-2 sm:grid-cols-4 gap-3 shadow-sm">
        <div>
          <span className="label-caps text-slate-400 block text-[10px]">Net Assessed Collateral</span>
          <p className="text-base sm:text-lg font-bold font-mono tabular-nums text-white mt-0.5">
            {formatIndianCurrency(valuation.netAssessedValue)}
          </p>
          <span className="text-[10px] text-slate-300">
            {formatIndianCurrency(valuation.netAssessedValue, 'short')}
          </span>
        </div>

        <div>
          <span className="label-caps text-slate-400 block text-[10px]">Distress Liquidation Value</span>
          <p className="text-base sm:text-lg font-bold font-mono tabular-nums text-amber-300 mt-0.5">
            {formatIndianCurrency(valuation.distressLiquidationValue)}
          </p>
          <span className="text-[10px] text-amber-200">
            {formatIndianCurrency(valuation.distressLiquidationValue, 'short')}
          </span>
        </div>

        <div>
          <span className="label-caps text-slate-400 block text-[10px]">Max Permissible Sanction</span>
          <p className="text-base sm:text-lg font-bold font-mono tabular-nums text-emerald-400 mt-0.5">
            {formatIndianCurrency(valuation.maxSanctionAmount)}
          </p>
          <span className="text-[10px] text-emerald-300">
            At {currentCase.ltvRatioPct}% LTV Cap
          </span>
        </div>

        <div>
          <span className="label-caps text-slate-400 block text-[10px]">Requested Loan Coverage</span>
          <div className="flex items-center gap-1.5 mt-1">
            <span
              className={`text-xs font-bold px-2 py-0.5 rounded ${
                valuation.maxSanctionAmount >= currentCase.loanRequested
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                  : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
              }`}
            >
              {valuation.maxSanctionAmount >= currentCase.loanRequested ? 'Adequate Collateral' : 'Shortfall Alert'}
            </span>
          </div>
          <span className="text-[10px] text-slate-300 font-mono block mt-0.5">
            Req: {formatIndianCurrency(currentCase.loanRequested, 'short')}
          </span>
        </div>
      </div>

      {/* Underwriter Rationale Note */}
      <div className="space-y-1">
        <label className="label-caps text-[#64748B] block">
          Underwriter Technical Rationale & Audit Defense:
        </label>
        <textarea
          rows={2}
          value={rationaleNote}
          onChange={(e) => setRationaleNote(e.target.value)}
          className="w-full text-xs p-2 rounded border border-[#CBD5E1] bg-white focus:outline-none focus:border-[#2563EB] text-[#172033]"
          placeholder="State reason for haircut, market absorption rate, or physical inspection findings..."
        />
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[#E2E8F0]">
        <button
          onClick={() => setShowReferModal(true)}
          className="px-3 py-1.5 text-xs font-semibold rounded border border-[#CBD5E1] text-[#142B4A] hover:bg-[#F8FAFC] transition-colors"
        >
          Refer to Credit Risk Committee
        </button>

        <div className="flex items-center gap-2">
          <button
            onClick={onOpenSignOffModal}
            className="px-4 py-2 text-xs font-semibold rounded bg-[#2563EB] hover:bg-[#1D4ED8] text-white shadow-sm transition-colors flex items-center gap-1.5"
          >
            <FileCheck className="w-4 h-4" />
            Approve & Sign-off Valuation
          </button>
        </div>
      </div>

      {/* Refer Committee Modal */}
      {showReferModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#142B4A]/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-md border border-[#CBD5E1] shadow-2xl max-w-md w-full p-4 space-y-3">
            <div className="flex items-center gap-2 text-[#D97706]">
              <ShieldAlert className="w-5 h-5" />
              <h3 className="text-xs font-bold text-[#142B4A] uppercase">
                Refer Collateral Case to Risk Committee
              </h3>
            </div>
            <p className="text-xs text-[#64748B]">
              This case will be escalated to the Credit Risk & Audit Committee for high-variance appraisal defense.
            </p>
            <div>
              <label className="label-caps text-[#64748B] block mb-1">Escalation Reason:</label>
              <textarea
                rows={3}
                value={referReason}
                onChange={(e) => setReferReason(e.target.value)}
                className="w-full text-xs p-2 rounded border border-[#CBD5E1] focus:border-[#2563EB] text-[#172033]"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-[#E2E8F0]">
              <button
                onClick={() => setShowReferModal(false)}
                className="px-3 py-1.5 text-xs font-medium text-[#64748B] hover:text-[#172033]"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  onReferCommittee(referReason);
                  setShowReferModal(false);
                }}
                className="px-3 py-1.5 text-xs font-semibold bg-[#D97706] text-white rounded hover:bg-[#B45309]"
              >
                Confirm Escalation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
