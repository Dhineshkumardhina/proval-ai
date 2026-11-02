/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { Database, Filter, ExternalLink, CheckCircle, ArrowUpDown } from 'lucide-react';
import { ComparableDeed, CREDIBILITY_LABELS } from '../../types/valuation';
import { formatIndianCurrency } from '../../utils/valuationEngine';

interface ComparablesGridProps {
  comparables: ComparableDeed[];
  selectedCompId?: string | null;
  onSelectComp?: (comp: ComparableDeed) => void;
}

export const ComparablesGrid: React.FC<ComparablesGridProps> = ({
  comparables,
  selectedCompId,
  onSelectComp,
}) => {
  const [filterRadius, setFilterRadius] = useState<number>(2000); // meters
  const [selectedDeedModal, setSelectedDeedModal] = useState<ComparableDeed | null>(null);

  const filteredComps = comparables.filter((c) => c.distanceMeters <= filterRadius);

  return (
    <div className="bg-white rounded-md border border-[#E2E8F0] shadow-sm overflow-hidden flex flex-col">
      {/* Top Bar */}
      <div className="p-3 bg-[#F8FAFC] border-b border-[#CBD5E1] flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-[#142B4A]" />
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-xs font-bold text-[#142B4A] uppercase tracking-wide">
                Sub-Market Comparables ({filteredComps.length})
              </h4>
              <span className="px-1.5 py-0.2 rounded text-[10px] font-semibold bg-[#FEF3C7] text-[#B45309] border border-[#FDE68A]">
                Synthetic Demo
              </span>
            </div>
            <p className="text-[11px] text-[#64748B]">
              {CREDIBILITY_LABELS.COMPARABLE_SYNTHETIC}
            </p>
          </div>
        </div>

        {/* Distance Filter Controls */}
        <div className="flex items-center gap-1.5 text-xs">
          <span className="text-[#64748B] text-[11px]">Radius:</span>
          {[500, 1000, 2000].map((radius) => (
            <button
              key={radius}
              onClick={() => setFilterRadius(radius)}
              className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors ${
                filterRadius === radius
                  ? 'bg-[#142B4A] text-white'
                  : 'bg-white border border-[#CBD5E1] text-[#64748B] hover:text-[#172033]'
              }`}
            >
              {radius < 1000 ? `${radius}m` : `${radius / 1000}km`}
            </button>
          ))}
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-[#F8FAFC] border-b border-[#CBD5E1] text-[#64748B] label-caps">
              <th className="py-2.5 px-3 font-semibold">Ref (Synthetic Sample)</th>
              <th className="py-2.5 px-3 font-semibold">Project & Unit</th>
              <th className="py-2.5 px-3 font-semibold">Reg Date</th>
              <th className="py-2.5 px-3 font-semibold text-right">Carpet Area</th>
              <th className="py-2.5 px-3 font-semibold text-right">Indicative Price</th>
              <th className="py-2.5 px-3 font-semibold text-right">Rate / Sq Ft</th>
              <th className="py-2.5 px-3 font-semibold text-center">Distance</th>
              <th className="py-2.5 px-3 font-semibold text-right">Model Weight</th>
              <th className="py-2.5 px-2 font-semibold text-center">Deed</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E2E8F0]">
            {filteredComps.map((comp, idx) => {
              const isSelected = selectedCompId === comp.id;

              return (
                <tr
                  key={comp.id}
                  onClick={() => onSelectComp && onSelectComp(comp)}
                  className={`h-10 cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-[#EFF6FF] border-l-2 border-l-[#2563EB]'
                      : idx % 2 === 1
                      ? 'bg-[#FBFBFC] hover:bg-[#F1F5F9]'
                      : 'bg-white hover:bg-[#F1F5F9]'
                  }`}
                >
                  <td className="py-2 px-3 font-mono text-[11px] text-[#142B4A] font-semibold whitespace-nowrap">
                    <span className="inline-block w-5 h-5 rounded bg-[#142B4A]/10 text-[#142B4A] text-center leading-5 text-[10px] mr-1.5 font-bold">
                      C{idx + 1}
                    </span>
                    {comp.sroRegNo}
                  </td>
                  <td className="py-2 px-3 font-medium text-[#172033] max-w-[160px] truncate">
                    {comp.propertyName}
                  </td>
                  <td className="py-2 px-3 text-[#64748B] font-mono text-[11px] whitespace-nowrap">
                    {comp.regDate}
                  </td>
                  <td className="py-2 px-3 text-right font-mono tabular-nums text-[#334155]">
                    {comp.carpetAreaSqFt} <span className="text-[10px] text-[#64748B]">sq ft</span>
                  </td>
                  <td className="py-2 px-3 text-right font-mono tabular-nums font-semibold text-[#172033]">
                    {formatIndianCurrency(comp.registeredPrice)}
                  </td>
                  <td className="py-2 px-3 text-right font-mono tabular-nums text-[#2563EB] font-bold">
                    ₹{comp.ratePerSqFt.toLocaleString('en-IN')}
                  </td>
                  <td className="py-2 px-3 text-center font-mono text-[11px] text-[#64748B]">
                    {comp.distanceMeters}m
                  </td>
                  <td className="py-2 px-3 text-right">
                    <span className="inline-flex items-center gap-1 font-mono text-[11px] font-bold text-[#0F766E] bg-[#CCFBF1] px-1.5 py-0.5 rounded border border-[#99F6E4]">
                      {Math.round(comp.weightInEstimate * 100)}% ({comp.similarityScorePct}% match)
                    </span>
                  </td>
                  <td className="py-2 px-2 text-center">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedDeedModal(comp);
                      }}
                      className="p-1 text-[#64748B] hover:text-[#2563EB] hover:bg-[#F1F5F9] rounded"
                      title="View Sample Deed Details (Synthetic)"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Deed Inspection Modal */}
      {selectedDeedModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#142B4A]/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-md border border-[#CBD5E1] shadow-2xl max-w-lg w-full p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-2">
              <h3 className="text-xs font-bold text-[#142B4A] uppercase">
                Synthetic Sample Record: {selectedDeedModal.sroRegNo}
              </h3>
              <button
                onClick={() => setSelectedDeedModal(null)}
                className="text-[#64748B] hover:text-[#172033] font-bold text-sm px-1"
              >
                ✕
              </button>
            </div>

            <div className="bg-[#F8FAFC] p-3 rounded font-mono text-xs space-y-1.5 border border-[#E2E8F0]">
              <p><span className="text-[#64748B]">Property:</span> {selectedDeedModal.propertyName}</p>
              <p><span className="text-[#64748B]">Unit No:</span> {selectedDeedModal.unitNo} (Floor {selectedDeedModal.floor})</p>
              <p><span className="text-[#64748B]">Carpet Area:</span> {selectedDeedModal.carpetAreaSqFt} sq ft (SBUA: {selectedDeedModal.superBuiltUpAreaSqFt} sq ft)</p>
              <p><span className="text-[#64748B]">Consideration Value:</span> {formatIndianCurrency(selectedDeedModal.registeredPrice)} ({formatIndianCurrency(selectedDeedModal.registeredPrice, 'short')})</p>
              <p><span className="text-[#64748B]">Realized Rate:</span> ₹{selectedDeedModal.ratePerSqFt.toLocaleString('en-IN')} / sq ft carpet</p>
              <p><span className="text-[#64748B]">Registration Date:</span> {selectedDeedModal.regDate}</p>
              <p><span className="text-[#64748B]">Spatial Distance:</span> {selectedDeedModal.distanceMeters} meters from subject asset</p>
              <p><span className="text-[#64748B]">Relative Weight:</span> {(selectedDeedModal.weightInEstimate * 100).toFixed(0)}% indicative weight (demonstration)</p>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-[#E2E8F0]">
              <button
                onClick={() => setSelectedDeedModal(null)}
                className="px-3 py-1.5 text-xs font-semibold bg-[#142B4A] text-white rounded hover:bg-[#1E3A5F]"
              >
                Close Record
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
