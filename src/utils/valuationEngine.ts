/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 * 
 * PropVal AI Institutional Valuation & Underwriting Math Engine
 * 
 * NOTE: This is a provisional rule-based estimation engine implementing
 * deterministic hedonic scorecard adjustments for property valuation and credit appraisal.
 * It is NOT a trained machine learning model, deep neural network, or predictive AI.
 * Designed for Indian Housing Finance Companies (HFCs) and Bank Credit Committees.
 */

export interface ValuationInputParams {
  carpetAreaSqFt: number;
  superBuiltUpAreaSqFt: number;
  baseMarketRatePerSqFt: number;
  circleRatePerSqFt: number; // Ready Reckoner / SRO Guideline rate
  floorRiseFactor: number; // ₹/sq ft adjustment
  roadWidthFactor: number; // ₹/sq ft adjustment
  amenitiesPremium: number; // ₹/sq ft adjustment
  structuralDepreciation: number; // negative ₹/sq ft adjustment
  underwriterHaircutPct: number; // e.g. -5% to +5%
  distressDiscountPct: number; // e.g. 15% to 25% (forced sale liquidation)
  ltvRatioPct: number; // Loan-to-Value limit, e.g. 75%
  legalRiskPenaltyPct: number; // e.g. 0% or 5% if title discrepancy
}

export interface ValuationResult {
  carpetAreaSqFt: number;
  superBuiltUpAreaSqFt: number;
  unadjustedRatePerSqFt: number;
  ruleAdjustedRatePerSqFt: number;
  /** @deprecated Alias for ruleAdjustedRatePerSqFt for backward compatibility */
  aiAdjustedRatePerSqFt: number;
  circleRatePerSqFt: number;
  grossMarketValue: number;
  netAssessedValue: number;
  distressLiquidationValue: number;
  maxSanctionAmount: number;
  deviationFromCircleRatePct: number;
  confidenceScorePct: number;
  riskTier: 'LOW_RISK' | 'MODERATE_RISK' | 'HIGH_ALERT';
  attributionBreakdown: {
    factor: string;
    impactPerSqFt: number;
    description: string;
    category: 'positive' | 'negative' | 'neutral';
  }[];
}

/**
 * Format currency according to Indian denomination rules (Hundreds, Thousands, Lakhs, Crores).
 * e.g., 14250000 -> "₹1,42,50,000" or "₹1.43 Cr"
 */
export function formatIndianCurrency(
  amount: number,
  mode: 'full' | 'short' = 'full'
): string {
  if (amount === undefined || amount === null || isNaN(amount)) return '₹0';
  const isNegative = amount < 0;
  const absAmount = Math.abs(amount);

  if (mode === 'short') {
    if (absAmount >= 10000000) {
      // 1 Crore = 10,000,000
      const cr = (absAmount / 10000000).toFixed(2);
      return `${isNegative ? '-' : ''}₹${cr} Cr`;
    } else if (absAmount >= 100000) {
      // 1 Lakh = 100,000
      const lk = (absAmount / 100000).toFixed(2);
      return `${isNegative ? '-' : ''}₹${lk} L`;
    } else {
      return `${isNegative ? '-' : ''}₹${formatIndianNumber(Math.round(absAmount))}`;
    }
  }

  return `${isNegative ? '-' : ''}₹${formatIndianNumber(Math.round(absAmount))}`;
}

/**
 * Formats a plain number with Indian comma grouping:
 * 14250000 -> 1,42,50,000
 */
export function formatIndianNumber(num: number): string {
  if (isNaN(num)) return '0';
  const str = Math.floor(Math.abs(num)).toString();
  if (str.length <= 3) return str;

  const lastThree = str.substring(str.length - 3);
  const otherNumbers = str.substring(0, str.length - 3);
  const formattedOthers = otherNumbers.replace(/\B(?=(\d{2})+(?!\d))/g, ',');
  return `${formattedOthers},${lastThree}`;
}

/**
 * Computes deterministic hedonic property valuation including scorecard attribution breakdown.
 * Uses bounded adjustments and RERA carpet-area based valuation math.
 */
