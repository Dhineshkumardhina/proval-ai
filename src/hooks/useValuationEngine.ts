/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * 
 * Reusable React Hook for PropVal AI Valuation Engine with Automatic Offline Fallback.
 */

import { useState, useEffect, useMemo, useRef } from 'react';
import { ValuationInputParams, ValuationResult, calculateValuation } from '../utils/valuationEngine';
import { fetchValuationEstimate } from '../services/apiClient';

export type EngineSourceType = 'fastapi' | 'fallback';

export interface UseValuationEngineReturn {
  valuationResult: ValuationResult;
  isLoading: boolean;
  engineSource: EngineSourceType;
  engineBadgeLabel: string;
  error: string | null;
}

/**
 * Custom hook to execute valuation estimates against FastAPI backend with
 * guaranteed, synchronous local rule-based offline fallback.
 */
export function useValuationEngine(params: ValuationInputParams): UseValuationEngineReturn {
  // Synchronous local calculation baseline (guarantees zero UI lag/flicker)
  const localFallbackResult = useMemo(() => {
    return calculateValuation(params);
  }, [
    params.carpetAreaSqFt,
    params.superBuiltUpAreaSqFt,
    params.baseMarketRatePerSqFt,
    params.circleRatePerSqFt,
    params.floorRiseFactor,
    params.roadWidthFactor,
    params.amenitiesPremium,
    params.structuralDepreciation,
    params.underwriterHaircutPct,
    params.distressDiscountPct,
    params.ltvRatioPct,
    params.legalRiskPenaltyPct,
  ]);

  const [valuationResult, setValuationResult] = useState<ValuationResult>(localFallbackResult);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [engineSource, setEngineSource] = useState<EngineSourceType>('fallback');
  const [error, setError] = useState<string | null>(null);

  // Keep ref to latest params to prevent stale updates
  const latestParamsRef = useRef(params);
  latestParamsRef.current = params;

  useEffect(() => {
    // Whenever input parameters change, update the local result immediately
    // so the UI never displays outdated numbers while the backend request is in-flight
    setValuationResult(localFallbackResult);

    const abortController = new AbortController();
    setIsLoading(true);

    const debounceTimer = setTimeout(async () => {
      try {
        const backendResult = await fetchValuationEstimate(latestParamsRef.current, abortController.signal);
        setValuationResult(backendResult);
        setEngineSource('fastapi');
        setError(null);
      } catch (err: any) {
        if (err.name === 'AbortError') {
          return; // Expected cancellation on rapid input updates
        }
        // Gracefully retain local rule-based fallback without breaking UI
        setValuationResult(localFallbackResult);
        setEngineSource('fallback');
        setError(err.message || 'FastAPI backend unreachable');
      } finally {
        setIsLoading(false);
      }
    }, 100);

    return () => {
      clearTimeout(debounceTimer);
      abortController.abort();
    };
  }, [localFallbackResult]);

  const engineBadgeLabel = useMemo(() => {
    if (engineSource === 'fastapi') {
      return 'Engine: FastAPI Backend (v0.2.0)';
    }
    return 'Engine: Local Rule-Based (Offline Fallback)';
  }, [engineSource]);

  return {
    valuationResult,
    isLoading,
    engineSource,
    engineBadgeLabel,
    error,
  };
}

