/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import {
  Building2,
  Bell,
  PlusCircle,
  FileSpreadsheet,
  ChevronDown,
  ShieldCheck,
  Search,
  Sparkles,
} from 'lucide-react';
import { ValuationCase } from '../types/valuation';

interface HeaderProps {
  cases: ValuationCase[];
  currentCaseId: string;
  onSelectCase: (caseId: string) => void;
  onOpenNewCaseModal: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  cases,
  currentCaseId,
  onSelectCase,
  onOpenNewCaseModal,
}) => {
  const currentCase = cases.find((c) => c.id === currentCaseId) || cases[0];

  return (
    <header className="h-14 bg-white border-b border-[#E2E8F0] px-4 flex items-center justify-between shrink-0 shadow-xs z-20">
      {/* Left: Case Selector & Quick Switcher */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-xs text-[#64748B]">
          <Building2 className="w-4 h-4 text-[#142B4A]" />
          <span className="font-semibold text-[#142B4A] hidden sm:inline">Active File:</span>
        </div>

        <select
          value={currentCaseId}
          onChange={(e) => onSelectCase(e.target.value)}
          className="text-xs font-semibold py-1.5 px-2.5 rounded border border-[#CBD5E1] bg-[#F8FAFC] text-[#142B4A] focus:outline-none focus:border-[#2563EB] cursor-pointer max-w-[280px] sm:max-w-md truncate"
        >
          {cases.map((c) => (
            <option key={c.id} value={c.id}>
              {c.applicationNo} — {c.projectName} ({c.city})
            </option>
          ))}
        </select>

        <span className="hidden md:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#FEF3C7] text-[#B45309] border border-[#FDE68A]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#D97706]" />
          Demonstration Data / Mock SRO
        </span>
      </div>

      {/* Right: Actions & User Underwriter Profile */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenNewCaseModal}
          className="px-3 py-1.5 text-xs font-semibold rounded bg-[#2563EB] hover:bg-[#1D4ED8] text-white flex items-center gap-1.5 shadow-xs transition-colors"
        >
          <PlusCircle className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">New Appraisal Intake</span>
          <span className="sm:hidden">New</span>
        </button>

        {/* Divider */}
        <div className="h-6 w-px bg-[#E2E8F0]" />

        {/* Underwriter Profile Badge */}
        <div className="flex items-center gap-2 text-xs">
          <div className="w-8 h-8 rounded-full bg-[#142B4A] text-white flex items-center justify-center font-bold text-xs ring-2 ring-[#CBD5E1]">
            VS
          </div>
          <div className="hidden sm:block text-left">
            <span className="font-semibold text-xs text-[#172033] block leading-tight">
              V. Sundaram
            </span>
            <span className="text-[10px] text-[#64748B] block leading-tight">
              Senior Credit Underwriter
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