export function calculateValuation(params: ValuationInputParams): ValuationResult {
  const {
    carpetAreaSqFt: rawCarpetArea,
    superBuiltUpAreaSqFt = 0,
    baseMarketRatePerSqFt: rawBaseRate,
    circleRatePerSqFt = 0,
    floorRiseFactor = 0,
    roadWidthFactor = 0,
    amenitiesPremium = 0,
    structuralDepreciation = 0,
    underwriterHaircutPct = 0,
    distressDiscountPct = 17,
    ltvRatioPct = 75,
    legalRiskPenaltyPct = 0,
  } = params;

  // Defensive input sanitization
  const carpetAreaSqFt = Math.max(0, isNaN(rawCarpetArea) ? 0 : rawCarpetArea);
  const baseMarketRatePerSqFt = Math.max(0, isNaN(rawBaseRate) ? 0 : rawBaseRate);

  // Scorecard adjusted rate per sq ft on Carpet Area (floor minimum ₹1,000/sqft)
  const netAdjustment =
    floorRiseFactor +
    roadWidthFactor +
    amenitiesPremium -
    Math.abs(structuralDepreciation);

  const ruleAdjustedRatePerSqFt = Math.max(1000, baseMarketRatePerSqFt + netAdjustment);
  const aiAdjustedRatePerSqFt = ruleAdjustedRatePerSqFt;

  // Gross Valuation (carpet area based)
  const grossMarketValue = Math.round(ruleAdjustedRatePerSqFt * carpetAreaSqFt);

  // Underwriter hair-cut adjustment & legal risk penalty (safely bounded)
  const safeHaircutPct = Math.max(-90, Math.min(50, isNaN(underwriterHaircutPct) ? 0 : underwriterHaircutPct));
  const safeLegalPenaltyPct = Math.max(0, Math.min(100, isNaN(legalRiskPenaltyPct) ? 0 : legalRiskPenaltyPct));
  const underwriterMultiplier = 1 + safeHaircutPct / 100;
  const legalMultiplier = 1 - safeLegalPenaltyPct / 100;
  const netAssessedValue = Math.max(0, Math.round(grossMarketValue * underwriterMultiplier * legalMultiplier));

  // Forced Sale / Distress Liquidation Value (standard HFC metric)
  const distressLiquidationValue = Math.round(
    netAssessedValue * (1 - Math.max(5, Math.min(50, isNaN(distressDiscountPct) ? 17 : distressDiscountPct)) / 100)
  );

  // Max Loan Sanction Amount based on permitted LTV (75% - 80% NHB cap)
  const maxSanctionAmount = Math.round(
    netAssessedValue * (Math.min(90, Math.max(30, isNaN(ltvRatioPct) ? 75 : ltvRatioPct)) / 100)
  );

  // Deviation from Circle Rate (Guideline Value)
  const safeCircleRate = Math.max(0, isNaN(circleRatePerSqFt) ? 0 : circleRatePerSqFt);
  const deviationFromCircleRatePct =
    safeCircleRate > 0
      ? Number((((aiAdjustedRatePerSqFt - safeCircleRate) / safeCircleRate) * 100).toFixed(1))
      : 0;

  // Attribution Waterfall Breakdown
  const attributionBreakdown = [
    {
      factor: 'Micro-Market Baseline',
      impactPerSqFt: baseMarketRatePerSqFt,
      description: 'Indicative micro-market baseline rate (synthetic benchmark, not verified transaction evidence)',
      category: 'neutral' as const,
    },
    {
      factor: 'Floor Rise Factor',
      impactPerSqFt: floorRiseFactor,
      description: floorRiseFactor >= 0 ? 'High-floor premium (+4th floor and above)' : 'Ground/lower floor discount',
      category: floorRiseFactor >= 0 ? ('positive' as const) : ('negative' as const),
    },
    {
      factor: 'Road Access & Arterial Width',
      impactPerSqFt: roadWidthFactor,
      description: roadWidthFactor > 0 ? '60ft+ master plan arterial road frontage' : 'Sub-30ft narrow approach road',
      category: roadWidthFactor >= 0 ? ('positive' as const) : ('negative' as const),
    },
    {
      factor: 'Gated Amenities & Security',
      impactPerSqFt: amenitiesPremium,
      description: 'Clubhouse, power backup, swimming pool, 24/7 security & STP',
      category: 'positive' as const,
    },
    {
      factor: 'Age & Structural Depreciation',
      impactPerSqFt: -Math.abs(structuralDepreciation),
      description: 'Asset vintage and physical maintenance wear factor',
      category: 'negative' as const,
    },
  ];

  // Heuristic confidence score calculation (rule-based deduction, not statistically calibrated)
  let baseConfidence = 95.5;
  if (Math.abs(deviationFromCircleRatePct) > 35) {
    baseConfidence -= 10.0;
  } else if (Math.abs(deviationFromCircleRatePct) > 20) {
    baseConfidence -= 4.2;
  }
  if (safeLegalPenaltyPct > 0) {
    baseConfidence -= 8.5;
  }
  const confidenceScorePct = Math.max(65, Math.min(99.4, Number(baseConfidence.toFixed(1))));

  // Deterministic Risk Tier Evaluation
  let riskTier: 'LOW_RISK' | 'MODERATE_RISK' | 'HIGH_ALERT' = 'LOW_RISK';
  if (deviationFromCircleRatePct > 40 || safeLegalPenaltyPct > 5 || confidenceScorePct < 80) {
    riskTier = 'HIGH_ALERT';
  } else if (deviationFromCircleRatePct > 20 || safeHaircutPct < -5 || confidenceScorePct < 90) {
    riskTier = 'MODERATE_RISK';
  }

  return {
    carpetAreaSqFt,
    superBuiltUpAreaSqFt,
    unadjustedRatePerSqFt: baseMarketRatePerSqFt,
    ruleAdjustedRatePerSqFt,
    aiAdjustedRatePerSqFt,
    circleRatePerSqFt,
    grossMarketValue,
    netAssessedValue,
    distressLiquidationValue,
    maxSanctionAmount,
    deviationFromCircleRatePct,
    confidenceScorePct,
    riskTier,
    attributionBreakdown,
  };
}
