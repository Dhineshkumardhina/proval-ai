/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { INITIAL_VALUATION_CASES } from './data/mockValuationData';
import { ValuationCase, CaseStatus } from './types/valuation';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { ValuationStudio } from './components/ValuationStudio/ValuationStudio';
import { UnderwritingPipeline } from './components/Pipeline/UnderwritingPipeline';
import { RiskAuditDashboard } from './components/RiskAudit/RiskAuditDashboard';
import { ModelGovernanceView } from './components/ModelGovernance/ModelGovernanceView';
import { NewCaseModal } from './components/NewCaseModal';

export default function App() {
  const [cases, setCases] = useState<ValuationCase[]>(INITIAL_VALUATION_CASES);
  const [currentCaseId, setCurrentCaseId] = useState<string>('case-blr-89412');
  const [currentTab, setCurrentTab] = useState<'STUDIO' | 'PIPELINE' | 'RISK_AUDIT' | 'GOVERNANCE'>('STUDIO');
  const [isNewCaseModalOpen, setIsNewCaseModalOpen] = useState<boolean>(false);

  const currentCase = cases.find((c) => c.id === currentCaseId) || cases[0];

  const handleUpdateCase = (updatedCase: ValuationCase) => {
    setCases((prev) =>
      prev.map((c) => (c.id === updatedCase.id ? updatedCase : c))
    );
  };

  const handleCaseStatusChange = (caseId: string, newStatus: CaseStatus, auditNote?: string) => {
    setCases((prev) =>
      prev.map((c) => {
        if (c.id !== caseId) return c;
        const statusLabels: Record<CaseStatus, string> = {
          READY_FOR_APPROVAL: 'Ready for Underwriter Sign-off',
          APPROVED: 'Approved & Digitally Certified',
          REVIEW_REQUIRED: 'Under Risk Committee Review',
          HIGH_ALERT: 'Critical Alert / Discrepancy',
          REJECTED: 'Valuation Rejected',
        };

        const updatedNotes = auditNote
          ? [...c.auditNotes, `${new Date().toLocaleTimeString()} - ${auditNote}`]
          : c.auditNotes;

        return {
          ...c,
          status: newStatus,
          statusLabel: statusLabels[newStatus] || newStatus,
          auditNotes: updatedNotes,
        };
      })
    );
  };

  const handleAddNewCase = (newCase: ValuationCase) => {
    setCases((prev) => [newCase, ...prev]);
    setCurrentCaseId(newCase.id);
    setCurrentTab('STUDIO');
  };

  const handleSelectCaseFromAnywhere = (caseId: string) => {
    setCurrentCaseId(caseId);
    setCurrentTab('STUDIO');
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#F5F7FA] text-[#172033]">
      {/* 260px Collapsible Institutional Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        cases={cases}
        currentCaseId={currentCaseId}
        onSelectCase={setCurrentCaseId}
      />

      {/* Main Analytical Canvas Frame */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Top Header */}
        <Header
          cases={cases}
          currentCaseId={currentCaseId}
          onSelectCase={setCurrentCaseId}
          onOpenNewCaseModal={() => setIsNewCaseModalOpen(true)}
        />

        {/* Scrollable Work Area */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          {currentTab === 'STUDIO' && (
            <ValuationStudio
              currentCase={currentCase}
              onUpdateCase={handleUpdateCase}
              onCaseStatusChange={handleCaseStatusChange}
            />
          )}

          {currentTab === 'PIPELINE' && (
            <UnderwritingPipeline
              cases={cases}
              onSelectCase={handleSelectCaseFromAnywhere}
              onOpenNewCaseModal={() => setIsNewCaseModalOpen(true)}
            />
          )}

          {currentTab === 'RISK_AUDIT' && (
            <RiskAuditDashboard
              cases={cases}
              onSelectCase={handleSelectCaseFromAnywhere}
            />
          )}

          {currentTab === 'GOVERNANCE' && <ModelGovernanceView />}
        </main>
      </div>

      {/* New Case Intake Modal */}
      <NewCaseModal
        isOpen={isNewCaseModalOpen}
        onClose={() => setIsNewCaseModalOpen(false)}
        onSubmit={handleAddNewCase}
      />
    </div>
  );
}
