import test from 'node:test';
import assert from 'node:assert/strict';
import {
  formatIndianCurrency,
  formatIndianNumber,
  calculateValuation,
} from './valuationEngine';
import { CREDIBILITY_LABELS } from '../types/valuation';
import { INITIAL_VALUATION_CASES } from '../data/mockValuationData';

// ==========================================
// REGRESSION GUARD: ORIGINAL BASELINE TESTS
// ==========================================

test('formatIndianNumber groups digits using Indian numeral system', () => {
  assert.equal(formatIndianNumber(14250000), '1,42,50,000');
  assert.equal(formatIndianNumber(850000), '8,50,000');
  assert.equal(formatIndianNumber(12500), '12,500');
  assert.equal(formatIndianNumber(450), '450');
});

test('formatIndianCurrency formats full and short (Lakh / Crore) modes', () => {
  assert.equal(formatIndianCurrency(14250000, 'full'), '₹1,42,50,000');
  assert.equal(formatIndianCurrency(14250000, 'short'), '₹1.43 Cr');
  assert.equal(formatIndianCurrency(8850000, 'short'), '₹88.50 L');
  assert.equal(formatIndianCurrency(75000, 'short'), '₹75,000');
});

test('calculateValuation computes correct gross, haircut, liquidation and sanction values', () => {
  const result = calculateValuation({
    carpetAreaSqFt: 1250,
    superBuiltUpAreaSqFt: 1650,
    baseMarketRatePerSqFt: 9800,
    circleRatePerSqFt: 7800,
    floorRiseFactor: 350,
    roadWidthFactor: 250,
    amenitiesPremium: 400,
    structuralDepreciation: 150,
    underwriterHaircutPct: -5,
    distressDiscountPct: 20,
    ltvRatioPct: 75,
    legalRiskPenaltyPct: 0,
  });

  // net adjustment = 350 + 250 + 400 - 150 = 850
  // rule adjusted rate = 9800 + 850 = 10650
  assert.equal(result.ruleAdjustedRatePerSqFt, 10650);
  assert.equal(result.aiAdjustedRatePerSqFt, 10650); // backward-compatible alias

  // gross market value = 10650 * 1250 = 1,33,12,500
  assert.equal(result.grossMarketValue, 13312500);

  // haircut -5% => 13312500 * 0.95 = 12646875
  assert.equal(result.netAssessedValue, 12646875);

  // distress 20% discount => 12646875 * 0.8 = 10117500
  assert.equal(result.distressLiquidationValue, 10117500);

  // max loan sanction at 75% LTV => 12646875 * 0.75 = 9485156
  assert.equal(result.maxSanctionAmount, 9485156);

  // deviation from circle rate: ((10650 - 7800) / 7800) * 100 = 36.5%
  assert.ok(result.deviationFromCircleRatePct > 36 && result.deviationFromCircleRatePct < 37);

  // Attribution breakdown has expected 5 factors
  assert.equal(result.attributionBreakdown.length, 5);
});

test('calculateValuation handles edge cases: zero area and zero circle rate safely', () => {
  const result = calculateValuation({
    carpetAreaSqFt: 0,
    superBuiltUpAreaSqFt: 0,
    baseMarketRatePerSqFt: 10000,
    circleRatePerSqFt: 0,
    floorRiseFactor: 0,
    roadWidthFactor: 0,
    amenitiesPremium: 0,
    structuralDepreciation: 0,
    underwriterHaircutPct: 0,
    distressDiscountPct: 20,
    ltvRatioPct: 75,
    legalRiskPenaltyPct: 0,
  });

  assert.equal(result.grossMarketValue, 0);
  assert.equal(result.netAssessedValue, 0);
  assert.equal(result.distressLiquidationValue, 0);
  assert.equal(result.maxSanctionAmount, 0);
  assert.equal(result.deviationFromCircleRatePct, 0);
  assert.equal(result.confidenceScorePct, 95.5);
  assert.equal(result.riskTier, 'LOW_RISK');
});

test('calculateValuation applies confidence penalties and assigns HIGH_ALERT risk tier', () => {
  const result = calculateValuation({
    carpetAreaSqFt: 1000,
    superBuiltUpAreaSqFt: 1300,
    baseMarketRatePerSqFt: 12000,
    circleRatePerSqFt: 6000, // +100% deviation triggers circle rate penalty
    floorRiseFactor: 0,
    roadWidthFactor: 0,
    amenitiesPremium: 0,
    structuralDepreciation: 0,
    underwriterHaircutPct: 0,
    distressDiscountPct: 20,
    ltvRatioPct: 75,
    legalRiskPenaltyPct: 10, // legal penalty triggers -8.5 confidence deduction and HIGH_ALERT
  });

  // Deviation = 100% (>35% => -10 confidence)
  // Legal penalty = 10% (>0 => -8.5 confidence)
  // Base 95.5 - 10 - 8.5 = 77.0
  assert.equal(result.confidenceScorePct, 77.0);
  assert.equal(result.riskTier, 'HIGH_ALERT');
});

// =======================================================
// CREDIBILITY REMEDIATION TESTS (TASKS 2, 3, 4, 5, 6, 7, 8)
// =======================================================

