/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  FileText,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Search,
  ExternalLink,
  ShieldCheck,
  Stamp,
  Eye,
  Download,
} from 'lucide-react';
import { ValuationCase, DocumentVerificationField, CREDIBILITY_LABELS } from '../../types/valuation';

interface DocumentOcrViewerProps {
  currentCase: ValuationCase;
}

export const DocumentOcrViewer: React.FC<DocumentOcrViewerProps> = ({ currentCase }) => {
  const [selectedDocType, setSelectedDocType] = useState<'INDEX_II' | 'ENCUMBRANCE' | 'SANCTION_PLAN'>('INDEX_II');
  const [highlightedField, setHighlightedField] = useState<string | null>(null);

  const matchedCount = currentCase.documentFields.filter((f) => f.matchStatus === 'MATCHED').length;
  const discrepancyCount = currentCase.documentFields.filter((f) => f.matchStatus === 'DISCREPANCY').length;

  return (
    <div className="w-full h-full flex flex-col bg-white rounded-md border border-[#E2E8F0] shadow-sm overflow-hidden">
      {/* Header with Sub-tabs and Verification Summary */}
      <div className="p-3 bg-[#F8FAFC] border-b border-[#E2E8F0] flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <FileText className="w-4 h-4 text-[#142B4A]" />
          <span className="text-xs font-bold text-[#142B4A] uppercase tracking-wide">
            Title & OCR Verification Matrix
          </span>
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#FEF3C7] text-[#B45309] border border-[#FDE68A]">
            {CREDIBILITY_LABELS.DATA_SOURCE_SYNTHETIC}
          </span>
        </div>

        {/* Status badges */}
        <div className="flex items-center gap-2 text-xs">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[#DCFCE7] text-[#15803D] border border-[#BBF7D0]">
            <CheckCircle2 className="w-3 h-3" />
            {matchedCount} Matched
          </span>
          {discrepancyCount > 0 ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[#FEE2E2] text-[#B91C1C] border border-[#FECACA]">
              <AlertTriangle className="w-3 h-3" />
              {discrepancyCount} Discrepancy
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[#CCFBF1] text-[#0F766E] border border-[#99F6E4]">
              <ShieldCheck className="w-3 h-3" />
              Nil Encumbrance (30 Yr Search)
            </span>
          )}
        </div>
      </div>

      {/* Doc Sub-nav Buttons */}
      <div className="px-3 pt-2 bg-white border-b border-[#E2E8F0] flex items-center gap-2 text-xs">
        {[
          { key: 'INDEX_II', label: 'SRO Index-II Extract (Kaveri/IGR)' },
          { key: 'ENCUMBRANCE', label: `Encumbrance Cert (Form 15 - ${currentCase.titleChainYears} Yrs)` },
          { key: 'SANCTION_PLAN', label: 'Municipal Sanctioned Layout' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setSelectedDocType(tab.key as any)}
            className={`pb-2 px-2 text-xs font-medium border-b-2 transition-colors ${
              selectedDocType === tab.key
                ? 'border-[#2563EB] text-[#2563EB] font-semibold'
                : 'border-transparent text-[#64748B] hover:text-[#172033]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content Split: OCR Comparison Matrix Table */}
      <div className="flex-1 p-3 overflow-y-auto space-y-3">
        {/* Verification Matrix Table */}
        <div className="border border-[#E2E8F0] rounded overflow-hidden">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-[#F8FAFC] border-b border-[#CBD5E1] text-[#64748B] label-caps">
                <th className="py-2 px-3 font-semibold w-1/4">Field Attribute</th>
                <th className="py-2 px-3 font-semibold w-1/3">Applicant Submission</th>
                <th className="py-2 px-3 font-semibold w-1/3">State Registry OCR Extract</th>
                <th className="py-2 px-3 font-semibold text-center w-20">Audit State</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E2E8F0]">
              {currentCase.documentFields.map((field, idx) => {
                const isSelected = highlightedField === field.label;
                const isDiscrepancy = field.matchStatus === 'DISCREPANCY';

                return (
                  <tr
                    key={idx}
                    onClick={() => setHighlightedField(isSelected ? null : field.label)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-[#EFF6FF]'
                        : isDiscrepancy
                        ? 'bg-[#FEF2F2] hover:bg-[#FEE2E2]/60'
                        : 'hover:bg-[#F8FAFC]'
                    }`}
                  >
                    <td className="py-2.5 px-3 font-medium text-[#172033]">
                      <div className="flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#2563EB]" />
                        {field.label}
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-[#334155] font-mono text-[11.5px] tabular-nums">
                      {field.applicantDeclared}
                    </td>
                    <td className="py-2.5 px-3 text-[#0F172A] font-mono text-[11.5px] tabular-nums font-medium">
                      {field.sroIndexExtract}
                      {field.notes && (
                        <p className="text-[10px] text-[#B45309] font-sans mt-0.5 font-normal">
                          * {field.notes}
                        </p>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      {field.matchStatus === 'MATCHED' ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#DCFCE7] text-[#15803D]">
                          MATCHED (DEMO)
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#FEE2E2] text-[#B91C1C]">
                          ALERT
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Simulated Institutional SRO Document Preview Box */}
        <div className="bg-[#FAF9F6] border border-[#D1D5DB] rounded p-3 relative font-serif text-[11px] text-[#333] shadow-inner">
          <div className="flex items-center justify-between border-b border-[#CBD5E1] pb-2 mb-2 font-sans">
            <div className="flex items-center gap-2">
              <Stamp className="w-4 h-4 text-[#B91C1C]" />
              <span className="text-xs font-bold text-[#142B4A] uppercase">
                [SYNTHETIC TEMPLATE PREVIEW] MOCK REGISTRATION EXTRACT — NOT A STATUTORY RECORD
              </span>
            </div>
            <span className="text-[10px] font-mono bg-white px-2 py-0.5 rounded border border-[#CBD5E1] text-[#64748B]">
              Ref: {currentCase.applicationNo}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 font-mono text-[11px] leading-relaxed">
            <div>
              <p><span className="text-[#64748B]">Document Volume / Book:</span> Book-1 (Immovable Property)</p>
              <p><span className="text-[#64748B]">SRO Jurisdiction:</span> {currentCase.locality}</p>
              <p><span className="text-[#64748B]">RERA Registration:</span> {currentCase.reraRegistration}</p>
            </div>
            <div>
              <p><span className="text-[#64748B]">Plan Sanction No:</span> {currentCase.bbmpPlanApprovalNo}</p>
              <p><span className="text-[#64748B]">Encumbrance Status:</span> {currentCase.encumbranceStatus}</p>
              <p><span className="text-[#64748B]">Title Search Vintage:</span> {currentCase.titleChainYears} Years Unbroken Chain</p>
            </div>
          </div>

          <div className="mt-2 pt-2 border-t border-dashed border-[#CBD5E1] flex items-center justify-between font-sans text-[11px] text-[#64748B]">
            <span className="flex items-center gap-1 text-[#64748B] font-medium">
              <CheckCircle2 className="w-3.5 h-3.5 text-[#15803D]" />
              Demonstration OCR extract simulation — Live State SRO API not connected in prototype
            </span>
            <button className="flex items-center gap-1 text-[#2563EB] hover:underline font-medium">
              <ExternalLink className="w-3 h-3" />
              View Full Deed Scan
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
