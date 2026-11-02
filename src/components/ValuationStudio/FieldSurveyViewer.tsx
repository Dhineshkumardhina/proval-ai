/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  Camera,
  MapPin,
  Clock,
  UserCheck,
  CheckCircle2,
  AlertTriangle,
  ZoomIn,
  ShieldCheck,
  Check,
} from 'lucide-react';
import { ValuationCase, FieldInspectionPhoto, CREDIBILITY_LABELS } from '../../types/valuation';

interface FieldSurveyViewerProps {
  currentCase: ValuationCase;
}

export const FieldSurveyViewer: React.FC<FieldSurveyViewerProps> = ({ currentCase }) => {
  const [selectedPhoto, setSelectedPhoto] = useState<FieldInspectionPhoto>(currentCase.surveyPhotos[0]);

  return (
    <div className="w-full h-full flex flex-col bg-white rounded-md border border-[#E2E8F0] shadow-sm overflow-hidden">
      {/* Header with Surveyor Audit Credentials */}
      <div className="p-3 bg-[#F8FAFC] border-b border-[#E2E8F0] flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <Camera className="w-4 h-4 text-[#142B4A]" />
          <span className="text-xs font-bold text-[#142B4A] uppercase tracking-wide">
            Site Survey & Structural Inspection
          </span>
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#FEF3C7] text-[#B45309] border border-[#FDE68A]">
            {CREDIBILITY_LABELS.DATA_SOURCE_SYNTHETIC}
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[#FEF3C7] text-[#B45309] border border-[#FDE68A]">
            <CheckCircle2 className="w-3 h-3" />
            Illustrative Survey Sample
          </span>
          <span className="text-[11px] text-[#64748B] font-mono">
            {currentCase.surveyPhotos.length} Demonstration Frames
          </span>
        </div>
      </div>

      {/* Main Inspection Grid */}
      <div className="flex-1 p-3 overflow-y-auto space-y-3">
        {/* Active Selected Photo Showcase */}
        <div className="relative rounded border border-[#CBD5E1] bg-[#0F172A] overflow-hidden group">
          <img
            src={selectedPhoto.imageUrl}
            alt={selectedPhoto.title}
            className="w-full h-64 object-cover"
          />

          {/* Watermark Overlay in bottom corner */}
          <div className="absolute bottom-2 left-2 right-2 bg-[#0F172A]/90 backdrop-blur-md p-2.5 rounded border border-white/10 text-white flex flex-wrap items-center justify-between gap-2 text-xs">
            <div>
              <p className="font-semibold text-white text-xs flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-[#38BDF8]" />
                {selectedPhoto.title}
              </p>
              <div className="flex items-center gap-3 text-[11px] text-[#94A3B8] font-mono mt-0.5">
                <span>GPS: {selectedPhoto.latLong}</span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {selectedPhoto.capturedAt}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono bg-[#1E293B] px-2 py-1 rounded text-[#E2E8F0] border border-[#334155]">
                {selectedPhoto.surveyor}
              </span>
              <span className="text-[10px] font-semibold bg-[#334155] text-white px-2 py-0.5 rounded">
                Demonstration Frame
              </span>
            </div>
          </div>
        </div>

        {/* Survey Notes & Structural Checklist */}
        <div className="bg-[#F8FAFC] border border-[#E2E8F0] p-3 rounded text-xs space-y-2">
          <p className="font-semibold text-[#142B4A] flex items-center gap-1">
            <UserCheck className="w-3.5 h-3.5 text-[#2563EB]" />
            Field Surveyor Observations:
          </p>
          <p className="text-[#334155] leading-relaxed">
            {selectedPhoto.description}
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-[#E2E8F0]">
            <div className="bg-white p-2 rounded border border-[#E2E8F0]">
              <span className="label-caps text-[#64748B]">Occupancy</span>
              <p className="font-semibold text-[#172033] mt-0.5">Self-Occupied</p>
            </div>
            <div className="bg-white p-2 rounded border border-[#E2E8F0]">
              <span className="label-caps text-[#64748B]">Construction Stage</span>
              <p className="font-semibold text-[#15803D] mt-0.5">100% Completed (OC)</p>
            </div>
            <div className="bg-white p-2 rounded border border-[#E2E8F0]">
              <span className="label-caps text-[#64748B]">Quality Grade</span>
              <p className="font-semibold text-[#2563EB] mt-0.5">Grade A+ (Premium)</p>
            </div>
            <div className="bg-white p-2 rounded border border-[#E2E8F0]">
              <span className="label-caps text-[#64748B]">Road Approach</span>
              <p className="font-semibold text-[#172033] mt-0.5">{currentCase.roadWidthFt} ft Bituminous</p>
            </div>
          </div>
        </div>

        {/* Thumbnails Bar */}
        <div>
          <span className="label-caps text-[#64748B] block mb-1.5">Survey Camera Reel:</span>
          <div className="grid grid-cols-4 gap-2">
            {currentCase.surveyPhotos.map((photo) => (
              <button
                key={photo.id}
                onClick={() => setSelectedPhoto(photo)}
                className={`relative rounded overflow-hidden border-2 transition-all ${
                  selectedPhoto.id === photo.id
                    ? 'border-[#2563EB] ring-2 ring-[#2563EB]/20'
                    : 'border-[#CBD5E1] opacity-75 hover:opacity-100'
                }`}
              >
                <img src={photo.imageUrl} alt={photo.title} className="w-full h-16 object-cover" />
                <span className="absolute bottom-0 inset-x-0 bg-black/70 text-white text-[9px] p-0.5 truncate text-center font-medium">
                  {photo.category}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
