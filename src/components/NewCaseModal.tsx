/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { PlusCircle, Building, Check, X, Sparkles } from 'lucide-react';
import { ValuationCase } from '../types/valuation';

interface NewCaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (newCase: ValuationCase) => void;
}

export const NewCaseModal: React.FC<NewCaseModalProps> = ({ isOpen, onClose, onSubmit }) => {
  const [borrowerName, setBorrowerName] = useState('');
  const [projectName, setProjectName] = useState('');
  const [unitAddress, setUnitAddress] = useState('');
  const [city, setCity] = useState<'Bengaluru' | 'Mumbai' | 'Delhi-NCR' | 'Hyderabad' | 'Pune' | 'Chennai'>('Bengaluru');
  const [locality, setLocality] = useState('');
  const [carpetAreaSqFt, setCarpetAreaSqFt] = useState<number>(1150);
  const [superBuiltUpAreaSqFt, setSuperBuiltUpAreaSqFt] = useState<number>(1500);
  const [floorNo, setFloorNo] = useState<number>(8);
  const [loanRequested, setLoanRequested] = useState<number>(8500000);
  const [declaredValue, setDeclaredValue] = useState<number>(11500000);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!borrowerName || !projectName) return;

    const newId = `case-${Date.now()}`;
    const newAppNo = `HFC-${city.slice(0, 3).toUpperCase()}-2026-${Math.floor(10000 + Math.random() * 90000)}`;

    const cityBaseRate =
      city === 'Mumbai' ? 24000 : city === 'Delhi-NCR' ? 21000 : city === 'Bengaluru' ? 9500 : 8000;
    const cityCircleRate =
      city === 'Mumbai' ? 20000 : city === 'Delhi-NCR' ? 17500 : city === 'Bengaluru' ? 7000 : 6000;

    const createdCase: ValuationCase = {
      id: newId,
      applicationNo: newAppNo,
      borrowerName,
      cibilScore: 780,
      loanRequested,
      declaredAgreementValue: declaredValue,
      propertyType: 'High-Rise Apartment',
      unitAddress: unitAddress || `Flat ${floorNo}02, ${projectName}`,
      projectName,
      locality: locality || 'Central Sub-Market Corridor',
      city,
      pincode: '560001',
      branch: `${city} Central Lending Hub`,
      carpetAreaSqFt,
      superBuiltUpAreaSqFt,
      floorNo,
      totalFloors: 18,
      ageYears: 1,
      roadWidthFt: 60,
      circleRatePerSqFt: cityCircleRate,
      baseMarketRatePerSqFt: cityBaseRate,
      floorRiseFactor: floorNo > 4 ? 300 : 0,
      roadWidthFactor: 250,
      amenitiesPremium: 400,
      structuralDepreciation: 80,
      status: 'READY_FOR_APPROVAL',
      statusLabel: 'Ready for Underwriter Sign-off',
      underwriterHaircutPct: 0,
      distressDiscountPct: 18,
      ltvRatioPct: 75,
      legalRiskPenaltyPct: 0,
      assignedUnderwriter: 'V. Sundaram (Sr. Underwriter)',
      createdAt: 'Just now',
      lastUpdated: 'Just now',
      reraRegistration: `PRM/${city.slice(0, 2).toUpperCase()}/RERA/2026/0014`,
      bbmpPlanApprovalNo: `PLAN/${city.slice(0, 3).toUpperCase()}/2024/889`,
      titleChainYears: 30,
      encumbranceStatus: 'NIL_ENCUMBRANCE',
      comparables: [
        {
          id: `comp-${Date.now()}-1`,
          sroRegNo: `SRO-${city.slice(0, 3).toUpperCase()}-2026-BK1-8411`,
          regDate: '20-Oct-2026',
          propertyName: `${projectName} (Adjacent Wing)`,
          unitNo: `${floorNo}04`,
          carpetAreaSqFt,
          superBuiltUpAreaSqFt,
          registeredPrice: Math.round(declaredValue * 0.98),
          ratePerSqFt: Math.round((declaredValue * 0.98) / carpetAreaSqFt),
          distanceMeters: 150,
          similarityScorePct: 95,
          weightInEstimate: 0.5,
          floor: floorNo,
          coordinates: { x: 50, y: 50 },
        },
      ],
      documentFields: [
        {
          label: 'SRO Registered Deed',
          applicantDeclared: `BK-1/${Math.floor(1000 + Math.random() * 9000)}/2024`,
          sroIndexExtract: 'Automated digital registry check passed',
          matchStatus: 'MATCHED',
        },
        {
          label: 'Carpet Area (RERA)',
          applicantDeclared: `${carpetAreaSqFt} sq ft`,
          sroIndexExtract: `${carpetAreaSqFt} sq ft sanctioned`,
          matchStatus: 'MATCHED',
        },
      ],
      surveyPhotos: [
        {
          id: `p-${Date.now()}`,
          title: 'Building Entrance & Façade',
          category: 'Exterior',
          latLong: '12.9716° N, 77.5946° E',
          capturedAt: 'Today 10:00 AM',
          surveyor: 'Kishore Gowda (ID: INSP-089)',
          surveyorId: 'INSP-089',
          status: 'VERIFIED',
          description: 'Modern residential tower with clear approach road.',
          imageUrl: 'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=800&q=80',
        },
      ],
      auditNotes: ['Case ingested into valuation engine pipeline.'],
    };

    onSubmit(createdCase);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#142B4A]/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white rounded-lg border border-[#CBD5E1] shadow-2xl max-w-xl w-full p-5 space-y-4 my-8 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-[#64748B] hover:text-[#172033]"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="border-b border-[#E2E8F0] pb-2 flex items-center gap-2">
          <div className="p-1.5 rounded bg-[#EFF6FF] text-[#2563EB]">
            <PlusCircle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-[#142B4A] uppercase tracking-wide">
              Intake New Collateral Valuation File
            </h3>
            <p className="text-xs text-[#64748B]">
              Enter property specifications to immediately trigger algorithmic sub-market hedonic appraisal
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3 text-xs">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label-caps text-[#64748B] block mb-1">Borrower Name *</label>
              <input
                type="text"
                required
                placeholder="e.g. Ramesh Iyer"
                value={borrowerName}
                onChange={(e) => setBorrowerName(e.target.value)}
                className="w-full p-2 border border-[#CBD5E1] rounded text-[#172033] focus:border-[#2563EB]"
              />
            </div>
            <div>
              <label className="label-caps text-[#64748B] block mb-1">Target Metro *</label>
              <select
                value={city}
                onChange={(e) => setCity(e.target.value as any)}
                className="w-full p-2 border border-[#CBD5E1] rounded text-[#172033] focus:border-[#2563EB]"
              >
                <option value="Bengaluru">Bengaluru</option>
                <option value="Mumbai">Mumbai</option>
                <option value="Delhi-NCR">Delhi-NCR</option>
                <option value="Hyderabad">Hyderabad</option>
                <option value="Pune">Pune</option>
                <option value="Chennai">Chennai</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label-caps text-[#64748B] block mb-1">Project Name *</label>
              <input
                type="text"
                required
                placeholder="e.g. Brigade Gateway"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                className="w-full p-2 border border-[#CBD5E1] rounded text-[#172033] focus:border-[#2563EB]"
              />
            </div>
            <div>
              <label className="label-caps text-[#64748B] block mb-1">Locality / Sector</label>
              <input
                type="text"
                placeholder="e.g. Malleshwaram"
                value={locality}
                onChange={(e) => setLocality(e.target.value)}
                className="w-full p-2 border border-[#CBD5E1] rounded text-[#172033] focus:border-[#2563EB]"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="label-caps text-[#64748B] block mb-1">Carpet Area (sq ft)</label>
              <input
                type="number"
                value={carpetAreaSqFt}
                onChange={(e) => setCarpetAreaSqFt(Number(e.target.value))}
                className="w-full p-2 border border-[#CBD5E1] rounded text-[#172033] font-mono focus:border-[#2563EB]"
              />
            </div>
            <div>
              <label className="label-caps text-[#64748B] block mb-1">SBUA (sq ft)</label>
              <input
                type="number"
                value={superBuiltUpAreaSqFt}
                onChange={(e) => setSuperBuiltUpAreaSqFt(Number(e.target.value))}
                className="w-full p-2 border border-[#CBD5E1] rounded text-[#172033] font-mono focus:border-[#2563EB]"
              />
            </div>
            <div>
              <label className="label-caps text-[#64748B] block mb-1">Floor Level</label>
              <input
                type="number"
                value={floorNo}
                onChange={(e) => setFloorNo(Number(e.target.value))}
                className="w-full p-2 border border-[#CBD5E1] rounded text-[#172033] font-mono focus:border-[#2563EB]"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label-caps text-[#64748B] block mb-1">Loan Requested (₹)</label>
              <input
                type="number"
                step="100000"
                value={loanRequested}
                onChange={(e) => setLoanRequested(Number(e.target.value))}
                className="w-full p-2 border border-[#CBD5E1] rounded text-[#172033] font-mono focus:border-[#2563EB]"
              />
            </div>
            <div>
              <label className="label-caps text-[#64748B] block mb-1">Declared Price (₹)</label>
              <input
                type="number"
                step="100000"
                value={declaredValue}
                onChange={(e) => setDeclaredValue(Number(e.target.value))}
                className="w-full p-2 border border-[#CBD5E1] rounded text-[#172033] font-mono focus:border-[#2563EB]"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-[#E2E8F0]">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 font-medium text-[#64748B] hover:text-[#172033]"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 font-semibold bg-[#2563EB] hover:bg-[#1D4ED8] text-white rounded flex items-center gap-1.5"
            >
              <Sparkles className="w-3.5 h-3.5" />
              Run AI Appraisal
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
