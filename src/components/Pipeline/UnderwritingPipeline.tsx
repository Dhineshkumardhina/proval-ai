/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  Search,
  Filter,
  ArrowRight,
  ShieldCheck,
  AlertTriangle,
  Building,
  CheckCircle2,
  Clock,
  Layers,
  PlusCircle,
} from 'lucide-react';
import { ValuationCase } from '../../types/valuation';
import { formatIndianCurrency } from '../../utils/valuationEngine';

interface UnderwritingPipelineProps {
  cases: ValuationCase[];
  onSelectCase: (caseId: string) => void;
  onOpenNewCaseModal: () => void;
}

export const UnderwritingPipeline: React.FC<UnderwritingPipelineProps> = ({
  cases,
  onSelectCase,
  onOpenNewCaseModal,
}) => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCity, setSelectedCity] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');

  const filteredCases = cases.filter((c) => {
    const matchesSearch =
      c.borrowerName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.applicationNo.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.projectName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.locality.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesCity = selectedCity === 'ALL' || c.city === selectedCity;
    const matchesStatus = selectedStatus === 'ALL' || c.status === selectedStatus;

    return matchesSearch && matchesCity && matchesStatus;
  });

  const totalPipelineValue = cases.reduce((sum, c) => sum + c.loanRequested, 0);
  const readyCount = cases.filter((c) => c.status === 'READY_FOR_APPROVAL').length;
  const reviewCount = cases.filter((c) => c.status === 'REVIEW_REQUIRED').length;
  const alertCount = cases.filter((c) => c.status === 'HIGH_ALERT').length;

  return (
    <div className="space-y-4">
      {/* Top Portfolio Stats Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-white p-3.5 rounded-md border border-[#E2E8F0] shadow-sm">
          <span className="label-caps text-[#64748B] block text-[10px]">Total Active Pipeline</span>
          <p className="text-xl font-bold font-mono tabular-nums text-[#142B4A] mt-0.5">
            {formatIndianCurrency(totalPipelineValue, 'short')}
          </p>
          <span className="text-[11px] text-[#64748B]">{cases.length} Collateral Files Active</span>
        </div>

        <div className="bg-white p-3.5 rounded-md border border-[#E2E8F0] shadow-sm">
          <span className="label-caps text-[#64748B] block text-[10px]">Ready for Underwriter Sign-off</span>
          <p className="text-xl font-bold font-mono tabular-nums text-[#15803D] mt-0.5">
            {readyCount} Files
          </p>
          <span className="text-[11px] text-[#15803D] font-medium">Clear Title & OCR Verified</span>
        </div>

        <div className="bg-white p-3.5 rounded-md border border-[#E2E8F0] shadow-sm">
          <span className="label-caps text-[#64748B] block text-[10px]">Review Required</span>
          <p className="text-xl font-bold font-mono tabular-nums text-[#D97706] mt-0.5">
            {reviewCount} Files
          </p>
          <span className="text-[11px] text-[#D97706] font-medium">Variance &gt; 15% from Circle Rate</span>
        </div>

        <div className="bg-white p-3.5 rounded-md border border-[#E2E8F0] shadow-sm">
          <span className="label-caps text-[#64748B] block text-[10px]">Critical Alerts</span>
          <p className="text-xl font-bold font-mono tabular-nums text-[#DC2626] mt-0.5">
            {alertCount} Files
          </p>
          <span className="text-[11px] text-[#DC2626] font-medium">Encumbrance / Plan Variance</span>
        </div>
      </div>

      {/* Table Card */}
      <div className="bg-white rounded-md border border-[#E2E8F0] shadow-sm overflow-hidden flex flex-col">
        {/* Table Filters Header */}
        <div className="p-3.5 bg-[#F8FAFC] border-b border-[#CBD5E1] flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 flex-1 min-w-[260px] max-w-md">
            <div className="relative w-full">
              <Search className="w-3.5 h-3.5 text-[#64748B] absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Search by borrower, file number, project or locality..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full text-xs pl-8 pr-3 py-1.5 rounded border border-[#CBD5E1] bg-white focus:outline-none focus:border-[#2563EB] text-[#172033]"
              />
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* City Filter */}
            <select
              value={selectedCity}
              onChange={(e) => setSelectedCity(e.target.value)}
              className="text-xs py-1.5 px-2.5 rounded border border-[#CBD5E1] bg-white text-[#172033] focus:border-[#2563EB]"
            >
              <option value="ALL">All Metros</option>
              <option value="Bengaluru">Bengaluru</option>
              <option value="Mumbai">Mumbai</option>
              <option value="Delhi-NCR">Delhi-NCR</option>
              <option value="Hyderabad">Hyderabad</option>
              <option value="Pune">Pune</option>
              <option value="Chennai">Chennai</option>
            </select>

            {/* Status Filter */}
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="text-xs py-1.5 px-2.5 rounded border border-[#CBD5E1] bg-white text-[#172033] focus:border-[#2563EB]"
            >
              <option value="ALL">All Risk Stages</option>
              <option value="READY_FOR_APPROVAL">Ready for Sign-off</option>
              <option value="REVIEW_REQUIRED">Review Required</option>
              <option value="HIGH_ALERT">Critical Alert</option>
              <option value="APPROVED">Approved</option>
            </select>

            <button
              onClick={onOpenNewCaseModal}
              className="px-3 py-1.5 text-xs font-semibold rounded bg-[#2563EB] text-white hover:bg-[#1D4ED8] flex items-center gap-1.5 shadow-xs"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              New Appraisal Intake
            </button>
          </div>
        </div>

        {/* High-Density Pipeline Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-[#F8FAFC] border-b border-[#CBD5E1] text-[#64748B] label-caps">
                <th className="py-2.5 px-3 font-semibold">Application No</th>
                <th className="py-2.5 px-3 font-semibold">Borrower Name</th>
                <th className="py-2.5 px-3 font-semibold">Collateral Asset & City</th>
                <th className="py-2.5 px-3 font-semibold text-right">Carpet Area</th>
                <th className="py-2.5 px-3 font-semibold text-right">Requested Loan</th>
                <th className="py-2.5 px-3 font-semibold text-right">Declared Price</th>
                <th className="py-2.5 px-3 font-semibold text-center">Circle Rate Dev</th>
                <th className="py-2.5 px-3 font-semibold text-center">Title & OCR</th>
                <th className="py-2.5 px-3 font-semibold text-center">Appraisal State</th>
                <th className="py-2.5 px-3 font-semibold text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E2E8F0]">
              {filteredCases.map((c, idx) => {
                const deviation = Number(
                  (((c.baseMarketRatePerSqFt - c.circleRatePerSqFt) / c.circleRatePerSqFt) * 100).toFixed(1)
                );

                return (
                  <tr
                    key={c.id}
                    onClick={() => onSelectCase(c.id)}
                    className="h-11 cursor-pointer transition-colors hover:bg-[#F1F5F9] group"
                  >
                    <td className="py-2 px-3 font-mono text-[11px] font-bold text-[#142B4A] whitespace-nowrap">
                      {c.applicationNo}
                    </td>

                    <td className="py-2 px-3 font-semibold text-[#172033]">
                      {c.borrowerName}
                      <span className="block text-[10px] text-[#64748B] font-normal">
                        CIBIL: {c.cibilScore}
                      </span>
                    </td>

                    <td className="py-2 px-3">
                      <span className="font-medium text-[#172033] block max-w-[200px] truncate">
                        {c.projectName}
                      </span>
                      <span className="text-[11px] text-[#64748B]">
                        {c.locality}, {c.city}
                      </span>
                    </td>

                    <td className="py-2 px-3 text-right font-mono tabular-nums text-[#334155]">
                      {c.carpetAreaSqFt} <span className="text-[10px] text-[#64748B]">sq ft</span>
                    </td>

                    <td className="py-2 px-3 text-right font-mono tabular-nums font-semibold text-[#172033]">
                      {formatIndianCurrency(c.loanRequested, 'short')}
                    </td>

                    <td className="py-2 px-3 text-right font-mono tabular-nums text-[#64748B]">
                      {formatIndianCurrency(c.declaredAgreementValue, 'short')}
                    </td>

                    <td className="py-2 px-3 text-center">
                      <span
                        className={`font-mono text-[11px] font-semibold px-2 py-0.5 rounded ${
                          deviation > 30
                            ? 'bg-[#FEE2E2] text-[#B91C1C]'
                            : deviation > 15
                            ? 'bg-[#FEF3C7] text-[#B45309]'
                            : 'bg-[#DCFCE7] text-[#15803D]'
                        }`}
                      >
                        +{deviation}%
                      </span>
                    </td>

                    <td className="py-2 px-3 text-center">
                      {c.encumbranceStatus === 'NIL_ENCUMBRANCE' ? (
                        <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-[#15803D]">
                          <CheckCircle2 className="w-3 h-3" />
                          Nil Encumbrance
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-[#B91C1C]">
                          <AlertTriangle className="w-3 h-3" />
                          Charge Flagged
                        </span>
                      )}
                    </td>

                    <td className="py-2 px-3 text-center">
                      <span
                        className={`inline-block px-2.5 py-0.5 rounded-full text-[10.5px] font-semibold border ${
                          c.status === 'APPROVED'
                            ? 'bg-[#DCFCE7] text-[#15803D] border-[#BBF7D0]'
                            : c.status === 'READY_FOR_APPROVAL'
                            ? 'bg-[#EFF6FF] text-[#2563EB] border-[#BFDBFE]'
                            : c.status === 'REVIEW_REQUIRED'
                            ? 'bg-[#FEF3C7] text-[#B45309] border-[#FDE68A]'
                            : 'bg-[#FEE2E2] text-[#B91C1C] border-[#FECACA]'
                        }`}
                      >
                        {c.statusLabel}
                      </span>
                    </td>

                    <td className="py-2 px-3 text-center">
                      <button className="px-2.5 py-1 text-[11px] font-semibold text-[#2563EB] bg-[#EFF6FF] hover:bg-[#2563EB] hover:text-white rounded border border-[#BFDBFE] transition-colors inline-flex items-center gap-1">
                        Evaluate
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
