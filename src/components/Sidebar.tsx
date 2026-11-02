/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import {
  Compass,
  Layers,
  Database,
  ShieldAlert,
  Cpu,
  FileCheck,
  Building2,
  ChevronRight,
  TrendingUp,
  MapPin,
} from 'lucide-react';
import { ValuationCase } from '../types/valuation';

interface SidebarProps {
  currentTab: 'STUDIO' | 'PIPELINE' | 'RISK_AUDIT' | 'GOVERNANCE';
  onSelectTab: (tab: 'STUDIO' | 'PIPELINE' | 'RISK_AUDIT' | 'GOVERNANCE') => void;
  cases: ValuationCase[];
  currentCaseId: string;
  onSelectCase: (caseId: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  cases,
  currentCaseId,
  onSelectCase,
}) => {
  const currentCase = cases.find((c) => c.id === currentCaseId) || cases[0];

  const navItems = [
    {
      id: 'STUDIO' as const,
      label: 'Valuation Studio',
      description: 'Split-Screen XAI Engine',
      icon: Compass,
    },
    {
      id: 'PIPELINE' as const,
      label: 'Underwriting Pipeline',
      description: `${cases.length} Active Collaterals`,
      icon: Database,
    },
    {
      id: 'RISK_AUDIT' as const,
      label: 'Risk & Audit Committee',
      description: 'Stress Testing & Breaches',
      icon: ShieldAlert,
    },
    {
      id: 'GOVERNANCE' as const,
      label: 'Model Governance',
      description: 'Compliance & Metrics State',
      icon: Cpu,
    },
  ];

  return (
    <aside className="w-[260px] bg-[#142B4A] text-white flex flex-col justify-between shrink-0 select-none border-r border-[#1E3A5F] z-30">
      {/* Brand Header */}
      <div>
        <div className="p-4 border-b border-[#1E3A5F]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded bg-[#2563EB] text-white flex items-center justify-center font-bold text-sm shadow-sm">
              PV
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-sm tracking-wide text-white">PropVal AI</span>
                <span className="text-[10px] font-mono px-1 rounded bg-[#0F766E] text-white font-semibold">
                  HFC
                </span>
              </div>
              <p className="text-[10.5px] text-[#7D93B7] font-medium leading-tight">
                Collateral Underwriting & XAI
              </p>
            </div>
          </div>
        </div>

        {/* Primary Navigation */}
        <nav className="p-2.5 space-y-1">
          <span className="label-caps text-[#7D93B7] px-2 py-1 block text-[10px]">
            Institutional Modules
          </span>

          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;

            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full text-left px-3 py-2 rounded-md transition-colors flex items-center justify-between group ${
                  isActive
                    ? 'bg-[#2563EB] text-white font-semibold shadow-xs'
                    : 'text-[#CBD5E1] hover:bg-[#1E3A5F]/70 hover:text-white'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-[#7D93B7] group-hover:text-white'}`} />
                  <div>
                    <span className="text-xs block leading-tight">{item.label}</span>
                    <span className={`text-[10px] block leading-tight ${isActive ? 'text-blue-100' : 'text-[#7D93B7]'}`}>
                      {item.description}
                    </span>
                  </div>
                </div>
                {isActive && <ChevronRight className="w-3.5 h-3.5 text-white/80" />}
              </button>
            );
          })}
        </nav>

        {/* Quick Active Case Selection Panel */}
        <div className="px-3 pt-3">
          <span className="label-caps text-[#7D93B7] px-1 py-1 block text-[10px]">
            Active Evaluation File
          </span>

          <div className="space-y-1 mt-1">
            {cases.slice(0, 4).map((c) => {
              const isSelected = c.id === currentCaseId;

              return (
                <button
                  key={c.id}
                  onClick={() => {
                    onSelectCase(c.id);
                    if (currentTab !== 'STUDIO') onSelectTab('STUDIO');
                  }}
                  className={`w-full text-left p-2 rounded transition-colors text-xs border ${
                    isSelected
                      ? 'bg-[#1E3A5F] border-[#2563EB] text-white'
                      : 'bg-[#142B4A] border-transparent text-[#94A3B8] hover:bg-[#1A3356] hover:text-[#E2E8F0]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10.5px] font-semibold truncate">
                      {c.applicationNo.slice(4)}
                    </span>
                    <span
                      className={`text-[9px] px-1 rounded font-medium ${
                        c.status === 'READY_FOR_APPROVAL'
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : c.status === 'HIGH_ALERT'
                          ? 'bg-rose-500/20 text-rose-300'
                          : 'bg-amber-500/20 text-amber-300'
                      }`}
                    >
                      {c.city}
                    </span>
                  </div>
                  <p className="text-[11px] font-medium text-white/90 truncate mt-0.5">
                    {c.projectName}
                  </p>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Model Version & System Footnote */}
      <div className="p-3 border-t border-[#1E3A5F] bg-[#0E2038] text-[11px] space-y-1">
        <div className="flex items-center justify-between text-[#7D93B7]">
          <span>Valuation Core:</span>
          <span className="font-mono text-white text-[10px] bg-[#1E3A5F] px-1.5 py-0.2 rounded font-semibold">
            v0.1.0-alpha (Heuristic)
          </span>
        </div>
        <p className="text-[10px] text-[#64748B] leading-tight">
          Rule-based valuation prototype. Synthetic demonstration data.
        </p>
      </div>
    </aside>
  );
};