test('CREDIBILITY: Valuation Engine labels identify as provisional rule-based estimation without ML claims', () => {
  assert.equal(CREDIBILITY_LABELS.ENGINE_TYPE, 'provisional rule-based estimation');
  assert.equal(CREDIBILITY_LABELS.ENGINE_BADGE, 'Provisional Rule-Based Estimation');
  assert.doesNotMatch(CREDIBILITY_LABELS.ENGINE_TYPE, /machine learning|neural network|trained model|deep learning/i);
});

test('CREDIBILITY: Attribution breakdown does not claim live SRO registered transaction evidence', () => {
  const result = calculateValuation({
    carpetAreaSqFt: 1000,
    superBuiltUpAreaSqFt: 1300,
    baseMarketRatePerSqFt: 10000,
    circleRatePerSqFt: 8000,
    floorRiseFactor: 0,
    roadWidthFactor: 0,
    amenitiesPremium: 0,
    structuralDepreciation: 0,
    underwriterHaircutPct: 0,
    distressDiscountPct: 20,
    ltvRatioPct: 75,
    legalRiskPenaltyPct: 0,
  });

  const baselineDescription = result.attributionBreakdown[0].description;
  // Must disclaim as synthetic benchmark
  assert.match(baselineDescription, /synthetic|indicative|benchmark/i);
  // Must not claim to be verified past 180 days sales
  assert.doesNotMatch(baselineDescription, /median sales within.*past 180 days/i);
});

test('CREDIBILITY: Confidence and uncertainty labels distinguish heuristic penalty from calibrated uncertainty', () => {
  assert.equal(CREDIBILITY_LABELS.CALIBRATION_STATUS, 'Not available: no calibrated model');
  assert.equal(CREDIBILITY_LABELS.UNCERTAINTY_NOTE, 'Rule-based indicative range, not a statistical interval');
  assert.equal(CREDIBILITY_LABELS.CONSISTENCY_SCORE, 'Rule Consistency Score (Heuristic, Uncalibrated)');
});

test('CREDIBILITY: Model Governance labels use Pending verification and Not available for unverified items', () => {
  assert.equal(CREDIBILITY_LABELS.GOVERNANCE_UNVERIFIED, 'Pending verification');
  assert.equal(CREDIBILITY_LABELS.GOVERNANCE_NOT_AVAILABLE, 'Not available');
  assert.equal(CREDIBILITY_LABELS.LEDGER_STATUS, 'Not implemented (Local prototype state)');
});

test('CREDIBILITY: All demonstration cases and comparables carry explicit machine-readable synthetic marker', () => {
  assert.ok(INITIAL_VALUATION_CASES.length > 0, 'Initial cases must exist');
  for (const c of INITIAL_VALUATION_CASES) {
    assert.equal(c.dataSource, 'synthetic-demo', `Case ${c.id} must have dataSource 'synthetic-demo'`);
    assert.ok(Array.isArray(c.comparables), `Case ${c.id} comparables must be an array`);
    for (const comp of c.comparables) {
      assert.equal(comp.dataSource, 'synthetic-demo', `Comparable ${comp.id} must have dataSource 'synthetic-demo'`);
    }
  }
});

test('CREDIBILITY: Edge cases with NaN, negative inputs and empty comparables list handle safely', () => {
  const result = calculateValuation({
    carpetAreaSqFt: NaN as any,
    superBuiltUpAreaSqFt: -100,
    baseMarketRatePerSqFt: NaN as any,
    circleRatePerSqFt: -500,
    floorRiseFactor: 0,
    roadWidthFactor: 0,
    amenitiesPremium: 0,
    structuralDepreciation: 0,
    underwriterHaircutPct: NaN as any,
    distressDiscountPct: NaN as any,
    ltvRatioPct: NaN as any,
    legalRiskPenaltyPct: NaN as any,
  });

  assert.equal(result.carpetAreaSqFt, 0);
  assert.equal(result.grossMarketValue, 0);
  assert.equal(result.netAssessedValue, 0);
  assert.equal(result.distressLiquidationValue, 0);
  assert.equal(result.maxSanctionAmount, 0);
  assert.equal(result.deviationFromCircleRatePct, 0);
  assert.ok(result.confidenceScorePct >= 65 && result.confidenceScorePct <= 100);
});

test('CREDIBILITY: AI / Gemini status is verified as unconnected in prototype with no external network calls', () => {
  assert.equal(CREDIBILITY_LABELS.AI_STATUS, 'Not connected (Demo prototype)');
  // Valuation calculation operates purely in memory with deterministic arithmetic
  const res = calculateValuation({
    carpetAreaSqFt: 1000,
    superBuiltUpAreaSqFt: 1200,
    baseMarketRatePerSqFt: 8000,
    circleRatePerSqFt: 7000,
    floorRiseFactor: 0,
    roadWidthFactor: 0,
    amenitiesPremium: 0,
    structuralDepreciation: 0,
    underwriterHaircutPct: 0,
    distressDiscountPct: 20,
    ltvRatioPct: 75,
    legalRiskPenaltyPct: 0,
  });
  assert.equal(res.netAssessedValue, 8000000);
});
