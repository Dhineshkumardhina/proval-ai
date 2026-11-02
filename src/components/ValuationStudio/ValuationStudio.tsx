/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useMemo } from 'react';
import {
  Map,
  FileText,
  Camera,
  TrendingUp,
  ShieldCheck,
  AlertTriangle,
  Building2,
  Sliders,
  Sparkles,
  Info,
  Maximize2,
  CheckCircle2,
} from 'lucide-react';
import { ValuationCase, ComparableDeed } from '../../types/valuation';
import { calculateValuation, formatIndianCurrency } from '../../utils/valuationEngine';
import { GisMapCanvas } from './GisMapCanvas';
import { DocumentOcrViewer } from './DocumentOcrViewer';
import { FieldSurveyViewer } from './FieldSurveyViewer';
import { XaiAttributionWaterfall } from './XaiAttributionWaterfall';
import { ComparablesGrid } from './ComparablesGrid';
import { UnderwriterControls } from './UnderwriterControls';
import { ValuationCertificateModal } from './ValuationCertificateModal';

interface ValuationStudioProps {
  currentCase: ValuationCase;
  onUpdateCase: (updatedCase: ValuationCase) => void;
  onCaseStatusChange: (caseId: string, status: any, note?: string) => void;
}

export const ValuationStudio: React.FC<ValuationStudioProps> = ({
  currentCase,
  onUpdateCase,
  onCaseStatusChange,
}) => {
  const [leftTab, setLeftTab] = useState<'GIS' | 'DOCUMENTS' | 'SURVEY'>('GIS');
  const [selectedCompId, setSelectedCompId] = useState<string | null>(null);
  const [isSignOffModalOpen, setIsSignOffModalOpen] = useState<boolean>(false);
  const [showNotification, setShowNotification] = useState<string | null>(null);

  // Live valuation calculation based on current case inputs and underwriter overrides
  const valuationResult = useMemo(() => {
    return calculateValuation({
      carpetAreaSqFt: currentCase.carpetAreaSqFt,
      superBuiltUpAreaSqFt: currentCase.superBuiltUpAreaSqFt,
      baseMarketRatePerSqFt: currentCase.baseMarketRatePerSqFt,
      circleRatePerSqFt: currentCase.circleRatePerSqFt,
      floorRiseFactor: currentCase.floorRiseFactor,
      roadWidthFactor: currentCase.roadWidthFactor,
      amenitiesPremium: currentCase.amenitiesPremium,
      structuralDepreciation: currentCase.structuralDepreciation,
      underwriterHaircutPct: currentCase.underwriterHaircutPct,
      distressDiscountPct: currentCase.distressDiscountPct,
      ltvRatioPct: currentCase.ltvRatioPct,
      legalRiskPenaltyPct: currentCase.legalRiskPenaltyPct,
    });
  }, [currentCase]);

  const handleUpdateParams = (newParams: Partial<ValuationCase>) => {
    onUpdateCase({
      ...currentCase,
      ...newParams,
    });
  };

  const handleSelectComp = (comp: ComparableDeed) => {
    setSelectedCompId(comp.id);
  };

  const handleConfirmSignOff = () => {
    onCaseStatusChange(
      currentCase.id,
      'APPROVED',
      `Signed off by ${currentCase.assignedUnderwriter} at net assessed valuation of ${formatIndianCurrency(
        valuationResult.netAssessedValue
      )}`
    );
    setShowNotification('Valuation approved and digital certificate cryptographically logged.');
    setTimeout(() => setShowNotification(null), 4000);
  };

  const handleReferCommittee = (reason: string) => {
    onCaseStatusChange(
      currentCase.id,
      'REVIEW_REQUIRED',
      `Referred to Credit Committee: ${reason}`
    );
    setShowNotification('Case escalated to Credit Risk & Audit Committee.');
    setTimeout(() => setShowNotification(null), 4000);
  };

  const ratePerSqFtSuperBuiltUp = Math.round(
    valuationResult.netAssessedValue / currentCase.superBuiltUpAreaSqFt
  );

  return (
    <div className="space-y-4">
      {/* Toast Notification */}
      {showNotification && (
        <div className="bg-[#142B4A] text-white px-4 py-2.5 rounded-md shadow-lg border border-[#2563EB] flex items-center justify-between transition-all">
          <div className="flex items-center gap-2 text-xs">
            <CheckCircle2 className="w-4 h-4 text-[#38BDF8]" />
            <span>{showNotification}</span>
          </div>
          <button
            onClick={() => setShowNotification(null)}
            className="text-slate-400 hover:text-white text-xs ml-4"
          >
            ✕
          </button>
        </div>
      )}

      {/* Case Header Banner */}
      <div className="bg-white rounded-md border border-[#E2E8F0] shadow-sm p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-xs font-bold text-[#142B4A] bg-[#F1F5F9] px-2 py-0.5 rounded border border-[#CBD5E1]">
              {currentCase.applicationNo}
            </span>
            <span className="text-sm font-bold text-[#172033]">
              {currentCase.projectName} — {currentCase.unitAddress}
            </span>
            <span
              className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${
                currentCase.status === 'APPROVED'
                  ? 'bg-[#DCFCE7] text-[#15803D] border-[#BBF7D0]'
                  : currentCase.status === 'READY_FOR_APPROVAL'
                  ? 'bg-[#EFF6FF] text-[#2563EB] border-[#BFDBFE]'
                  : currentCase.status === 'REVIEW_REQUIRED'
                  ? 'bg-[#FEF3C7] text-[#B45309] border-[#FDE68A]'
                  : 'bg-[#FEE2E2] text-[#B91C1C] border-[#FECACA]'
              }`}
            >
              {currentCase.statusLabel}
            </span>
          </div>

          <p className="text-xs text-[#64748B]">
            Borrower: <span className="text-[#172033] font-medium">{currentCase.borrowerName}</span> | Branch:{' '}
            <span className="text-[#172033] font-medium">{currentCase.branch}</span> | SRO Circle Rate:{' '}
            <span className="font-mono text-[#172033] font-medium">₹{currentCase.circleRatePerSqFt}/sq ft</span>
          </p>
        </div>

        {/* Quick Underwriter Profile Badge */}
        <div className="flex items-center gap-3 text-xs bg-[#F8FAFC] px-3 py-1.5 rounded border border-[#E2E8F0]">
          <div className="w-7 h-7 rounded-full bg-[#142B4A] text-white flex items-center justify-center font-bold text-xs">
            VS
          </div>
          <div>
            <span className="label-caps text-[#64748B] block text-[10px]">Active Evaluator</span>
            <span className="font-semibold text-[#142B4A]">{currentCase.assignedUnderwriter}</span>
          </div>
        </div>
      </div>

      {/* Top High-Density KPI Stat Widgets */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Metric 1: Assessed Collateral Value */}
        <div className="bg-white p-3 rounded-md border border-[#E2E8F0] shadow-sm border-t-2 border-t-[#2563EB]">
          <span className="label-caps text-[#64748B] block text-[10px]">Estimated Base Value</span>
          <p className="text-lg font-bold font-mono tabular-nums text-[#142B4A] mt-0.5">
            {formatIndianCurrency(valuationResult.netAssessedValue, 'short')}
          </p>
          <p className="text-[10px] text-[#64748B] font-mono tabular-nums">
            {formatIndianCurrency(valuationResult.netAssessedValue, 'full')}
          </p>
        </div>

        {/* Metric 2: Heuristic Confidence */}
        <div className="bg-white p-3 rounded-md border border-[#E2E8F0] shadow-sm border-t-2 border-t-[#0F766E]">
          <span className="label-caps text-[#64748B] block text-[10px]">Heuristic Confidence</span>
          <p className="text-lg font-bold font-mono tabular-nums text-[#0F766E] mt-0.5">
            {valuationResult.confidenceScorePct}%
          </p>
          <span className="inline-block px-1.5 py-0.2 rounded text-[10px] font-semibold bg-[#F1F5F9] text-[#64748B] border border-[#CBD5E1]">
            Rule-Based Score
          </span>
        </div>

        {/* Metric 3: Rate per Carpet Area */}
        <div className="bg-white p-3 rounded-md border border-[#E2E8F0] shadow-sm border-t-2 border-t-[#142B4A]">
          <span className="label-caps text-[#64748B] block text-[10px]">₹ / sq ft (Carpet)</span>
          <p className="text-lg font-bold font-mono tabular-nums text-[#172033] mt-0.5">
            ₹{Math.round(valuationResult.netAssessedValue / currentCase.carpetAreaSqFt).toLocaleString('en-IN')}
          </p>
          <p className="text-[10px] text-[#64748B]">
            {currentCase.carpetAreaSqFt} sq ft carpet
          </p>
        </div>

        {/* Metric 4: Rate per Super Built-up */}
        <div className="bg-white p-3 rounded-md border border-[#E2E8F0] shadow-sm border-t-2 border-t-slate-400">
          <span className="label-caps text-[#64748B] block text-[10px]">₹ / sq ft (SBUA)</span>
          <p className="text-lg font-bold font-mono tabular-nums text-[#334155] mt-0.5">
            ₹{ratePerSqFtSuperBuiltUp.toLocaleString('en-IN')}
          </p>
          <p className="text-[10px] text-[#64748B]">
            {currentCase.superBuiltUpAreaSqFt} sq ft built-up
          </p>
        </div>

        {/* Metric 5: Circle Rate Variance */}
        <div className="bg-white p-3 rounded-md border border-[#E2E8F0] shadow-sm border-t-2 border-t-[#D97706]">
          <span className="label-caps text-[#64748B] block text-[10px]">Circle Rate Deviation</span>
          <p className="text-lg font-bold font-mono tabular-nums text-[#D97706] mt-0.5">
            +{valuationResult.deviationFromCircleRatePct}%
          </p>
          <p className="text-[10px] text-[#64748B]">
            Base: ₹{currentCase.circleRatePerSqFt}/sq ft
          </p>
        </div>

        {/* Metric 6: Max Permissible Sanction */}
        <div className="bg-white p-3 rounded-md border border-[#E2E8F0] shadow-sm border-t-2 border-t-[#15803D]">
          <span className="label-caps text-[#64748B] block text-[10px]">Max Sanction (75% LTV)</span>
          <p className="text-lg font-bold font-mono tabular-nums text-[#15803D] mt-0.5">
            {formatIndianCurrency(valuationResult.maxSanctionAmount, 'short')}
          </p>
          <p className="text-[10px] text-[#64748B] font-mono tabular-nums">
            {formatIndianCurrency(valuationResult.maxSanctionAmount, 'full')}
          </p>
        </div>
      </div>

      {/* Main Split-Screen 55/45 or 50/50 Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
        {/* Left Pane (6 cols on lg): Spatial GIS, Registry OCR & Field Photos (Sticky) */}
        <div className="lg:col-span-6 space-y-3 lg:sticky lg:top-4 self-start">
          {/* Sub-tab navigation */}
          <div className="bg-white p-1 rounded border border-[#E2E8F0] flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-1">
              <button
                onClick={() => setLeftTab('GIS')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold transition-colors ${
                  leftTab === 'GIS'
                    ? 'bg-[#142B4A] text-white shadow-xs'
                    : 'text-[#64748B] hover:text-[#142B4A] hover:bg-[#F1F5F9]'
                }`}
              >
                <Map className="w-3.5 h-3.5" />
                GIS Spatial & Satellite
              </button>

              <button
                onClick={() => setLeftTab('DOCUMENTS')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold transition-colors ${
                  leftTab === 'DOCUMENTS'
                    ? 'bg-[#142B4A] text-white shadow-xs'
                    : 'text-[#64748B] hover:text-[#142B4A] hover:bg-[#F1F5F9]'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                Registry OCR & Title
              </button>

              <button
                onClick={() => setLeftTab('SURVEY')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold transition-colors ${
                  leftTab === 'SURVEY'
                    ? 'bg-[#142B4A] text-white shadow-xs'
                    : 'text-[#64748B] hover:text-[#142B4A] hover:bg-[#F1F5F9]'
                }`}
              >
                <Camera className="w-3.5 h-3.5" />
                Physical Field Survey
              </button>
            </div>

            <span className="text-[11px] text-[#64748B] pr-2 font-mono">
              {leftTab === 'GIS'
                ? '5 Comps'
                : leftTab === 'DOCUMENTS'
                ? '6 OCR Fields'
                : '4 Geo-Frames'}
            </span>
          </div>

          {/* Left Pane Dynamic Viewport */}
          <div className="min-h-[500px]">
            {leftTab === 'GIS' && (
              <GisMapCanvas
                currentCase={currentCase}
                selectedCompId={selectedCompId}
                onSelectComp={handleSelectComp}
              />
            )}
            {leftTab === 'DOCUMENTS' && <DocumentOcrViewer currentCase={currentCase} />}
            {leftTab === 'SURVEY' && <FieldSurveyViewer currentCase={currentCase} />}
          </div>
        </div>

        {/* Right Pane (6 cols on lg): Explainable AI Waterfall, Comps Grid, Underwriter Overrides */}
        <div className="lg:col-span-6 space-y-4">
          {/* XAI Attribution Waterfall */}
          <XaiAttributionWaterfall valuation={valuationResult} />

          {/* Sub-market Comps Grid */}
          <ComparablesGrid
            comparables={currentCase.comparables}
            selectedCompId={selectedCompId}
            onSelectComp={handleSelectComp}
          />

          {/* Underwriter Stress Testing & Sign-off Action */}
          <UnderwriterControls
            currentCase={currentCase}
            valuation={valuationResult}
            onUpdateParams={handleUpdateParams}
            onOpenSignOffModal={() => setIsSignOffModalOpen(true)}
            onReferCommittee={handleReferCommittee}
          />
        </div>
      </div>

      {/* Institutional Sign-off Certificate Modal */}
      <ValuationCertificateModal
        isOpen={isSignOffModalOpen}
        onClose={() => setIsSignOffModalOpen(false)}
        currentCase={currentCase}
        valuation={valuationResult}
        onConfirmSignOff={handleConfirmSignOff}
      />
    </div>
  );
};
