/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  FileCheck2,
  CheckCircle2,
  Download,
  Printer,
  ShieldCheck,
  Building2,
  Stamp,
  QrCode,
  X,
} from 'lucide-react';
import { ValuationCase } from '../../types/valuation';
import { ValuationResult, formatIndianCurrency } from '../../utils/valuationEngine';

interface ValuationCertificateModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentCase: ValuationCase;
  valuation: ValuationResult;
  onConfirmSignOff: () => void;
}

export const ValuationCertificateModal: React.FC<ValuationCertificateModalProps> = ({
  isOpen,
  onClose,
  currentCase,
  valuation,
  onConfirmSignOff,
}) => {
  const [signedBy, setSignedBy] = useState<string>(currentCase.assignedUnderwriter);
  const [isSigned, setIsSigned] = useState<boolean>(false);
  const [downloadSuccess, setDownloadSuccess] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleSign = () => {
    setIsSigned(true);
    onConfirmSignOff();
  };

  const handleDownload = () => {
    setDownloadSuccess(true);
    window.print();
    setTimeout(() => setDownloadSuccess(false), 3000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#142B4A]/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white rounded-lg border border-[#94A3B8] shadow-2xl max-w-2xl w-full p-6 space-y-4 my-8 relative">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-[#64748B] hover:text-[#172033] p-1 rounded-full hover:bg-[#F1F5F9]"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Certificate Header */}
        <div className="border-b-2 border-[#142B4A] pb-3 flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded bg-[#142B4A] text-white flex items-center justify-center font-bold text-sm">
                PV
              </div>
              <div>
                <h2 className="text-base font-bold text-[#142B4A] uppercase tracking-wide">
                  PropVal AI — Collateral Valuation & Credit Appraisal Memo
                </h2>
                <p className="text-[11px] text-[#64748B]">
                  Provisional Rule-Based Valuation Memo (Illustrative Prototype — Not a Statutory Certification)
                </p>
              </div>
            </div>
          </div>

          <div className="text-right">
            <span className="label-caps text-[#64748B] block">Evaluation Ref</span>
            <span className="font-mono text-xs font-bold text-[#142B4A]">
              DEMO-{currentCase.applicationNo}
            </span>
          </div>
        </div>

        {/* Key Appraisal Summary Box */}
        <div className="bg-[#F8FAFC] border border-[#CBD5E1] rounded p-4 grid grid-cols-2 sm:grid-cols-3 gap-3">
          <div>
            <span className="label-caps text-[#64748B]">Borrower / Mortgagor</span>
            <p className="font-semibold text-xs text-[#172033] mt-0.5">{currentCase.borrowerName}</p>
            <p className="text-[10px] text-[#64748B]">CIBIL Score: {currentCase.cibilScore}</p>
          </div>
          <div>
            <span className="label-caps text-[#64748B]">Property Description</span>
            <p className="font-semibold text-xs text-[#172033] mt-0.5 truncate">{currentCase.projectName}</p>
            <p className="text-[10px] text-[#64748B] truncate">{currentCase.unitAddress}</p>
          </div>
          <div>
            <span className="label-caps text-[#64748B]">Carpet / SBUA Area</span>
            <p className="font-mono font-semibold text-xs text-[#172033] mt-0.5">
              {currentCase.carpetAreaSqFt} / {currentCase.superBuiltUpAreaSqFt} sq ft
            </p>
            <p className="text-[10px] text-[#64748B]">Floor: {currentCase.floorNo} of {currentCase.totalFloors}</p>
          </div>
        </div>

        {/* Financial Numbers Matrix */}
        <div className="border border-[#CBD5E1] rounded overflow-hidden">
          <table className="w-full text-xs text-left">
            <tbody className="divide-y divide-[#E2E8F0]">
              <tr className="bg-[#F8FAFC]">
                <td className="py-2 px-3 text-[#64748B] font-medium">Ready Reckoner / SRO Guideline Value</td>
                <td className="py-2 px-3 text-right font-mono tabular-nums text-[#334155]">
                  ₹{currentCase.circleRatePerSqFt.toLocaleString('en-IN')}/sq ft ({formatIndianCurrency(currentCase.circleRatePerSqFt * currentCase.carpetAreaSqFt)})
                </td>
              </tr>
              <tr>
                <td className="py-2 px-3 text-[#64748B] font-medium">Applicant Declared Agreement Price</td>
                <td className="py-2 px-3 text-right font-mono tabular-nums font-semibold text-[#172033]">
                  {formatIndianCurrency(currentCase.declaredAgreementValue)} ({formatIndianCurrency(currentCase.declaredAgreementValue, 'short')})
                </td>
              </tr>
              <tr className="bg-[#EFF6FF]">
                <td className="py-2 px-3 text-[#142B4A] font-bold">
                  Assessed Fair Market Collateral Value (Provisional Rule-Based Engine)
                </td>
                <td className="py-2 px-3 text-right font-mono tabular-nums text-sm font-bold text-[#2563EB]">
                  {formatIndianCurrency(valuation.netAssessedValue)} ({formatIndianCurrency(valuation.netAssessedValue, 'short')})
                </td>
              </tr>
              <tr>
                <td className="py-2 px-3 text-[#64748B] font-medium">Forced Sale Liquidation Value (Distress Discount {currentCase.distressDiscountPct}%)</td>
                <td className="py-2 px-3 text-right font-mono tabular-nums font-semibold text-[#B45309]">
                  {formatIndianCurrency(valuation.distressLiquidationValue)}
                </td>
              </tr>
              <tr className="bg-[#F0FDF4]">
                <td className="py-2 px-3 text-[#15803D] font-bold">
                  Max Permissible Mortgage Sanction ({currentCase.ltvRatioPct}% LTV Cap)
                </td>
                <td className="py-2 px-3 text-right font-mono tabular-nums text-sm font-bold text-[#15803D]">
                  {formatIndianCurrency(valuation.maxSanctionAmount)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Digital Signature & Verification Box */}
        <div className="bg-[#FAF9F6] border border-[#CBD5E1] p-3 rounded flex items-center justify-between text-xs">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white rounded border border-[#CBD5E1]">
              <QrCode className="w-10 h-10 text-[#142B4A]" />
            </div>
            <div className="space-y-0.5">
              <span className="label-caps text-[#64748B]">Audit Ledger Status</span>
              <p className="font-mono text-[10px] text-[#334155]">
                Cryptographic Ledger: Not implemented (Local prototype state)
              </p>
              <p className="text-[11px] text-[#2563EB] flex items-center gap-1 font-semibold">
                Engine: Provisional Rule-Based Prototype v0.1.0-alpha (Consistency: {valuation.confidenceScorePct}%)
              </p>
            </div>
          </div>

          <div className="text-right">
            <span className="label-caps text-[#64748B] block">Appraisal Officer</span>
            <span className="font-semibold text-xs text-[#142B4A] block">{signedBy}</span>
            <span className="text-[10px] text-[#64748B]">Prototype Session ID: SIM-IN-7841</span>
          </div>
        </div>

        {/* Prototype Evaluation Disclaimer */}
        <div className="p-2.5 bg-[#FFFBEB] border border-[#FDE68A] rounded text-[11px] text-[#B45309]">
          <strong>Prototype Notice:</strong> This valuation memo is generated by a provisional rule-based calculation using synthetic demonstration data. It does not constitute a certified statutory valuation or regulatory sign-off.
        </div>

        {/* Action Controls */}
        <div className="flex items-center justify-between pt-2 border-t border-[#E2E8F0]">
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownload}
              className="px-3 py-1.5 text-xs font-semibold rounded border border-[#CBD5E1] text-[#142B4A] hover:bg-[#F8FAFC] flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5" />
              {downloadSuccess ? 'Downloaded Memo.pdf' : 'Export Appraisal Memo (PDF)'}
            </button>
            <button
              onClick={() => window.print()}
              className="px-3 py-1.5 text-xs font-semibold rounded border border-[#CBD5E1] text-[#64748B] hover:text-[#142B4A] flex items-center gap-1.5"
            >
              <Printer className="w-3.5 h-3.5" />
              Print
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-3 py-1.5 text-xs font-medium text-[#64748B] hover:text-[#172033]"
            >
              Cancel
            </button>

            <button
              onClick={handleSign}
              disabled={isSigned}
              className={`px-4 py-2 text-xs font-semibold rounded text-white flex items-center gap-1.5 transition-colors ${
                isSigned
                  ? 'bg-[#15803D] cursor-default'
                  : 'bg-[#2563EB] hover:bg-[#1D4ED8]'
              }`}
            >
              <CheckCircle2 className="w-4 h-4" />
              {isSigned ? 'Signed & Recorded to Session' : 'Confirm Underwriter Sign-off'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
