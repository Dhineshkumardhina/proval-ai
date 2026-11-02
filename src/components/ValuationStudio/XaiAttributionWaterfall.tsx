/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { Sparkles, TrendingUp, TrendingDown, HelpCircle, Layers, ArrowRight } from 'lucide-react';
import { ValuationResult } from '../../utils/valuationEngine';

interface XaiAttributionWaterfallProps {
  valuation: ValuationResult;
}

export const XaiAttributionWaterfall: React.FC<XaiAttributionWaterfallProps> = ({ valuation }) => {
  return (
    <div className="bg-white rounded-md border border-[#E2E8F0] shadow-sm p-3.5 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-2">
        <div className="flex items-center gap-2">
          <span className="p-1 rounded bg-[#EFF6FF] text-[#2563EB] border border-[#BFDBFE]">
            <Sparkles className="w-3.5 h-3.5" />
          </span>
          <div>
            <h4 className="text-xs font-bold text-[#142B4A] uppercase tracking-wide">
              Hedonic Factor Decomposition & Waterfall
            </h4>
            <p className="text-[11px] text-[#64748B]">
              Provisional rule-based estimation: deterministic additive micro-market adjustments (not machine learning)
            </p>
          </div>
        </div>

        <span className="text-[11px] font-semibold text-[#334155] bg-[#F1F5F9] px-2 py-0.5 rounded-full border border-[#CBD5E1] flex items-center gap-1">
          Rule Consistency: {valuation.confidenceScorePct}% (Uncalibrated)
        </span>
      </div>

      {/* Attribution Factors List */}
      <div className="space-y-2">
        {valuation.attributionBreakdown.map((item, idx) => {
          const isBaseline = idx === 0;
          const isPositive = item.impactPerSqFt > 0;
          const isNegative = item.impactPerSqFt < 0;

          return (
            <div
              key={idx}
              className={`p-2.5 rounded border transition-colors ${
                isBaseline
                  ? 'bg-[#F8FAFC] border-[#CBD5E1]'
                  : isPositive
                  ? 'bg-white border-[#E2E8F0] hover:border-[#99F6E4]'
                  : 'bg-white border-[#E2E8F0] hover:border-[#FECACA]'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className={`w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold ${
                      isBaseline
                        ? 'bg-[#142B4A] text-white'
                        : isPositive
                        ? 'bg-[#DCFCE7] text-[#15803D]'
                        : 'bg-[#FEE2E2] text-[#B91C1C]'
                    }`}
                  >
                    {isBaseline ? 'B' : isPositive ? '+' : '-'}
                  </span>

                  <div>
                    <span className="text-xs font-semibold text-[#172033]">
                      {item.factor}
                    </span>
                    <p className="text-[11px] text-[#64748B]">
                      {item.description}
                    </p>
                  </div>
                </div>

                <div className="text-right">
                  <span
                    className={`text-xs font-bold font-mono tabular-nums ${
                      isBaseline
                        ? 'text-[#142B4A]'
                        : isPositive
                        ? 'text-[#15803D]'
                        : 'text-[#B91C1C]'
                    }`}
                  >
                    {isBaseline
                      ? `₹${item.impactPerSqFt.toLocaleString('en-IN')}`
                      : `${isPositive ? '+' : ''}₹${item.impactPerSqFt.toLocaleString('en-IN')}`}{' '}
                    <span className="text-[10px] font-normal text-[#64748B]">/ sq ft</span>
                  </span>
                </div>
              </div>

              {/* Relative Impact Progress Bar */}
              {!isBaseline && (
                <div className="w-full bg-[#F1F5F9] h-1.5 rounded-full overflow-hidden mt-1.5">
                  <div
                    className={`h-full rounded-full ${isPositive ? 'bg-[#0F766E]' : 'bg-[#DC2626]'}`}
                    style={{
                      width: `${Math.min(100, (Math.abs(item.impactPerSqFt) / 1000) * 100)}%`,
                    }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Net Scorecard Rate Summary Footnote */}
      <div className="p-2.5 bg-[#F1F5F9] rounded border border-[#CBD5E1] flex items-center justify-between text-xs">
        <div>
          <span className="font-semibold text-[#142B4A] flex items-center gap-1.5">
            <ArrowRight className="w-3.5 h-3.5 text-[#2563EB]" />
            Net Rule-Based Assessed Rate:
          </span>
          <span className="text-[10px] text-[#64748B] block mt-0.5">
            * Additive adjustments applied to micro-market baseline (Provisional rule-based estimation)
          </span>
        </div>
        <div className="text-right font-mono font-bold tabular-nums text-sm text-[#142B4A]">
          ₹{(valuation.ruleAdjustedRatePerSqFt ?? valuation.aiAdjustedRatePerSqFt).toLocaleString('en-IN')}{' '}
          <span className="text-[11px] text-[#64748B] font-normal">/ sq ft carpet</span>
        </div>
      </div>
    </div>
  );
};
