/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, lazy, Suspense } from 'react';
import { INITIAL_VALUATION_CASES } from './data/mockValuationData';
import { ValuationCase, CaseStatus } from './types/valuation';
import {
  checkBackendHealth,
  ensureAuthenticated,
  fetchCases,
  createCase,
  updateCase,
  updateCaseStatus,
  fetchMLStatus,
  fetchAIStatus,
  MLModelStatus,
  AIStatus,
} from './services/apiClient';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { ValuationStudio } from './components/ValuationStudio/ValuationStudio';

// Code-splitting & Lazy loading of non-landing tabs and intake modal
const UnderwritingPipeline = lazy(() =>
  import('./components/Pipeline/UnderwritingPipeline').then((m) => ({ default: m.UnderwritingPipeline }))
);
const RiskAuditDashboard = lazy(() =>
  import('./components/RiskAudit/RiskAuditDashboard').then((m) => ({ default: m.RiskAuditDashboard }))
);
const ModelGovernanceView = lazy(() =>
  import('./components/ModelGovernance/ModelGovernanceView').then((m) => ({ default: m.ModelGovernanceView }))
);
const NewCaseModal = lazy(() =>
  import('./components/NewCaseModal').then((m) => ({ default: m.NewCaseModal }))
);

export default function App() {
  const [cases, setCases] = useState<ValuationCase[]>(INITIAL_VALUATION_CASES);
  const [currentCaseId, setCurrentCaseId] = useState<string>('case-blr-89412');
  const [currentTab, setCurrentTab] = useState<'STUDIO' | 'PIPELINE' | 'RISK_AUDIT' | 'GOVERNANCE'>('STUDIO');
  const [isNewCaseModalOpen, setIsNewCaseModalOpen] = useState<boolean>(false);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(false);
  const [mlStatus, setMlStatus] = useState<MLModelStatus | null>(null);
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null);

  // Load cases from backend on mount if reachable, preserving local fallback
  useEffect(() => {
    let isMounted = true;
    async function loadCases() {
      try {
        const healthy = await checkBackendHealth();
        if (!isMounted) return;
        setIsBackendConnected(healthy);
        if (healthy) {
          await ensureAuthenticated();
          const [res, ml, ai] = await Promise.all([
            fetchCases({ limit: 50 }),
            fetchMLStatus(),
            fetchAIStatus(),
          ]);
          if (isMounted) {
            if (ml) setMlStatus(ml);
            if (ai) setAiStatus(ai);
            if (res.items && res.items.length > 0) {
              setCases(res.items);
              if (!res.items.some((c) => c.id === currentCaseId)) {
                setCurrentCaseId(res.items[0].id);
              }
            }
          }
        }
      } catch {
        if (isMounted) setIsBackendConnected(false);
      }
    }
    loadCases();
    return () => {
      isMounted = false;
    };
  }, []);

  const currentCase = cases.find((c) => c.id === currentCaseId) || cases[0];

  const handleUpdateCase = (updatedCase: ValuationCase) => {
    // Immediate optimistic local state update
    setCases((prev) =>
      prev.map((c) => (c.id === updatedCase.id ? updatedCase : c))
    );

    // Sync to backend asynchronously
    updateCase(updatedCase.id, updatedCase).catch(() => {
      // Local fallback retains working state seamlessly
    });
  };

  const handleCaseStatusChange = (caseId: string, newStatus: CaseStatus, auditNote?: string) => {
    const statusLabels: Record<CaseStatus, string> = {
      READY_FOR_APPROVAL: 'Ready for Underwriter Sign-off',
      APPROVED: 'Approved & Digitally Certified',
      REVIEW_REQUIRED: 'Under Risk Committee Review',
      HIGH_ALERT: 'Critical Alert / Discrepancy',
      REJECTED: 'Valuation Rejected',
    };

    const updatedNotes = auditNote
      ? [`${new Date().toLocaleTimeString()} - ${auditNote}`]
      : [];

    setCases((prev) =>
      prev.map((c) => {
        if (c.id !== caseId) return c;
        return {
          ...c,
          status: newStatus,
          statusLabel: statusLabels[newStatus] || newStatus,
          auditNotes: [...c.auditNotes, ...updatedNotes],
        };
      })
    );

    // Persist status change to backend
    updateCaseStatus(caseId, newStatus, auditNote).catch(() => {
      // Local fallback preserves status change
    });
  };

  const handleAddNewCase = async (newCase: ValuationCase) => {
    // Immediate optimistic update
    setCases((prev) => [newCase, ...prev]);
    setCurrentCaseId(newCase.id);
    setCurrentTab('STUDIO');

    try {
      const created = await createCase(newCase);
      setCases((prev) => prev.map((c) => (c.id === newCase.id ? created : c)));
      setCurrentCaseId(created.id);
      setIsBackendConnected(true);
    } catch {
      // Retained in local session on backend offline
    }
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
          isBackendConnected={isBackendConnected}
          mlStatus={mlStatus}
          aiStatus={aiStatus}
        />

        {/* Scrollable Work Area */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <Suspense fallback={<div className="flex items-center justify-center h-64 text-slate-400 font-mono text-xs">Loading module...</div>}>
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
          </Suspense>
        </main>
      </div>

      {/* New Case Intake Modal */}
      {isNewCaseModalOpen && (
        <Suspense fallback={null}>
          <NewCaseModal
            isOpen={isNewCaseModalOpen}
            onClose={() => setIsNewCaseModalOpen(false)}
            onSubmit={handleAddNewCase}
          />
        </Suspense>
      )}
    </div>
  );
}
