/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  Layers,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  MapPin,
  Compass,
  Building2,
  Train,
  ShieldCheck,
  Eye,
  Info,
} from 'lucide-react';
import { ValuationCase, ComparableDeed } from '../../types/valuation';
import { formatIndianCurrency } from '../../utils/valuationEngine';

interface GisMapCanvasProps {
  currentCase: ValuationCase;
  onSelectComp?: (comp: ComparableDeed) => void;
  selectedCompId?: string | null;
}

export const GisMapCanvas: React.FC<GisMapCanvasProps> = ({
  currentCase,
  onSelectComp,
  selectedCompId,
}) => {
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [mapMode, setMapMode] = useState<'cadastral' | 'satellite' | 'hybrid'>('cadastral');
  const [showCircleRateZone, setShowCircleRateZone] = useState<boolean>(true);
  const [showRadiusRings, setShowRadiusRings] = useState<boolean>(true);
  const [showTransitCorridor, setShowTransitCorridor] = useState<boolean>(true);
  const [hoveredComp, setHoveredComp] = useState<ComparableDeed | null>(null);

  const handleZoomIn = () => setZoomLevel((prev) => Math.min(prev + 0.25, 2.0));
  const handleZoomOut = () => setZoomLevel((prev) => Math.max(prev - 0.25, 0.75));
  const handleResetZoom = () => setZoomLevel(1);

  return (
    <div className="relative w-full h-full min-h-[460px] bg-[#0F172A] rounded-md overflow-hidden border border-[#E2E8F0] shadow-sm select-none flex flex-col">
      {/* Top Map Control Bar */}
      <div className="absolute top-3 left-3 right-3 z-20 flex items-center justify-between pointer-events-none">
        {/* Layer & Mode Selector */}
        <div className="flex items-center gap-1.5 bg-white/95 backdrop-blur-md px-2.5 py-1.5 rounded shadow-sm border border-[#E2E8F0] pointer-events-auto">
          <Layers className="w-3.5 h-3.5 text-[#142B4A]" />
          <span className="text-[11px] font-semibold text-[#142B4A] uppercase tracking-wider mr-1">GIS View:</span>
          {(['cadastral', 'satellite', 'hybrid'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setMapMode(mode)}
              className={`px-2 py-0.5 text-[11px] font-medium rounded transition-colors ${
                mapMode === mode
                  ? 'bg-[#142B4A] text-white'
                  : 'text-[#64748B] hover:text-[#142B4A] hover:bg-[#F1F5F9]'
              }`}
            >
              {mode.charAt(0).toUpperCase() + mode.slice(1)}
            </button>
          ))}
        </div>

        {/* Proximity & Coordinate Badge */}
        <div className="hidden sm:flex items-center gap-2 bg-[#142B4A]/90 text-white backdrop-blur-md px-3 py-1 rounded shadow-sm border border-white/10 pointer-events-auto">
          <Compass className="w-3.5 h-3.5 text-[#38BDF8]" />
          <span className="text-[11px] font-mono tabular-nums">
            {currentCase.locality} | {currentCase.city} ({currentCase.pincode})
          </span>
          <span className="bg-[#0F766E] text-white text-[10px] px-1.5 py-0.2 rounded font-semibold">
            {currentCase.roadWidthFt}ft Master Road
          </span>
        </div>
      </div>

      {/* SVG GIS Canvas */}
      <div className="relative flex-1 w-full h-full overflow-hidden flex items-center justify-center">
        <svg
          viewBox="0 0 1000 700"
          className="w-full h-full transition-transform duration-300 ease-out"
          style={{
            transform: `scale(${zoomLevel})`,
            transformOrigin: 'center center',
          }}
        >
          {/* Background Map Styling based on Mode */}
          <defs>
            <pattern id="grid-pattern" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#334155" strokeWidth="0.5" strokeOpacity="0.4" />
            </pattern>
            <radialGradient id="subject-glow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#2563EB" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#2563EB" stopOpacity="0" />
            </radialGradient>
            <linearGradient id="circle-rate-grad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#0F766E" stopOpacity="0.18" />
              <stop offset="100%" stopColor="#2563EB" stopOpacity="0.08" />
            </linearGradient>
            <pattern id="satellite-texture" width="100" height="100" patternUnits="userSpaceOnUse">
              <rect width="100" height="100" fill="#131B2E" />
              <circle cx="20" cy="20" r="1.5" fill="#334155" opacity="0.5" />
              <circle cx="70" cy="80" r="2" fill="#334155" opacity="0.4" />
              <circle cx="90" cy="30" r="1" fill="#475569" opacity="0.6" />
            </pattern>
          </defs>

          {/* Base Layer */}
          {mapMode === 'satellite' ? (
            <rect width="1000" height="700" fill="#0C1425" />
          ) : mapMode === 'hybrid' ? (
            <rect width="1000" height="700" fill="#09101F" />
          ) : (
            <rect width="1000" height="700" fill="#0F172A" />
          )}

          {/* Cadastral Grid */}
          <rect width="1000" height="700" fill="url(#grid-pattern)" />

          {/* SRO Ready Reckoner / Circle Rate Micro-Market Polygon Zone */}
          {showCircleRateZone && (
            <g>
              <polygon
                points="220,120 780,100 890,520 620,640 180,560"
                fill="url(#circle-rate-grad)"
                stroke="#0F766E"
                strokeWidth="1.5"
                strokeDasharray="6,4"
              />
              <text x="240" y="145" fill="#5EEAD4" fontSize="12" fontWeight="600" className="label-caps font-mono">
                DEMO GUIDELINE JURISDICTION: {currentCase.locality.toUpperCase()} [₹{currentCase.circleRatePerSqFt}/sq ft]
              </text>
            </g>
          )}

          {/* Master Plan Road Network */}
          <g>
            {/* Primary Arterial Road 60ft/80ft */}
            <path
              d="M 60,350 C 280,360 450,330 650,370 L 940,390"
              fill="none"
              stroke="#475569"
              strokeWidth="28"
              strokeLinecap="round"
            />
            <path
              d="M 60,350 C 280,360 450,330 650,370 L 940,390"
              fill="none"
              stroke="#94A3B8"
              strokeWidth="2"
              strokeDasharray="8,8"
            />
            <text x="100" y="340" fill="#CBD5E1" fontSize="11" fontWeight="500" letterSpacing="0.05em">
              MASTER PLAN ARTERIAL ROAD ({currentCase.roadWidthFt} FT DUAL CARRIAGEWAY)
            </text>

            {/* Secondary Sector Road */}
            <path
              d="M 500,80 L 520,345 L 480,660"
              fill="none"
              stroke="#334155"
              strokeWidth="14"
              strokeLinecap="round"
            />
          </g>

          {/* Transit Corridor (Metro Line / Highway) */}
          {showTransitCorridor && (
            <g>
              <path
                d="M 80,610 Q 420,580 880,590"
                fill="none"
                stroke="#F59E0B"
                strokeWidth="5"
                strokeDasharray="10,6"
              />
              <g transform="translate(680, 580)">
                <circle cx="0" cy="0" r="10" fill="#F59E0B" />
                <circle cx="0" cy="0" r="4" fill="#FFFFFF" />
                <text x="16" y="4" fill="#FDE68A" fontSize="11" fontWeight="600">
                  Metro Transit Station (1.2 km)
                </text>
              </g>
            </g>
          )}

          {/* Concentric Appraisal Distance Rings from Subject Property (Center: 500, 350) */}
          {showRadiusRings && (
            <g>
              {/* 500m Radius */}
              <circle
                cx="500"
                cy="350"
                r="110"
                fill="none"
                stroke="#2563EB"
                strokeWidth="1"
                strokeDasharray="4,4"
                opacity="0.6"
              />
              <text x="500" y="235" fill="#93C5FD" fontSize="10" textAnchor="middle">
                500m Primary Density Ring
              </text>

              {/* 1.0 km Radius */}
              <circle
                cx="500"
                cy="350"
                r="220"
                fill="none"
                stroke="#3B82F6"
                strokeWidth="1"
                strokeDasharray="4,4"
                opacity="0.4"
              />
              <text x="500" y="125" fill="#60A5FA" fontSize="10" textAnchor="middle">
                1.0 km Sample Comparable Benchmark
              </text>

              {/* 2.0 km Radius */}
              <circle
                cx="500"
                cy="350"
                r="330"
                fill="none"
                stroke="#64748B"
                strokeWidth="1"
                strokeDasharray="5,5"
                opacity="0.25"
              />
            </g>
          )}

          {/* Subject Property Parcel Outline & Beacon (Center at 500, 350) */}
          <g>
            {/* Pulsing halo */}
            <circle cx="500" cy="350" r="48" fill="url(#subject-glow)" className="animate-pulse" />

            {/* Parcel Polygon Boundary */}
            <polygon
              points="465,320 540,310 550,375 475,385"
              fill="#2563EB"
              fillOpacity="0.3"
              stroke="#38BDF8"
              strokeWidth="2.5"
            />

            {/* Subject Pin Marker */}
            <circle cx="500" cy="350" r="14" fill="#2563EB" stroke="#FFFFFF" strokeWidth="2.5" />
            <circle cx="500" cy="350" r="5" fill="#FFFFFF" />

            {/* Subject Label Tag */}
            <g transform="translate(500, 310)">
              <rect x="-95" y="-30" width="190" height="26" rx="4" fill="#142B4A" stroke="#38BDF8" strokeWidth="1" />
              <text x="0" y="-13" fill="#FFFFFF" fontSize="11" fontWeight="700" textAnchor="middle">
                SUBJECT COLLATERAL
              </text>
            </g>
          </g>

          {/* Comparable Deed Pins */}
          {currentCase.comparables.map((comp, idx) => {
            // Map relative coordinate (0-100) to svg canvas (1000x700)
            const cx = (comp.coordinates.x / 100) * 800 + 100;
            const cy = (comp.coordinates.y / 100) * 500 + 100;
            const isSelected = selectedCompId === comp.id;
            const isHovered = hoveredComp?.id === comp.id;

            return (
              <g
                key={comp.id}
                className="cursor-pointer transition-all duration-200"
                onClick={() => onSelectComp && onSelectComp(comp)}
                onMouseEnter={() => setHoveredComp(comp)}
                onMouseLeave={() => setHoveredComp(null)}
              >
                {/* Distance connector line to subject property */}
                <line
                  x1="500"
                  y1="350"
                  x2={cx}
                  y2={cy}
                  stroke={isSelected ? '#38BDF8' : '#475569'}
                  strokeWidth={isSelected ? '2' : '1'}
                  strokeDasharray="3,3"
                  opacity={isSelected || isHovered ? '0.9' : '0.4'}
                />

                {/* Pin Circle */}
                <circle
                  cx={cx}
                  cy={cy}
                  r={isSelected ? 16 : isHovered ? 14 : 11}
                  fill={isSelected ? '#0F766E' : '#1E293B'}
                  stroke={isSelected ? '#2DD4BF' : '#94A3B8'}
                  strokeWidth={isSelected ? '3' : '2'}
                  className="transition-all"
                />

                <text
                  x={cx}
                  y={cy + 4}
                  fill="#FFFFFF"
                  fontSize="10"
                  fontWeight="700"
                  textAnchor="middle"
                  className="select-none"
                >
                  C{idx + 1}
                </text>

                {/* Tooltip on Hover or Select */}
                {(isHovered || isSelected) && (
                  <g transform={`translate(${cx}, ${cy - 20})`}>
                    <rect
                      x="-85"
                      y="-44"
                      width="170"
                      height="40"
                      rx="4"
                      fill="#0F172A"
                      stroke="#2DD4BF"
                      strokeWidth="1.2"
                      filter="drop-shadow(0 4px 6px rgba(0,0,0,0.5))"
                    />
                    <text x="0" y="-28" fill="#F8FAFC" fontSize="10" fontWeight="600" textAnchor="middle">
                      {comp.propertyName.slice(0, 24)}
                    </text>
                    <text x="0" y="-13" fill="#2DD4BF" fontSize="10" fontWeight="700" textAnchor="middle">
                      ₹{comp.ratePerSqFt.toLocaleString('en-IN')}/sqft ({comp.distanceMeters}m away)
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {/* Bottom GIS Legend & Layer Quick Toggles */}
      <div className="bg-[#1E293B]/95 border-t border-[#334155] px-3 py-2 flex flex-wrap items-center justify-between text-xs text-[#94A3B8] gap-2 z-10">
        <div className="flex items-center gap-4 flex-wrap">
          <label className="flex items-center gap-1.5 cursor-pointer text-[11px] hover:text-white">
            <input
              type="checkbox"
              checked={showCircleRateZone}
              onChange={(e) => setShowCircleRateZone(e.target.checked)}
              className="accent-[#0F766E] rounded"
            />
            <span className="w-2.5 h-2.5 rounded-sm bg-[#0F766E]/40 border border-[#0F766E]" />
            SRO Circle Zone
          </label>

          <label className="flex items-center gap-1.5 cursor-pointer text-[11px] hover:text-white">
            <input
              type="checkbox"
              checked={showRadiusRings}
              onChange={(e) => setShowRadiusRings(e.target.checked)}
              className="accent-[#2563EB] rounded"
            />
            <span className="w-2.5 h-2.5 rounded-full border border-[#3B82F6] border-dashed" />
            500m / 1km Rings
          </label>

          <label className="flex items-center gap-1.5 cursor-pointer text-[11px] hover:text-white">
            <input
              type="checkbox"
              checked={showTransitCorridor}
              onChange={(e) => setShowTransitCorridor(e.target.checked)}
              className="accent-[#F59E0B] rounded"
            />
            <span className="w-2.5 h-2.5 rounded-sm bg-[#F59E0B]" />
            Transit Corridor
          </label>
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center gap-1 bg-[#0F172A] p-0.5 rounded border border-[#334155]">
          <button
            onClick={handleZoomIn}
            title="Zoom In"
            className="p-1 text-[#94A3B8] hover:text-white hover:bg-[#334155] rounded"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <span className="text-[10px] font-mono px-1 text-slate-300">
            {Math.round(zoomLevel * 100)}%
          </span>
          <button
            onClick={handleZoomOut}
            title="Zoom Out"
            className="p-1 text-[#94A3B8] hover:text-white hover:bg-[#334155] rounded"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleResetZoom}
            title="Reset View"
            className="p-1 text-[#94A3B8] hover:text-white hover:bg-[#334155] rounded ml-0.5"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
